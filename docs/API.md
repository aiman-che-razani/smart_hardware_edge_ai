# SentinelDAQ host API

Read-only JSON over HTTP plus one WebSocket, served by `create_app(root, allowed_hosts)`
(`python/sentinel/api/main.py:18`). All routes are under `/api` (`main.py:24`). Start it with
`python -m sentinel --data data/demo api --port 8001`; it binds `127.0.0.1` (`cli.py`), default
port 8000. The serial wire protocol is a separate interface: see [protocol/v1.md](protocol/v1.md)
and [ADR-009](decisions/ADR-009-serial-protocol-v1.md).

## Conventions

- No trailing slash, no auth, no CORS middleware, no writes. A command endpoint would let the
  browser drive the physical alarm; it needs security and architecture sign-off first.
- Timestamps are UTC epoch seconds (float). Responses are plain JSON lists of row dicts, except
  `health` and `system/status`. `features` (feature_window) and `metadata` columns are raw JSON strings.
- Errors are FastAPI defaults (`422` validation, `404`, `400` for a bad raw path); no custom envelope.
- Host check (`main.py:23`): only Host `127.0.0.1` and `localhost` are accepted (`LOCAL_HOSTS`,
  `main.py:15`); anything else gets 400 (DNS-rebinding defence). `[::1]` is not accepted, because
  the server binds IPv4 only and Starlette cannot match a bracketed IPv6 Host.
- An empty `run_id=` means "no filter / latest" on every route.
- Data access lives in `python/sentinel/storage/queries.py`, not in the routes.

## Routes

| Route | Params (default, bounds) | Response |
|---|---|---|
| `GET /api/health` | none | `{service:"ok", daq:<status object>}` |
| `GET /api/system/status` | none | `status.json` snapshot plus `stale` (bool, older than 3 s). `state` is forced `"UNKNOWN"` when stale or when `acquisition_status` is set. Missing/invalid file gives `{state:"UNKNOWN", stale:true}` (`queries.py:15`). |
| `GET /api/machines` | none | `[{machine_id}]` (distinct) |
| `GET /api/experiments` | `limit` (100, 1-1000) | `experiment_run` rows, newest `started_at` first |
| `GET /api/measurements` | `run_id`, `limit` (800, 1-3200) | raw Parquet rows, oldest to newest, last `limit`. Latest run if `run_id` omitted/empty; `[]` if no runs. Chunks are read newest-first until `limit` rows. A chunk path outside the data dir gives 400. |
| `GET /api/features` | `run_id`, `limit` (100, 1-1000) | `feature_window` rows, newest first |
| `GET /api/predictions` | `run_id`, `limit` (100, 1-1000) | `prediction` rows joined to `feature_window` (adds `run_id`, `timestamp`), newest first |
| `GET /api/events` | `run_id`, `limit` (100, 1-1000) | `event` rows, newest `started_at` first |
| `WS /api/live` | none | sends the status object (same as `system/status`) once per second until the client disconnects |

`/api/live` origin rule (`main.py:66`): if an `Origin` header is present and is not the same origin
as `Host`, the socket is closed with code 1008 before any data is sent. Clients without an Origin
header (scripts) are allowed. Note: the code calls `close` before `accept`, which Starlette reports
to the client as an HTTP 403 handshake rejection, not a 1008 close frame.

`/` serves `frontend/dist` (`StaticFiles`, `html=True`) when built; otherwise only `/api/*` exists.

## Known issue

`GET /openapi.json` (and so `/docs`) returns 500 on Python 3.9.0: it cannot flatten nested `Literal`
types that pydantic's JSON-schema generator needs. Use a Python >= 3.9.1 venv; `create_app` logs a
warning on 3.9.0.

## Frontend usage

`frontend/src/api.js` uses relative `/api/...` (no trailing slash). `App.jsx` polls once per second:
`status`, `experiments`, `measurements` (selected and compare run), `predictions`, `events(10)`.
Not used by the UI: `/api/live`, `/api/features`, `/api/machines`, `/api/health`. `api.events` takes
no run id. The Vite dev proxy target is `VITE_API_PROXY` / `SENTINEL_API_URL`, default
`http://localhost:8000`. A route rename must update `api.js`, the proxy, and `tests/test_integration.py`.

## Testing notes

Use `TestClient(app, base_url="http://127.0.0.1")` and absolute `ws://127.0.0.1/...` WebSocket URLs
(the test client hard-codes `testserver` for WebSockets, which the host check rejects).

## Dependencies

`starlette>=0.49.1` (CVE-2025-62727, Range-header DoS in `FileResponse`/`StaticFiles`) with
`fastapi>=0.121,<0.125` (`pyproject.toml`).
