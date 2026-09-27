# Architecture decision records

Status: accepted direction for Phase 0; all performance claims require measurement.
ADR-001 to ADR-006 exist only as the table rows below (no separate files);
ADR-007 onward have their own files.

| ADR | Decision | Reason / consequence |
|---|---|---|
| 001 | Existing Uno / ATmega328P | Uses available hardware and exposes resource engineering; small buffers and host windows required |
| 002 | SPI for ADXL345 | Dedicated high-rate interface with data-ready/FIFO investigation; costs pins and requires voltage verification. **Superseded by ADR-008** (no SPI remains) |
| 003 | Host-side ML | PC holds windows and scientific tooling; USB/host availability becomes an operational dependency |
| 004 | Parquet + SQLite first | Efficient raw files and simple transactional metadata; coordinate file finalization with metadata and avoid pretending they form one transaction. Details in [ADR-010](ADR-010-storage-layout.md) |
| 005 | Group splits by run_id | Correlated overlapping windows otherwise leak physical-run information; fewer independent groups may limit evaluation |
| 006 | CSV bring-up then binary | Readability first; binary needed for bandwidth and robust integrity checks; maintain explicit versions. Binary format in [ADR-009](ADR-009-serial-protocol-v1.md) |
| 007 | Implement all software now, keep physical acceptance gates | See [ADR-007](ADR-007-simulation-and-acceptance.md) |
| 008 | Pivot sensor set to tank/environmental monitoring | Owned hardware didn't match the ADXL345/INA219/DS18B20/motor BOM; see [ADR-008](ADR-008-sensor-set-pivot.md). Supersedes ADR-002 — no SPI/I2C/OneWire remains in the design |
| 009 | Serial wire protocol v1: length+CRC-16 framed binary, one command in flight with ACK/retry | See [ADR-009](ADR-009-serial-protocol-v1.md). Integrity and bounded resync rather than bandwidth; alarm is not a hard latch; real-hardware command/reset behaviour untested |
| 010 | Storage layout: SQLite metadata + Parquet chunks, file first then manifest, no migration framework | See [ADR-010](ADR-010-storage-layout.md). Crash leaves orphans not partial references; 30 s time-based flush; killed runs are marked INTERRUPTED by `sentinel reconcile`; `PRAGMA user_version` schema version |
| 011 | Calibration approach: labelled placeholders, measured constants recorded with the run and the model artifact | See [ADR-011](ADR-011-calibration-approach.md). No calibration has actually been *measured* yet (still placeholders); as of 2026-09-27 the four distance/water constants plus the thermistor constants are recorded in run metadata and the model artifact, and a run/model calibration mismatch is refused; procedure for dry/wet ADC and tank empty/full distance |

Alternatives deferred: replacing Uno before measuring its limits, I2C high-rate
vibration, embedded window-based ML, PostgreSQL services and random window splits.
