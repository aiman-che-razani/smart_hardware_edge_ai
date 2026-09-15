import dataclasses
import json
import pytest
from sentinel.acquisition.protocol import Sample, OVERRUN
from sentinel.pipeline import Pipeline
from sentinel.storage.database import Store, audit
from sentinel.benchmark import analyze
from sentinel.runner import run


def test_invalid_sensor_and_fifo_overrun_clear_windows(tmp_path):
    store=Store(tmp_path)
    store.start('NORMAL',800,True)
    pipeline=Pipeline(store)
    for i in range(799):
        pipeline.accept(Sample(1,i,i*1250,0,0,256,0,480,0,0,7),i*1250000)
    pipeline.accept(Sample(1,799,998750,0,0,256,0,480,0,0,6),998750000)
    assert not pipeline.windows.records
    assert pipeline.state.state=='UNKNOWN'
    pipeline.accept(Sample(1,800,1000000,0,0,256,0,480,0,0,7|OVERRUN),1000000000)
    assert len(pipeline.windows.records)==1
    pipeline.disconnect()
    assert not pipeline.windows.records
    store.close()


def test_orphan_and_partial_audit(tmp_path):
    result=run(tmp_path,1,'NORMAL')
    directory=tmp_path/'raw'/result['run_id']
    (directory/'orphan.parquet').write_bytes(b'not a valid parquet')
    (directory/'interrupted.partial').write_bytes(b'partial')
    result=audit(tmp_path)
    assert len(result['orphaned'])==1 and len(result['partial'])==1


def test_benchmark_simulation_label_and_rate(tmp_path):
    run(tmp_path,2,'NORMAL')
    report=analyze(tmp_path)
    assert report['source']=='SIMULATED'
    assert report['readout_sequence_rate_hz']==800
    assert report['false_alarm_events']==0


def test_failed_configuration_closes_run(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path,1,'NORMAL',warning=0.9,fault=0.8)
    assert not audit(tmp_path)['unfinished_runs']


def test_locked_live_status_does_not_stop_acquisition(tmp_path, monkeypatch):
    from pathlib import Path
    original=Path.replace
    def locked(path,target):
        if path.name=='status.partial':
            raise PermissionError('injected Windows file lock')
        return original(path,target)
    monkeypatch.setattr(Path,'replace',locked)
    result=run(tmp_path,2,'NORMAL')
    assert result['samples']==1600
    assert result['acquisition_status']=='COMPLETE'
    assert result['status_publish_skips']>0
    assert not audit(tmp_path)['unfinished_runs']
