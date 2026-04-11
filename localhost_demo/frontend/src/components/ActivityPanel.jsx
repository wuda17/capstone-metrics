import { useState, useMemo, useEffect, useRef } from 'react'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  Activity, Clock, Mic, Calendar, MessageSquare,
  Sun, CalendarDays, CalendarRange, RefreshCw,
} from 'lucide-react'
import { useSummary } from '../hooks/useApi.js'
import { PATIENT_NAME } from '../config.js'
import { RED, GREEN, AMBER, TEAL, PURPLE } from '../theme.js'
import './ActivityPanel.css'

// ── Helpers ───────────────────────────────────────────────────────────────────

function emotionColor(score) {
  if (score == null) return 'var(--border)'
  if (score > 0.1) return GREEN
  if (score < -0.1) return RED
  return AMBER
}

function buildWeekUsage(timeSeries, segmentMinutes) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const counts = Object.fromEntries(days.map(d => [d, 0]))
  for (const seg of timeSeries ?? []) {
    try {
      const d = days[new Date(seg.segment_start).getDay()]
      counts[d] += (seg.sample_count ?? 1) * segmentMinutes
    } catch {}
  }
  return days.map(d => ({ day: d, minutes: Math.round(counts[d]) }))
}

function relativeTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (isNaN(date.getTime())) return '—'
  const diff = Date.now() - date.getTime()
  const mins = Math.round(diff / 60_000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7)  return `${days}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// ── Summary card ──────────────────────────────────────────────────────────────

const PERIODS = [
  { key: 'today', label: 'Today',      sub: 'Past 24 hours', Icon: Sun,          color: TEAL   },
  { key: 'week',  label: 'This Week',  sub: 'Past 7 days',   Icon: CalendarDays, color: RED    },
  { key: 'month', label: 'This Month', sub: 'Past 30 days',  Icon: CalendarRange, color: PURPLE },
]

function SummaryCard({ period, text, loading }) {
  return (
    <div className="ap-summary-card tile">
      <div className="ap-sc-header">
        <period.Icon size={18} strokeWidth={1.75} style={{ color: period.color, flexShrink: 0 }} />
        <div>
          <div className="ap-sc-period">{period.label}</div>
          <div className="ap-sc-sub">{period.sub}</div>
        </div>
      </div>
      <div className="ap-sc-body">
        {loading ? (
          <div className="ap-sc-skeleton">
            <div className="ap-skeleton-line" style={{ width: '92%' }} />
            <div className="ap-skeleton-line" style={{ width: '78%' }} />
            <div className="ap-skeleton-line" style={{ width: '85%' }} />
          </div>
        ) : text ? (
          <p className="ap-sc-text">{text}</p>
        ) : (
          <p className="ap-sc-empty">No summary available yet.</p>
        )}
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

const LS_KEY = 'ferb_last_seen_ts'

export default function ActivityPanel({ current, status, highlightTime }) {
  const [expandedKey, setExpandedKey] = useState(null)
  const [highlightKey, setHighlightKey] = useState(null)
  const itemRefs = useRef({})
  const { data: summaries, loading: sumLoading, refresh } = useSummary()

  // Track unseen messages — initialise to now on first ever visit so nothing starts unseen
  const [lastSeenTs] = useState(() => {
    const stored = localStorage.getItem(LS_KEY)
    if (!stored) {
      const now = new Date().toISOString()
      localStorage.setItem(LS_KEY, now)
      return now
    }
    return stored
  })

  // On unmount mark everything seen as of now
  useEffect(() => {
    return () => localStorage.setItem(LS_KEY, new Date().toISOString())
  }, [])

  // Scroll to and highlight the matching transcript when highlightTime changes
  useEffect(() => {
    if (!highlightTime || !current?.transcripts?.items) return
    const targetMs = new Date(highlightTime).getTime()
    let bestKey = null
    let bestDiff = Infinity
    for (const item of current.transcripts.items) {
      if (!item.event_time) continue
      const diff = Math.abs(new Date(item.event_time).getTime() - targetMs)
      if (diff < bestDiff) { bestDiff = diff; bestKey = item.event_time }
    }
    if (!bestKey) return
    setExpandedKey(bestKey)
    setHighlightKey(bestKey)
    // Delay scroll so DOM has updated
    setTimeout(() => {
      itemRefs.current[bestKey]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 120)
    const t = setTimeout(() => setHighlightKey(null), 3000)
    return () => clearTimeout(t)
  }, [highlightTime, current])

  const segmentMinutes = current?.meta?.segment_minutes ?? 1
  const timeSeries     = current?.metrics?.time_series ?? []
  const totalMinutes   = (current?.meta?.snapshot_count ?? 0) * segmentMinutes
  const sessionCount   = current?.meta?.snapshot_count ?? 0

  const lastItem = current?.transcripts?.items?.at(-1)
  const lastSeen = lastItem
    ? new Date(lastItem.event_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'

  const weekData = useMemo(
    () => buildWeekUsage(timeSeries, segmentMinutes),
    [timeSeries, segmentMinutes]
  )

  const moodData = useMemo(() => (
    timeSeries
      .filter(seg => seg.values?.emotion_score != null)
      .map(seg => ({
        t: seg.segment_start,
        label: new Date(seg.segment_start).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        value: +seg.values.emotion_score.toFixed(3),
      }))
      .slice(-30)
  ), [timeSeries])

  const groupedTranscripts = useMemo(() => {
    const sorted = [...(current?.transcripts?.items ?? [])]
      .sort((a, b) => {
        const ta = a.event_time ? new Date(a.event_time).getTime() : 0
        const tb = b.event_time ? new Date(b.event_time).getTime() : 0
        return tb - ta  // newest first
      })
      .slice(0, 40)
    const result = []
    let lastDate = null
    for (const item of sorted) {
      const dateLabel = item.event_time
        ? new Date(item.event_time).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
        : null
      if (dateLabel && dateLabel !== lastDate) {
        result.push({ type: 'sep', label: dateLabel })
        lastDate = dateLabel
      }
      result.push({ type: 'item', item })
    }
    return result
  }, [current])

  return (
    <div className="activity-panel">

      {/* ── Hero ── */}
      <div className="ap-hero">
        <div className="ap-hero-left">
          <h1 className="ap-hero-name">{PATIENT_NAME}</h1>
          {status?.recording && (
            <div className="ap-live-badge">
              <span className="ap-live-dot" />
              <span className="ap-live-label">Live</span>
            </div>
          )}
        </div>
        <div className="ap-hero-stats">
          <div className="ap-hero-stat">
            <Clock size={14} strokeWidth={2} style={{ color: 'var(--text-dim)' }} />
            <span className="ap-hero-stat-val">{totalMinutes}</span>
            <span className="ap-hero-stat-lbl">total minutes</span>
          </div>
          <div className="ap-hero-divider" />
          <div className="ap-hero-stat">
            <Mic size={14} strokeWidth={2} style={{ color: 'var(--text-dim)' }} />
            <span className="ap-hero-stat-val">{sessionCount}</span>
            <span className="ap-hero-stat-lbl">sessions</span>
          </div>
          <div className="ap-hero-divider" />
          <div className="ap-hero-stat">
            <span className="ap-hero-stat-lbl">Last session</span>
            <span className="ap-hero-stat-val ap-hero-stat-val--sm">{lastSeen}</span>
          </div>
        </div>
      </div>

      {/* ── AI Summaries ── */}
      <div className="ap-section-header">
        <h3 className="ap-tile-title">
          <Sun size={14} strokeWidth={2} /> AI Summaries
        </h3>
        <button className="ap-refresh-btn" onClick={refresh} title="Regenerate summaries">
          <RefreshCw size={13} strokeWidth={2} />
          Refresh
        </button>
      </div>
      <div className="ap-summaries">
        {PERIODS.map(p => (
          <SummaryCard
            key={p.key}
            period={p}
            text={summaries?.[p.key]}
            loading={sumLoading}
          />
        ))}
      </div>

      {/* ── Weekly usage + session stats ── */}
      <div className="tile ap-usage-tile">
        <div className="ap-usage-inner">
          <div className="ap-usage-chart">
            <h3 className="ap-tile-title">
              <Calendar size={14} strokeWidth={2} /> Weekly Usage
            </h3>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={weekData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }} barSize={22}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} width={30} />
                <Tooltip
                  contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }}
                  formatter={v => [`${v} min`, 'Usage']}
                />
                <Bar dataKey="minutes" fill={AMBER} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="ap-usage-stats">
            <div className="ap-ustat">
              <span className="ap-ustat-val">{totalMinutes}</span>
              <span className="ap-ustat-lbl">total minutes recorded</span>
            </div>
            <div className="ap-ustat">
              <span className="ap-ustat-val">{sessionCount}</span>
              <span className="ap-ustat-lbl">total sessions</span>
            </div>
            <div className="ap-ustat">
              <span className="ap-ustat-val">{weekData.filter(d => d.minutes > 0).length}</span>
              <span className="ap-ustat-lbl">active days this week</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Mood trend ── */}
      <div className="tile">
        <h3 className="ap-tile-title">
          <Activity size={14} strokeWidth={2} /> Mood Trend
        </h3>
        {moodData.length === 0 ? (
          <p className="ap-empty">No mood data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={moodData} margin={{ top: 14, right: 14, bottom: 4, left: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis domain={[-1, 1]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} width={36} />
              <ReferenceLine
                y={0}
                stroke="var(--border)"
                strokeDasharray="5 3"
                label={{ value: 'neutral', fill: 'var(--text-dim)', fontSize: 9, position: 'insideTopRight' }}
              />
              <Tooltip
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }}
                formatter={v => [v.toFixed(3), 'Mood Score']}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--border)"
                strokeWidth={2}
                dot={({ cx, cy, index }) => {
                  if (!cx || !cy) return null
                  const val = moodData[index]?.value
                  const color = val > 0.1 ? GREEN : val < -0.1 ? RED : AMBER
                  const s = 11 // radius
                  return (
                    <g key={index} transform={`translate(${cx},${cy})`}>
                      <circle r={s} fill={color} stroke="var(--surface)" strokeWidth={2} />
                      <circle cx={-3.5} cy={-2.5} r={1.4} fill="white" />
                      <circle cx={3.5}  cy={-2.5} r={1.4} fill="white" />
                      {val > 0.1
                        ? <path d="M-4 2 Q0 6 4 2"   stroke="white" strokeWidth={1.6} fill="none" strokeLinecap="round" />
                        : val < -0.1
                        ? <path d="M-4 5 Q0 1 4 5"   stroke="white" strokeWidth={1.6} fill="none" strokeLinecap="round" />
                        : <line x1={-4} y1={3} x2={4} y2={3} stroke="white" strokeWidth={1.6} strokeLinecap="round" />
                      }
                    </g>
                  )
                }}
                activeDot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Transcript timeline ── */}
      <div className="tile">
        <h3 className="ap-tile-title">
          <MessageSquare size={14} strokeWidth={2} /> Conversation Log
        </h3>
        {groupedTranscripts.length === 0 ? (
          <p className="ap-empty">No transcripts recorded yet.</p>
        ) : (
          <div className="ap-timeline">
            {groupedTranscripts.map((entry, i) => {
              if (entry.type === 'sep') {
                return (
                  <div key={`sep-${i}`} className="ap-date-sep">
                    <span>{entry.label}</span>
                  </div>
                )
              }
              const { item } = entry
              const key = item.event_time ?? String(i)
              const isExpanded = expandedKey === key
              const isUnseen = !!(lastSeenTs && item.event_time && item.event_time > lastSeenTs)
              const isHighlighted = highlightKey === key
              const timeLabel = relativeTime(item.event_time)
              return (
                <div
                  key={key}
                  ref={el => { if (el) itemRefs.current[key] = el; else delete itemRefs.current[key] }}
                  className={`ap-bubble-row${isHighlighted ? ' highlighted' : ''}`}
                  onClick={() => setExpandedKey(isExpanded ? null : key)}
                >
                  <div className={`ap-bubble-avatar${isUnseen ? ' unseen' : ''}`}>E</div>
                  <div className="ap-bubble-body">
                    <div className={`ap-bubble${isExpanded ? ' expanded' : ''}${isUnseen ? ' unseen' : ''}${isHighlighted ? ' highlighted' : ''}`}>
                      {item.text || <em style={{ color: 'var(--text-dim)' }}>No transcript text.</em>}
                    </div>
                    <div className="ap-bubble-meta">
                      <span className="ap-bubble-time">{timeLabel}</span>
                      {isUnseen && <span className="ap-bubble-new">New</span>}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

    </div>
  )
}
