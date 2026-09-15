"""Analyze recorded device/readout time; never equate synthetic rate with hardware rate."""
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from sentinel.storage.database import connect


def analyze(root, run_id=None):
    root=Path(root)
    with connect(root) as db:
        if run_id is None:
            run_id=db.execute("SELECT run_id FROM experiment_run ORDER BY started_at DESC LIMIT 1").fetchone()[0]
        run=dict(db.execute("SELECT * FROM experiment_run WHERE run_id=?",(run_id,)).fetchone())
        chunks=db.execute("SELECT path FROM raw_chunk WHERE run_id=? ORDER BY rowid",(run_id,)).fetchall()
        events=[dict(r) for r in db.execute("SELECT * FROM event WHERE run_id=? ORDER BY started_at",(run_id,))]
    intervals=[]; sequence_steps=0; time_us=0; pairs=0; previous=None; rows=0
    for chunk in chunks:
        for record in pq.read_table(root/chunk[0]).to_pylist():
            rows+=1
            if previous is not None and record["boot"]==previous["boot"]:
                delta=(record["sequence"]-previous["sequence"]) & 0xFFFFFFFF
                dt=(record["timestamp_us"]-previous["timestamp_us"]) & 0xFFFFFFFF
                if 0<delta<0x80000000 and 0<dt<0x80000000:
                    sequence_steps+=delta; time_us+=dt; pairs+=1
                    if delta==1: intervals.append(dt)
            previous=record
    rate=sequence_steps*1e6/time_us if time_us else None
    seconds=time_us/1e6
    false_alarms=sum(e["state"]=="FAULT" for e in events) if run["condition"]=="NORMAL" else None
    result={"run_id":run_id,"source":"SIMULATED" if run["simulated"] else "PHYSICAL",
            "configured_hz":run["sampling_rate"],"readout_sequence_rate_hz":rate,
            "rate_error_percent":100*(rate/run["sampling_rate"]-1) if rate else None,
            "records":rows,"interval_pairs":pairs,
            "interval_us_p50":float(np.median(intervals)) if intervals else None,
            "interval_us_p99":float(np.percentile(intervals,99)) if intervals else None,
            "readout_interval_jitter_std_us":float(np.std(intervals)) if intervals else None,
            "false_alarm_events":false_alarms,
            "false_alarms_per_hour":false_alarms*3600/seconds if seconds and false_alarms is not None else None,
            "limitations":"Device time is FIFO readout time on hardware; simulation time is generated. Sensor overrun loss is not reconstructable. No synchronized T0-T7 latency is measured."}
    (root/f"{run_id}-benchmark.json").write_text(json.dumps(result,indent=2))
    return result
