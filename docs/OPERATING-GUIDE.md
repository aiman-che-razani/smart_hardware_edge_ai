# SentinelDAQ operating guide

## Current scope

The user authorized implementation across phases and selected simulation until
hardware details are available. Software paths are implemented and exercised
against generated data. The Uno binary firmware has since been uploaded and
bring-up captures exist (see [Hardware bring-up](#hardware-bring-up-in-progress)),
but they are uncalibrated and are not a dataset; physical phase acceptance is
pending. The original phase-by-phase brief and
Phase 0 documents remain historical design records. This guide describes current
commands and behavior and supersedes their scaffold-only instructions.

## Quick start (PowerShell, repository root)

```powershell
Set-Location 'C:\Users\nadee\Documents\smart_hardware_edge_ai'
.\.venv\Scripts\python.exe -m sentinel --data data/demo simulate --seconds 60 --realtime
```

While that runs, open another terminal:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo api
```

FastAPI's interactive Swagger page is served at **http://127.0.0.1:8000/docs**
(not under `/api/`). Known issue: under the current venv (Python 3.9.0, fastapi
0.124.4, starlette 0.49.3, pydantic 2.13.5) OpenAPI generation fails, so
`/openapi.json` returns HTTP 500 and the Swagger page cannot load its spec
(observed 2026-09-23 on the older fastapi 0.119.1; the same failure was
reconfirmed 2026-09-27 after upgrading to 0.124.4/starlette 0.49.3, so it is not
the FastAPI/Starlette version — `app.openapi()` called in-process, without
starting a server, raised `AttributeError: '_SpecialForm' object has no attribute
'replace'` inside pydantic's `json_schema.py`, a pydantic/`typing` incompatibility
on Python 3.9.0). The endpoints themselves do not use that code path. Use the web
UI or `curl` against the endpoints below until the Python version is upgraded.
Read-only endpoints: `/api/health`, `/api/machines`, `/api/measurements`,
`/api/features`, `/api/predictions`, `/api/events`, `/api/experiments`,
`/api/system/status`; WebSocket `/api/live` publishes status each second.
Binds to loopback. Only one acquisition writer may use a given data directory.

### Data directories are separate stores; start the API per directory

The global `--data <dir>` option (given before the subcommand) selects a
self-contained store: `sentinel.sqlite`, `raw/` Parquet chunks, `status.json` and
the per-run `<run_id>-summary.json` files. `sentinel api` serves **exactly one**
data directory, and `status.json` (live state) is per directory too. To view
`data/physical` start `sentinel --data data/physical api`; the demo API on
`data/demo` will not show it. To run two APIs at once give each its own `--port`
(`api --port 8001`). Keep physical captures and synthetic runs in separate
directories, as the repository does (`data/physical`, `data/physical_check`,
`data/demo`, `data/research`, ...). Port 8000 must be free: an unrelated process
already listening there (an unrelated `python -m http.server` was found holding
it during bring-up) means the browser shows that process, not this API; check
what owns the port or pass a different `--port`.

### Web UI (React, at `/`)

The same `sentinel api` process also serves the web UI, once it's built:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Then open **http://127.0.0.1:8000** — the dashboard shows SIMULATED/PHYSICAL, a
state, DAQ counters, six current-reading tiles (raw + converted, per sensor,
updated every second regardless of Parquet flush timing), tank-level traces
from both sensors, DHT/thermistor/light charts, risk-score history and events.
Select another run to compare against. Finished/stale acquisition displays
UNKNOWN rather than presenting old NORMAL as live health. Historical data
remains accessible.

For active frontend development instead (hot reload), run `npm run dev` in
`frontend/` (separate terminal, port 5173) while `sentinel api` is running —
Vite proxies `/api/*` through to it. Rebuild (`npm run build`) when you're done
so `sentinel api` serves the updated version directly.

## Environment from scratch

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
$env:PLATFORMIO_CORE_DIR = Join-Path (Get-Location) '.pio'
.\.venv\Scripts\python.exe -m platformio run --project-dir firmware -e uno -e uno_csv
```

Dependencies: PySerial owns the serial port; NumPy performs the slow-signal
feature math; PyArrow stores columnar raw data; scikit-learn/joblib train and
persist small models; FastAPI/Uvicorn provide the local API (Starlette is pinned to
0.49.1 or newer, which fixes a `StaticFiles` Range-header denial of service); Plotly
renders the standalone HTML report (optional: the `report` extra, also part of `dev`);
the web UI is the React app in `frontend/` (Dash is not used by any
code and is not a declared dependency, even though it may still be installed in an
older venv). SQLite is in Python's standard library. Firmware uses
the SimpleDHT library for the DHT sensor; no SPI/I2C/OneWire remains in the
design. No distributed infrastructure is required. Use Python 3.9.1 or newer: on
3.9.0 (the version this venv was first built with) pydantic cannot build the OpenAPI
schema, so `/openapi.json` returns 500 and `/docs` cannot load; the API logs a
warning at startup on that version.

## Synthetic research workflow

Keep labelled research runs separate from changing-condition CYCLE demos.

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/research-new dataset --runs 5 --seconds 90
.\.venv\Scripts\python.exe -m sentinel --data data/research-new train --simulated --output data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/research-new evaluate --model-dir data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/ml-demo simulate --seconds 90 --model data/models/new-model/model.joblib
```

`train` writes `model.joblib` together with `model.joblib.sha256`; `evaluate` and
`simulate/acquire --model` refuse a model whose file does not match that recorded
hash, because a joblib file is a pickle and loading one executes code. The model
artifact also records the calibration it was trained under, and a run whose
calibration differs is refused. Models trained before 2026-09-27 have neither and
must be retrained.

These commands create explicitly synthetic NORMAL, LOW_WATER, OVERFLOW,
RAPID_DRAIN, SENSOR_MISMATCH and ENVIRONMENTAL_ANOMALY signals. `--seconds`
must be at least the window size (30s by default) for a run to produce even
one feature window — 90s gives a couple. They test integration, not diagnostic
accuracy on a real tank. Other simulator conditions are available through
`simulate --condition`. Synthetic ambient/thermistor/light values are simple
illustrative baselines, not a thermal/hydraulic model.

Training defaults to PHYSICAL records. `--simulated` is mandatory for synthetic
training, and physical inference refuses synthetic artifacts. Models are local
joblib files: load only trusted artifacts, since deserialization executes Python.
An output directory must be new to prevent accidental overwrite of provenance.

Run IDs are split as whole groups, stratified by condition; at least three runs
per class are required, preferably ten or more for physical research. Default
split is approximately 60/20/20. StandardScaler fits inside each training
pipeline; Isolation Forest sees only NORMAL training data. Validation compares
thresholds, logistic regression, a shallow tree, a random forest and Isolation
Forest. Automatic selection among supervised candidates ranks fault recall,
false positives, then simplicity. Review per-class results before deployment.
XGBoost is intentionally deferred until evidence justifies another dependency.

The final test partition stays unused by training. Explicit `evaluate` writes one
test report and refuses overwriting it. Dataset fingerprints reject mutations
after model/split freeze. This protects accidental workflow mistakes; it is not
a security boundary preventing a researcher from deliberately changing files.

## Acquisition and tuning

```powershell
# Fault injection through actual byte parser:
.\.venv\Scripts\python.exe -m sentinel --data data/failures simulate --seconds 60 --drop-every 20 --corrupt-every 30
# Change window and operational thresholds:
.\.venv\Scripts\python.exe -m sentinel --data data/tuning simulate --window-seconds 60 --overlap 0.5 --fault 0.85 --persistence 4
```

Features are slow-signal statistics per channel (tank level from both sensors,
DHT temp/humidity, thermistor, light): mean, linear slope (per second), range
and standard deviation over the window — no FFT, since nothing here is a
waveform. Two extra features target the two-sensor setup directly: the mean
and max absolute disagreement between the ultrasonic and water-level readings
(`level_agreement_abs_*`, feeds `SENSOR_MISMATCH`), and the steepest single-step
drop in the ultrasonic reading within the window (`level_ultrasonic_min_slope_
per_s`, feeds `RAPID_DRAIN` — a window-average slope alone would average a
brief steep drop away).

Default windows are 30 s with 50% overlap, updating every 15 s at the firmware's
fixed 1 Hz report rate — this adds latency to the initial window fill. Three
high-risk windows are required for FAULT; five low-risk windows for recovery.
Default threshold score (used when no trained model is loaded) is the mean
two-sensor level disagreement divided by 15 percentage points, clipped to
[0,1] — an uncalibrated engineering demo score, not a calibrated fault
probability.

Gaps, an invalid ultrasonic/water-level reading, disconnect and inconsistent
window time clear the window/state to UNKNOWN. DHT readings older than 4s are
treated as invalid; the plain analog reads (water-level, thermistor,
photoresistor) are always fresh by construction, since they're read fresh
each report cycle.

## Storage, evidence and reports

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo audit
.\.venv\Scripts\python.exe -m sentinel --data data/demo analyze
.\.venv\Scripts\python.exe -m sentinel --data data/demo report --output data/reports/sentinel-report.html
.\.venv\Scripts\python.exe -m sentinel --data data/benchmark-new benchmark --seconds 60
.\.venv\Scripts\python.exe -m sentinel profile --output data/reports/host-profile.json
```

The report is a standalone Plotly HTML file (tank-level and DHT charts for one run). `analyze` reports readout rate,
interval/jitter statistics and event-based false alarms/hour only for labelled
NORMAL runs. Simulation time is generated; its perfect rate is not hardware
evidence. The benchmark runs as fast as possible by default: `60` means sixty
seconds of generated signal, not sixty seconds of wall-clock soak testing.
Use `simulate --seconds 3600 --realtime` for a one-hour PC soak.
`profile` measures repeated feature/inference calls and traced Python allocation
peak; tracing perturbs timings and does not report full process RSS.

SQLite contains experiments, raw chunk manifests, features, predictions, events
and model metadata, with foreign keys and run/time indexes. Raw rows are buffered
in memory and written as a Parquet chunk every 30 seconds or once 1600 rows have
accumulated (whichever comes first) and at clean shutdown, so a killed process loses
at most about the last 30 seconds (before 2026-09-27 the threshold was rows only,
about 27 minutes at 1 Hz, and a kill lost far more).
Raw Parquet files are written to `.partial`, atomically renamed, then indexed. Crash between rename
and SQLite commit leaves an orphan, not a referenced partial file. `audit` lists
orphans, missing files, partial files and unfinished runs; it never deletes data.
Keep a backup/snapshot before evaluation. The schema carries a version
(`PRAGMA user_version`); there is no migration framework, so a column change needs a
deliberate migration (see [ADR-010](decisions/ADR-010-storage-layout.md)). A process
that is killed rather than stopped with Ctrl-C leaves its run in status `RUNNING`;
`audit` lists such runs under `unfinished_runs`, and
`sentinel --data <dir> reconcile` marks stale ones `INTERRUPTED` and closes their
open events (it skips a run that is still publishing live status). `audit` opens the
database read-only.

Each run has a JSON summary; raw data, models and large reports stay in ignored
`data/`. Commit curated evidence from `docs/benchmarks` instead. Operator details
can be supplied using `--machine`, `--notes`, `--metadata-json` (see experiment
template). These do not override the generated source/configuration provenance.

## Hardware bring-up (in progress)

Status as of 2026-09-27: the plain `uno` binary firmware has been uploaded to a
real Uno and captures have been made (the port was COM5 during bring-up; the COM
number varies with the USB port and can change after a replug, so always check
Device Manager or `python -m serial.tools.list_ports`). Captures are in
`data/physical` (2026-09-19/20) and `data/physical_check` (2026-09-23); see
[failures](failures/README.md) for what they showed. They are bring-up data, not a
dataset: every run is labelled NORMAL, none was calibrated (all runs used the
placeholder `--distance-*`/`--water-*` defaults, which the run metadata records),
and no run has a tape-measure reference. Firmware compilation and a successful
capture are still not electrical validation or acceptance.

First review `hardware/design.md` and identify actual module part numbers and
voltages. See [ADR-008](decisions/ADR-008-sensor-set-pivot.md) for the sensor-set
pivot this guide reflects. Checklist (done = observed in the captures; the rest is
open):

1. Done: Uno with the HC-SR04 wired (see `hardware/design.md`'s pin table).
2. Optional debug: build/upload `uno_csv` at the identified COM port (115200
   baud) and run `sentinel csv --port COMx`.
3. **Open:** confirm distance readings against a tape measure at a few known
   distances. Not yet done: one capture reports ~2.2 m (sensor not aimed at the
   tank) and another has ~38% of readings without a valid echo. A missing/
   out-of-range echo produces records without the distance-valid bit. Reboot after
   fixing wiring.
4. Done: the plain `uno` binary build is uploaded and streaming. Acquire with:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical acquire --port COMx --seconds 60 --condition NORMAL --metadata-json docs/experiments/run-template.json
```

   Stop a run with Ctrl-C (status `INTERRUPTED`, buffered rows flushed) or let
   `--seconds` elapse. Do not kill the process or unplug the Uno mid-run: a killed
   process leaves the run `RUNNING` and loses the unflushed rows.
5. Partly done: `analyze`, validity and gap diagnostics exist and were used; the
   1 h capture showed no sequence gaps or parser errors. Device timestamps are
   host-assembly (`millis()`) time, not per-sensor conversion time.
6. **Open:** all five sensor channels report values, but none is calibrated. Measure
   the water-level module's actual dry/wet ADC range (the 5 h capture sat at a dry
   floor around raw 7) and pass it via `--water-dry-raw`/`--water-wet-raw`; measure
   the thermistor's real part and update `pipeline.py`'s NTC constants; confirm
   DHT11 vs DHT22 against the part's markings (see `hardware/design.md`).
7. **Open:** measure the tank's actual empty/full sensor-to-surface distance and
   pass it via `--distance-empty-mm`/`--distance-full-mm`; record the measured
   values in the run metadata (`docs/experiments/run-template.json`) and see
   [ADR-011](decisions/ADR-011-calibration-approach.md).
8. **Open:** verify the LED/PN2222-driven buzzer and serial commands on real
   outputs. UNKNOWN is amber. Firmware behaviour: a FAULT state is not dropped by the
   3 s host-silence timeout, but any host `SET_ALARM` or `CLEAR_ALARM` overrides it,
   and the host sends `SET_ALARM(3)` (UNKNOWN) after a reconnect, so FAULT is not a
   hard latch. Non-fault states become UNKNOWN after three seconds without a valid
   host command. Host retries ACKs, resets state on reconnect, validates config and
   explicitly requests streaming. USB unplug/replug and Arduino reset are not yet
   tested (see [verification matrix](failures/verification-matrix.md)).

Physical experiments, accepted timing limits, sensor calibration, long-run
reliability, model generalization and physical T0-T7 latency remain unmeasured.
