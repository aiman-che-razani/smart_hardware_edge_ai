"""Export standalone interactive engineering plots from stored runs."""
from pathlib import Path
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from sentinel.api.main import measurements, query
from sentinel.processing.features import spectrum


def export(root, output, run_id=None):
    data=measurements(root,run_id,3200)
    if not data:
        raise ValueError("no measurements available")
    run=query(root,"SELECT * FROM experiment_run WHERE run_id=?",(data[-1]['run_id'],))[0]
    fig=make_subplots(rows=2,cols=1,subplot_titles=("Acceleration (g)","X-axis Hann spectrum (g)"))
    t=[((r['timestamp_us']-data[0]['timestamp_us']) & 0xFFFFFFFF)/1e6 for r in data]
    for axis in 'xyz':
        fig.add_trace(go.Scatter(x=t,y=[r[f'a{axis}_g'] for r in data],name=axis),row=1,col=1)
    continuous=all(b['boot']==a['boot'] and b['sequence']==(a['sequence']+1)&0xFFFFFFFF for a,b in zip(data,data[1:]))
    if continuous and len(data)>=8:
        f,amplitude,_=spectrum([r['ax_g'] for r in data],run['sampling_rate'])
        fig.add_trace(go.Scatter(x=f,y=amplitude,name='X spectrum'),row=2,col=1)
    fig.update_layout(template='plotly_dark',height=800,title=f"SentinelDAQ — {'SIMULATED' if run['simulated'] else 'PHYSICAL'} — {run['condition']} — {run['run_id']}")
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    fig.write_html(output,include_plotlyjs=True,full_html=True)
    return {"report":str(output),"spectrum_included":continuous}
