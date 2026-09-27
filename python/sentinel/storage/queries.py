"""Read-only queries shared by the API and the report export."""
import contextlib
import json
from pathlib import Path
import time
import pyarrow.parquet as pq
from sentinel.storage.database import connect


def query(root, sql, parameters=()):
    with contextlib.closing(connect(root, readonly=True)) as db:
        return [dict(r) for r in db.execute(sql, parameters)]


def status(root):
    try:
        value = json.loads((Path(root)/"status.json").read_text())
        if not isinstance(value, dict):
            raise ValueError("status snapshot is not an object")
    except (OSError, ValueError):
        return {"state": "UNKNOWN", "stale": True}
    updated = value.get("updated_at")
    value["stale"] = not isinstance(updated, (int, float)) or time.time()-updated > 3
    if value["stale"] or value.get("acquisition_status"):
        value["state"] = "UNKNOWN"
    return value


def measurements(root, run_id=None, limit=800):
    if not run_id:
        latest = query(root, "SELECT run_id FROM experiment_run ORDER BY started_at DESC LIMIT 1")
        if not latest:
            return []
        run_id = latest[0]["run_id"]
    result = []
    for row in query(root, "SELECT path, rows FROM raw_chunk WHERE run_id=? ORDER BY rowid DESC", (run_id,)):
        path = (Path(root)/row["path"]).resolve()
        if Path(root).resolve() not in path.parents:
            raise ValueError("raw path outside data directory")
        result = pq.read_table(path).to_pylist() + result
        if len(result) >= limit:
            break
    return result[-limit:]
