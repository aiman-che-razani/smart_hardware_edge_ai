# SentinelDAQ engineering case study — implementation draft

## Problem

An existing Arduino Uno must acquire tank fill level from two independent
sensors alongside slower ambient measurements, stream those readings to a
Windows PC and respond to acknowledged health-state commands. The project
investigates acquisition quality and operational behavior rather than
treating a model accuracy score as the system.

## Implemented system

HC-SR04 (ultrasonic), a water-level module, a DHT temp/humidity module, a
thermistor and a photoresistor are separate C++ modules, each polled at its
own practical rate and assembled into one report per second — there is no
high-rate waveform, so no ISR/FIFO scheduling is needed. The binary and CSV
builds share one cooperative loop with bounded command parsing and alarm
service (the firmware drives the buzzer through a PN2222; the physical LED and
buzzer response has not been checked). The PC owns windowing,
slow-signal feature extraction (mean/slope/range/std per channel, plus a
two-sensor level-agreement feature) and inference. Parquet preserves raw
runs; SQLite indexes experiments and stores derived results. A read-only API
and a React web UI expose current and historical state.

The repository includes a byte-level simulator using the same frame codec as
the host parser, independent synthetic runs, grouped train/validation/test
manifests, model comparisons, fault injection and a standalone HTML export.

## Engineering trade-offs

- A DATA payload is 29 bytes, which is a 36-byte frame on the wire; with the
  17-byte STATUS frame (10-byte payload) that is about 53 bytes/s from the Uno,
  roughly 0.5% of 115200 baud's ~11520 bytes/s capacity. There was
  no bandwidth problem to design around here, unlike the original 800 Hz
  vibration brief this project started from (see
  [ADR-008](decisions/ADR-008-sensor-set-pivot.md)).
- Only the two sensors with real transient-failure modes (HC-SR04 echo
  timeout, DHT checksum failure) carry an age/validity flag; the three plain
  analog reads (water-level, thermistor, photoresistor) are always fresh by
  construction, so they don't need one.
- Two independent, cross-checking level sensors (ultrasonic + water-level
  module) turn "the two disagree" into a first-class anomaly signal
  (`SENSOR_MISMATCH`), not just redundancy for its own sake. So far this has only
  been exercised on synthetic data; on the real rig the two channels disagreed
  because of aiming and the probe's dry floor (below), not because of a
  demonstrated sensor fault.
- UNKNOWN is explicit after gaps and loss of contact. Persistent FAULT
  requires multiple windows. In firmware a FAULT alarm survives host silence (the
  3 s timeout only drops non-FAULT states to UNKNOWN), but any host SET_ALARM or
  CLEAR_ALARM overrides it and the host sends SET_ALARM(UNKNOWN) after a
  reconnect, so it is not a hard latch.
- Grouped run splits reduce leakage from overlapping windows. Synthetic
  models are explicitly blocked from physical inference.
- Tank geometry, the water-level module's ADC range and the thermistor's
  exact resistance/beta are all unmeasured placeholders in `pipeline.py`
  pending the real hardware — see `docs/hardware/design.md`.

## Evidence

The [evidence ledger](benchmarks/README.md) lists every number with its date, method
and raw file, and separates what was measured on the rig from what was measured in
simulation and what is only configured. The software checks are: 79 automated
tests passing on 2026-09-27 (79 after the security/data-integrity fixes, then 164
after adding the tests proposed by the `testing` agent's review the same day; 58
on 2026-09-18), and the `uno` firmware compiling to
7,212 bytes of flash (22%) and 394 bytes of static RAM (19%), which are compile-time
sizes and not runtime stack measurements. See
[verification results](benchmarks/software-verification.md) for the dated narrative.
Synthetic model scores demonstrate the training/evaluation code path only (a
held-out synthetic test of 30 windows gave 0.80 accuracy and 0.96 fault recall). They cannot support claims of diagnostic
accuracy, robustness to a real tank, safe fault detection or generalization.

## What the first hardware captures showed

Bring-up captures exist (2026-09-19/20 and 2026-09-23; see
[failures](failures/README.md)). They are engineering findings, not results: a
1 h capture streamed 3,598 samples in 3,600 s with no sequence gaps and no parser
errors, yet 38% of its samples had no valid ultrasonic echo (the firmware clears the
distance-valid flag when no echo returns within 25 ms; 38.9% of samples were flagged
invalid once DHT errors are counted), with dropout streaks up to 204 samples. The
5 h run did not show this (1 invalid echo in 18,155), so the dropouts are tied to
that session's aim or setup, and the cause is not established. Three early runs
read a median ~2.2 m, consistent with the sensor not being aimed at the tank. The
water probe sat at its dry floor (raw 5-15) for the whole ~5 h run, while the 1 h
run read hundreds, so the probe's behaviour is not yet understood either. The
thermistor (placeholder constants) and the DHT disagreed by about 5 C in both long
runs, with no reference thermometer to say which is right. Killed runs lost
buffered raw data: run `0ef6e2a5`'s samples are unrecoverable. In total, four
runs from 2026-09-19/20 hold 19,369 stored rows, and two more of that batch have
none. All runs are labelled NORMAL and uncalibrated, so they are not a dataset and
support no claim about diagnostic performance. Some of them also drove the
threshold score to WARNING or FAULT on labelled-NORMAL data; with placeholder
calibration that is not a measurable false-alarm rate.

What was fixed on 2026-09-27, and how far it is verified: raw data now flushes
every 30 s (a kill loses at most about 30 s, unit-tested but not tried with a real
hardware kill); `sentinel reconcile` closed the two runs left RUNNING; the
dashboard shows stale, "acquisition ended" and "API unreachable" states and a
SIMULATED / PHYSICAL / NO STATUS headline, so old NORMAL is not presented as live;
calibration is stored with each model and run and mismatches are refused; the
API rejects foreign Host headers and unverified model files. The dashboard changes
were built (`npm run build`) but not yet viewed in a browser, and the firmware
changes (named constants, packed struct) were compiled but not flashed. Open
findings from the same audit are listed in [audit-2026-09-27](audit-2026-09-27.md).

## Remaining portfolio evidence

Hardware identity and photos, final wiring schematic, physical dataset,
measured timing/resource headroom, physical confusion matrices, operational
false alarms/hour, a dashboard screenshot showing the PHYSICAL label, the real
LED/buzzer response and a demonstration video are all pending (none exists in the
repository today) — none of it
carries over from the pre-pivot motor design. Do not fill these gaps with
stock photos or simulated numbers presented as measurements. The next
engineering step is calibration: tape-measure the ultrasonic distance and the
tank's empty/full range, aim the sensor at the surface, measure the water probe's
dry/wet ADC values, then collect labelled runs (see
[ADR-011](decisions/ADR-011-calibration-approach.md)).

## Demo recording outline

1. Show the SIMULATED source label and architecture (a recording of a physical
   run must instead show the PHYSICAL label).
2. Run a 90-second real-time CYCLE simulation; point out the tank-level dip
   and the warning/fault/recovery transitions.
3. Show the tank-level/agreement chart, DHT/thermistor/light chart and
   historical run comparison.
4. Inject corrupt frames and show gaps/reset windows without invented continuity.
5. Open model split manifest and synthetic evaluation report; explain why these
   are integration tests rather than a real tank-performance result.
6. Show Uno build resource sizes and list the physical measurements still needed.
