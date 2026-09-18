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
service (the buzzer now driven through a PN2222). The PC owns windowing,
slow-signal feature extraction (mean/slope/range/std per channel, plus a
two-sensor level-agreement feature) and inference. Parquet preserves raw
runs; SQLite indexes experiments and stores derived results. A read-only API
and Dash dashboard expose current and historical state.

The repository includes a byte-level simulator using the same frame codec as
the host parser, independent synthetic runs, grouped train/validation/test
manifests, model comparisons, fault injection and a standalone HTML export.

## Engineering trade-offs

- A 29-byte data frame once per second is roughly 40-50 bytes/s including
  STATUS — trivial against 115200 baud's ~11520 bytes/s capacity. There was
  no bandwidth problem to design around here, unlike the original 800 Hz
  vibration brief this project started from (see
  [ADR-008](decisions/ADR-008-sensor-set-pivot.md)).
- Only the two sensors with real transient-failure modes (HC-SR04 echo
  timeout, DHT checksum failure) carry an age/validity flag; the three plain
  analog reads (water-level, thermistor, photoresistor) are always fresh by
  construction, so they don't need one.
- Two independent, cross-checking level sensors (ultrasonic + water-level
  module) turn "the two disagree" into a first-class anomaly signal
  (`SENSOR_MISMATCH`), not just redundancy for its own sake.
- UNKNOWN is explicit after gaps and loss of contact. Persistent FAULT
  requires multiple windows; a hardware alarm remains latched if the host
  disappears.
- Grouped run splits reduce leakage from overlapping windows. Synthetic
  models are explicitly blocked from physical inference.
- Tank geometry, the water-level module's ADC range and the thermistor's
  exact resistance/beta are all unmeasured placeholders in `pipeline.py`
  pending the real hardware — see `docs/hardware/design.md`.

## Evidence

See [verification results](benchmarks/software-verification.md) for actual test,
compile and software timing observations. Synthetic model scores demonstrate the
training/evaluation code path only. They cannot support claims of diagnostic
accuracy, robustness to a real tank, safe fault detection or generalization.

## Remaining portfolio evidence

Hardware identity and photos, final wiring schematic, physical dataset,
measured timing/resource headroom, physical confusion matrices, operational
false alarms/hour and a demonstration video are all pending — none of it
carries over from the pre-pivot motor design. Do not fill these gaps with
stock photos or simulated numbers presented as measurements. The next
engineering step is wiring the HC-SR04 and confirming distance readings
against a tape measure (Phase 1), followed by the remaining sensors.

## Demo recording outline

1. Show the SIMULATED source label and architecture.
2. Run a 90-second real-time CYCLE simulation; point out the tank-level dip
   and the warning/fault/recovery transitions.
3. Show the tank-level/agreement chart, DHT/thermistor/light chart and
   historical run comparison.
4. Inject corrupt frames and show gaps/reset windows without invented continuity.
5. Open model split manifest and synthetic evaluation report; explain why these
   are integration tests rather than a real tank-performance result.
6. Show Uno build resource sizes and list the physical measurements still needed.
