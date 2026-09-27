# Testing and verification

Owner: the `testing` agent. Last full run: **2026-09-27, 164 passed in 15.1 s** (Python 3.9.0 venv, pytest 8.4.2),
after the 82 tests proposed below were added to `tests/` and the two defects this review found were fixed the same
day (see both sections below); the review itself was done against 79 passing tests.
"Tests pass" means the code paths below behave as asserted on simulated data and mocked serial. It does not mean
the firmware, the USB link, the sensors, the alarm outputs or the web UI work; those are in
[Verification only a human can give](#verification-no-automated-test-can-give).

## How to run

From the repository root, PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q                              # all 79, about 5 s
.\.venv\Scripts\python.exe -m pytest -q --co                         # list test ids
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --durations=5
.\.venv\Scripts\python.exe -m pytest tests/test_storage.py -q        # one file
```

Do not pass `-x` when judging a change: the files run alphabetically (`test_api`, `test_failures`,
`test_integration`, `test_processing`, `test_protocol`, ...), so `-x` hides the unit tests that would also fail.

Rules for tests in this repo: use `tmp_path`, simulated data and mocked `serial.Serial`; never open a real port,
never run `sentinel acquire`/`csv`, never write into `data/`.
API tests must use `TestClient(create_app(root), base_url="http://127.0.0.1")` and absolute `ws://127.0.0.1/...`
URLs (the client hard-codes `testserver` for WebSockets, which the Host check refuses).
Time-dependent storage tests monkeypatch `database.time.monotonic`.
No coverage tool is installed in the venv (`coverage`, `pytest-cov` absent), so the map below is derived from reading
the code against the tests, not from measured line coverage.

Slowest tests (2026-09-27): `test_serial_owner_recovers_and_restarts_stream` 1.25 s, `test_group_split_and_model_workflow`
0.76 s, the two model-refusal tests about 0.3 s each.

## What each test file covers

| File | Tests | Covers |
|---|---|---|
| `tests/test_protocol.py` | 42 ids | CRC-16 reference vector and 29-byte layout; every fragment boundary (37 params); CRC corruption, unknown kind, oversized length, parser timeout, bounded buffer; `Continuity` wrap/gap/duplicate/boot reset; command retry, identical retry bytes, wrong-ID ACK, 3-attempt failure; CSV parser recovery after long line and bad integer |
| `tests/test_processing.py` | 7 | Feature vector shape, constant/ramp/mismatch windows, invalid input, `Windows` 50 % overlap and discontinuity reset, `StateMachine` persistence and sustained recovery |
| `tests/test_integration.py` | 5 | 90 s simulated end to end (samples, windows, FAULT, alarm state on event, audit clean, every API route, 422 on oversize limit, one WebSocket message); corruption/drops give gaps and no false windows; grouped split + train + one-shot evaluate + physical refusal of synthetic data; model SHA-256 missing/mismatch refusal; model/run calibration mismatch refused with no open run left |
| `tests/test_failures.py` | 5 | Invalid sensor and DHT checksum clear windows; orphan and `.partial` audit; benchmark labelled SIMULATED with rate 1 Hz; bad state config closes the run; locked `status.json` does not stop acquisition |
| `tests/test_reconnect.py` | 1 | Mock serial owner: injected cable loss, reopen, reconfigure, restart stream, reset counted |
| `tests/test_storage.py` | 8 | Timed flush; reconcile of a killed run and of a live one; schema versioning, adoption of unstamped DB, refusal of a newer one; FAILED status when the final flush fails; read-only audit; equal calibration points rejected before a run exists |
| `tests/test_api.py` | 11 ids | Foreign Host refused; cross-origin WebSocket refused; malformed status snapshots (5 params) give UNKNOWN/stale; empty `run_id` means latest; events filter by run; raw path escape is HTTP 400; measurements across many chunks |

## Coverage map (from reading code and tests; not measured)

Legend: T = tested, P = partly, N = no test.

| Module | Tested | Not tested |
|---|---|---|
| `acquisition/protocol.py` | T: CRC vector, framing at every split, bad CRC, unknown kind, oversized, timeout clear, bounded buffer, `Continuity` wrap/gap/dup/boot change, `Sample` round trip | N: `Continuity.out_of_order` counter (backwards sequence, backwards device time), `Sample.decode` wrong length, `encode` over `MAX_PAYLOAD`, version-byte mismatch |
| `acquisition/commands.py` | T: retry bytes, wrong ACK, failure after attempts, ID assignment | N: ID wrap at 0xFFFF, `begin` while pending raises, ACK with wrong length |
| `acquisition/simulator.py` | P: used by nearly every test; `drop_every`/`corrupt_every` via the corruption test | N: individual `condition` shapes (RAPID_DRAIN, OVERFLOW, ENVIRONMENTAL_ANOMALY produce their intended features), `STOP_STREAM`, `CLEAR_ALARM`, unknown command error=1 |
| `acquisition/csv_protocol.py` | T: long line then valid, bad integer | N: wrong prefix, wrong field count, uint overflow/negative, non-ASCII, CRLF, byte-at-a-time feed, blank lines (counted as errors) |
| `runner.py` | T: simulated completion, reconnect and reset count, config error in `Store`/`Pipeline` construction (closes run), locked status file, calibration mismatch | N: device `report_interval` mismatch `ValueError` (`:132-137`), boot change on a live stream (`:138-143`), silent device: `now-last_rx > 2` and `now-last_data > 2` UNKNOWN paths (`:169-176`), command-failure counters, heartbeat PING (`:188`), ACK-driven `alarm_ack` for non-FAULT states, queue-full `queue_drops` (`:75`, `:107`), `metadata_json` non-object, `duration<=0`/`fs!=1`, raw-write failure mid-run, `KeyboardInterrupt` -> INTERRUPTED |
| `pipeline.py` | T: invalid flags/DHT checksum clear windows, gap clears windows, calibration mismatch, model fs/window guards partly | N: window device-timing rejection (`:89-95`), stale distance (`>1000 ms`) and stale ambient (`>4000 ms`) invalidation, percent clipping, thermistor at ADC rail (raw 0/1023 makes the sample invalid, `:50`), `latencies` trim at 10000 |
| `processing/features.py` | T: shape, constant, ramp, mismatch, NaN and short window | P: 30-sample real window values not golden-checked |
| `processing/windows.py` | T: 50 % overlap, discontinuity | N: overlap 0 and high overlap step, configuration validation (`size<8`, `overlap>=1`), full refill after `clear()` |
| `state.py` | T: persistence, sustained recovery, None -> UNKNOWN | N: exact threshold equality (`>= fault`, `>= warning`, `<= recovery`), NaN/inf/out-of-range score, FAULT held by a mid score, constructor validation |
| `ml/train.py` | T: grouped split without leakage, train, one-shot evaluate, refusal of physical training on synthetic-only data | N: reused output dir, CYCLE rows refused, fewer than 3 runs per class, mixed window/rate/calibration refusal, `evaluate` when the dataset changed, threshold baseline numbers |
| `ml/inference.py` | T: SHA-256 missing and mismatch, synthetic model refused for physical inference | N: feature-schema and pipeline-version mismatch, isolation-forest scoring branch |
| `storage/database.py` | T: timed flush, reconcile (killed, live), schema version/adopt/newer, failed final flush, audit read-only and orphan/partial, run start/close | N: `flush` failure with rows retained and retried, reconcile with stale or finished snapshot, reconcile end time from last window, `reconcile` on a directory that does not exist (see finding 2), `alarm_ack` update in isolation, `close(status)` variants |
| `storage/queries.py` | T: measurements across chunks, path escape, empty run id | N: fresh `status()` staying live, 3 s stale cut-off, `acquisition_status` forcing UNKNOWN, unknown run id |
| `storage/status.py` | T: locked file skipped | N: other `OSError` types propagate (only `PermissionError` is caught) |
| `api/main.py` | T: all routes 200, Host check, Origin check, limit 422 on measurements, malformed status | N: limit boundaries on other routes, `localhost` and host:port forms, static-frontend mount, WebSocket beyond one message, slow consumer |
| `cli.py` | T: none directly (tests call `run()` and library functions) | N: every subcommand and argument parsing: `simulate`, `dataset` (`--runs<3` error), `reconcile`, `analyze`, `report`, `profile`, `audit`, `train`, `evaluate`, `benchmark`; `api` and `csv` by design (long-lived) |
| `calibration.py` | T: equal points rejected via `run()` | N: `from_metadata` missing keys, default thermistor |
| `benchmark.py` | T: simulated label, rate 1 Hz, zero false alarms | N: drop/wrap handling in rate estimate, false alarms per hour on a NORMAL run with FAULT events, empty DB |
| `profiling.py` | N: no test | whole module (`profile()` output shape and `limitations` text) |
| `report.py` | N: no test | whole module (`export` HTML, `continuous` flag, no-data error) |

## Known gaps register

Severity: H = could hide a real defect in the data path or a documented invariant; M = behaviour unpinned; L = polish.

| # | Gap | Sev | Evidence / note |
|---|---|---|---|
| 1 | **Firmware has no automated tests.** Only `platformio run -e uno -e uno_csv` compiles it; no `native` env. Parser, CRC and alarm state logic are unverified by execution. | H | Both sides assert 29-byte `Sample` and CRC(`123456789`)=0x29B1; a shared golden-vector file would let the host tests pin the firmware parser without hardware. Ask before adding a native env |
| 2 | **Frontend has no tests** and has never been viewed in a browser (`npm run build` only). | H | Needs a new dev dependency (Vitest/Testing Library or Playwright screenshot); ask first |
| 3 | The serial-reconnect test is a **mock**, not USB. Unplug/replug, Arduino reset, stop-Python, missing sensor and physical alarm are "Not yet done". | H | See the matrix |
| 4 | ~~Runner receive path barely tested~~ **Closed 2026-09-27**: device rate mismatch, mid-stream boot change and silence/heartbeat behaviour are pinned. | H | `test_reconnect.py::test_device_reporting_a_different_rate_is_refused_and_the_run_marked_failed`, `test_boot_change_on_a_live_stream_counts_a_reset_and_keeps_both_boots_apart`, `test_silent_device_is_never_configured_and_its_commands_time_out` |
| 5 | ~~`Pipeline` device-timing rejection and stale-channel rules unpinned~~ **Closed 2026-09-27**. | H | `test_failures.py::test_window_whose_device_timing_disagrees_with_the_rate_is_rejected`, `test_stale_or_unusable_channel_makes_the_sample_invalid_but_keeps_the_raw_row` |
| 6 | ~~Live status freshness untested for the valid case~~ **Closed 2026-09-27**. | H | `test_api.py::test_status_is_live_only_when_fresh_and_not_finished` |
| 7 | ~~No test proves the 30 s loss bound when the stream stops~~ **Closed 2026-09-27**: `Store.flush_due()` is now also called from the acquisition loop each pass (not only on a new row), so a stopped stream still gets its buffered tail written within `FLUSH_SECONDS`. | M | `test_storage.py::test_flush_due_writes_the_tail_even_when_no_new_row_arrives` |
| 8 | ~~`cli.py` has no tests~~ **Closed 2026-09-27** for `reconcile`, `dataset`, `simulate`+`analyze`+`report`+`profile`. `analyze`/`report` on an empty/no-run directory still has thin coverage. | M | new `test_cli.py` |
| 9 | ~~`Store.flush` failure / raw-write failure mid-run unpinned~~ **Closed 2026-09-27**, and the underlying bug is fixed: `runner.py`'s `finally` block now writes the summary/status file before re-raising a `store.close` failure, so a mid-run write failure still leaves `<run_id>-summary.json` with `acquisition_status: "FAILED"`. | M | `test_storage.py::test_a_failed_flush_keeps_the_rows_and_a_later_flush_writes_them_once`, `test_failures.py::test_raw_write_failure_during_a_run_marks_it_failed`, `test_raw_write_failure_still_writes_the_run_summary_as_failed` |
| 10 | ~~CSV/Windows/state-machine edge cases unpinned~~ **Closed 2026-09-27**. | M | `test_protocol.py`, `test_processing.py` additions |
| 11 | ~~Model refusal paths beyond SHA-256/simulated/calibration unpinned~~ **Closed 2026-09-27**: pipeline-version, feature-schema, window and rate mismatch; `train` reused dir / CYCLE / <3 runs; `evaluate` after data changed. | M | `test_integration.py` additions |
| 12 | API pagination bounds on routes other than `/measurements`; unknown `run_id`. **Closed 2026-09-27.** | L | `test_api.py::test_api_limits_are_enforced_at_the_boundary`, `test_unknown_run_id_returns_empty_lists_not_errors` |
| 13 | No soak, load or slow-consumer test; the WebSocket test reads one message; `sentinel csv` exclusivity with `acquire` untested. | L | |
| 14 | Statistical claims are untested by design: synthetic scores are separable by construction and prove only the code path. | L | Never quote accuracy from synthetic runs |
| 15 | No coverage measurement (no `coverage`/`pytest-cov`). | L | Would replace the hand-built map above; ask before installing |

### Defects found while testing (2026-09-27), all fixed the same day

1. **Fixed:** `LOCAL_HOSTS` no longer contains `"[::1]"` (`api/main.py`) — Starlette 0.49.3's `TrustedHostMiddleware` reads the Host header as `header.split(":")[0]`, which turned `[::1]` and `[::1]:8000` into `[`, both refused with 400. Harmless (the server binds `127.0.0.1` only), but the entry was dead and misleading; removed rather than handling the bracket form, since IPv6 is not served. Test: `test_api.py::test_host_check_accepts_only_exact_loopback_names_with_or_without_a_port`.
2. **Fixed:** `reconcile()` on a data directory that was never used (`database.py`) used to create the directory and an empty `sentinel.sqlite` before raising `sqlite3.OperationalError: no such table`. It now returns `[]` without creating anything if `sentinel.sqlite` doesn't already exist. Test: `test_storage.py::test_reconcile_of_a_data_directory_that_was_never_used_creates_nothing`.
3. **Fixed:** a raw-write failure during a run now still writes `<run_id>-summary.json` with `acquisition_status: "FAILED"` (`runner.py`'s `finally` block records the close failure, publishes and writes the summary, then re-raises). Tests: `test_storage.py::test_a_failed_flush_keeps_the_rows_and_a_later_flush_writes_them_once`, `test_failures.py::test_raw_write_failure_still_writes_the_run_summary_as_failed`.

## Mutation sanity check (2026-09-27)

Method: copy `python/sentinel` and `tests` to a scratch directory, change one line in the copy, run the suite with
`PYTHONPATH` pointing at the copy (import path verified). The repository was not touched.

| Mutation | Result | First failing test |
|---|---|---|
| Parser CRC check disabled | caught | `test_corruption_unknown_oversized_and_timeout_recovery`, `test_corruption_creates_gaps_not_false_continuous_windows` |
| Continuity gap counting removed | caught | `test_continuity_wrap_reset_gap_duplicate`, `test_corruption_creates_gaps_not_false_continuous_windows` |
| Continuity sequence wrap mask removed | caught | `test_continuity_wrap_reset_gap_duplicate` |
| Host-header middleware removed | caught | `test_foreign_host_header_is_refused_to_stop_dns_rebinding` |
| WebSocket Origin check removed | caught | `test_live_socket_refuses_a_cross_origin_page` |
| Model SHA-256 comparison disabled / missing sidecar tolerated | caught | `test_model_is_refused_unless_its_recorded_sha256_matches` |
| Model/run calibration check removed | caught | `test_model_cannot_be_used_with_a_different_calibration` |
| Raw path escape check removed | caught | `test_raw_path_outside_the_data_directory_is_a_client_error` |
| Timed flush removed | caught | `test_raw_rows_reach_disk_on_a_timer_not_only_at_the_row_threshold` |
| Reconcile ignores live status | caught | `test_reconcile_leaves_a_run_that_is_publishing_live_status` |
| `close()` stops marking FAILED on flush error | caught | `test_close_marks_the_run_failed_when_the_final_flush_fails` |
| FAULT persistence 3 -> 1 | caught | `test_state_persistence_and_sustained_recovery` |
| Boot change no longer counts a reset | caught | `test_serial_owner_recovers_and_restarts_stream` |
| Grouped split leaks test runs into train | caught | `test_group_split_and_model_workflow` |
| Pipeline window-timing check removed | **fixed 2026-09-27**, now caught | `test_window_whose_device_timing_disagrees_with_the_rate_is_rejected` |
| Runner device-rate mismatch check removed | **fixed 2026-09-27**, now caught | `test_device_reporting_a_different_rate_is_refused_and_the_run_marked_failed` |
| `status()` never marks a snapshot stale | **fixed 2026-09-27**, now caught | `test_status_is_live_only_when_fresh_and_not_finished` |
| Ambient staleness limit removed | **fixed 2026-09-27**, now caught | `test_stale_or_unusable_channel_makes_the_sample_invalid_but_keeps_the_raw_row` |

At the time of the review (79 tests) none of these four were caught; they are listed here as history. The tests
below were added to `tests/` the same day, closing all four (re-run the mutation against the current 164 to confirm
if this is doubted).

## Tests added 2026-09-27 (were "proposed tests awaiting application")

Validated in a scratch file first (82 pass, plus one bug-exposing test that failed until the defect above was
fixed), then added to `tests/` in these homes (all 164 tests pass together):

| Test name | Add to | Pins |
|---|---|---|
| `test_status_is_live_only_when_fresh_and_not_finished` | `test_api.py` | 3 s freshness, `acquisition_status` forces UNKNOWN (gap 6) |
| `test_api_limits_are_enforced_at_the_boundary` (8 params) | `test_api.py` | limit 0/max/max+1 on every route |
| `test_host_check_accepts_only_exact_loopback_names_with_or_without_a_port` | `test_api.py` | Host allow-list forms |
| `test_unknown_run_id_returns_empty_lists_not_errors` | `test_api.py` | |
| `test_window_whose_device_timing_disagrees_with_the_rate_is_rejected` | `test_failures.py` | gap 5 |
| `test_stale_or_unusable_channel_makes_the_sample_invalid_but_keeps_the_raw_row` (5 params) | `test_failures.py` | distance/ambient age, thermistor at rail, flags |
| `test_out_of_range_readings_are_clipped_to_a_percentage` | `test_failures.py` | |
| `test_metadata_json_must_be_an_object_...`, `test_run_refuses_a_non_positive_duration_...`, `test_raw_write_failure_during_a_run_marks_it_failed` | `test_failures.py` | gap 9 |
| `test_device_reporting_a_different_rate_is_refused_and_the_run_marked_failed` | `test_reconnect.py` | gap 4 |
| `test_boot_change_on_a_live_stream_counts_a_reset_and_keeps_both_boots_apart` | `test_reconnect.py` | gap 4 |
| `test_silent_device_is_never_configured_and_its_commands_time_out` (2 s real time) | `test_reconnect.py` | gap 4 |
| `test_a_failed_flush_keeps_the_rows_and_a_later_flush_writes_them_once` | `test_storage.py` | gap 9 |
| `test_reconcile_takes_over_a_run_whose_status_is_stale_or_finished` (3 params), `test_reconcile_stamps_the_run_end_with_its_last_window_not_now` | `test_storage.py` | |
| `test_csv_bad_line_...` (7 params), `test_csv_line_is_held_until_its_newline_...`, `test_continuity_rejects_backwards_sequence_and_backwards_device_time` | `test_protocol.py` | gap 10 |
| `test_window_step_follows_the_overlap` (4), `test_window_configuration_is_validated` (3), `test_a_cleared_window_needs_a_full_size_...`, `test_state_machine_threshold_boundaries` (12), `test_state_machine_rejects_inconsistent_thresholds` (6) | `test_processing.py` | gap 10 |
| `test_cli_reconcile_...`, `test_cli_dataset_refuses_...` (2), `test_cli_dataset_records_the_same_number_...`, `test_cli_simulate_then_analyze_then_report_then_profile`, `test_report_says_when_the_run_was_not_continuous_...` | new `test_cli.py` | gap 8 |
| `test_model_from_another_feature_pipeline_is_refused_...` (2), `test_run_refuses_a_model_trained_for_another_window_...`, `test_train_and_evaluate_refuse_reused_output_...`, `test_cycle_demo_runs_can_never_become_training_data` | `test_integration.py` | gap 11 |
| `test_reconcile_of_a_data_directory_that_was_never_used_leaves_no_files_behind` | `test_storage.py` | **fails until `reconcile` opens read-only or checks the file exists** |

## Failure-injection tools that already exist

- `Simulator(drop_every, corrupt_every)`; CLI `simulate --drop-every N --corrupt-every N`.
- Simulator `condition`: NORMAL, LOW_WATER, OVERFLOW, RAPID_DRAIN, SENSOR_MISMATCH, ENVIRONMENTAL_ANOMALY, and CYCLE (demo only; refused as training data).
- `monkeypatch.setattr(Path, "replace", ...)` for a locked `status.json` (Windows antivirus/reader lock).
- `monkeypatch.setattr("sentinel.runner.serial.Serial", Fake)` for reconnect, silent device, rate mismatch, reboot: the fake needs `__enter__/__exit__`, `in_waiting`, `write`, `read`.
- `monkeypatch.setattr(database.pq, "write_table", broken)` / `monkeypatch.setattr(store, "flush", broken)` for disk-full.
- `monkeypatch.setattr(database.time, "monotonic", ...)` and `database.FLUSH_ROWS` for flush timing and many small chunks.
- Direct `Store` / `Pipeline` construction with hand-built `Sample(...)` records and explicit `host_ns`.
- Hand-edited `status.json` (fresh, stale, malformed, finished) and hand-edited `raw_chunk` rows (path escape).

## Verification no automated test can give

Nothing in this list has been done as of 2026-09-27; each stays "Not yet done" in the matrix until logs exist.

- **Firmware behaviour**: compile is the only check. Needs serial capture of the real Uno for CRC/parse under noise, sensor timing (HC-SR04 echo dropouts, DHT read spacing), watchdog UNKNOWN after 3 s of host silence, FAULT held.
- **USB unplug/replug, Arduino reset, stop-Python**: controlled runs with a log of host, firmware and expected/observed state; boot IDs, `reconnections`, `resets`, `command_failures`.
- **Missing sensor**: rewire only with power off; expect invalid flags and no fabricated measurement.
- **Physical alarm latency**: a shared logic-analyzer trigger; never subtract clocks across the device and host domains.
- **Real calibration**: tank empty/full distance, water-level dry/wet raw, thermistor part; all defaults are placeholders.
- **Browser**: `frontend/dist` never opened; check dashboard state colours, stale badge, WebSocket reconnect, 1 Hz updates, mobile width.
- **Long run**: hours of real acquisition for the flush/WAL/`status.json` behaviour on this Windows machine.
- **Python >= 3.9.1**: the venv is 3.9.0, where `/openapi.json` cannot be built; not exercised by any test.

For any hardware evidence record: configuration, date, duration, observed vs expected, exact logs, root cause, retest.
