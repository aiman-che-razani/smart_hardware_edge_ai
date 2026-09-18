"""Export standalone interactive engineering plots from stored runs."""
from pathlib import Path
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from sentinel.api.main import measurements, query


def export(root, output, run_id=None):
    data=measurements(root,run_id,3200)
    if not data:
        raise ValueError("no measurements available")
    run=query(root,"SELECT * FROM experiment_run WHERE run_id=?",(data[-1]['run_id'],))[0]
    fig=make_subplots(rows=2,cols=1,subplot_titles=("Tank level (%, both sensors)","Ambient temp/humidity (DHT)"))
    t=[((r['timestamp_ms']-data[0]['timestamp_ms']) & 0xFFFFFFFF)/1000 for r in data]
    fig.add_trace(go.Scatter(x=t,y=[r['level_ultrasonic_pct'] for r in data],name='ultrasonic'),row=1,col=1)
    fig.add_trace(go.Scatter(x=t,y=[r['level_water_pct'] for r in data],name='water-level'),row=1,col=1)
    fig.add_trace(go.Scatter(x=t,y=[r['ambient_temp_c'] for r in data],name='ambient temp'),row=2,col=1)
    fig.add_trace(go.Scatter(x=t,y=[r['ambient_humidity_pct'] for r in data],name='humidity'),row=2,col=1)
    continuous=all(b['boot']==a['boot'] and b['sequence']==(a['sequence']+1)&0xFFFFFFFF for a,b in zip(data,data[1:]))
    fig.update_layout(template='plotly_dark',height=800,title=f"SentinelDAQ — {'SIMULATED' if run['simulated'] else 'PHYSICAL'} — {run['condition']} — {run['run_id']}")
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    fig.write_html(output,include_plotlyjs=True,full_html=True)
    return {"report":str(output),"continuous":continuous}
