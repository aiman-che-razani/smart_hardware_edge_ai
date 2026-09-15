import json
from pathlib import Path
import sqlite3
import time
import uuid
import pyarrow as pa
import pyarrow.parquet as pq

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


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "sentinel.sqlite", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.db = connect(root)
        self.db.executescript(SCHEMA)
        self.pending = []
        self.run_id = None
        self.event_id = None
        self.event_state = None

    def start(self, condition, fs, simulated, metadata=None, machine="rig-1"):
        if self.run_id:
            raise RuntimeError("run already started")
        self.run_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO experiment_run VALUES (?,?,?,?,?,?,?,?,?)",
                        (self.run_id, machine, time.time(), None, condition, int(simulated), fs,
                         json.dumps(metadata or {}), "RUNNING"))
        self.db.commit()
        return self.run_id

    def raw(self, record):
        self.pending.append(dict(record, run_id=self.run_id))
        if len(self.pending) >= 1600:
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
        self.db.execute("INSERT INTO raw_chunk VALUES (?,?,?,?,?)",
                        (str(path.relative_to(self.root)), self.run_id, len(self.pending),
                         self.pending[0]["sequence"], self.pending[-1]["sequence"]))
        self.db.commit()
        self.pending.clear()

    def window(self, timestamp, features, model, state, score, latency):
        window_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO feature_window VALUES (?,?,?,?)",
                        (window_id, self.run_id, timestamp, json.dumps(features, allow_nan=False)))
        self.db.execute("INSERT INTO prediction VALUES (?,?,?,?,?)", (window_id, model, state, score, latency))
        self.transition(timestamp, state, score)
        self.db.commit()

    def transition(self, timestamp, state, score=None, alarm="unconfirmed"):
        if state == self.event_state:
            return
        if self.event_id:
            self.db.execute("UPDATE event SET ended_at=? WHERE event_id=?", (timestamp, self.event_id))
        self.event_id = str(uuid.uuid4())
        self.event_state = state
        self.db.execute("INSERT INTO event VALUES (?,?,?,?,?,?,?)",
                        (self.event_id, self.run_id, timestamp, None, state, score, alarm))
        self.db.commit()

    def alarm_ack(self, state):
        if self.event_id:
            self.db.execute("UPDATE event SET alarm_state=? WHERE event_id=?", (state, self.event_id))
            self.db.commit()

    def close(self, status="COMPLETE"):
        try:
            self.flush()
            now = time.time()
            if self.event_id:
                self.db.execute("UPDATE event SET ended_at=? WHERE event_id=?", (now, self.event_id))
            if self.run_id:
                self.db.execute("UPDATE experiment_run SET ended_at=?, status=? WHERE run_id=?", (now, status, self.run_id))
            self.db.commit()
        finally:
            self.db.close()


def audit(root):
    root = Path(root)
    with connect(root) as db:
        tracked = {r[0] for r in db.execute("SELECT path FROM raw_chunk")}
        unfinished = [r[0] for r in db.execute("SELECT run_id FROM experiment_run WHERE status='RUNNING'")]
    actual = {str(p.relative_to(root)) for p in root.glob("raw/**/*.parquet")}
    return {"missing": sorted(tracked - actual), "orphaned": sorted(actual - tracked),
            "partial": [str(p.relative_to(root)) for p in root.glob("raw/**/*.partial")],
            "unfinished_runs": unfinished}
