# Phase coverage and remaining acceptance

Software implementation across phases was authorized after Phase 0. User selected
simulation; no physical experiment is claimed complete.

| Phase | Implemented / verified software | Remaining physical or research acceptance |
|---|---|---|
| 0 Foundation | Specification, Git origin, environment, architecture | Confirm real BOM/module identity |
| 1 Vibration slice | SPI ID/config driver, 100 Hz CSV firmware/parser | Wire, upload, six orientations, scale verification |
| 2 DAQ | Sensor ODR/FIFO polling, bounded service, timestamp/gap diagnostics | Measure actual rate/jitter; assess interrupt/FIFO service design |
| 3 Transport | V0/V1, CRC, bounded resync, commands/ACK retries | Sustained USB throughput, physical reset/disconnect |
| 4 Complete sensing | INA219, async DS18B20, freshness, LEDs/buzzer | Verify shunt/temperature calibration and safe output drive |
| 5 Python DAQ | Serial owner thread, bounded queues, reconnect, logging, Parquet/SQLite | Long hardware soak and driver-specific failures |
| 6 DSP | DC removal, Hann/FFT, moments/bands/harmonics, overlap, plots | Rig spectra, mounting repeatability, aliasing assessment |
| 7 Dataset | Run metadata/storage, independent synthetic runs | Controlled safe physical runs and labels |
| 8 ML | Grouped partitions, model ladder, frozen test workflow, model artifact | Physical model comparison/calibration, operating limits |
| 9 Live inference | Threshold/model scoring, persistence/recovery, UNKNOWN | Tune against physical false alarms and latency |
| 10 Closed loop | ACK/retry/idempotency, simulated alarm integration | Verify actual LED/buzzer response and watchdog |
| 11 API/UI | Read-only FastAPI/WebSocket, Dash monitoring/explorer | User review on live rig |
| 12 Verification | Unit/integration/fault tests, generated-data stress, evidence scripts | Hardware timing, resource headroom, synchronized T0–T7 |
| 13 Portfolio | Runnable demo, case-study draft, standalone plots, evidence ledger | Real photos/schematic/video and measured engineering findings |
| 14 Optional edge | Separate compiled streaming threshold variant | Measure inference timing/power and compare meaningful equivalent tasks |

## Validation sequence when hardware arrives

Use Phase 1 criteria first, then validate phases 2–4 before collecting a dataset.
Record failing and passing runs; do not train on unreliable acquisition. Establish
run-group train/validation/test splits before model development. Finish operational
tests before presenting the system as a physical diagnostic success.

## Known limitations

- Sensor timestamps are FIFO readout times. Polling and 1-Wire activity affect
  arrival intervals; uniform true-conversion timestamps are not measured.
- Full FIFO overflow flags indicate incomplete signal history; exact sensor-loss
  counts cannot be inferred. Firmware has no runtime stack watermark yet.
- Invalid windows are discarded. The system does not resample irregular data.
- API history is bounded and local; there is no authentication/deployment setup.
- Alarm output is advisory. Motor power/control is outside this software.
- Edge variant detects four consecutive large raw X samples; it is orientation
  sensitive and is not equivalent to host window RMS or a trained classifier.
- A physical trained model does not exist. Synthetic classification scores reflect
  deliberately separable generated signals and are not evidence of generalization.
