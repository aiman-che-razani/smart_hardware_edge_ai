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
.\.venv\Scripts\python.exe -m sentinel --data data/demo dashboard
```

Visit **http://127.0.0.1:8050**. The dashboard shows SIMULATED, a state, DAQ
counters, XYZ waveforms, X FFT, current, temperature, scores and events. Select
another run for comparison. Parquet flushes every 1600 records, so waveform
refresh is approximately two seconds at 800 Hz; this is not a hard real-time UI.
Finished/stale acquisition displays UNKNOWN rather than presenting old NORMAL
as live health. Historical data remains accessible.

Optional independent API:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo api
```

Open **http://127.0.0.1:8000/docs**. Read-only endpoints: `/health`, `/machines`,
`/measurements`, `/features`, `/predictions`, `/events`, `/experiments`,
`/system/status`; WebSocket `/live` publishes status each second. Both servers
bind to loopback. Only one acquisition writer may use a given data directory.

## Environment from scratch

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
$env:PLATFORMIO_CORE_DIR = Join-Path (Get-Location) '.pio'
.\.venv\Scripts\python.exe -m platformio run --project-dir firmware -e uno -e uno_csv -e uno_edge
```

Dependencies: PySerial owns the serial port; NumPy/SciPy perform numerical DSP;
PyArrow stores columnar raw data; scikit-learn/joblib train and persist small
models; FastAPI/Uvicorn provide the local API; Dash/Plotly plot the engineering
views. SQLite is in Python's standard library. OneWire supplies tested bus timing
primitives; the DS18B20 conversion state machine and CRC checks are explicit in
our driver. No motor-control service or distributed infrastructure is required.

## Synthetic research workflow

Keep labelled research runs separate from changing-condition CYCLE demos.

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/research-new dataset --runs 5 --seconds 8
.\.venv\Scripts\python.exe -m sentinel --data data/research-new train --simulated --output data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/research-new evaluate --model-dir data/models/new-model
.\.venv\Scripts\python.exe -m sentinel --data data/ml-demo simulate --seconds 24 --model data/models/new-model/model.joblib
```

These commands create explicitly synthetic NORMAL, IMBALANCE_LOW,
IMBALANCE_HIGH and LOOSE_MOUNT signals. They test integration, not diagnostic
accuracy on machinery. Other simulator conditions are available through
`simulate --condition`. Synthetic current/temperature are simple illustrative
values, not a thermal/electrical model.

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
.\.venv\Scripts\python.exe -m sentinel --data data/failures simulate --seconds 10 --drop-every 211 --corrupt-every 300
# Change window and operational thresholds:
.\.venv\Scripts\python.exe -m sentinel --data data/tuning simulate --window-seconds 2 --overlap 0.5 --fault 0.85 --persistence 4
```

Features use DC removal per axis and Hann spectra. RMS/std/variance describe
overall fluctuating vibration, peak-to-peak and crest factor reveal extremes,
Pearson kurtosis/skewness describe impulsiveness/asymmetry, dominant frequency
and harmonic ratio describe periodicity, and PSD integration describes band
energy. RMS is AC RMS, not total RMS including gravity. Constant signals return
zero moments rather than undefined NaN. All acceleration is in g.

The optional tested high-pass function is available for investigation; the default
model pipeline does not apply it. It changes phase/transients and must be versioned
if enabled. Without RPM measurement, harmonic ratios are not shaft orders.
Frequency resolution is fs/N: default 800 samples at 800 Hz gives 1 Hz bins.
One-second windows with 50% overlap update every 0.5 s. Three high-risk windows
are required for FAULT; five low-risk windows for recovery. This adds latency to
the initial window fill. Default threshold score is max axis RMS / 0.25 g clipped
to [0,1], an uncalibrated engineering demo score.

Gaps, invalid acceleration, FIFO overrun, disconnect and inconsistent window time
clear the window/state to UNKNOWN. Latest slow-sensor readings carry ages; current
older than 200 ms and temperature older than 2 s are stored as null engineering
values. They are displayed and preserved but are not yet model features.

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
`profile` measures repeated FFT/feature/inference calls and traced Python allocation
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

First review `hardware/design.md` and identify actual modules, voltages, shunt
rating and safe motor fixture. Firmware compilation is not electrical validation.
No sketch has been uploaded by this implementation task.

1. Start with motor disconnected and only the verified ADXL345 interface.
2. Build/upload `uno_csv` manually at the identified COM port. This uses 100 Hz
   ODR / 115200 baud; run `sentinel csv --port COMx` for debug output.
3. Record six static orientations, raw scale and device configuration. Acceleration
   initialization checks ID 0xE5 and rate/range readback; missing sensor produces
   records without the acceleration-valid bit. Reboot after fixing wiring.
4. Build/upload `uno` for 800 Hz / 500000 baud. Then run:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical acquire --port COMx --seconds 60 --condition NORMAL --metadata-json docs/experiments/run-template.json
```

5. Inspect `analyze`, validity and gap diagnostics. Verify real timing with a logic
   analyzer before calling sampling deterministic. FIFO is polled cooperatively,
   at most four samples per loop; D2 is reserved but no ISR currently uses it.
   Device timestamps are FIFO readout time, not exact conversion time.
6. Add INA219 and externally powered DS18B20; verify units against instruments.
   INA219 is configured at address 0x40, shunt +/-320 mV, continuous conversion;
   raw 10 uV/LSB shunt voltage is converted with configured resistance (default
   0.1 ohm, must match the actual board). Temperature uses 1/16 °C raw units.
7. Verify LED/buzzer driver and serial commands. UNKNOWN is amber; FAULT red/buzzer
   remains latched if host contact is lost. Non-fault states become UNKNOWN after
   three seconds without a valid host command. Host retries ACKs, resets state on
   reconnect, validates config and explicitly requests streaming.

Physical experiments, accepted timing limits, sensor calibration, long-run
reliability, model generalization and physical T0–T7 latency remain unmeasured.
