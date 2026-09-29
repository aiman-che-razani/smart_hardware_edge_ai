# SentinelDAQ security and safety

Last reviewed: 2026-09-29. Scope: local tool, single user, no deployment.

## Threat model

Assets: the user's PC (code execution), physical alarm outputs (LEDs, PN2222 buzzer; advisory, not a safety shutoff), run data and models under `data/`, and the integrity of simulated vs physical labelling.

Threats: a malicious web page talking to `127.0.0.1:8000`; a tampered model artifact; hostile serial bytes; path traversal via stored paths; dependency CVEs; API exposed beyond localhost; a synthetic model driving a physical alarm.

## Controls (verified 2026-09-29)

1. Model integrity: `ml/inference.py::load_artifact` requires a matching `<model>.joblib.sha256` and unpickles the bytes it hashed. Used by `Inference` and `train.evaluate`. `train` writes the sidecar and records `model_sha256`.
2. Host/Origin: `TrustedHostMiddleware` with `LOCAL_HOSTS` (`api/main.py`); `/api/live` refuses Origin not equal to Host. No CORS. `cli.py:89` binds `127.0.0.1`.
3. Dependencies: `starlette>=0.49.1`, `fastapi>=0.121,<0.125`; `plotly` optional (`report`, `dev`).
4. Robustness: `queries.status` never raises; raw paths escaping the data dir give 400; equal calibration points rejected.
5. `.gitignore` covers `.env`, `data/`, `*.sqlite*`, `*.parquet`, `*.log`, `.venv/`, `.pio/`, `node_modules/`, `.claude/settings.local.json`. `frontend/dist/` is covered by the `dist/` rule.
6. Command validation (added 2026-09-29): `acquisition/commands.py::Commands.begin` rejects non-command kinds and out-of-range values (SET_ALARM 0..3, else 0..255) before anything is encoded. The firmware also checks `value<=3` and answers unknown kinds with an error ACK.

## Known-issues register

| # | Severity if regressed | Issue | Status |
|---|---|---|---|
| 1 | Critical | Model loading is code execution (`joblib.load`). The SHA-256 sidecar stops accidents, not an attacker who can write the model directory. Keep models on trusted local disk; never add a fetch/upload path. | Accepted residual |
| 2 | High | Synthetic-model guard in `Inference.__init__`; schema, pipeline version, `fs`, window and calibration checked (`pipeline.py:31-35`). | Holds |
| 3 | Critical | API is unauthenticated and read-only on loopback. Any write/command route, non-loopback bind or wildcard CORS needs an auth design first. | Holds (all routes GET/WS) |
| 4 | Medium | Parquet path containment (`queries.py::measurements`) holds; SQL uses bound parameters. `benchmark.py` joins a manifest path without containment (CLI only, trusted DB). | Accepted |
| 5 | Medium | Serial parser bounds: host `MAX_PAYLOAD` 40, CRC, 500 ms timeout, unknown kinds counted; firmware `kFrameMax`, `kMaxPayload`, CRC, timeout, `kRxBudget`. Firmware only accepts 3-byte command payloads. Recheck both sides for any new frame kind. | Holds |
| 6 | Low | A mismatched STATUS frame aborts the run on purpose (`runner.py:138`). | Accepted |
| 7 | High | Only `runner.py` sends `SET_ALARM`; a host `SET_ALARM`/`CLEAR_ALARM` overrides the firmware FAULT hold. Do not add an API/agent path to the alarm; do not present it as a safety shutoff. | Holds |
| 8 | Medium | Python 3.9.0 (EOL) breaks `/openapi.json`; use >= 3.9.1, ideally 3.11/3.12. `requires-python` is still `>=3.9`. The venv was not present in this checkout, so the version was not re-checked. | Open |
| 9 | High | Ignore rules for secrets and data (see control 5). | Holds |
| 10 | High | Never send commands to a serial port the user did not name (Bluetooth virtual ports are not the device). | Process rule |

Minor notes: `Inference` reads `self.artifact["simulated"]` etc. from the pickle, so a well-formed but hostile pickle is out of scope once the hash matches. The `/api/live` Origin check compares strings after the scheme, which is adequate given TrustedHost also restricts Host.

## Checklist for any diff

Auth/exposure unchanged? New route read-only? Bound parameters? Path checks intact? Model source trusted and hash-checked? Synthetic/physical separation intact? Parser bounds intact on both sides? Alarm commands unchanged in meaning? No secrets or data files staged?

## Review log

- 2026-09-29: all 2026-09-27 fixes confirmed present; no Critical or High findings. Added host-side command validation (Low, defence in depth). Tests were not run (pytest is not installed in this environment); the command change was checked with a manual import test.
