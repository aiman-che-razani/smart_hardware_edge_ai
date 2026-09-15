# Experimental data policy (design only)

No physical dataset exists yet. In Phase 7 create a unique run_id for each
independent setup/run. Record machine ID, UTC start/end, condition, fault type and
severity, motor setting, operator notes, firmware/protocol/configuration versions,
configured and measured rates, sensor mounting and calibration.

Raw records retain host/device time, session, sequence, run_id, raw XYZ,
current/temperature and validity/freshness. Preserve units and conversion metadata.
Store Parquet outside Git with SQLite run metadata; features/predictions reference
run/window/model IDs. Define schema keys/indexes when storage is implemented.

Aim initially at multiple independent 60–120 s runs per major condition; revise
counts based on repeatability. Safe conditions and operating envelope need review
before powered experiments. Keep all windows from each run in one dataset split;
freeze the final test run manifest before model development.
