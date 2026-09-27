import json
import pytest
from fastapi.testclient import TestClient
from sentinel.runner import run
from sentinel.storage.database import audit, connect
from sentinel.api.main import create_app, measurements
from sentinel.ml.train import train, evaluate
from sentinel.ml.inference import Inference
import joblib


def test_end_to_end_and_api(tmp_path):
    result=run(tmp_path,90,"SENSOR_MISMATCH")
    assert result["samples"]==90
    assert result["windows"]==5
    assert result["state"]=="FAULT"
    assert result["parser_errors"]==0
    assert not any(audit(tmp_path).values())
    assert len(measurements(tmp_path,limit=800))==90
    with connect(tmp_path) as db:
        assert db.execute("SELECT alarm_state FROM event WHERE state='FAULT'").fetchone()[0]=="FAULT"
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as client:
        for endpoint in ("health","machines","experiments","features","predictions","events","measurements","system/status"):
            assert client.get('/api/'+endpoint).status_code==200
        assert client.get('/api/measurements?limit=999999').status_code==422
        assert client.get('/api/predictions?run_id='+result['run_id']).status_code==200
        with client.websocket_connect('ws://127.0.0.1/api/live') as websocket:
            assert websocket.receive_json()["state"]=="UNKNOWN" # completed acquisition isn't live NORMAL


def test_corruption_creates_gaps_not_false_continuous_windows(tmp_path):
    result=run(tmp_path,20,"NORMAL",corrupt_every=5,drop_every=7)
    assert result["parser_errors"]>0
    assert result["sequence_gaps"]>0
    assert result["windows"]==0


def test_group_split_and_model_workflow(tmp_path):
    data=tmp_path/'data'
    for condition in ("NORMAL","LOW_WATER"):
        for seed in range(3):
            run(data,32,condition,seed=seed+10)
    report=train(data,tmp_path/'models',simulated=True)
    splits=json.loads((tmp_path/'models'/'splits.json').read_text())
    assert not set(splits['train']) & set(splits['test'])
    assert not set(splits['validation']) & set(splits['test'])
    assert report['source']=='SIMULATED'
    with pytest.raises(ValueError): Inference(tmp_path/'models'/'model.joblib')
    assert evaluate(data,tmp_path/'models')['source']=='SIMULATED'
    with pytest.raises(ValueError): evaluate(data,tmp_path/'models')
    with pytest.raises(ValueError): train(data,tmp_path/'physical')


def _trained(tmp_path):
    data=tmp_path/'data'
    for condition in ("NORMAL","LOW_WATER"):
        for seed in range(3):
            run(data,32,condition,seed=seed+10)
    train(data,tmp_path/'models',simulated=True)
    return data,tmp_path/'models'


def test_model_is_refused_unless_its_recorded_sha256_matches(tmp_path):
    data,models=_trained(tmp_path)
    model=models/'model.joblib'
    assert Inference(model,allow_simulated=True).artifact["simulated"]
    (models/'model.joblib.sha256').unlink()
    with pytest.raises(ValueError,match="no recorded SHA-256"): Inference(model,allow_simulated=True)
    with pytest.raises(ValueError,match="no recorded SHA-256"): evaluate(data,models)
    (models/'model.joblib.sha256').write_text("0"*64)
    with pytest.raises(ValueError,match="does not match"): Inference(model,allow_simulated=True)
    with pytest.raises(ValueError,match="does not match"): evaluate(data,models)


def test_model_cannot_be_used_with_a_different_calibration(tmp_path):
    data,models=_trained(tmp_path)
    artifact=Inference(models/'model.joblib',allow_simulated=True).artifact
    assert artifact["calibration"]["water_dry_raw"]==200
    with pytest.raises(ValueError,match="calibration"):
        run(tmp_path/'other',5,"NORMAL",model=models/'model.joblib',water_dry_raw=100)
    assert not audit(tmp_path/'other')['unfinished_runs']


def _retag(models, **changes):
    """Rewrite the artifact with altered metadata and a matching SHA-256, as a hostile/old file would carry."""
    import hashlib
    artifact = joblib.load(models / "model.joblib")
    artifact.update(changes)
    joblib.dump(artifact, models / "model.joblib")
    (models / "model.joblib.sha256").write_text(hashlib.sha256((models / "model.joblib").read_bytes()).hexdigest())


@pytest.mark.parametrize("changes,message", [
    ({"pipeline": "old-v0"}, "feature pipeline"), ({"features": ["only_one"]}, "feature schema"),
])
def test_model_from_another_feature_pipeline_is_refused_even_with_a_valid_sha256(tmp_path, changes, message):
    _, models = _trained(tmp_path)
    _retag(models, **changes)
    with pytest.raises(ValueError, match=message):
        Inference(models / "model.joblib", allow_simulated=True)


def test_run_refuses_a_model_trained_for_another_window_and_records_no_open_run(tmp_path):
    _, models = _trained(tmp_path)
    with pytest.raises(ValueError, match="window"):
        run(tmp_path / "other", 5, "NORMAL", model=models / "model.joblib", window_seconds=20)
    with pytest.raises(ValueError, match="sampling rate"):
        _retag(models, fs=2)
        run(tmp_path / "other2", 5, "NORMAL", model=models / "model.joblib")
    assert not audit(tmp_path / "other")["unfinished_runs"] and not audit(tmp_path / "other2")["unfinished_runs"]


def test_train_and_evaluate_refuse_reused_output_changed_data_and_too_few_runs(tmp_path):
    data, models = _trained(tmp_path)
    with pytest.raises(ValueError, match="new output directory"):
        train(data, models, simulated=True)
    run(data, 32, "NORMAL", seed=99)
    with pytest.raises(ValueError, match="dataset changed"):
        evaluate(data, models)
    assert not (models / "test-report.json").exists()
    small = tmp_path / "small"
    for condition in ("NORMAL", "LOW_WATER"):
        for seed in range(2):
            run(small, 32, condition, seed=seed)
    with pytest.raises(ValueError, match="at least 3"):
        train(small, tmp_path / "small-models", simulated=True)
    assert not (tmp_path / "small-models").exists()


def test_cycle_demo_runs_can_never_become_training_data(tmp_path):
    run(tmp_path, 32, "CYCLE")
    with pytest.raises(ValueError, match="CYCLE"):
        train(tmp_path, tmp_path / "models", simulated=True)
