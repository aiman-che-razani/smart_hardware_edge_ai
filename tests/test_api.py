import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sentinel.api.main import create_app
from sentinel.runner import run
from sentinel.storage.database import connect
import json
import time
from sentinel.storage.queries import status

LOCAL = "http://127.0.0.1"


def client(root):
    return TestClient(create_app(root), base_url=LOCAL)


def test_foreign_host_header_is_refused_to_stop_dns_rebinding(tmp_path):
    with TestClient(create_app(tmp_path), base_url="http://attacker.example") as foreign:
        assert foreign.get("/api/health").status_code == 400
    with client(tmp_path) as local:
        assert local.get("/api/health").status_code == 200


def test_live_socket_refuses_a_cross_origin_page(tmp_path):
    with client(tmp_path) as local:
        with pytest.raises(WebSocketDisconnect):
            with local.websocket_connect("ws://127.0.0.1/api/live", headers={"origin": "http://evil.example"}):
                pass
        with local.websocket_connect("ws://127.0.0.1/api/live", headers={"origin": "http://127.0.0.1"}) as socket:
            assert socket.receive_json()["state"] == "UNKNOWN"


@pytest.mark.parametrize("content", ["not json", "[]", "{}", '{"updated_at": "yesterday"}', '{"updated_at": null}'])
def test_malformed_status_snapshot_is_unknown_not_a_server_error(tmp_path, content):
    (tmp_path / "status.json").parent.mkdir(exist_ok=True)
    with client(tmp_path) as local:
        (tmp_path / "status.json").write_text(content)
        response = local.get("/api/system/status")
    assert response.status_code == 200
    assert response.json()["state"] == "UNKNOWN" and response.json()["stale"] is True


def test_empty_run_id_means_latest_run_everywhere(tmp_path):
    run(tmp_path, 40, "NORMAL")
    with client(tmp_path) as local:
        assert local.get("/api/measurements?run_id=").json() == local.get("/api/measurements").json() != []
        assert local.get("/api/predictions?run_id=").json() == local.get("/api/predictions").json() != []
        assert local.get("/api/features?run_id=").json() == local.get("/api/features").json() != []


def test_events_can_be_filtered_by_run(tmp_path):
    first = run(tmp_path, 40, "NORMAL")["run_id"]
    second = run(tmp_path, 40, "LOW_WATER", seed=7)["run_id"]
    with client(tmp_path) as local:
        only_first = local.get(f"/api/events?run_id={first}").json()
        assert only_first and {e["run_id"] for e in only_first} == {first}
        assert {e["run_id"] for e in local.get("/api/events").json()} == {first, second}


def test_raw_path_outside_the_data_directory_is_a_client_error(tmp_path):
    run_id = run(tmp_path, 3, "NORMAL")["run_id"]
    with connect(tmp_path) as db:
        db.execute("INSERT INTO raw_chunk (path, run_id, rows, first_sequence, last_sequence) VALUES (?,?,?,?,?)",
                   ("../outside.parquet", run_id, 1, 0, 0))
    with client(tmp_path) as local:
        assert local.get(f"/api/measurements?run_id={run_id}").status_code == 400


def test_measurements_span_many_small_chunks(tmp_path, monkeypatch):
    from sentinel.storage import database
    monkeypatch.setattr(database, "FLUSH_ROWS", 10)
    run(tmp_path, 95, "NORMAL")
    with client(tmp_path) as local:
        assert len(local.get("/api/measurements?limit=800").json()) == 95
        assert len(local.get("/api/measurements?limit=25").json()) == 25


def test_status_is_live_only_when_fresh_and_not_finished(tmp_path):
    def write(**fields):
        (tmp_path / "status.json").write_text(json.dumps(fields))
    write(updated_at=time.time(), state="NORMAL")
    assert status(tmp_path)["state"] == "NORMAL" and status(tmp_path)["stale"] is False
    write(updated_at=time.time() - 4, state="NORMAL")
    assert status(tmp_path)["state"] == "UNKNOWN" and status(tmp_path)["stale"] is True
    write(updated_at=time.time(), state="FAULT", acquisition_status="COMPLETE")
    assert status(tmp_path)["state"] == "UNKNOWN" and status(tmp_path)["stale"] is False
    (tmp_path / "status.json").unlink()
    assert status(tmp_path) == {"state": "UNKNOWN", "stale": True}


@pytest.mark.parametrize("path,limit,code", [
    ("measurements", 0, 422), ("measurements", 3200, 200), ("measurements", 3201, 422),
    ("experiments", 1001, 422), ("features", 0, 422), ("predictions", 1001, 422),
    ("events", 1000, 200), ("events", -1, 422),
])
def test_api_limits_are_enforced_at_the_boundary(tmp_path, path, limit, code):
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as local:
        assert local.get(f"/api/{path}?limit={limit}").status_code == code


@pytest.mark.parametrize("host,code", [
    ("localhost", 200), ("localhost:8000", 200), ("127.0.0.1:8000", 200),
    ("localhost.evil.example", 400), ("evil.example:8000", 400), ("", 400),
])
def test_host_check_accepts_only_exact_loopback_names_with_or_without_a_port(tmp_path, host, code):
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as local:
        assert local.get("/api/health", headers={"host": host}).status_code == code


def test_unknown_run_id_returns_empty_lists_not_errors(tmp_path):
    run(tmp_path, 3, "NORMAL")
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as local:
        for endpoint in ("measurements", "features", "predictions", "events"):
            assert local.get(f"/api/{endpoint}?run_id=no-such-run").json() == []
