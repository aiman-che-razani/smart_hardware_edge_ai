# Verification matrix

Automated rows are re-run with `.\.venv\Scripts\python.exe -m pytest -q` (79 passed, 2026-09-27). See `docs/TESTING.md`
for coverage, gaps and mutation results. "Passes 2026-09-27" means the named test passes; it does not mean the behavior
was seen on hardware.

| Test | Automated path / manual procedure | Expected behavior |
|---|---|---|
| Fragment every byte boundary | `test_protocol.py::test_every_fragment_boundary` (37 splits). Passes 2026-09-27 | Identical decoded sample |
| CRC corruption / unknown type / long input | `test_corruption_unknown_oversized_and_timeout_recovery`. Passes 2026-09-27 | Reject, increment counter, recover boundedly |
| Truncated frame | same test, parser timeout branch | Clear stale fragment and decode next frame |
| Sequence gap / duplicate / wrap / boot change | `test_continuity_wrap_reset_gap_duplicate`. Passes 2026-09-27. Backwards sequence/time (`out_of_order`) has no test yet | Count loss, reject duplicate, preserve wrap, start session |
| Corrupt and dropped frames end to end | `test_integration.py::test_corruption_creates_gaps_not_false_continuous_windows`. Passes 2026-09-27 | Parser errors and sequence gaps counted; no window spans a gap |
| ACK lost / duplicate command / wrong ACK | `test_commands_retry_idempotency_wrong_ack`. Passes 2026-09-27 | Same retry bytes, idempotent state, ignore wrong ID, failure counted after 3 attempts |
| Serial reconnection (mock) | `test_reconnect.py::test_serial_owner_recovers_and_restarts_stream`. Passes 2026-09-27. Mock only, not USB | Reopen/configure and resume after injected cable loss |
| Device reports a different rate; boot change mid-stream; silent device | Not yet automated: proposed tests in `docs/TESTING.md`. Mutation removing the rate check passed all 79 tests | Run fails with a mismatch error and is marked FAILED; reset counted and windows cleared; UNKNOWN and command failures |
| Windows status file locked | `test_failures.py::test_locked_live_status_does_not_stop_acquisition` (injected lock). Passes 2026-09-27. Observed stress rerun: not repeated | Skip snapshot; keep collecting measurements |
| Invalid sensor / DHT checksum error | `test_invalid_sensor_and_dht_checksum_error_clear_windows`. Passes 2026-09-27 | Clear window and UNKNOWN |
| Stale channel age / window timing inconsistent with rate | Not yet automated: mutations removing the timing check and the ambient age limit passed all 79 tests; proposed tests in `docs/TESTING.md` | Sample or window invalid, UNKNOWN, raw row still stored |
| Host queue overflow (`queue_drops`) | Not yet done: never provoked by any test | Drops counted, run continues |
| Constant / ramp / level-mismatch window features | `test_processing.py` feature tests. Passes 2026-09-27 | Known mean, slope, range, std and level-agreement values |
| State persistence/recovery | `test_state_persistence_and_sustained_recovery`. Passes 2026-09-27. Threshold-equality and NaN cases not yet automated | No single-window FAULT; sustained clear |
| Storage round-trip / orphan / partial | `test_orphan_and_partial_audit`, `test_end_to_end_and_api` (audit clean). Pass 2026-09-27 | Read complete records; identify unfinished evidence |
| Timed flush (added 2026-09-27) | `test_storage.py::test_raw_rows_reach_disk_on_a_timer_not_only_at_the_row_threshold` (fake clock). Passes 2026-09-27. Fires only when a new row arrives | Rows on disk within 30 s of arriving, manifest matches files |
| Final flush fails (added 2026-09-27) | `test_close_marks_the_run_failed_when_the_final_flush_fails`. Passes 2026-09-27. Flush retry and mid-run failure not yet automated | Run row FAILED, error re-raised |
| Killed process left run RUNNING / `sentinel reconcile` (added 2026-09-27) | `test_killed_run_is_reconciled_and_open_events_are_closed`, `test_reconcile_leaves_a_run_that_is_publishing_live_status`. Pass 2026-09-27. Not yet done: real `kill` of `sentinel acquire` then `reconcile`; the CLI wrapper has no test | Run INTERRUPTED with end time, open events closed; a live run left alone |
| Schema version (added 2026-09-27) | `test_schema_is_versioned_and_unstamped_databases_are_adopted`, `test_database_from_a_newer_version_is_refused`. Pass 2026-09-27 | Stamp v1; adopt an unstamped DB with its data; refuse a newer one |
| Read-only audit | `test_audit_is_read_only_and_does_not_create_the_directory`. Passes 2026-09-27. Known defect: `reconcile` on a missing directory creates an empty database (see `docs/TESTING.md`) | Audit never writes or creates files |
| Foreign Host header / DNS rebinding (added 2026-09-27) | `test_api.py::test_foreign_host_header_is_refused_to_stop_dns_rebinding`. Passes 2026-09-27; mutation removing the middleware is caught. `[::1]` is in the allow-list but is refused by Starlette 0.49.3 (verified, harmless: server binds IPv4 only) | HTTP 400 for a foreign Host; 200 for loopback |
| Cross-origin WebSocket (added 2026-09-27) | `test_live_socket_refuses_a_cross_origin_page`. Passes 2026-09-27; mutation caught | Close 1008 for a foreign Origin; same-origin accepted |
| Model SHA-256 (added 2026-09-27) | `test_integration.py::test_model_is_refused_unless_its_recorded_sha256_matches`. Passes 2026-09-27; mutations (compare disabled, missing sidecar tolerated) caught | Missing or mismatched sidecar refused before unpickling, in inference and in `evaluate` |
| Calibration refusal (added 2026-09-27) | `test_model_cannot_be_used_with_a_different_calibration`, `test_storage.py::test_equal_calibration_points_are_rejected_before_a_run_is_recorded`. Pass 2026-09-27. Real calibration values: Not yet done (placeholders) | Model bound to its calibration; equal empty/full or dry/wet points refused with no run recorded |
| Stale / malformed live status (added 2026-09-27) | `test_api.py::test_malformed_status_snapshot_is_unknown_not_a_server_error` (5 params). Pass 2026-09-27. The valid-fresh and 3 s stale cases are not automated: a mutation that never marks status stale passed all 79 tests | Missing/unparseable/finished/stale status reads as UNKNOWN, HTTP 200 |
| API run filter and path safety | `test_empty_run_id_means_latest_run_everywhere`, `test_events_can_be_filtered_by_run`, `test_raw_path_outside_the_data_directory_is_a_client_error`, `test_measurements_span_many_small_chunks`. Pass 2026-09-27 | Empty run id is latest; filters apply; escaping path is HTTP 400; all chunks read |
| API endpoints (no UI) | `test_end_to_end_and_api`: every route 200, oversize limit 422, one WebSocket message. Passes 2026-09-27. The web UI is not tested or viewed | Bounded endpoint responses |
| Dataset split | `test_group_split_and_model_workflow`. Passes 2026-09-27 | No overlapping run IDs; physical mode refuses synthetic data |
| Freeze/evaluation | same test | Preserve selected model and one held-out evaluation |
| CLI subcommands, `report`, `profile` | Not yet automated: no test calls `sentinel.cli.main`; `report.py` and `profiling.py` have no tests. Proposed tests in `docs/TESTING.md` | Each command exits 0 and writes its documented output |
| Firmware parser / alarm logic | Not yet done: firmware is compiled only (`platformio run -e uno -e uno_csv`), no native tests | Same golden vectors as `test_protocol.py` |
| Web UI in a browser | Not yet done: `npm run build` only, never viewed (2026-09-27) | State colours, stale badge, live updates, mobile layout |
| USB unplug/replug | Not yet done: the COM port was reported to disappear on unplug, but no controlled test with logs exists (2026-09-27). The mock reconnect test above is not a USB test | UNKNOWN within host timeout; reconnect/config/start; no stale command replay |
| Arduino reset | Not yet done (2026-09-27): boot IDs in the captures (47 and 55 in the last records) show the Uno has been reset many times, but no controlled reset test with logs exists | Changed boot/session clears windows; host re-establishes state |
| Stop Python | Not yet done (2026-09-27); note a Ctrl-C/kill stops the host only. Firmware drops non-FAULT states to UNKNOWN after 3 s and keeps FAULT, but any later host SET_ALARM/CLEAR_ALARM (including the reconnect SET_ALARM(3)) overrides it | MCU watchdog UNKNOWN, or existing FAULT remains until a host command changes it |
| Missing sensor | Not yet done; rewire only powered off (ultrasonic echo dropouts were observed, but that is not a removed sensor) | Invalid reading flags; no fake measurements |
| Physical alarm latency | Not yet done; needs a common-clock capture | Measure command/ACK/actual GPIO separately |

For hardware evidence record configuration, date, duration, observed/expected
behavior, exact logs, root cause and retest. T0 sensor conversion and T1 host
receipt are in different clock domains. Use a shared logic-analyzer trigger or
explicit clock mapping before claiming one-way latency. Host stage timings use
`perf_counter`; software timing results exclude physical actuation.
