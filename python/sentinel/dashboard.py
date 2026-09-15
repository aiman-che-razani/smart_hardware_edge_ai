import json
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sentinel.api.main import status, measurements, query
from sentinel.processing.features import spectrum
from sentinel.storage.database import Store


def create_dashboard(root="data"):
    Store(root).close()
    app = Dash(__name__, title="SentinelDAQ | Machine condition")
    app.layout = html.Main(style={"background": "#0b1220", "color": "#e2e8f0", "minHeight": "100vh", "padding": "32px", "fontFamily": "Arial"}, children=[
        html.Div("SENTINEL / DAQ", style={"color": "#38bdf8", "letterSpacing": "4px"}),
        html.H1("Machine condition monitor"), html.Div(id="health"),
        html.P("Engineering score is not a calibrated fault probability. Historical data remains visible when acquisition stops."),
        dcc.Dropdown(id="run", placeholder="Latest run", style={"color": "#111"}),
        dcc.Dropdown(id="compare", placeholder="Compare another experimental run", style={"color": "#111"}),
        dcc.Graph(id="signals"), dcc.Graph(id="history"), html.H2("Recent events"),
        html.Pre(id="events", style={"whiteSpace": "pre-wrap"}), dcc.Interval(id="tick", interval=1000)])

    @app.callback(Output("run", "options"), Output("compare", "options"), Input("tick", "n_intervals"))
    def runs(_):
        rows = query(root, "SELECT run_id, condition, simulated FROM experiment_run ORDER BY started_at DESC LIMIT 100")
        options = [{"label": f"{'SIMULATED' if r['simulated'] else 'PHYSICAL'} | {r['condition']} | {r['run_id'][:8]}", "value": r["run_id"]} for r in rows]
        return options, options

    @app.callback(Output("health", "children"), Output("signals", "figure"), Output("history", "figure"), Output("events", "children"),
                  Input("tick", "n_intervals"), Input("run", "value"), Input("compare", "value"))
    def update(_, run_id, comparison):
        current = status(root)
        fig = make_subplots(rows=2, cols=2, subplot_titles=("Acceleration (g)", "Hann amplitude spectrum (g)", "Current (A)", "Temperature (°C)"))
        for selected, label in [(run_id, "selected"), (comparison, "comparison")]:
            if label == "comparison" and not selected:
                continue
            data = measurements(root, selected)
            if not data:
                continue
            rate_rows = query(root, "SELECT sampling_rate FROM experiment_run WHERE run_id=?", (data[-1]["run_id"],))
            fs = rate_rows[0]["sampling_rate"]
            times = [((r["timestamp_us"]-data[0]["timestamp_us"]) & 0xFFFFFFFF)/1e6 for r in data]
            for axis in "xyz":
                fig.add_trace(go.Scatter(x=times, y=[r[f"a{axis}_g"] for r in data], name=f"{label} {axis}"), row=1, col=1)
            if len(data) >= 8 and all(b["sequence"] == (a["sequence"]+1)&0xFFFFFFFF and a["boot"] == b["boot"] for a,b in zip(data,data[1:])):
                f, amplitude, _ = spectrum([r["ax_g"] for r in data], fs)
                fig.add_trace(go.Scatter(x=f, y=amplitude, name=f"{label} X spectrum"), row=1, col=2)
            fig.add_trace(go.Scatter(x=times, y=[r["current_a"] for r in data], name=f"{label} current"), row=2, col=1)
            fig.add_trace(go.Scatter(x=times, y=[r["temperature_c"] for r in data], name=f"{label} temperature"), row=2, col=2)
        fig.update_layout(template="plotly_dark", height=650, paper_bgcolor="#0b1220")
        history = go.Figure()
        rows = query(root, "SELECT f.timestamp, p.score FROM prediction p JOIN feature_window f USING(window_id) WHERE (? IS NULL OR f.run_id=?) ORDER BY f.timestamp DESC LIMIT 200", (run_id, run_id))
        history.add_trace(go.Scatter(x=[r["timestamp"] for r in reversed(rows)], y=[r["score"] for r in reversed(rows)], name="risk score"))
        history.update_layout(template="plotly_dark", title="Recent risk score (UTC epoch seconds)", paper_bgcolor="#0b1220")
        events = query(root, "SELECT state, score, alarm_state, started_at FROM event ORDER BY started_at DESC LIMIT 10")
        headline = f"{'SIMULATED' if current.get('simulated') else 'DAQ'} | {current['state']} | Samples {current.get('samples', 0)} | Gaps {current.get('sequence_gaps', 0)} | Parser errors {current.get('parser_errors', 0)}"
        return headline, fig, history, json.dumps(events, indent=2)
    return app
