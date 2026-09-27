import json
import sys
import pytest
from sentinel import cli
from sentinel.report import export
from sentinel.runner import run
from sentinel.storage.database import Store, connect


def cli_run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["sentinel", *argv])
    cli.main()
    return capsys.readouterr().out


def test_cli_reconcile_reports_the_runs_it_closed(tmp_path, monkeypatch, capsys):
    store = Store(tmp_path)
    run_id = store.start("NORMAL", 1, True)
    assert json.loads(cli_run(monkeypatch, capsys, "--data", str(tmp_path), "reconcile")) == {"reconciled": [run_id]}
    assert json.loads(cli_run(monkeypatch, capsys, "--data", str(tmp_path), "reconcile")) == {"reconciled": []}
    store.db.close()


@pytest.mark.parametrize("args", [["--runs", "2"], ["--seconds", "1"]])
def test_cli_dataset_refuses_too_few_runs_or_seconds(tmp_path, monkeypatch, capsys, args):
    monkeypatch.setattr(sys, "argv", ["sentinel", "--data", str(tmp_path), "dataset", *args])
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert stop.value.code == 2
    assert not (tmp_path / "sentinel.sqlite").exists()


def test_cli_dataset_records_the_same_number_of_runs_for_every_class(tmp_path, monkeypatch, capsys):
    out = json.loads(cli_run(monkeypatch, capsys, "--data", str(tmp_path), "dataset", "--runs", "3", "--seconds", "2"))
    assert len(out) == 18
    with connect(tmp_path) as db:
        counts = dict(db.execute("SELECT condition, COUNT(*) FROM experiment_run GROUP BY condition").fetchall())
    assert counts == {c: 3 for c in ("NORMAL", "LOW_WATER", "OVERFLOW", "RAPID_DRAIN", "SENSOR_MISMATCH", "ENVIRONMENTAL_ANOMALY")}
    assert all(r["simulated"] for r in out)


def test_cli_simulate_then_analyze_then_report_then_profile(tmp_path, monkeypatch, capsys):
    data = str(tmp_path / "data")
    simulated = json.loads(cli_run(monkeypatch, capsys, "--data", data, "simulate", "--seconds", "40", "--condition", "NORMAL"))
    analysis = json.loads(cli_run(monkeypatch, capsys, "--data", data, "analyze", "--run-id", simulated["run_id"]))
    assert analysis["source"] == "SIMULATED" and analysis["records"] == 40
    assert (tmp_path / "data" / f"{simulated['run_id']}-benchmark.json").is_file()
    page = tmp_path / "out" / "report.html"
    exported = json.loads(cli_run(monkeypatch, capsys, "--data", data, "report", "--output", str(page)))
    assert exported["continuous"] is True and "SIMULATED" in page.read_text(encoding="utf-8")
    profile = json.loads(cli_run(monkeypatch, capsys, "profile", "--output", str(tmp_path / "p" / "profile.json")))
    assert profile["source"] == "GENERATED MICROBENCHMARK" and profile["model_version"] == "threshold-demo-v1"


def test_report_says_when_the_run_was_not_continuous_and_refuses_an_empty_directory(tmp_path):
    run(tmp_path, 20, "NORMAL", drop_every=7)
    assert export(tmp_path, tmp_path / "gap.html")["continuous"] is False
    Store(tmp_path / "empty").close()
    with pytest.raises(ValueError, match="no measurements"):
        export(tmp_path / "empty", tmp_path / "none.html")
    assert not (tmp_path / "none.html").exists()
