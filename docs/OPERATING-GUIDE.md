# SentinelDAQ operating guide

## Current scope

The user authorized implementation across phases and selected simulation until
hardware details are available. Software paths are implemented and exercised;
physical phase acceptance is pending. The original phase-by-phase brief and
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

Open **http://127.0.0.1:8000/api/docs** for the interactive JSON API explorer.
Read-only endpoints: `/api/health`, `/api/machines`, `/api/measurements`,
`/api/features`, `/api/predictions`, `/api/events`, `/api/experiments`,
`/api/system/status`; WebSocket `/api/live` publishes status each second.
Binds to loopback. Only one acquisition writer may use a given data directory.

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
persist small models; FastAPI/Uvicorn provide the local API; Dash/Plotly plot
the engineering views. SQLite is in Python's standard library. Firmware uses
the SimpleDHT library for the DHT sensor; no SPI/I2C/OneWire remains in the
design. No distributed infrastructure is required.

## Synthetic research workflow

Keep labelled research runs separate from changing-condition CYCLE demos.

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/research-new dataset --runs 5 --seconds 90
.\.venv\Scripts\python.exe -m sentinel --data data/research-new train --simulated --output data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/research-new evaluate --model-dir data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/ml-demo simulate --seconds 90 --model data/models/new-model/model.joblib
```

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
.\.venv\Scripts\python.exe -m sentinel --data data/demo report --output data/reports/waveform.html
.\.venv\Scripts\python.exe -m sentinel --data data/benchmark-new benchmark --seconds 60
.\.venv\Scripts\python.exe -m sentinel profile --output data/reports/host-profile.json
```

The report is a standalone Plotly HTML file. `analyze` reports readout rate,
interval/jitter statistics and event-based false alarms/hour only for labelled
NORMAL runs. Simulation time is generated; its perfect rate is not hardware
evidence. The benchmark runs as fast as possible by default: `60` means sixty
seconds of generated signal, not sixty seconds of wall-clock soak testing.
Use `simulate --seconds 3600 --realtime` for a one-hour PC soak.
`profile` measures repeated feature/inference calls and traced Python allocation
peak; tracing perturbs timings and does not report full process RSS.

SQLite contains experiments, raw chunk manifests, features, predictions, events
and model metadata, with foreign keys and run/time indexes. Raw Parquet files
are written to `.partial`, atomically renamed, then indexed. Crash between rename
and SQLite commit leaves an orphan, not a referenced partial file. `audit` lists
orphans, missing files, partial files and unfinished runs; it never deletes data.
Keep a backup/snapshot before evaluation. No schema migration framework is present;
this is schema version 1 and future schema changes must have explicit migration.

Each run has a JSON summary; raw data, models and large reports stay in ignored
`data/`. Commit curated evidence from `docs/benchmarks` instead. Operator details
can be supplied using `--machine`, `--notes`, `--metadata-json` (see experiment
template). These do not override the generated source/configuration provenance.

## Hardware bring-up (pending)

First review `hardware/design.md` and identify actual module part numbers and
voltages. Firmware compilation is not electrical validation. No sketch has been
uploaded to real hardware by this implementation task — see
[ADR-008](decisions/ADR-008-sensor-set-pivot.md) for the sensor-set pivot this
guide already reflects.

1. Start with just the Uno and the HC-SR04 wired (see `hardware/design.md`'s
   pin table); nothing else connected yet.
2. Build/upload `uno_csv` manually at the identified COM port (115200 baud).
   Run `sentinel csv --port COMx` for debug output.
3. Confirm distance readings against a tape measure at a few known distances.
   A missing/out-of-range echo produces records without the distance-valid bit.
   Reboot after fixing wiring.
4. Build/upload the plain `uno` binary build. Then run:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical acquire --port COMx --seconds 60 --condition NORMAL --metadata-json docs/experiments/run-template.json
```

5. Inspect `analyze`, validity and gap diagnostics. Device timestamps are
   host-assembly (`millis()`) time, not per-sensor conversion time.
6. Add the water-level module, thermistor and photoresistor (plain analog
   reads on A0/A1/A2) and the DHT module (D4). Measure the water-level
   module's actual dry/wet ADC range and pass it via `--water-dry-raw`/
   `--water-wet-raw`; measure the thermistor's real part and update
   `pipeline.py`'s NTC constants; confirm DHT11 vs DHT22 against the part's
   markings (see `hardware/design.md`).
7. Measure the tank's actual empty/full sensor-to-surface distance and pass it
   via `--distance-empty-mm`/`--distance-full-mm`.
8. Verify the LED/PN2222-driven buzzer and serial commands. UNKNOWN is amber;
   FAULT red/buzzer remains latched if host contact is lost. Non-fault states
   become UNKNOWN after three seconds without a valid host command. Host
   retries ACKs, resets state on reconnect, validates config and explicitly
   requests streaming.

Physical experiments, accepted timing limits, sensor calibration, long-run
reliability, model generalization and physical T0–T7 latency remain unmeasured.
