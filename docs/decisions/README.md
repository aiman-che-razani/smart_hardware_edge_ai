# Architecture decision records

Status: accepted direction for Phase 0; all performance claims require measurement.

| ADR | Decision | Reason / consequence |
|---|---|---|
| 001 | Existing Uno / ATmega328P | Uses available hardware and exposes resource engineering; small buffers and host windows required |
| 002 | SPI for ADXL345 | Dedicated high-rate interface with data-ready/FIFO investigation; costs pins and requires voltage verification |
| 003 | Host-side ML | PC holds windows and scientific tooling; USB/host availability becomes an operational dependency |
| 004 | Parquet + SQLite first | Efficient raw files and simple transactional metadata; coordinate file finalization with metadata and avoid pretending they form one transaction |
| 005 | Group splits by run_id | Correlated overlapping windows otherwise leak physical-run information; fewer independent groups may limit evaluation |
| 006 | CSV bring-up then binary | Readability first; binary needed for bandwidth and robust integrity checks; maintain explicit versions |

Alternatives deferred: replacing Uno before measuring its limits, I2C high-rate
vibration, embedded window-based ML, PostgreSQL services and random window splits.
