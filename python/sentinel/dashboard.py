import json
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sentinel.api.main import status, measurements, query
from sentinel.storage.database import Store


def create_dashboard(root="data"):
    Store(root).close()
    app = Dash(__name__, title="SentinelDAQ | Tank & environment")
    app.layout = html.Main(style={"background": "#0b1220", "color": "#e2e8f0", "minHeight": "100vh", "padding": "32px", "fontFamily": "Arial"}, children=[
        html.Div("SENTINEL / DAQ", style={"color": "#38bdf8", "letterSpacing": "4px"}),
        html.H1("Tank & environment monitor"), html.Div(id="health"),
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
        fig = make_subplots(rows=2, cols=2, subplot_titles=(
            "Tank level (%, both sensors)", "Level agreement (abs diff, pct pts)",
            "Ambient temp/humidity (DHT)", "Thermistor (°C) / light (%)"))
        for selected, label in [(run_id, "selected"), (comparison, "comparison")]:
            if label == "comparison" and not selected:
                continue
            data = measurements(root, selected)
            if not data:
                continue
            times = [((r["timestamp_ms"]-data[0]["timestamp_ms"]) & 0xFFFFFFFF)/1000 for r in data]
            fig.add_trace(go.Scatter(x=times, y=[r["level_ultrasonic_pct"] for r in data], name=f"{label} ultrasonic"), row=1, col=1)
            fig.add_trace(go.Scatter(x=times, y=[r["level_water_pct"] for r in data], name=f"{label} water-level"), row=1, col=1)
            agreement = [abs(r["level_ultrasonic_pct"]-r["level_water_pct"]) if r["level_ultrasonic_pct"] is not None and r["level_water_pct"] is not None else None for r in data]
            fig.add_trace(go.Scatter(x=times, y=agreement, name=f"{label} agreement"), row=1, col=2)
            fig.add_trace(go.Scatter(x=times, y=[r["ambient_temp_c"] for r in data], name=f"{label} ambient temp"), row=2, col=1)
            fig.add_trace(go.Scatter(x=times, y=[r["ambient_humidity_pct"] for r in data], name=f"{label} humidity"), row=2, col=1)
            fig.add_trace(go.Scatter(x=times, y=[r["thermistor_temp_c"] for r in data], name=f"{label} thermistor"), row=2, col=2)
            fig.add_trace(go.Scatter(x=times, y=[r["light_pct"] for r in data], name=f"{label} light"), row=2, col=2)
        fig.update_layout(template="plotly_dark", height=650, paper_bgcolor="#0b1220")
        history = go.Figure()
        rows = query(root, "SELECT f.timestamp, p.score FROM prediction p JOIN feature_window f USING(window_id) WHERE (? IS NULL OR f.run_id=?) ORDER BY f.timestamp DESC LIMIT 200", (run_id, run_id))
        history.add_trace(go.Scatter(x=[r["timestamp"] for r in reversed(rows)], y=[r["score"] for r in reversed(rows)], name="risk score"))
        history.update_layout(template="plotly_dark", title="Recent risk score (UTC epoch seconds)", paper_bgcolor="#0b1220")
        events = query(root, "SELECT state, score, alarm_state, started_at FROM event ORDER BY started_at DESC LIMIT 10")
        headline = f"{'SIMULATED' if current.get('simulated') else 'DAQ'} | {current['state']} | Samples {current.get('samples', 0)} | Gaps {current.get('sequence_gaps', 0)} | Parser errors {current.get('parser_errors', 0)}"
        return headline, fig, history, json.dumps(events, indent=2)
    return app
