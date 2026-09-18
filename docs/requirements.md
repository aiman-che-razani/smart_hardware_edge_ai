# SentinelDAQ V1 engineering specification

> Historical Phase 0 specification. Current implementation and verification status:
> [operating guide](OPERATING-GUIDE.md), [phase coverage](PHASE-STATUS.md).

## Objective and scope

Monitor a small water tank and its ambient environment using an ATmega328P Uno
and a Windows host. Acquire tank level from two independent sensors, ambient
temperature/humidity, thermistor and light readings at practical per-sensor
rates; preserve measurement provenance; infer condition on the PC; return
acknowledged alarm commands. The alarm is advisory, not a safety-critical
shutoff system. Phase 0 provides specifications and environment checks only.

## Functional requirements

| ID | Requirement | Verification phase / evidence |
|---|---|---|
| F01 | Detect/configure HC-SR04 (trig/echo), water-level, thermistor and photoresistor analog channels, and DHT temp/humidity; expose raw readings and validity | 1: echo timing, ADC readback, DHT checksum tests |
| F02 | Target ~150 ms ultrasonic ping interval, ~2 s DHT interval, instant analog reads, assembled into one DATA frame/second | 2/4: interval and staleness records |
| F03 | Attach device time, sequence, sensor validity and freshness information | 3/4: reset, rollover and stale-data tests |
| F04 | Support readable CSV first, then framed binary with CRC16 and recovery | 1/3: golden packets, corruption/truncation tests |
| F05 | Receive commands with IDs; ACK or report errors; handle duplicates | 3/10: retry and ACK-loss tests |
| F06 | Host acquisition owns serial, timestamps receipt, detects gaps/resets, reconnects and shuts down cleanly | 5: disconnect/reset/long-run tests |
| F07 | Store raw runs in Parquet and metadata/events in SQLite | 5/11: round-trip, interrupted-write and schema tests |
| F08 | Independently test preprocessing, overlapping windows and physical (slow-signal) features | 6: known synthetic signal tests |
| F09 | Create independent labelled physical runs with unique run_id | 7: run checklist and provenance audit |
| F10 | Split by run_id into train/validation/test; fit preprocessing only on training data | 8: disjoint-group assertions and frozen test manifest |
| F11 | Compare thresholds and progressively more complex models using operational metrics | 8: recorded model comparisons |
| F12 | Produce NORMAL/WARNING/FAULT with configurable persistence and hysteresis | 9: transition tests |
| F13 | Drive acknowledged LED/buzzer alarms with retry-safe commands | 10: disconnect, duplicate and physical activation tests |
| F14 | Present live/historical measurements, predictions and DAQ health | 11: API/dashboard integration checks |

## Non-functional requirements

| ID | Requirement / initial target | Evidence |
|---|---|---|
| N01 | Respect 2 KB SRAM and usable bootloader-dependent flash; avoid heap allocation in firmware | build size plus runtime stack/headroom investigation |
| N02 | Sampling must not silently block behind serial or slow sensors | interval distribution, FIFO/queue overflow counters |
| N03 | Bound all buffers and parser lengths; reject invalid data explicitly | oversized/malformed-input tests |
| N04 | Keep host acquisition separate from processing/inference/storage | module interfaces and slow-consumer tests |
| N05 | Reproduce runs with firmware/config/protocol/model versions and units | metadata audit |
| N06 | No invented benchmark figures; distinguish sensor time from host receipt time | benchmark ledger with method and raw evidence |
| N07 | Use one-process/simple local infrastructure first | Parquet + SQLite; no services in Phase 0 |
| N08 | ~29-byte DATA frame once/second is far below the 115200-baud transport budget; revisit only if a future sensor materially raises the rate | encoded byte counts and throughput test |
| N09 | Provisional Phase 2 mean report rate within 1% of the configured 1 Hz over 60 s, with all observed loss reported | measured rate and loss; failure triggers design review |

Jitter, long-run loss, false-alarm and inference-latency acceptance limits must be
set from the rig and operational requirements before their respective experiments.
They are unresolved requirements, not claimed performance.

## Explicit assumptions and open questions

- Board is Uno R3 compatible with ATmega328P at 16 MHz, not Uno R4.
- Exact water-level module characteristics (dry/wet ADC range) are unknown and
  must be measured before trusting `pipeline.py`'s calibration defaults.
- Exact thermistor part (resistance, beta) is unknown; the NTC beta approximation
  in `pipeline.py` uses placeholder constants pending the real datasheet.
- DHT module variant (DHT11 vs DHT22) is unknown; firmware defaults to DHT11
  scaling — confirm against the physical part's markings, see hardware/design.md.
- Tank geometry (empty/full sensor-to-surface distance) is unknown; calibrate
  `--distance-empty-mm`/`--distance-full-mm` against the real tank before
  trusting level percentages.
- USB serial adapter/driver and COM port are unknown. Opening the port may reset Uno.
- Python 3.9.0 was found locally; it can run the scaffold. Prefer a maintained
  Python 3.11/3.12 environment before adding the scientific stack.
- Initial 30 s / 50% overlap windows and dataset sizes are experimental starting points.
- Hardware purchase costs and availability have not been established.
- Stepper motor and IR receiver module are owned but explicitly deferred — not
  wired or coded in this revision; see ADR-008.

## Phase 0 acceptance

Specification, pin/power proposal, risks and Phase 1 criteria are documented;
Git has the intended origin; isolated Python package runs; Uno smoke firmware
compiles. Hardware-specific uncertainties remain explicit gates before wiring.
Record actual checks in `benchmarks/README.md`. Stop here before Phase 1.
