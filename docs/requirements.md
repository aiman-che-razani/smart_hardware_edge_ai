# SentinelDAQ V1 engineering specification

> Historical Phase 0 specification. Current implementation and verification status:
> [operating guide](OPERATING-GUIDE.md), [phase coverage](PHASE-STATUS.md).

## Objective and scope

Monitor a guarded small rotating machine using an ATmega328P Uno and a Windows
host. Acquire vibration, current and temperature at independent rates; preserve
measurement provenance; infer condition on the PC; return acknowledged alarm
commands. The alarm is advisory, not a machine protection or emergency-stop system.
Phase 0 provides specifications and environment checks only.

## Functional requirements

| ID | Requirement | Verification phase / evidence |
|---|---|---|
| F01 | Detect/configure ADXL345 over SPI; expose raw XYZ and configuration | 1: device ID, register readback, six orientations |
| F02 | Target 800 Hz acceleration, 20–50 Hz current, 1 Hz temperature independently | 2/4: rate, interval and overrun records |
| F03 | Attach device time, sequence, sensor validity and freshness information | 3/4: reset, rollover and stale-data tests |
| F04 | Support readable CSV first, then framed binary with CRC16 and recovery | 1/3: golden packets, corruption/truncation tests |
| F05 | Receive commands with IDs; ACK or report errors; handle duplicates | 3/10: retry and ACK-loss tests |
| F06 | Host acquisition owns serial, timestamps receipt, detects gaps/resets, reconnects and shuts down cleanly | 5: disconnect/reset/long-run tests |
| F07 | Store raw runs in Parquet and metadata/events in SQLite | 5/11: round-trip, interrupted-write and schema tests |
| F08 | Independently test preprocessing, overlapping windows, FFT and physical features | 6: known synthetic signal tests |
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
| N08 | Proposed 800 Hz transport average utilization <=70%; revise after measurement | encoded byte counts and throughput test |
| N09 | Provisional Phase 2 mean rate within 1% of configured ODR over 60 s, with all observed loss reported | measured rate and loss; failure triggers design review |

Jitter, long-run loss, false-alarm and inference-latency acceptance limits must be
set from the rig and operational requirements before their respective experiments.
They are unresolved requirements, not claimed performance.

## Explicit assumptions and open questions

- Board is Uno R3 compatible with ATmega328P at 16 MHz, not Uno R4.
- Exact ADXL345 breakout schematic, regulator and level shifting are unknown.
  Voltage compatibility must be verified before connecting it.
- Motor is a low-power 6–12 V brushed DC unit with a guarded fixture. Rated/stall
  current, supply rating, shunt rating and mounting remain to be confirmed.
- USB serial adapter/driver and COM port are unknown. Opening the port may reset Uno.
- Python 3.9.0 was found locally; it can run the scaffold. Prefer a maintained
  Python 3.11/3.12 environment before adding the scientific stack.
- No RPM sensor initially; frequency peaks alone cannot establish shaft order.
- Initial 1 s / 50% overlap windows and dataset sizes are experimental starting points.
- Hardware purchase costs and availability have not been established.

## Phase 0 acceptance

Specification, pin/power proposal, risks and Phase 1 criteria are documented;
Git has the intended origin; isolated Python package runs; Uno smoke firmware
compiles. Hardware-specific uncertainties remain explicit gates before wiring.
Record actual checks in `benchmarks/README.md`. Stop here before Phase 1.
