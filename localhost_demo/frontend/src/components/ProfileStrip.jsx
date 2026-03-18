import { useState, useMemo } from 'react'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'
import { ChevronDown, ChevronUp, Sun, CalendarDays, CalendarRange, BarChart2, MessageSquare } from 'lucide-react'
import { useSummary } from '../hooks/useApi.js'
import { ACCENT } from '../theme.js'
import './ProfileStrip.css'

const PERIODS = [
  { key: 'today', label: 'Today',      color: '#5ab8a0', Icon: Sun          },
  { key: 'week',  label: 'This Week',  color: '#c8695a', Icon: CalendarDays  },
  { key: 'month', label: 'This Month', color: '#c4a882', Icon: CalendarRange },
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
        {collapsed
          ? <ChevronDown size={13} strokeWidth={2} className="ps-toggle-icon" />
          : <ChevronUp   size={13} strokeWidth={2} className="ps-toggle-icon" />
        }
      </div>

      {/* Cards row — hidden when collapsed */}
      {!collapsed && (
        <div className="profile-strip">

          {/* LLM summary cards */}
          {PERIODS.map(({ key, label, color, Icon }) => (
            <div key={key} className="ps-card ps-summary" style={{ '--c': color }}>
              <div className="ps-label" style={{ color }}>
                <Icon size={11} strokeWidth={2.5} />
                {label}
              </div>
              {sumLoading ? (
                <div className="ps-skeleton-lines">
                  <div className="ps-skeleton" style={{ width: '90%' }} />
                  <div className="ps-skeleton" style={{ width: '75%' }} />
                  <div className="ps-skeleton" style={{ width: '82%' }} />
                </div>
              ) : (
                <p className="ps-summary-text">{summaries?.[key] ?? '—'}</p>
              )}
            </div>
          ))}

          {/* Usage sparkline */}
          <div className="ps-card ps-chart">
            <div className="ps-label">
              <BarChart2 size={11} strokeWidth={2.5} />
              Activity
            </div>
            <ResponsiveContainer width="100%" height={50}>
              <AreaChart data={sparkData} margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
                <defs>
                  <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={ACCENT} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={ACCENT} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="sessions"
                  stroke={ACCENT}
                  fill="url(#sparkFill)"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Tooltip
                  contentStyle={{ background: '#1c1510', border: '1px solid #2e221c', fontSize: 11, borderRadius: 6 }}
                  formatter={v => [v, 'sessions']}
                  labelFormatter={l => l}
                />
              </AreaChart>
            </ResponsiveContainer>
            <div className="ps-chart-foot">{weekTotal} session{weekTotal !== 1 ? 's' : ''} this week</div>
          </div>

          {/* Latest transcript */}
          <div className="ps-card ps-latest">
            <div className="ps-label">
              <MessageSquare size={11} strokeWidth={2.5} />
              Latest
            </div>
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
