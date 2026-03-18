import { useState, useMemo } from 'react'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'
import { useSummary } from '../hooks/useApi.js'
import './ProfileStrip.css'

const PERIODS = [
  { key: 'today', label: 'Today',      color: '#14c8a8' },
  { key: 'week',  label: 'This Week',  color: '#7c6af7' },
  { key: 'month', label: 'This Month', color: '#f5a623' },
]

export default function ProfileStrip({ current }) {
  const [collapsed, setCollapsed] = useState(false)
  const { data: summaries, loading: sumLoading } = useSummary()

  // Sessions per day for the last 7 days
  const sparkData = useMemo(() => {
    const now = new Date()
    const days = {}
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      days[d.toISOString().slice(0, 10)] = 0
    }
    for (const t of current?.transcripts?.items ?? []) {
      const day = t.event_time?.slice(0, 10)
      if (day && day in days) days[day]++
    }
    return Object.entries(days).map(([date, sessions]) => ({
      date: date.slice(5),
      sessions,
    }))
  }, [current])

  const weekTotal  = sparkData.reduce((a, d) => a + d.sessions, 0)
  const latestItem = current?.transcripts?.items?.at(-1)

  return (
    <div className={`profile-strip-wrap${collapsed ? ' ps-collapsed' : ''}`}>

      {/* Collapse toggle bar */}
      <div className="ps-toggle-bar" onClick={() => setCollapsed(c => !c)}>
        <span className="ps-toggle-label">Patient Overview</span>
        <span className="ps-toggle-icon">{collapsed ? '▾' : '▴'}</span>
      </div>

      {/* Cards row — hidden when collapsed */}
      {!collapsed && (
        <div className="profile-strip">

          {/* LLM summary cards */}
          {PERIODS.map(p => (
            <div key={p.key} className="ps-card ps-summary" style={{ '--c': p.color }}>
              <div className="ps-label" style={{ color: p.color }}>{p.label}</div>
              {sumLoading ? (
                <div className="ps-skeleton-lines">
                  <div className="ps-skeleton" style={{ width: '90%' }} />
                  <div className="ps-skeleton" style={{ width: '75%' }} />
                  <div className="ps-skeleton" style={{ width: '82%' }} />
                </div>
              ) : (
                <p className="ps-summary-text">{summaries?.[p.key] ?? '—'}</p>
              )}
            </div>
          ))}

          {/* Usage sparkline */}
          <div className="ps-card ps-chart">
            <div className="ps-label">Activity</div>
            <ResponsiveContainer width="100%" height={50}>
              <AreaChart data={sparkData} margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
                <defs>
                  <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#7c6af7" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#7c6af7" stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="sessions"
                  stroke="#7c6af7"
                  fill="url(#sparkFill)"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Tooltip
                  contentStyle={{ background: '#13131f', border: '1px solid #2a2a3a', fontSize: 11, borderRadius: 6 }}
                  formatter={v => [v, 'sessions']}
                  labelFormatter={l => l}
                />
              </AreaChart>
            </ResponsiveContainer>
            <div className="ps-chart-foot">{weekTotal} session{weekTotal !== 1 ? 's' : ''} this week</div>
          </div>

          {/* Latest transcript */}
          <div className="ps-card ps-latest">
            <div className="ps-label">Latest</div>
            {latestItem ? (
              <>
                <p className="ps-latest-text">
                  {latestItem.text?.slice(0, 130)}{latestItem.text?.length > 130 ? '…' : ''}
                </p>
                <span className="ps-latest-time">
                  {new Date(latestItem.event_time).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                  })}
                </span>
              </>
            ) : (
              <p className="ps-empty">No conversations yet.</p>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
