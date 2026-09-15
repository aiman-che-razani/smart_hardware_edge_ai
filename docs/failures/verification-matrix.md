# Verification matrix

| Test | Automated path / manual procedure | Expected behavior |
|---|---|---|
| Fragment every byte boundary | `test_protocol.py` | Identical decoded sample |
| CRC corruption / unknown type / long input | protocol tests | Reject, increment counter, recover boundedly |
| Truncated frame | parser timeout test | Clear stale fragment and decode next frame |
| Sequence gap / duplicate / wrap / boot change | continuity tests | Count loss, reject duplicate, preserve wrap, start session |
| ACK lost / duplicate command / wrong ACK | command/simulator tests | Same retry bytes, idempotent state, ignore wrong ID |
| Serial reconnection | Mock serial-owner integration test | Reopen/configure and resume after injected cable loss |
| Windows status file locked | Injected file lock and observed stress rerun | Skip snapshot; keep collecting measurements |
| Invalid sensor / FIFO overflow | pipeline failure tests | Clear window and UNKNOWN |
| Known sine / DC / constant input | DSP tests | Known RMS, amplitude, moments and energy |
| State persistence/recovery | state tests | No single-window FAULT; sustained clear |
| Storage round-trip / orphan / partial | storage tests and audit | Read complete records; identify unfinished evidence |
| API/UI integration | TestClient / Flask test client | Bounded endpoint responses and page loads |
| Dataset split | ML integration test | No overlapping run IDs; physical mode refuses synthetic data |
| Freeze/evaluation | ML workflow | Preserve selected model and one held-out evaluation |
| USB unplug/replug | Pending real board | UNKNOWN within host timeout; reconnect/config/start; no stale command replay |
| Arduino reset | Pending real board | Changed boot/session clears windows; host re-establishes state |
| Stop Python | Pending real board | MCU watchdog UNKNOWN, or existing FAULT remains latched |
| Missing sensor | Pending real board, rewire only powered off | Invalid reading flags; no fake measurements |
| Physical alarm latency | Pending common-clock capture | Measure command/ACK/actual GPIO separately |

For hardware evidence record configuration, date, duration, observed/expected
behavior, exact logs, root cause and retest. T0 sensor conversion and T1 host
receipt are in different clock domains. Use a shared logic-analyzer trigger or
explicit clock mapping before claiming one-way latency. Host stage timings use
`perf_counter`; software timing results exclude physical actuation.
