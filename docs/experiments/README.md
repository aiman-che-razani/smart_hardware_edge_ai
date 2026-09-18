# Experimental data policy (design only)

No physical dataset exists yet. In Phase 7 create a unique run_id for each
independent setup/run. Record machine ID, UTC start/end, condition, tank fill
state, operator notes, firmware/protocol/configuration versions, configured
and measured report rate, sensor placement and calibration (tank empty/full
distance, water-level module dry/wet range).

Raw records retain host/device time, session, sequence, run_id, raw distance/
water-level/thermistor/light/DHT readings and validity/freshness. Preserve
units and conversion metadata. Store Parquet outside Git with SQLite run
metadata; features/predictions reference run/window/model IDs. Define schema
keys/indexes when storage is implemented.

Aim initially at multiple independent 90+ s runs per major condition (long
enough to fill at least one 30 s window); revise counts based on repeatability.
Safe conditions and operating envelope need review before powered experiments.
Keep all windows from each run in one dataset split; freeze the final test run
manifest before model development.
