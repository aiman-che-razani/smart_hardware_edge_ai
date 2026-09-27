# Initial risk register

Owner: project engineer. All mitigation checks remain open until evidence exists.

| Risk | Impact / priority | Mitigation and verification |
|---|---|---|
| Water contacting the Uno, breadboard or USB connection | Sensor/board damage / high | Route the water-level probe's leads away from logic wiring; keep the tank and electronics physically separated |
| Unknown module supply voltage (water-level, DHT) | Sensor/board damage / medium | Confirm each module's rated voltage against its datasheet before wiring to Uno 5V |
| Blocking DHT read stalls the main loop | Missed ultrasonic pings / medium | DHT read is bounded (~ms via SimpleDHT) and polled at most every 2s; confirm actual blocking duration on real hardware |
| SRAM/stack exhaustion | Reset/corruption / high | Static buffers, build-size ledger, runtime headroom testing |
| Uncalibrated water-level/thermistor readings | Misleading level/temperature values / high | Measure the actual dry/wet ADC range and thermistor part before trusting `pipeline.py`'s placeholder constants |
| USB reset/disconnect or timestamp wrap | False continuity / high | Sessions, boot records, rollover/reconnect tests |
| Stale DHT reading shown as fresh | Misleading features / medium | Validity, age (4s threshold) and independent update times |
| Overlapping-run ML leakage | Inflated results / high | Split by run; fit transforms on train only |
| Lost commands / false alarms | Unreliable indication / high | ACK/retry, idempotency, hysteresis and explicit communication state |
| Python 3.9 scientific dependency support | Installation friction / medium | Move to maintained Python before later dependencies |

## Observed development issues

- Sandbox user differs from repository owner: use a command-local Git
  `safe.directory` exception for this exact project, not a global wildcard.
- Sandbox restricts `.git` writes and network access; repository connection needs
  the corresponding tool approval.
- PlatformIO was not installed in the system Python at initial inspection.
- A generated-data stress run encountered Windows `WinError 5` while atomically
  replacing `status.json`. The run was marked FAILED and stored data was finalized.
  Live status is now published at most five times per second, and a transient
  PermissionError skips that snapshot instead of stopping DAQ. The next update
  retries; stale snapshots display UNKNOWN. A regression test injects this lock.

## Observed failures (hardware bring-up)

Dated entries. Evidence is in the git-ignored `data/physical` (2026-09-19/20) and
`data/physical_check` (2026-09-23) stores: each run's `<run_id>-summary.json`,
its `sentinel.sqlite` row and the raw Parquet. Numbers below were read from those
files on 2026-09-27. Root causes marked "not established" were not investigated.
Nothing here is marked resolved.

### 2026-09-23 - Ultrasonic echo dropouts (Phase 1/2, open)

- Observed: 1 h run `48b1ce36-77c2-4661-877e-3b17f6c9cb59` (3,598 samples, 0
  sequence gaps, 0 parser errors, 105 windows) has `invalid_windows_or_samples` =
  1,398, i.e. 38.9% of samples. In the raw Parquet 1,367 samples (38.0%) have the
  distance-valid flag clear; the counter also includes samples whose distance
  reading was older than 1 s or whose DHT reading was invalid. The transport was
  clean, so this is a sensor-side loss.
- Mechanism: firmware clears distance-valid when `pulseIn` sees no echo within
  25 ms (`kUltrasonicTimeoutUs`); an invalid sample clears the DSP window, so
  windows rarely fill.
- Root cause: not established (aiming, surface reflection, target distance,
  wiring/power noise all untested). Expected behaviour: a tank-facing HC-SR04 at a
  known distance returns a valid echo almost every 150 ms poll.
- Next check: aim at a flat target at tape-measured distances and log the valid
  fraction per distance.

### 2026-09-19/20 - Water-level probe stuck at the dry floor (Phase 4, open, needs hardware)

- Observed: 5 h run `a8c0ebf2-b38f-4506-b5cf-dd485f9873cd` (18,155 samples)
  has `water_level_raw` median 7 (range 5-15), so `level_water_pct` is 0.0
  throughout. The 2026-09-23 20 s run (`e05e4450`) and the first run
  (`30284a5b`, median 9) also read at the floor; other runs read hundreds
  (medians 590, 581, 496).
- Root cause: not established (probe out of the water, module or wiring fault, or
  the tank was empty). No dry/wet measurement exists, so 200/800 remain
  placeholders.

### 2026-09-19/20 - Ultrasonic aimed away from the tank (Phase 1, open, needs hardware)

- Observed: runs `30284a5b`, `1ba3ff02` and `fe263795` report median distance
  2,212 / 2,212 / 2,207 mm (about 2.2 m), far beyond the placeholder tank empty
  distance of 1,000 mm, so `level_ultrasonic_pct` is clipped and meaningless. The
  5 h run reads a median 379 mm and the 1 h run 164 mm, so the sensor was moved
  between sessions.
- Root cause: mounting/aiming (operator report); no tape-measure reference or
  mounting record exists.

### 2026-09-19/20 - Five runs ended INTERRUPTED (Phase 5, informational)

- Observed: `30284a5b`, `1ba3ff02`, `fe263795`, `1a285efb`, `a8c0ebf2` have status
  INTERRUPTED. The runner sets that status only on Ctrl-C (`KeyboardInterrupt`),
  so these were stopped by hand rather than reaching `--seconds`; that is
  inferred from the code, not recorded.
- `1a285efb` (372 s wall time) recorded 0 samples, 0 parser errors and 1 serial
  open: the port opened but no frame was decoded. Cause not established.

### 2026-09-19 and 2026-09-23 - Two runs left RUNNING after a kill (Phase 5, open)

- Observed: `data/physical` run `0ef6e2a5-d2b7-425e-ab42-10f385f6d26f` (started
  2026-09-19 04:49 UTC) and `data/physical_check` run
  `fb76dfcd-961a-4c4e-b697-b5f681e4f7de` (started 2026-09-23 02:58 UTC, 17 s
  before the next run) are still status RUNNING with no end time, no
  `<run_id>-summary.json` and no raw chunk. `sentinel audit` reports both as
  `unfinished_runs`.
- Root cause (inferred from the code): the process ended before `Store.close()`
  could set the final status; nothing reconciled stale RUNNING rows.
- Fixed 2026-09-27: `sentinel --data <dir> reconcile` marked both rows INTERRUPTED
  and closed their open events (SQLite backups were taken first). The command is
  covered by `tests/test_storage.py`; it skips a run that is still publishing fresh
  `status.json`.

### 2026-09-19 - Raw data lost to buffering on a kill (Phase 5, fixed 2026-09-27; lost rows unrecoverable)

- Observed: `Store` buffers raw rows in memory and flushes a Parquet chunk only
  every 1,600 rows or at clean close (about 27 minutes at 1 Hz). Run
  `0ef6e2a5` has 36 feature windows and events in SQLite but no raw rows at all:
  the windows imply roughly nine minutes of samples (30 s windows, 15 s hop) that
  were never written. Every completed or Ctrl-C run is intact: chunk row sums
  equal the summary sample counts (e.g. 12 chunks = 18,155 rows for the 5 h run).
- Consequence: kill = up to 1,599 rows (nearly 27 minutes) of raw data lost; the
  derived windows survive, so the raw and derived stores disagree.
- Fixed 2026-09-27: raw rows now flush every 30 s (or at 1,600 rows), so a kill
  loses at most about 30 s. Verified by unit tests only (`tests/test_storage.py`),
  not by a real hardware kill; the lost rows of `0ef6e2a5` cannot be recovered.

### Reported, not logged - COM port disappears when the Uno is unplugged (Phase 3)

- Reported by the operator during bring-up: unplugging the Uno removes its COM
  port (COM5 during bring-up), so a running `acquire` cannot reopen it until the
  board is replugged, and the number can change. No log of a controlled unplug
  was captured, so timing and host behaviour are unverified. The runs above show
  `reconnections` = 1 (the initial open) only. See the unplug/replug row in the
  [verification matrix](verification-matrix.md).

### Reported, not logged - Port 8000 held by an unrelated `http.server` (Phase 11)

- Reported by the operator: an unrelated `python -m http.server` held port 8000,
  so `sentinel api` could not use its default port and the browser showed the
  other process. Workaround: free the port or pass `sentinel api --port <n>`. No
  log was captured.

For new failures record date, phase, reproduction, expected/observed behavior,
raw evidence, root cause, fix and regression check. Do not mark risks resolved
merely because a mitigation has been proposed.
