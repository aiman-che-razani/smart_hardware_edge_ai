# ADR-010 — Storage layout: SQLite metadata plus Parquet raw chunks, file first, manifest second

Status: accepted (refines ADR-004); implemented in
`python/sentinel/storage/database.py`. The schema version, the time-based flush and
`reconcile` were added on 2026-09-27 and are covered by `tests/test_storage.py`.

## Decision

Each `--data <dir>` is a self-contained store:

- `sentinel.sqlite` (WAL, foreign keys on) holds `experiment_run` (metadata JSON and
  status), `raw_chunk` (manifest: path, run, row count, first/last sequence),
  `feature_window`, `prediction`, `event` and `model`, with run/time indexes.
- Raw samples live in immutable Parquet chunks under `raw/<run_id>/`, compressed with
  zstd. Samples are buffered in memory and a chunk is written every 30 seconds
  (`FLUSH_SECONDS`) or at 1,600 rows (`FLUSH_ROWS`), whichever comes first, and at
  clean close. The original rows-only threshold lost data on a kill (see
  [failures](../failures/README.md)); the cost of the timer is many small chunks
  (about 120 per hour), which the API reads newest-first until it has enough rows.
- **Ordering:** write `<uuid>.partial`, atomically rename to `.parquet`, then insert
  the `raw_chunk` row and commit. A crash between rename and commit leaves an
  orphan file, never a manifest row pointing at a partial file. `audit` lists
  orphans, missing files, `.partial` files and runs still `RUNNING`, and never
  deletes anything. The two stores are not one transaction and are not presented as
  such.
- `status.json` is a best-effort live snapshot written via `status.partial` and an
  atomic replace; a locked file skips that snapshot rather than stopping
  acquisition.
- **Versioned schema, no migration framework.** The schema is created with
  `CREATE TABLE IF NOT EXISTS` and `SCHEMA_VERSION` is stamped in `PRAGMA
  user_version`. Schema changes are handled explicitly rather than implicitly: a
  column change bumps the version and ships a real migration keyed on the old number
  (or uses a fresh data directory), never an in-place edit that older databases
  silently miss.
- Run metadata records source, protocol/firmware version, baud, the four calibration
  constants, window settings and operator metadata (see
  [ADR-011](ADR-011-calibration-approach.md)). Raw data and models stay in the
  git-ignored `data/`; curated evidence is committed under `docs/benchmarks`.

## Consequences

- Reads of finished runs are simple SQL plus Parquet, and readers (the API) need no
  writer coordination beyond WAL. One acquisition writer per data directory.
- A killed process leaves its run `RUNNING` until `sentinel --data <dir> reconcile`
  marks it `INTERRUPTED` and closes its open events (observed twice; both rows were
  reconciled on 2026-09-27 after taking SQLite backups). At most the last 30 s of
  raw rows are lost on a kill, but runs killed before the change (e.g. `0ef6e2a5`)
  lost far more and it is unrecoverable. Derived windows in SQLite can outlive their
  raw rows by up to that interval.
- Existing databases were created without a stored schema version: an unstamped
  database is treated as version 1 and stamped on first open, a database newer than
  the code is refused, and any column change must ship a real migration keyed on the
  number (an old-layout database test exists).
- All inserts name their columns, so column order no longer couples the code to the
  layout.
- Separate directories per purpose (physical, demo, research) avoid mixing
  synthetic and physical data but mean the API serves one directory at a time.
