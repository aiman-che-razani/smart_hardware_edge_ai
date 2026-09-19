import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import TimeSeriesChart from './TimeSeriesChart.jsx'
import './App.css'

function Tile({ label, raw, value, unit }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value == null ? '—' : `${value.toFixed(1)}${unit}`}</div>
      <div className="tile-raw">raw {raw ?? 'no data'}</div>
    </div>
  )
}

function agreement(record) {
  return record && record.level_ultrasonic_pct != null && record.level_water_pct != null
    ? Math.abs(record.level_ultrasonic_pct - record.level_water_pct)
    : null
}

// Recharts wants one merged array (both series aligned by index = elapsed
// samples since each run's own start), not two separate series like Plotly.
function mergeSeries(selected, compare) {
  const n = Math.max(selected.length, compare.length)
  const rows = []
  for (let i = 0; i < n; i++) {
    const s = selected[i]
    const c = compare[i]
    rows.push({
      t: i,
      sel_ultrasonic: s?.level_ultrasonic_pct ?? null,
      sel_water: s?.level_water_pct ?? null,
      sel_agreement: agreement(s),
      sel_ambient_temp: s?.ambient_temp_c ?? null,
      sel_humidity: s?.ambient_humidity_pct ?? null,
      sel_thermistor: s?.thermistor_temp_c ?? null,
      sel_light: s?.light_pct ?? null,
      cmp_ultrasonic: c?.level_ultrasonic_pct ?? null,
      cmp_water: c?.level_water_pct ?? null,
      cmp_agreement: agreement(c),
      cmp_ambient_temp: c?.ambient_temp_c ?? null,
      cmp_humidity: c?.ambient_humidity_pct ?? null,
      cmp_thermistor: c?.thermistor_temp_c ?? null,
      cmp_light: c?.light_pct ?? null,
    })
  }
  return rows
}

function runLabel(run) {
  return `${run.simulated ? 'SIMULATED' : 'PHYSICAL'} | ${run.condition} | ${run.run_id.slice(0, 8)}`
}

export default function App() {
  const [status, setStatus] = useState({})
  const [experiments, setExperiments] = useState([])
  const [runId, setRunId] = useState('')
  const [compareRunId, setCompareRunId] = useState('')
  const [chartData, setChartData] = useState([])
  const [history, setHistory] = useState([])
  const [events, setEvents] = useState([])

  const refresh = useCallback(async () => {
    try {
      const [statusRes, experimentsRes, selectedRes, compareRes, predictionsRes, eventsRes] = await Promise.all([
        api.status(),
        api.experiments(),
        api.measurements(runId || null),
        compareRunId ? api.measurements(compareRunId) : Promise.resolve([]),
        api.predictions(runId || null),
        api.events(10),
      ])
      setStatus(statusRes)
      setExperiments(experimentsRes)
      setChartData(mergeSeries(selectedRes, compareRes))
      setHistory([...predictionsRes].reverse())
      setEvents(eventsRes)
    } catch (err) {
      console.error('refresh failed', err)
    }
  }, [runId, compareRunId])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 1000)
    return () => clearInterval(id)
  }, [refresh])

  const last = status.last_record || {}
  const headline = `${status.simulated ? 'SIMULATED' : 'DAQ'} | ${status.state ?? 'UNKNOWN'} | ` +
    `Samples ${status.samples ?? 0} | Gaps ${status.sequence_gaps ?? 0} | Parser errors ${status.parser_errors ?? 0}`
  const showCompare = Boolean(compareRunId)

  return (
    <main className="page">
      <div className="eyebrow">SENTINEL / DAQ</div>
      <h1>Tank &amp; environment monitor</h1>
      <p className="headline">{headline}</p>
      <p className="disclaimer">
        Engineering score is not a calibrated fault probability. Historical data remains visible when acquisition stops.
      </p>

      <h2 className="section-label">Current readings</h2>
      <div className="tiles">
        <Tile label="Ultrasonic level" raw={last.distance_mm} value={last.level_ultrasonic_pct} unit="%" />
        <Tile label="Water-level level" raw={last.water_level_raw} value={last.level_water_pct} unit="%" />
        <Tile label="Thermistor" raw={last.thermistor_raw} value={last.thermistor_temp_c} unit="°C" />
        <Tile label="Photoresistor" raw={last.light_raw} value={last.light_pct} unit="%" />
        <Tile label="DHT temperature" raw={last.ambient_temp_c_ds} value={last.ambient_temp_c} unit="°C" />
        <Tile label="DHT humidity" raw={last.ambient_humidity_ds} value={last.ambient_humidity_pct} unit="%" />
      </div>

      <div className="selectors">
        <select value={runId} onChange={(e) => setRunId(e.target.value)}>
          <option value="">Latest run</option>
          {experiments.map((run) => (
            <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>
          ))}
        </select>
        <select value={compareRunId} onChange={(e) => setCompareRunId(e.target.value)}>
          <option value="">Compare another experimental run</option>
          {experiments.map((run) => (
            <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>
          ))}
        </select>
      </div>

      <div className="chart-grid">
        <TimeSeriesChart
          title="Tank level (%, both sensors)"
          data={chartData}
          lines={[
            { dataKey: 'sel_ultrasonic', name: 'selected ultrasonic', color: '#38bdf8' },
            { dataKey: 'sel_water', name: 'selected water-level', color: '#34d399' },
            ...(showCompare ? [
              { dataKey: 'cmp_ultrasonic', name: 'comparison ultrasonic', color: '#38bdf8', dashed: true },
              { dataKey: 'cmp_water', name: 'comparison water-level', color: '#34d399', dashed: true },
            ] : []),
          ]}
        />
        <TimeSeriesChart
          title="Level agreement (abs diff, pct pts)"
          data={chartData}
          lines={[
            { dataKey: 'sel_agreement', name: 'selected agreement', color: '#f472b6' },
            ...(showCompare ? [{ dataKey: 'cmp_agreement', name: 'comparison agreement', color: '#f472b6', dashed: true }] : []),
          ]}
        />
        <TimeSeriesChart
          title="Ambient temp/humidity (DHT)"
          data={chartData}
          lines={[
            { dataKey: 'sel_ambient_temp', name: 'selected ambient temp', color: '#a78bfa' },
            { dataKey: 'sel_humidity', name: 'selected humidity', color: '#fbbf24' },
            ...(showCompare ? [
              { dataKey: 'cmp_ambient_temp', name: 'comparison ambient temp', color: '#a78bfa', dashed: true },
              { dataKey: 'cmp_humidity', name: 'comparison humidity', color: '#fbbf24', dashed: true },
            ] : []),
          ]}
        />
        <TimeSeriesChart
          title="Thermistor (°C) / light (%)"
          data={chartData}
          lines={[
            { dataKey: 'sel_thermistor', name: 'selected thermistor', color: '#22d3ee' },
            { dataKey: 'sel_light', name: 'selected light', color: '#fb7185' },
            ...(showCompare ? [
              { dataKey: 'cmp_thermistor', name: 'comparison thermistor', color: '#22d3ee', dashed: true },
              { dataKey: 'cmp_light', name: 'comparison light', color: '#fb7185', dashed: true },
            ] : []),
          ]}
        />
      </div>

      <TimeSeriesChart
        title="Recent risk score (UTC epoch seconds)"
        data={history.map((row) => ({ t: row.timestamp, risk: row.score }))}
        lines={[{ dataKey: 'risk', name: 'risk score', color: '#f59e0b' }]}
      />

      <h2 className="section-label">Recent events</h2>
      <div className="events-list">
        {events.length === 0 && <p className="disclaimer" style={{ padding: '12px 0' }}>No events yet.</p>}
        {events.map((event, i) => (
          <div className="event-row" key={i}>
            <span className="state">{event.state}</span>
            <span className="meta">score {event.score == null ? '—' : event.score.toFixed(2)}</span>
            <span className="meta">alarm {event.alarm_state}</span>
            <span className="meta">{new Date(event.started_at * 1000).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </main>
  )
}
