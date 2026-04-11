import { useState, useRef, useEffect, useMemo } from 'react'
import { ArrowUp, ArrowDown, Minus, Brain, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { LineChart, Line, BarChart, Bar, AreaChart, Area, ResponsiveContainer } from 'recharts'
import { sendChatMessage } from '../hooks/useApi.js'
import { PATIENT_NAME } from '../config.js'
import { computeAcuity } from './MetricsPanel.jsx'
import { GREEN, AMBER, RED, PURPLE, TEAL } from '../theme.js'
import './EntryPage.css'

const SUGGESTIONS = [
  `How has ${PATIENT_NAME} been feeling this week?`,
  'Are there any concerning trends?',
  'What topics have they been discussing most?',
  'Give me a summary of last month',
]

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

// ── TrendCircle ───────────────────────────────────────────────────────────────

function TrendCircle({ color, dir, size = 20 }) {
  const Icon = dir === 'up' ? ArrowUp : dir === 'down' ? ArrowDown : Minus
  return (
    <span className="trend-circle" style={{ background: color, width: size, height: size }}>
      <Icon size={Math.round(size * 0.55)} color="#fff" strokeWidth={3} />
    </span>
  )
}

// ── InsightsPanel ─────────────────────────────────────────────────────────────

function InsightsPanel({ current, history, memories, status, open, onToggle, onNavigate }) {
  const acuity      = useMemo(() => computeAcuity(current), [current])
  const acuityColor = acuity >= 80 ? GREEN : acuity >= 60 ? AMBER : RED

  const segmentMinutes = current?.meta?.segment_minutes ?? 1
  const totalMinutes   = (current?.meta?.snapshot_count ?? 0) * segmentMinutes
  const timeSeries     = current?.metrics?.time_series ?? []

  const acuityTrend = useMemo(() => {
    if (!Array.isArray(history) || history.length < 2) return 'flat'
    const sorted = [...history].sort((a, b) => (a.meta?.generated_at ?? '').localeCompare(b.meta?.generated_at ?? ''))
    const prev = computeAcuity(sorted.at(-2))
    return acuity > prev + 2 ? 'up' : acuity < prev - 2 ? 'down' : 'flat'
  }, [history, acuity])

  const moodScore = timeSeries.at(-1)?.values?.emotion_score ?? null
  const moodColor = emotionColor(moodScore)
  const moodTrend = useMemo(() => {
    const pts = timeSeries.filter(s => s.values?.emotion_score != null).slice(-6)
    if (pts.length < 2) return 'flat'
    const first = pts[0].values.emotion_score
    const last  = pts.at(-1).values.emotion_score
    return last > first + 0.05 ? 'up' : last < first - 0.05 ? 'down' : 'flat'
  }, [timeSeries])

  const activeAlerts = (current?.alerts?.items ?? []).filter(a => a.status === 'alert')

  const moodSparkData = useMemo(() =>
    timeSeries.filter(s => s.values?.emotion_score != null)
      .slice(-15)
      .map(s => ({ value: s.values.emotion_score })),
    [timeSeries]
  )

  const weekData = useMemo(
    () => buildWeekUsage(timeSeries, segmentMinutes),
    [timeSeries, segmentMinutes]
  )

  const timeline = memories?.timeline ?? memories?.memories ?? []
  const latestMem = [...timeline].sort((a, b) => {
    const ta = a.source_event_time ?? a.date ?? ''
    const tb = b.source_event_time ?? b.date ?? ''
    return tb.localeCompare(ta)
  })[0]
  const latestTranscript = current?.transcripts?.items?.at(-1)

  return (
    <div className="insights-panel tile">
      {/* Header */}
      <div className="insights-header" onClick={onToggle}>
        <div className="insights-identity">
          <span className="insights-name">{PATIENT_NAME}</span>
          {status?.recording && <span className="insights-live-dot" />}
        </div>
        <div className="insights-header-stats">
          <TrendCircle color={acuityColor} dir={acuityTrend} size={22} />
          <span className="insights-stat-label">{acuity} acuity</span>
          {activeAlerts.length > 0 && (
            <>
              <span className="insights-sep" />
              <span className="insights-alert-count">{activeAlerts.length} alert{activeAlerts.length !== 1 ? 's' : ''}</span>
            </>
          )}
          <span className="insights-sep" />
          <TrendCircle color={moodColor} dir={moodTrend} size={22} />
          <span className="insights-stat-label">mood</span>
          <span className="insights-sep" />
          <span className="insights-stat-label">{totalMinutes} min</span>
        </div>
        <button className="insights-toggle-pill" onClick={e => { e.stopPropagation(); onToggle() }}>
          {open ? 'Collapse' : 'Expand'}
          <ChevronRight size={12} strokeWidth={2} className={`insights-toggle-icon${open ? ' rotated' : ''}`} />
        </button>
      </div>

      {/* Collapsible body */}
      <div className={`insights-body${open ? ' insights-body--open' : ''}`}>
        <div className="insights-columns">

          {/* Activity */}
          <button className="insights-col insights-activity" onClick={() => onNavigate?.('activity')}>
            <div className="ic-label">Activity</div>
            <div className="ic-big">{totalMinutes}<span className="ic-big-unit">min</span></div>
            {moodSparkData.length > 1 && (
              <div className="ic-chart">
                <ResponsiveContainer width="100%" height={36}>
                  <LineChart data={moodSparkData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
                    <Line type="monotone" dataKey="value" stroke={moodColor} strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {weekData.some(d => d.minutes > 0) && (
              <div className="ic-chart">
                <ResponsiveContainer width="100%" height={32}>
                  <BarChart data={weekData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={10}>
                    <Bar dataKey="minutes" fill={AMBER} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="ic-footer">See all activity <ChevronRight size={11} strokeWidth={2} /></div>
          </button>

          <div className="insights-divider" />

          {/* Wellbeing */}
          <button className="insights-col insights-wellbeing" onClick={() => onNavigate?.('wellbeing')}>
            <div className="ic-label">Wellbeing</div>
            <div className="ic-big" style={{ color: acuityColor }}>{acuity}</div>
            <div className="ic-sub">/ 100 acuity</div>
            {activeAlerts.length === 0 ? (
              <div className="ic-ok">All clear</div>
            ) : (
              <div className="ic-alerts">
                {activeAlerts.slice(0, 3).map((a, i) => (
                  <div key={i} className="ic-alert-row">
                    <span className="ic-alert-dot" />
                    <span>{a.label ?? a.metric?.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="ic-footer">View wellbeing <ChevronRight size={11} strokeWidth={2} /></div>
          </button>

          <div className="insights-divider" />

          {/* Memory */}
          <button className="insights-col insights-memory" onClick={() => onNavigate?.('memories')}>
            <div className="ic-label"><Brain size={11} strokeWidth={2} /> Memory</div>
            {latestMem ? (
              <p className="ic-mem-text">{latestMem.content}</p>
            ) : (
              <p className="ic-mem-empty">No memories yet.</p>
            )}
            {latestTranscript && (
              <p className="ic-transcript">
                &ldquo;{latestTranscript.text?.slice(0, 70)}{latestTranscript.text?.length > 70 ? '…' : ''}&rdquo;
              </p>
            )}
            <div className="ic-footer">View memories <ChevronRight size={11} strokeWidth={2} /></div>
          </button>

        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EntryPage({ current, history, memories, status, onNavigate }) {
  const [messages, setMessages]         = useState([])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [insightsOpen, setInsightsOpen] = useState(true)
  const bottomRef = useRef()
  const inputRef  = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (messages.length === 1) setInsightsOpen(false)
  }, [messages.length])

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setLoading(true)
    try {
      const res = await sendChatMessage(msg)
      setMessages(prev => [...prev, { role: 'assistant', text: res.response }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Something went wrong — please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="home-chat">

      {/* ── InsightsPanel — always visible ── */}
      <InsightsPanel
        current={current}
        history={history}
        memories={memories}
        status={status}
        open={insightsOpen}
        onToggle={() => setInsightsOpen(o => !o)}
        onNavigate={onNavigate}
      />

      {/* ── Scrollable chat body ── */}
      <div className="home-body">
        {!hasMessages ? (
          <div className="home-empty">
            <img
              src="/brand/logo.png"
              alt="Ferb"
              className="home-logo-img"
              onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'block' }}
            />
            <span className="home-logo home-logo-fallback">F</span>
            <h1 className="home-heading">What would you like to know about {PATIENT_NAME}?</h1>
            <p className="home-sub">
              Ask anything about their recent conversations, mood patterns, or speech trends.
            </p>
          </div>
        ) : (
          <div className="home-messages">
            {messages.map((m, i) => (
              <div key={i} className={`hm hm--${m.role}`}>
                {m.role === 'assistant' && (
                  <span className="hm-avatar">
                    <img
                      src="/brand/logo.png"
                      alt=""
                      className="hm-avatar-img"
                      onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'inline' }}
                    />
                    <span className="hm-avatar-fallback">F</span>
                  </span>
                )}
                <div className="hm-bubble">
                  {m.role === 'assistant' ? <ReactMarkdown>{m.text}</ReactMarkdown> : m.text}
                </div>
              </div>
            ))}

            {loading && (
              <div className="hm hm--assistant">
                <span className="hm-avatar">
                  <img
                    src="/brand/logo.png"
                    alt=""
                    className="hm-avatar-img"
                    onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'inline' }}
                  />
                  <span className="hm-avatar-fallback">F</span>
                </span>
                <div className="hm-bubble hm-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Suggestion chips — only on empty state */}
      {!hasMessages && (
        <div className="home-chips">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="home-chip" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="home-input-wrap">
        <div className="home-input-row">
          <input
            ref={inputRef}
            className="home-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder={`Ask about ${PATIENT_NAME}…`}
            disabled={loading}
          />
          <button
            className="home-send"
            onClick={() => send()}
            disabled={loading || !input.trim()}
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </div>
        <p className="home-input-hint">Ferb may make mistakes. Always verify clinical decisions independently.</p>
      </div>

    </div>
  )
}
