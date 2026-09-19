import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// lines: [{ dataKey, name, color, dashed? }]
export default function TimeSeriesChart({ title, data, lines }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--panel-border)" />
          <XAxis dataKey="t" stroke="var(--muted)" tick={{ fontSize: 11 }} label={{ value: 's', position: 'insideBottomRight', offset: -4, fill: 'var(--muted)', fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ background: 'var(--panel)', border: '1px solid var(--panel-border)', fontSize: 12 }} labelStyle={{ color: 'var(--ink-dim)' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {lines.map((line) => (
            <Line
              key={line.dataKey}
              type="monotone"
              dataKey={line.dataKey}
              name={line.name}
              stroke={line.color}
              strokeDasharray={line.dashed ? '4 3' : undefined}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
