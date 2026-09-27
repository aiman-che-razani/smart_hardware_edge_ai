import json
import sqlite3
import time
import pytest
from sentinel.runner import run
from sentinel.storage import database
from sentinel.storage.database import SCHEMA_VERSION, Store, audit, connect, reconcile


def test_raw_rows_reach_disk_on_a_timer_not_only_at_the_row_threshold(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(database.time, "monotonic", lambda: now[0])
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    for sequence in range(5):
        store.raw({"sequence": sequence})
    assert store.pending and not audit(tmp_path)["orphaned"]
    now[0] = database.FLUSH_SECONDS
    store.raw({"sequence": 5})
    assert not store.pending
    with connect(tmp_path) as db:
        assert db.execute("SELECT SUM(rows) FROM raw_chunk").fetchone()[0] == 6
    report = audit(tmp_path)
    assert not (report["missing"] or report["orphaned"] or report["partial"])
    store.close()


def test_killed_run_is_reconciled_and_open_events_are_closed(tmp_path):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    store.transition(time.time(), "NORMAL")
    assert audit(tmp_path)["unfinished_runs"] == [run_id]
    assert reconcile(tmp_path) == [run_id]
    with connect(tmp_path) as db:
        run_row = db.execute("SELECT status, ended_at FROM experiment_run").fetchone()
        assert run_row["status"] == "INTERRUPTED" and run_row["ended_at"] is not None
        assert db.execute("SELECT COUNT(*) FROM event WHERE ended_at IS NULL").fetchone()[0] == 0
    assert audit(tmp_path)["unfinished_runs"] == []
    store.db.close()


def test_reconcile_leaves_a_run_that_is_publishing_live_status(tmp_path):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    (tmp_path / "status.json").write_text(json.dumps({"run_id": run_id, "updated_at": time.time()}))
    assert reconcile(tmp_path) == []
    store.db.close()


def test_schema_is_versioned_and_unstamped_databases_are_adopted(tmp_path):
    Store(tmp_path).close()
    with connect(tmp_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    old = sqlite3.connect(legacy / "sentinel.sqlite")
    old.executescript(database.SCHEMA)
    old.execute("INSERT INTO model (version, created_at, path, metadata) VALUES ('m', 0, 'p', '{}')")
    old.commit()
    assert old.execute("PRAGMA user_version").fetchone()[0] == 0
    old.close()
    Store(legacy).close()
    with connect(legacy) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert db.execute("SELECT COUNT(*) FROM model").fetchone()[0] == 1


def test_database_from_a_newer_version_is_refused(tmp_path):
    Store(tmp_path).close()
    with connect(tmp_path) as db:
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
    with pytest.raises(RuntimeError):
        Store(tmp_path)


def test_close_marks_the_run_failed_when_the_final_flush_fails(tmp_path, monkeypatch):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    store.raw({"sequence": 0})

    def broken():
        raise OSError("disk full")
    monkeypatch.setattr(store, "flush", broken)
    with pytest.raises(OSError):
        store.close()
    with connect(tmp_path) as db:
        assert db.execute("SELECT status FROM experiment_run WHERE run_id=?", (run_id,)).fetchone()[0] == "FAILED"


def test_audit_is_read_only_and_does_not_create_the_directory(tmp_path):
    with pytest.raises(sqlite3.OperationalError):
        audit(tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_equal_calibration_points_are_rejected_before_a_run_is_recorded(tmp_path):
    for bad in ({"distance_empty_mm": 500, "distance_full_mm": 500}, {"water_dry_raw": 300, "water_wet_raw": 300}):
        with pytest.raises(ValueError):
            run(tmp_path, 1, "NORMAL", **bad)
    assert not (tmp_path / "sentinel.sqlite").exists()


def test_a_failed_flush_keeps_the_rows_and_a_later_flush_writes_them_once(tmp_path, monkeypatch):
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    for sequence in range(3):
        store.raw({"sequence": sequence})
    good = database.pq.write_table

    def broken(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(database.pq, "write_table", broken)
    with pytest.raises(OSError):
        store.flush()
    assert len(store.pending) == 3 and audit(tmp_path)["orphaned"] == []
    monkeypatch.setattr(database.pq, "write_table", good)
    store.flush()
    with connect(tmp_path) as db:
        assert db.execute("SELECT SUM(rows), COUNT(*) FROM raw_chunk").fetchone()[:] == (3, 1)
    assert not any(v for k, v in audit(tmp_path).items() if k != "unfinished_runs")
    store.close()


@pytest.mark.parametrize("snapshot", [
    {"updated_at": "old"}, {"acquisition_status": "COMPLETE"}, {"updated_at": 0},
])
def test_reconcile_takes_over_a_run_whose_status_is_stale_or_finished(tmp_path, snapshot):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    (tmp_path / "status.json").write_text(json.dumps(dict(snapshot, run_id=run_id, **({} if "updated_at" in snapshot else {"updated_at": time.time()}))))
    assert reconcile(tmp_path) == [run_id]
    store.db.close()


def test_reconcile_stamps_the_run_end_with_its_last_window_not_now(tmp_path):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    started = store.db.execute("SELECT started_at FROM experiment_run").fetchone()[0]
    store.window(started + 5.0, {"x": 1.0}, "m", "NORMAL", 0.1, 1.0)
    assert reconcile(tmp_path) == [run_id]
    with connect(tmp_path) as db:
        assert db.execute("SELECT ended_at FROM experiment_run").fetchone()[0] == pytest.approx(started + 5.0)
        assert db.execute("SELECT ended_at FROM event").fetchone()[0] == pytest.approx(started + 5.0)
    store.db.close()


def test_flush_due_writes_the_tail_even_when_no_new_row_arrives(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(database.time, "monotonic", lambda: now[0])
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    store.raw({"sequence": 0})
    store.flush_due()
    assert store.pending
    now[0] = database.FLUSH_SECONDS
    store.flush_due()
    assert not store.pending
    store.close()


def test_reconcile_of_a_data_directory_that_was_never_used_creates_nothing(tmp_path):
    assert reconcile(tmp_path / "never-used") == []
    assert not (tmp_path / "never-used").exists()
