import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
import pyarrow.parquet as pq
from sentinel.storage.database import Store, connect


def query(root, sql, parameters=()):
    with connect(root) as db:
        return [dict(r) for r in db.execute(sql, parameters)]


def status(root):
    import time
    try:
        value = json.loads((Path(root)/"status.json").read_text())
        value["stale"] = time.time()-value["updated_at"] > 3
        if value["stale"] or value.get("acquisition_status"):
            value["state"] = "UNKNOWN"
        return value
    except (FileNotFoundError, PermissionError, json.JSONDecodeError):
        return {"state": "UNKNOWN", "stale": True}


def measurements(root, run_id=None, limit=800):
    if run_id is None:
        latest = query(root, "SELECT run_id FROM experiment_run ORDER BY started_at DESC LIMIT 1")
        if not latest:
            return []
        run_id = latest[0]["run_id"]
    sql = "SELECT path FROM raw_chunk"
    args = ()
    if run_id:
        sql += " WHERE run_id=?"
        args = (run_id,)
    rows = query(root, sql+" ORDER BY rowid DESC LIMIT 4", args)
    result = []
    for row in rows:
        path = (Path(root)/row["path"]).resolve()
        if Path(root).resolve() not in path.parents:
            raise ValueError("raw path outside data directory")
        result = pq.read_table(path).to_pylist() + result
        if len(result) >= limit:
            break
    return result[-limit:]


def create_app(root="data"):
    Store(root).close()
    app = FastAPI(title="SentinelDAQ", version="0.1.0")

    @app.get("/health")
    def health():
        return {"service": "ok", "daq": status(root)}

    @app.get("/system/status")
    def system_status():
        return status(root)

    @app.get("/machines")
    def machines():
        return query(root, "SELECT DISTINCT machine_id FROM experiment_run")

    @app.get("/experiments")
    def experiments(limit: int = Query(100, ge=1, le=1000)):
        return query(root, "SELECT * FROM experiment_run ORDER BY started_at DESC LIMIT ?", (limit,))

    @app.get("/measurements")
    def raw(run_id: str = None, limit: int = Query(800, ge=1, le=3200)):
        return measurements(root, run_id, limit)

    @app.get("/features")
    def features(run_id: str = None, limit: int = Query(100, ge=1, le=1000)):
        return query(root, "SELECT * FROM feature_window WHERE (? IS NULL OR run_id=?) ORDER BY timestamp DESC LIMIT ?", (run_id, run_id, limit))

    @app.get("/predictions")
    def predictions(limit: int = Query(100, ge=1, le=1000)):
        return query(root, "SELECT p.*, f.run_id, f.timestamp FROM prediction p JOIN feature_window f USING(window_id) ORDER BY timestamp DESC LIMIT ?", (limit,))

    @app.get("/events")
    def events(limit: int = Query(100, ge=1, le=1000)):
        return query(root, "SELECT * FROM event ORDER BY started_at DESC LIMIT ?", (limit,))

    @app.websocket("/live")
    async def live(socket: WebSocket):
        await socket.accept()
        try:
            while True:
                await socket.send_json(status(root))
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass
    return app
