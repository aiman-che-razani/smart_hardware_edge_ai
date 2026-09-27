import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import TimeSeriesChart from './TimeSeriesChart.jsx'
import './App.css'

function Tile({ label, raw, value, unit }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value == null ? '—' : `${value.toFixed(1)}${unit}`}</div>
      <div className="tile-raw">raw {raw ?? '—'}</div>
    </div>
  )
}

function agreement(record) {
  return record && record.level_ultrasonic_pct != null && record.level_water_pct != null
    ? Math.abs(record.level_ultrasonic_pct - record.level_water_pct)
    : null
}

// Recharts wants one merged array: the selected and comparison runs are aligned
// by index (elapsed samples since each run's own start, about 1 s per sample at
// 1 Hz), not by wall-clock time.
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

// A run that is not in the (limited) experiments list still gets its id shown.
function runLabelById(experiments, runId) {
  const run = runId ? experiments.find((item) => item.run_id === runId) : experiments[0]
  if (run) return runLabel(run)
  return runId ? `run ${runId.slice(0, 8)}` : '—'
}

function sourceLabel(status) {
  if (status.simulated == null) return 'NO STATUS'
  return status.simulated ? 'SIMULATED' : 'PHYSICAL'
}

// Known states only, so an unexpected value never picks up a colour by accident.
function stateClass(state) {
  return ['NORMAL', 'WARNING', 'FAULT'].includes(state) ? `state-${state.toLowerCase()}` : 'state-unknown'
}

const SAMPLE_AXIS = 'elapsed samples (~s at 1 Hz)'

const dash = (value) => value ?? '—'

export default function App() {
  const [status, setStatus] = useState({})
  const [experiments, setExperiments] = useState([])
  const [runId, setRunId] = useState('')
  const [compareRunId, setCompareRunId] = useState('')
  const [chartData, setChartData] = useState([])
  const [history, setHistory] = useState([])
  const [events, setEvents] = useState([])
  const [error, setError] = useState(false)

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
      setError(false)
    } catch (err) {
      console.error('refresh failed', err)
      setError(true)
    }
  }, [runId, compareRunId])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 1000)
    return () => clearInterval(id)
  }, [refresh])

  const last = status.last_record || {}
  const state = status.state ?? 'UNKNOWN'
  const stale = status.stale === true
  const dimmed = stale || error
  const showCompare = Boolean(compareRunId)

  return (
    <main className="page">
      <div className="eyebrow">SENTINEL / DAQ</div>
      <h1>Tank &amp; environment monitor</h1>
      <p className="headline">
        {sourceLabel(status)} | <span className={stateClass(state)}>{state}</span> | Samples {dash(status.samples)} | Gaps{' '}
        {dash(status.sequence_gaps)} | Parser errors {dash(status.parser_errors)}
      </p>
      <p className="disclaimer">
        Engineering score is not a calibrated fault probability. Historical data remains visible when acquisition stops.
      </p>

      <div role="status" aria-live="polite">
        {error && <p className="banner banner-error">API unreachable</p>}
        {(stale || status.acquisition_status) && (
          <p className="banner banner-stale">
            {stale ? 'STALE | showing last recorded values, acquisition not running' : 'ACQUISITION ENDED'}
            {status.acquisition_status ? ` | run status ${status.acquisition_status}` : ''}
          </p>
        )}
      </div>

      <h2 className="section-label">Current readings</h2>
      <div className={dimmed ? 'tiles is-dimmed' : 'tiles'}>
        <Tile label="Ultrasonic level" raw={last.distance_mm} value={last.level_ultrasonic_pct} unit="%" />
        <Tile label="Water level" raw={last.water_level_raw} value={last.level_water_pct} unit="%" />
        <Tile label="Thermistor" raw={last.thermistor_raw} value={last.thermistor_temp_c} unit="°C" />
        <Tile label="Photoresistor" raw={last.light_raw} value={last.light_pct} unit="%" />
        <Tile label="DHT temperature" raw={last.ambient_temp_c_ds} value={last.ambient_temp_c} unit="°C" />
        <Tile label="DHT humidity" raw={last.ambient_humidity_ds} value={last.ambient_humidity_pct} unit="%" />
      </div>

      <div className="selectors">
        <select aria-label="Run" value={runId} onChange={(e) => setRunId(e.target.value)}>
          <option value="">Latest run</option>
          {experiments.map((run) => (
            <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>
          ))}
        </select>
        <select aria-label="Compare run" value={compareRunId} onChange={(e) => setCompareRunId(e.target.value)}>
          <option value="">Compare another experimental run</option>
          {experiments.map((run) => (
            <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>
          ))}
        </select>
      </div>

      <p className="run-label">Run: {runLabelById(experiments, runId)}</p>
      {showCompare && <p className="run-label">Comparison (dashed): {runLabelById(experiments, compareRunId)}</p>}

      <div className="chart-grid">
        <TimeSeriesChart
          title="Tank level (%, both sensors)"
          data={chartData}
          xLabel={SAMPLE_AXIS}
          lines={[
            { dataKey: 'sel_ultrasonic', name: 'selected ultrasonic', color: 'var(--series-1)' },
            { dataKey: 'sel_water', name: 'selected water-level', color: 'var(--series-2)' },
            ...(showCompare ? [
              { dataKey: 'cmp_ultrasonic', name: 'comparison ultrasonic', color: 'var(--series-1)', dashed: true },
              { dataKey: 'cmp_water', name: 'comparison water-level', color: 'var(--series-2)', dashed: true },
            ] : []),
          ]}
        />
        <TimeSeriesChart
          title="Level agreement (abs diff, pct pts)"
          data={chartData}
          xLabel={SAMPLE_AXIS}
          lines={[
            { dataKey: 'sel_agreement', name: 'selected agreement', color: 'var(--series-3)' },
            ...(showCompare ? [{ dataKey: 'cmp_agreement', name: 'comparison agreement', color: 'var(--series-3)', dashed: true }] : []),
          ]}
        />
        <TimeSeriesChart
          title="Ambient temp/humidity (DHT)"
          data={chartData}
          xLabel={SAMPLE_AXIS}
          lines={[
            { dataKey: 'sel_ambient_temp', name: 'selected ambient temp (°C)', color: 'var(--series-4)' },
            { dataKey: 'sel_humidity', name: 'selected humidity (%)', color: 'var(--series-5)' },
            ...(showCompare ? [
              { dataKey: 'cmp_ambient_temp', name: 'comparison ambient temp (°C)', color: 'var(--series-4)', dashed: true },
              { dataKey: 'cmp_humidity', name: 'comparison humidity (%)', color: 'var(--series-5)', dashed: true },
            ] : []),
          ]}
        />
        <TimeSeriesChart
          title="Thermistor (°C) / light (%)"
          data={chartData}
          xLabel={SAMPLE_AXIS}
          lines={[
            { dataKey: 'sel_thermistor', name: 'selected thermistor (°C)', color: 'var(--series-6)' },
            { dataKey: 'sel_light', name: 'selected light (%)', color: 'var(--series-7)' },
            ...(showCompare ? [
              { dataKey: 'cmp_thermistor', name: 'comparison thermistor (°C)', color: 'var(--series-6)', dashed: true },
              { dataKey: 'cmp_light', name: 'comparison light (%)', color: 'var(--series-7)', dashed: true },
            ] : []),
          ]}
        />
      </div>

      <TimeSeriesChart
        title="Recent risk score (UTC epoch seconds)"
        data={history.map((row) => ({ t: row.timestamp, risk: row.score }))}
        xLabel="UTC epoch s"
        lines={[{ dataKey: 'risk', name: 'risk score', color: 'var(--series-8)' }]}
      />

      <h2 className="section-label">Recent events</h2>
      <div className="events-list">
        {events.length === 0 && <p className="events-empty">No events yet.</p>}
        {events.map((event) => (
          <div className="event-row" key={event.event_id}>
            <span className={`state ${stateClass(event.state)}`}>{event.state}</span>
            {/* two decimals: the score is a unitless index, not a percent like the tiles */}
            <span className="meta">score {event.score == null ? '—' : event.score.toFixed(2)}</span>
            <span className="meta">alarm {event.alarm_state}</span>
            <span className="meta">{new Date(event.started_at * 1000).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </main>
  )
}
