import json
from pathlib import Path
import sqlite3
import time
import uuid
import pyarrow as pa
import pyarrow.parquet as pq

# Version 0 (unstamped) databases already have the version 1 layout; the first open stamps them.
# A column change must add a real migration keyed on this number.
SCHEMA_VERSION = 1
# Raw rows reach disk after this many rows or seconds, whichever comes first. At the firmware's
# fixed 1 Hz report rate, a row-count-only threshold would hold data for many minutes.
FLUSH_ROWS = 1600
FLUSH_SECONDS = 30.0
STATUS_STALE_SECONDS = 10.0

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS experiment_run (
 run_id TEXT PRIMARY KEY, machine_id TEXT NOT NULL, started_at REAL NOT NULL,
 ended_at REAL, condition TEXT NOT NULL, simulated INTEGER NOT NULL,
 sampling_rate REAL NOT NULL, metadata TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS raw_chunk (
 path TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES experiment_run,
 rows INTEGER NOT NULL, first_sequence INTEGER NOT NULL, last_sequence INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS feature_window (
 window_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES experiment_run,
 timestamp REAL NOT NULL, features TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS feature_run ON feature_window(run_id, timestamp);
CREATE TABLE IF NOT EXISTS prediction (
 window_id TEXT PRIMARY KEY REFERENCES feature_window, model_version TEXT NOT NULL,
 state TEXT NOT NULL, score REAL NOT NULL, latency_ms REAL NOT NULL);
CREATE TABLE IF NOT EXISTS event (
 event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES experiment_run,
 started_at REAL NOT NULL, ended_at REAL, state TEXT NOT NULL, score REAL,
 alarm_state TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS event_run ON event(run_id, started_at);
CREATE TABLE IF NOT EXISTS model (
 version TEXT PRIMARY KEY, created_at REAL NOT NULL, path TEXT NOT NULL, metadata TEXT NOT NULL);
"""


def connect(root, readonly=False):
    root = Path(root)
    if readonly:
        db = sqlite3.connect(f"file:{(root / 'sentinel.sqlite').as_posix()}?mode=ro", uri=True, timeout=10)
    else:
        root.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(root / "sentinel.sqlite", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def ensure_schema(db):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(f"database schema v{version} is newer than this code (v{SCHEMA_VERSION})")
    db.executescript(SCHEMA)
    if version < SCHEMA_VERSION:
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.db = connect(root)
        ensure_schema(self.db)
        self.pending = []
        self.last_flush = time.monotonic()
        self.run_id = None
        self.event_id = None
        self.event_state = None

    def start(self, condition, fs, simulated, metadata=None, machine="rig-1"):
        if self.run_id:
            raise RuntimeError("run already started")
        self.run_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO experiment_run (run_id, machine_id, started_at, ended_at, condition, simulated,"
            " sampling_rate, metadata, status) VALUES (?,?,?,?,?,?,?,?,?)",
            (self.run_id, machine, time.time(), None, condition, int(simulated), fs,
             json.dumps(metadata or {}), "RUNNING"))
        self.db.commit()
        return self.run_id

    def raw(self, record):
        self.pending.append(dict(record, run_id=self.run_id))
        if len(self.pending) >= FLUSH_ROWS:
            self.flush()
        else:
            self.flush_due()

    def flush_due(self):
        # Also called from the acquisition loop, so a stream that stops still gets its tail written.
        if self.pending and time.monotonic() - self.last_flush >= FLUSH_SECONDS:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        directory = self.root / "raw" / self.run_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (str(uuid.uuid4()) + ".parquet")
        temporary = path.with_suffix(".partial")
        pq.write_table(pa.Table.from_pylist(self.pending), temporary, compression="zstd")
        temporary.replace(path)
        # File first, manifest second: crash can leave an orphan, never a partial referenced file.
        self.db.execute(
            "INSERT INTO raw_chunk (path, run_id, rows, first_sequence, last_sequence) VALUES (?,?,?,?,?)",
            (str(path.relative_to(self.root)), self.run_id, len(self.pending),
             self.pending[0]["sequence"], self.pending[-1]["sequence"]))
        self.db.commit()
        self.pending.clear()
        self.last_flush = time.monotonic()

    def window(self, timestamp, features, model, state, score, latency):
        window_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO feature_window (window_id, run_id, timestamp, features) VALUES (?,?,?,?)",
                        (window_id, self.run_id, timestamp, json.dumps(features, allow_nan=False)))
        self.db.execute("INSERT INTO prediction (window_id, model_version, state, score, latency_ms)"
                        " VALUES (?,?,?,?,?)", (window_id, model, state, score, latency))
        self.transition(timestamp, state, score)
        self.db.commit()

    def transition(self, timestamp, state, score=None, alarm="unconfirmed"):
        if state == self.event_state:
            return
        if self.event_id:
            self.db.execute("UPDATE event SET ended_at=? WHERE event_id=?", (timestamp, self.event_id))
        self.event_id = str(uuid.uuid4())
        self.event_state = state
        self.db.execute("INSERT INTO event (event_id, run_id, started_at, ended_at, state, score, alarm_state)"
                        " VALUES (?,?,?,?,?,?,?)",
                        (self.event_id, self.run_id, timestamp, None, state, score, alarm))
        self.db.commit()

    def alarm_ack(self, state):
        if self.event_id:
            self.db.execute("UPDATE event SET alarm_state=? WHERE event_id=?", (state, self.event_id))
            self.db.commit()

    def close(self, status="COMPLETE"):
        flush_error = None
        try:
            self.flush()
        except Exception as error:
            flush_error, status = error, "FAILED"
        try:
            now = time.time()
            if self.event_id:
                self.db.execute("UPDATE event SET ended_at=? WHERE event_id=?", (now, self.event_id))
            if self.run_id:
                self.db.execute("UPDATE experiment_run SET ended_at=?, status=? WHERE run_id=?", (now, status, self.run_id))
            self.db.commit()
        finally:
            self.db.close()
        if flush_error:
            raise flush_error


def reconcile(root):
    """Mark runs a killed process left RUNNING as INTERRUPTED and close their open events."""
    root = Path(root)
    if not (root / "sentinel.sqlite").is_file():
        return []
    live = None
    try:
        snapshot = json.loads((root / "status.json").read_text())
        if time.time() - snapshot["updated_at"] <= STATUS_STALE_SECONDS and "acquisition_status" not in snapshot:
            live = snapshot["run_id"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    reconciled = []
    db = connect(root)
    try:
        for run_id, started in db.execute("SELECT run_id, started_at FROM experiment_run WHERE status='RUNNING'").fetchall():
            if run_id == live:
                continue
            last = db.execute("SELECT MAX(timestamp) FROM feature_window WHERE run_id=?", (run_id,)).fetchone()[0]
            ended = max(started, last or started)
            db.execute("UPDATE event SET ended_at=? WHERE run_id=? AND ended_at IS NULL", (ended, run_id))
            db.execute("UPDATE experiment_run SET ended_at=?, status='INTERRUPTED' WHERE run_id=?", (ended, run_id))
            reconciled.append(run_id)
        db.commit()
    finally:
        db.close()
    return reconciled


def audit(root):
    root = Path(root)
    db = connect(root, readonly=True)
    try:
        tracked = {r[0] for r in db.execute("SELECT path FROM raw_chunk")}
        unfinished = [r[0] for r in db.execute("SELECT run_id FROM experiment_run WHERE status='RUNNING'")]
    finally:
        db.close()
    actual = {str(p.relative_to(root)) for p in root.glob("raw/**/*.parquet")}
    return {"missing": sorted(tracked - actual), "orphaned": sorted(actual - tracked),
            "partial": [str(p.relative_to(root)) for p in root.glob("raw/**/*.partial")],
            "unfinished_runs": unfinished}
