# Phase coverage and remaining acceptance

Software implementation across phases was authorized after Phase 0. User selected
simulation; no physical experiment is claimed complete. The sensor set was
pivoted from motor/vibration monitoring to tank/environmental monitoring — see
[ADR-008](decisions/ADR-008-sensor-set-pivot.md). **No physical acceptance from
the old ADXL345/INA219/DS18B20 BOM carries over**; every phase below must be
re-earned against the actual hardware.

| Phase | Implemented / verified software | Remaining physical or research acceptance |
|---|---|---|
| 0 Foundation | Specification, Git origin, environment, architecture | Confirm real module identity for all five sensors |
| 1 Ultrasonic slice | HC-SR04 trig/echo driver, CSV firmware/parser | Wire, upload, verify distance readings against a tape measure |
| 2 DAQ | Cooperative per-sensor polling, bounded service, timestamp/staleness diagnostics | Measure actual echo timing/jitter; confirm DHT read reliability |
| 3 Transport | V0/V1, CRC, bounded resync, commands/ACK retries | Sustained USB throughput, physical reset/disconnect |
| 4 Complete sensing | Water-level/thermistor/photoresistor analog reads, DHT, LEDs/PN2222 buzzer | Measure water-level module's dry/wet ADC range and thermistor's real resistance/beta |
| 5 Python DAQ | Serial owner thread, bounded queues, reconnect, logging, Parquet/SQLite | Long hardware soak and driver-specific failures |
| 6 DSP | Slow-signal mean/slope/range/std per channel, two-sensor agreement feature, overlap | Real tank fill/drain curves, sensor noise characterization |
| 7 Dataset | Run metadata/storage, independent synthetic runs | Controlled safe physical runs and labels |
| 8 ML | Grouped partitions, model ladder, frozen test workflow, model artifact | Physical model comparison/calibration, operating limits |
| 9 Live inference | Threshold/model scoring, persistence/recovery, UNKNOWN | Tune against physical false alarms and latency |
| 10 Closed loop | ACK/retry/idempotency, simulated alarm integration | Verify actual LED/buzzer response through the PN2222 and watchdog |
| 11 API/UI | Read-only FastAPI/WebSocket, Dash monitoring/explorer | User review on the live tank |
| 12 Verification | Unit/integration/fault tests, generated-data stress, evidence scripts | Hardware timing, resource headroom, synchronized T0–T7 |
| 13 Portfolio | Runnable demo, case-study draft, standalone plots, evidence ledger | Real photos/schematic/video and measured engineering findings |
| 14 Deferred | Stepper motor and IR receiver reserved pins only (D9–D12, A3) | Not designed or wired this revision; see ADR-008 |

## Validation sequence when hardware arrives

Use Phase 1 criteria first, then validate phases 2–4 before collecting a dataset.
Record failing and passing runs; do not train on unreliable acquisition. Establish
run-group train/validation/test splits before model development. Finish operational
tests before presenting the system as a physical diagnostic success.

## Known limitations

- Sensor timestamps are host-assembly (`millis()`) time, not per-sensor
  conversion time. Polling and DHT activity affect arrival intervals.
- Invalid windows are discarded. The system does not resample irregular data.
- API history is bounded and local; there is no authentication/deployment setup.
- Alarm output is advisory only.
- A physical trained model does not exist. Synthetic classification scores reflect
  deliberately separable generated signals and are not evidence of generalization.
- Water-level module dry/wet range, thermistor resistance/beta, DHT11-vs-DHT22
  scaling, and tank empty/full distance are all unmeasured placeholders — see
  requirements.md's assumptions section and hardware/design.md.
