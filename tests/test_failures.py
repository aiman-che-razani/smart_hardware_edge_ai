import pytest
from sentinel.acquisition.protocol import Sample, DHT_CHECKSUM_ERROR
from sentinel.pipeline import Pipeline
from sentinel.storage.database import Store, audit
from sentinel.benchmark import analyze
from sentinel.runner import run
import dataclasses
import json
from sentinel.storage import database
from sentinel.storage.database import connect


def test_invalid_sensor_and_dht_checksum_error_clear_windows(tmp_path):
    store=Store(tmp_path)
    store.start('NORMAL',1,True)
    pipeline=Pipeline(store)
    for i in range(29):
        pipeline.accept(Sample(1,i,i*1000,500,0,500,500,500,240,500,0,3),i*1_000_000_000)
    pipeline.accept(Sample(1,29,29000,500,0,500,500,500,240,500,0,2),29_000_000_000)
    assert not pipeline.windows.records
    assert pipeline.state.state=='UNKNOWN'
    pipeline.accept(Sample(1,30,30000,500,0,500,500,500,240,500,0,3|DHT_CHECKSUM_ERROR),30_000_000_000)
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
    assert report['readout_sequence_rate_hz']==1
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
    assert result['samples']==2
    assert result['acquisition_status']=='COMPLETE'
    assert result['status_publish_skips']>0
    assert not audit(tmp_path)['unfinished_runs']


def sample(**kwargs):
    return dataclasses.replace(Sample(1, 1, 1250, 500, 2, 256, 512, 700, 240, 500, 10, 3), **kwargs)


def _feed(pipeline, count, step_ms=1000, **fields):
    for i in range(count):
        pipeline.accept(sample(sequence=i, timestamp_ms=i * step_ms, distance_age_ms=0, ambient_age_ms=0, **fields),
                        i * 1_000_000_000)


def test_window_whose_device_timing_disagrees_with_the_rate_is_rejected(tmp_path):
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    good = Pipeline(store)
    _feed(good, 30)
    assert good.window_count == 1 and good.invalid == 0
    slow = Pipeline(store)
    _feed(slow, 30, step_ms=2000)
    assert slow.window_count == 0 and slow.invalid == 1
    assert slow.state.state == "UNKNOWN" and not slow.windows.records
    store.close()


@pytest.mark.parametrize("fields", [
    {"distance_age_ms": 1001}, {"ambient_age_ms": 4001}, {"thermistor_raw": 0}, {"thermistor_raw": 1023}, {"flags": 0},
])
def test_stale_or_unusable_channel_makes_the_sample_invalid_but_keeps_the_raw_row(tmp_path, fields):
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    pipeline = Pipeline(store)
    for i in range(3):
        base = dict(sequence=i, timestamp_ms=i * 1000, distance_age_ms=0, ambient_age_ms=0)
        base.update(fields)
        pipeline.accept(sample(**base), i * 1_000_000_000)
    assert pipeline.invalid == 3 and pipeline.count == 3 and len(store.pending) == 3
    assert not pipeline.windows.records
    store.close()


def test_out_of_range_readings_are_clipped_to_a_percentage(tmp_path):
    store = Store(tmp_path)
    store.start("NORMAL", 1, True)
    pipeline = Pipeline(store)
    pipeline.accept(sample(distance_mm=2000, distance_age_ms=0, water_level_raw=1023), 0)
    assert pipeline.last_record["level_ultrasonic_pct"] == 0.0
    assert pipeline.last_record["level_water_pct"] == 100.0
    store.close()


def test_metadata_json_must_be_an_object_and_is_checked_before_any_run_is_recorded(tmp_path):
    bad = tmp_path / "meta.json"
    bad.write_text("[1, 2]")
    with pytest.raises(ValueError, match="object"):
        run(tmp_path / "d", 1, "NORMAL", metadata_json=bad)
    assert not (tmp_path / "d" / "sentinel.sqlite").exists()
    bad.write_text('{"operator": "aiman"}')
    run(tmp_path / "d", 1, "NORMAL", metadata_json=bad)
    with connect(tmp_path / "d") as db:
        assert json.loads(db.execute("SELECT metadata FROM experiment_run").fetchone()[0])["operator_metadata"] == {"operator": "aiman"}


@pytest.mark.parametrize("kwargs", [{"duration": 0}, {"duration": -1}, {"fs": 2}])
def test_run_refuses_a_non_positive_duration_or_a_rate_the_firmware_cannot_report(tmp_path, kwargs):
    arguments = dict(duration=1, fs=1, **{})
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        run(tmp_path, arguments.pop("duration"), "NORMAL", **arguments)
    assert not (tmp_path / "sentinel.sqlite").exists()


def test_raw_write_failure_during_a_run_marks_it_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "FLUSH_ROWS", 5)

    def broken(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(database.pq, "write_table", broken)
    with pytest.raises(OSError):
        run(tmp_path, 12, "NORMAL")
    with connect(tmp_path) as db:
        assert db.execute("SELECT status FROM experiment_run").fetchone()[0] == "FAILED"


def test_raw_write_failure_still_writes_the_run_summary_as_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "FLUSH_ROWS", 5)

    def broken(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(database.pq, "write_table", broken)
    with pytest.raises(OSError):
        run(tmp_path, 12, "NORMAL")
    summaries = list(tmp_path.glob("*-summary.json"))
    assert len(summaries) == 1
    assert json.loads(summaries[0].read_text())["acquisition_status"] == "FAILED"
