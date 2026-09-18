import json
import pytest
from fastapi.testclient import TestClient
from sentinel.runner import run
from sentinel.storage.database import audit, connect
from sentinel.api.main import create_app, measurements
from sentinel.dashboard import create_dashboard
from sentinel.ml.train import grouped_partitions, train, evaluate
from sentinel.ml.inference import Inference


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
    with TestClient(create_app(tmp_path)) as client:
        for endpoint in ("health","machines","experiments","features","predictions","events","measurements","system/status"):
            assert client.get('/'+endpoint).status_code==200
        assert client.get('/measurements?limit=999999').status_code==422
        with client.websocket_connect('/live') as websocket:
            assert websocket.receive_json()["state"]=="UNKNOWN" # completed acquisition isn't live NORMAL
    app=create_dashboard(tmp_path)
    assert app.server.test_client().get('/').status_code==200
    key = next(k for k in app.callback_map if 'health.children' in k)
    response = app.server.test_client().post('/_dash-update-component', json={
        'output': key,
        'outputs': [{'id':'health','property':'children'}, {'id':'signals','property':'figure'},
                    {'id':'history','property':'figure'}, {'id':'events','property':'children'}],
        'inputs': [{'id':'tick','property':'n_intervals','value':1},
                   {'id':'run','property':'value','value':result['run_id']},
                   {'id':'compare','property':'value','value':None}],
        'state': [], 'changedPropIds':['tick.n_intervals']})
    assert response.status_code == 200, response.data
    assert 'SIMULATED' in response.json['response']['health']['children']


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
