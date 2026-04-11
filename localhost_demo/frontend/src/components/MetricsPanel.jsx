import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  AreaChart, Area,
} from 'recharts'
import { HeartPulse, AlertTriangle, TrendingUp, Radar as RadarIcon, ChevronDown, CheckCircle2, Maximize2, ArrowUp, ArrowDown } from 'lucide-react'
import { RED, BLUE, TEAL, PURPLE, AMBER, GREEN, PINK, DIM } from '../theme.js'
import { METRIC_REFS } from '../references.js'
import './MetricsPanel.css'
import { PATIENT_NAME } from '../config.js'

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtTime(iso) {
  try { return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }
  catch { return iso }
}

function fmtDate(iso) {
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }
  catch { return iso }
}

/** Collect all unique time-series segments across history entries + current. */
export function buildTimeSeriesData(current, history, metric) {
  const pointMap = new Map()
  const addEntry = (entry) => {
    for (const seg of entry?.metrics?.time_series ?? []) {
      const t = seg.segment_start
      if (!t) continue
      const v = seg.values?.[metric]
      if (v != null && !pointMap.has(t)) {
        pointMap.set(t, { t, value: +v.toFixed(3), label: fmtTime(t), date: fmtDate(t) })
      }
    }
  }
  if (Array.isArray(history)) history.forEach(addEntry)
  if (current) addEntry(current)
  return [...pointMap.values()].sort((a, b) => a.t.localeCompare(b.t))
}


/** Build acuity score history for sparkline. */
function buildAcuityHistory(current, history) {
  const seen = new Set()
  const points = []
  const processEntry = (entry) => {
    const t = entry?.meta?.generated_at
    if (!t || seen.has(t)) return
    seen.add(t)
    points.push({ t, value: computeAcuity(entry) })
  }
  if (Array.isArray(history)) history.forEach(processEntry)
  if (current) processEntry(current)
  return points.sort((a, b) => a.t.localeCompare(b.t)).slice(-20)
}

// ── metrics config ────────────────────────────────────────────────────────────

export const METRICS = [
  { key: 'speech_rate_wpm',         label: 'Speaking Speed',       unit: 'wpm', color: RED,    higherIsBetter: true,  radarLabel: 'Speaking\nSpeed'  },
  { key: 'phonation_to_time_ratio', label: 'Phonation Ratio',      unit: '',    color: TEAL,   higherIsBetter: true,  radarLabel: 'Phonation'        },
  { key: 'mean_pause_duration_sec', label: 'Mean Pause Duration',  unit: 's',   color: AMBER,  higherIsBetter: false, radarLabel: 'Fluency'          },
  { key: 'type_token_ratio',        label: 'Vocabulary Diversity', unit: '',    color: PURPLE, higherIsBetter: true,  radarLabel: 'Vocabulary'       },
  { key: 'emotion_score',           label: 'Mood Score',           unit: '',    color: GREEN,  higherIsBetter: true,  radarLabel: 'Mood'             },
  { key: 'jitter_local',            label: 'Voice Jitter',         unit: '',    color: PINK,   higherIsBetter: false, radarLabel: 'Voice\nStability' },
  { key: 'articulation_rate_wpm',   label: 'Articulation Rate',    unit: 'wpm', color: BLUE,   higherIsBetter: true,  radarLabel: null               },
  { key: 'f0_mean_hz',              label: 'Pitch (F0)',           unit: 'Hz',  color: BLUE,   higherIsBetter: null,  radarLabel: null               },
  { key: 'shimmer_local_db',        label: 'Voice Shimmer',        unit: 'dB',  color: PINK,   higherIsBetter: false, radarLabel: null               },
  { key: 'self_pronoun_ratio',      label: 'Self-Reference',       unit: '',    color: AMBER,  higherIsBetter: null,  radarLabel: null               },
]

const METRIC_LABEL_MAP = Object.fromEntries(METRICS.map(m => [m.key, m.label]))
const metricLabel = (key) => METRIC_LABEL_MAP[key] ?? (key ? key.replace(/_/g, ' ') : '—')
const METRIC_OPTIONS = METRICS.map(({ key, label, unit, color, higherIsBetter }) => ({ key, label, unit, color, higherIsBetter }))

const RADAR_AXES = METRICS
  .filter(m => m.radarLabel)
  .map(({ key, radarLabel: label, higherIsBetter }) => ({ key, label, higherIsBetter }))

// ── acuity ────────────────────────────────────────────────────────────────────

export function computeAcuity(current) {
  const items = (current?.alerts?.items ?? []).filter(a => a.status === 'alert')
  if (items.length === 0) return 100
  let score = 100
  for (const a of items) score -= a.severity === 'high' ? 30 : 15
  return Math.max(0, Math.min(100, score))
}

function acuityMeta(acuity) {
  if (acuity >= 80) return { color: GREEN, tileClass: 'tile--filled-green' }
  if (acuity >= 60) return { color: AMBER, tileClass: 'tile--filled-amber' }
  return               { color: RED,   tileClass: 'tile--filled-red'   }
}

// ── radar ─────────────────────────────────────────────────────────────────────

function radarScore(currentVal, baselineVal, higherIsBetter) {
  if (baselineVal == null || currentVal == null || baselineVal === 0) return 50
  if (higherIsBetter) return Math.max(10, Math.min(90, (currentVal / baselineVal) * 50))
  return Math.max(10, Math.min(90, (baselineVal / currentVal) * 50))
}

function buildRadarData(current) {
  const baseline    = current?.metrics?.baseline?.values ?? {}
  const currentVals = current?.metrics?.current?.values ?? current?.metrics?.time_series?.at(-1)?.values ?? {}
  const latest      = current?.metrics?.time_series?.at(-1)?.values ?? {}
  return RADAR_AXES.map(m => {
    const b = baseline[m.key]
    const c = currentVals[m.key] ?? latest[m.key]
    const score = m.key === 'emotion_score'
      ? Math.max(10, Math.min(90, ((c ?? 0) + 1) / 2 * 80 + 10))
      : radarScore(c, b, m.higherIsBetter)
    return { metric: m.label, current: score, baseline: 50 }
  })
}

// ── Radar tick ────────────────────────────────────────────────────────────────

function makeRadarTick(onNavigate) {
  return function RadarTick({ x, y, payload, textAnchor }) {
    const axis = RADAR_AXES.find(a => a.label === payload.value)
    const lines = payload.value.split('\n')
    return (
      <g
        className="radar-tick"
        style={{ cursor: axis ? 'pointer' : 'default' }}
        onClick={() => axis && onNavigate('literature', axis.key)}
      >
        {lines.map((line, i) => (
          <text
            key={i}
            x={x}
            y={y + i * 14 - (lines.length - 1) * 7}
            textAnchor={textAnchor}
            fill={axis ? BLUE : 'var(--text-muted)'}
            fontSize={11}
          >
            {line}
          </text>
        ))}
      </g>
    )
  }
}

// ── AlertRows ─────────────────────────────────────────────────────────────────

function alertKey(a) { return `${a.metric}-${a.severity}` }

function AlertRows({ alerts, current, history, onNavigate }) {
  const [selected, setSelected] = useState(null)
  const active = useMemo(() => alerts.filter(a => a.status !== 'ok'), [alerts])

  const [seenKeys, setSeenKeys] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('ferbai_seen_alerts') || '[]')) }
    catch { return new Set() }
  })

  const markSeen = (a) => {
    const key = alertKey(a)
    setSeenKeys(prev => {
      if (prev.has(key)) return prev
      const next = new Set(prev)
      next.add(key)
      try { localStorage.setItem('ferbai_seen_alerts', JSON.stringify([...next])) } catch {}
      return next
    })
  }

  const toggle = (i) => {
    setSelected(selected === i ? null : i)
    if (active[i]) markSeen(active[i])
  }

  const sel = selected !== null ? active[selected] : null
  const selMetric = sel ? METRICS.find(m => m.key === sel.metric) : null

  const chartData = useMemo(() => {
    if (!sel?.metric) return []
    return buildTimeSeriesData(current, history, sel.metric)
  }, [sel, current, history])

  const baselineVal = sel?.metric
    ? current?.metrics?.baseline?.values?.[sel.metric]
    : null

  if (active.length === 0) {
    return (
      <div className="alert-all-ok">
        <CheckCircle2 size={16} strokeWidth={2} />
        <span>All metrics within baseline</span>
      </div>
    )
  }

  return (
    <div className="alert-rows-wrap">
      {active.map((a, i) => {
        const isNew  = !seenKeys.has(alertKey(a))
        const isOpen = selected === i
        return (
          <div key={i} className="alert-row-item">
            <button
              className={`alert-row ${a.severity}${isOpen ? ' open' : ''}${isNew ? ' new' : ''}`}
              onClick={() => toggle(i)}
            >
              <span className={`alert-dot ${a.severity}`} />
              <span className="alert-row-label">{a.label ?? metricLabel(a.metric)}</span>
              {isNew && <span className="alert-badge-new">new</span>}
              {!isNew && a.delta_pct != null && (
                <span className={`alert-delta ${a.severity}`}>
                  {a.delta_pct > 0 ? '+' : ''}{a.delta_pct.toFixed(1)}%
                </span>
              )}
              <ChevronDown size={14} className={`alert-chevron${isOpen ? ' open' : ''}`} strokeWidth={2} />
            </button>

            {isOpen && (
              <div className={`alert-expand ${a.severity}`}>
                {chartData.length > 1 && (
                  <ResponsiveContainer width="100%" height={130}>
                    <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke="rgba(0,0,0,0.06)" strokeDasharray="4 4" vertical={false} />
                      <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} width={36} />
                      <Tooltip
                        contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }}
                        formatter={v => [`${v} ${selMetric?.unit ?? ''}`, selMetric?.label ?? a.label]}
                      />
                      {baselineVal != null && (
                        <ReferenceLine
                          y={baselineVal}
                          stroke={DIM}
                          strokeDasharray="5 3"
                          label={{ value: 'baseline', fill: 'var(--text-dim)', fontSize: 9, position: 'insideTopRight' }}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke={RED}
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
                <p className="alert-expand-msg">{a.message}</p>
                {METRIC_REFS[a.metric] && (
                  <div className="alert-evidence">
                    <div className="alert-evidence-hdr">Evidence</div>
                    <p className="alert-evidence-desc">{METRIC_REFS[a.metric].description}</p>
                    <p className="alert-evidence-claim">"{METRIC_REFS[a.metric].claim}"</p>
                    <div className="alert-evidence-footer">
                      <span className="alert-evidence-cite">{METRIC_REFS[a.metric].citation}</span>
                      <button
                        className="alert-evidence-more"
                        onClick={e => { e.stopPropagation(); onNavigate('literature', a.metric) }}
                      >
                        Show more →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── SingleMetricChart ─────────────────────────────────────────────────────────

function SingleMetricChart({ metric, current, history, onMaximize, isOnly }) {
  const tsData = useMemo(
    () => buildTimeSeriesData(current, history, metric.key),
    [current, history, metric.key]
  )
  const baselineVal = current?.metrics?.baseline?.values?.[metric.key]
  const currentVal  = current?.metrics?.time_series?.at(-1)?.values?.[metric.key]
    ?? current?.metrics?.current?.values?.[metric.key]

  const ref = METRIC_REFS[metric.key]

  // Trend direction: compare last two time-series points
  const trendDir = useMemo(() => {
    if (tsData.length < 2) return null
    const last = tsData.at(-1).value
    const prev = tsData.at(-2).value
    if (last === prev) return null
    return last > prev ? 'up' : 'down'
  }, [tsData])

  const trendColor = useMemo(() => {
    if (!trendDir) return 'var(--text-dim)'
    if (metric.higherIsBetter === null) return 'var(--text-dim)'
    const isGood = (trendDir === 'up') === (metric.higherIsBetter !== false)
    return isGood ? GREEN : RED
  }, [trendDir, metric.higherIsBetter])

  return (
    <div className="single-metric-tile tile">
      <div className="smt-header">
        <span className="smt-dot" style={{ background: metric.color }} />
        <span className="smt-label">{metric.label}</span>
        {metric.unit && <span className="smt-unit">{metric.unit}</span>}
        {!isOnly && onMaximize && (
          <button className="smt-maximize" onClick={onMaximize} title="Focus this chart">
            <Maximize2 size={11} strokeWidth={2} />
          </button>
        )}
      </div>
      {currentVal != null && (
        <div className="smt-value-row">
          <span className="smt-value" style={{ color: metric.color }}>
            {typeof currentVal === 'number' ? currentVal.toFixed(2) : currentVal}
          </span>
          {trendDir && (
            <span className="smt-trend-circle" style={{ background: trendColor }}>
              {trendDir === 'up'
                ? <ArrowUp size={11} strokeWidth={3} color="#fff" />
                : <ArrowDown size={11} strokeWidth={3} color="#fff" />}
            </span>
          )}
        </div>
      )}
      {tsData.length === 0 ? (
        <div className="smt-empty">No data yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={140}>
          <LineChart data={tsData} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} width={38} />
            <Tooltip
              contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }}
              formatter={v => [`${v} ${metric.unit}`, metric.label]}
            />
            {baselineVal != null && (
              <ReferenceLine
                y={baselineVal}
                stroke={DIM}
                strokeDasharray="5 3"
                label={{ value: 'baseline', fill: 'var(--text-dim)', fontSize: 9, position: 'insideTopRight' }}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={metric.color}
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, index } = props
                if (!cx || !cy) return null
                if (tsData.length > 1 && index === tsData.length - 1)
                  return <g key={index}><circle cx={cx} cy={cy} r={6} fill={metric.color} fillOpacity={0.2} /><circle cx={cx} cy={cy} r={3} fill={metric.color} stroke="var(--surface)" strokeWidth={1.5} /></g>
                return <circle key={index} cx={cx} cy={cy} r={2} fill={metric.color} />
              }}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
      {ref && (
        <a className="smt-cite" href={ref.doi} target="_blank" rel="noopener noreferrer" style={{ color: metric.color }}>
          {ref.citation} ↗
        </a>
      )}
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function MetricsPanel({ current, history, onNavigate = () => {} }) {
  const [selectedMetrics, setSelectedMetrics] = useState([METRIC_OPTIONS[0], METRIC_OPTIONS[4]])

  const toggleMetric = (metric) => {
    setSelectedMetrics(prev => {
      const exists = prev.find(m => m.key === metric.key)
      if (exists) return prev.length > 1 ? prev.filter(m => m.key !== metric.key) : prev
      if (prev.length >= 4) return prev
      return [...prev, metric]
    })
  }

  const acuityHistory = useMemo(() => buildAcuityHistory(current, history), [current, history])
  const radarData    = useMemo(() => buildRadarData(current), [current])
  const acuity       = useMemo(() => computeAcuity(current), [current])

  const { color: acuityColor, tileClass: acuityTileClass } = acuityMeta(acuity)

  const alerts        = current?.alerts?.items ?? []
  const activeAlerts  = alerts.filter(a => a.status === 'alert')
  const sessionCount = current?.meta?.snapshot_count ?? 0
  const lastItem     = current?.transcripts?.items?.at(-1)
  const lastSeen     = lastItem
    ? new Date(lastItem.event_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'

  const moodScore  = current?.metrics?.time_series?.at(-1)?.values?.emotion_score
    ?? current?.metrics?.current?.values?.emotion_score ?? null
  const moodTsData = useMemo(() => buildTimeSeriesData(current, history, 'emotion_score'), [current, history])
  const moodColor  = moodScore == null ? TEAL : moodScore > 0.1 ? GREEN : moodScore < -0.1 ? RED : AMBER
  const moodLabel  = moodScore == null ? 'No data' : moodScore > 0.1 ? 'Positive' : moodScore < -0.1 ? 'Concerning' : 'Neutral'
  const moodDisplay = moodScore == null ? '—' : (moodScore >= 0 ? '+' : '') + (moodScore * 100).toFixed(0)
  const moodTileClass = moodScore == null ? 'tile--filled-teal' : moodScore > 0.1 ? 'tile--filled-green' : moodScore < -0.1 ? 'tile--filled-red' : 'tile--filled-amber'

  const RadarTick = useMemo(() => makeRadarTick(onNavigate), [onNavigate])

  return (
    <div className="metrics-panel">

      <div className="panel-header">
        <h2 className="panel-title"><HeartPulse size={18} strokeWidth={2} /> Wellbeing</h2>
        <p className="panel-sub">Speech and vocal pattern analysis for {PATIENT_NAME}</p>
      </div>

      <div className="metrics-grid">

        {/* ── Alerts tile — col span 2 ── */}
        <div className="tile alerts-tile">
          <h3 className="tile-title"><AlertTriangle size={14} strokeWidth={2} /> Alerts</h3>
          <AlertRows alerts={alerts} current={current} history={history} onNavigate={onNavigate} />
        </div>

        {/* ── Acuity KPI tile ── */}
        <div className={`tile ${acuityTileClass} kpi-tile`}>
          <div className="kpi-label">Acuity Score</div>
          <div className="kpi-value-row">
            <span className="kpi-value" style={{ color: acuityColor }}>{acuity}</span>
            <span className="kpi-outof" style={{ color: acuityColor }}>/100</span>
          </div>
          <div className="kpi-sub">Starts at 100 · −30 per high alert · −15 per medium</div>

          {activeAlerts.length > 0 && (
            <div className="kpi-contributors">
              {activeAlerts.map((a, i) => (
                <div key={i} className="kpi-contrib-row">
                  <span className="kpi-contrib-label">{a.label ?? metricLabel(a.metric)}</span>
                  <span className="kpi-contrib-badge" data-sev={a.severity}>
                    {a.severity === 'high' ? '−30' : '−15'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {acuityHistory.length > 1 && (
            <div className="kpi-sparkline">
              <div className="kpi-sparkline-label">Score history</div>
              <ResponsiveContainer width="100%" height={56}>
                <AreaChart data={acuityHistory} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="acuityFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={acuityColor} stopOpacity={0.35} />
                      <stop offset="95%" stopColor={acuityColor} stopOpacity={0}    />
                    </linearGradient>
                  </defs>
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                    formatter={v => [v, 'Acuity']}
                    labelFormatter={() => ''}
                  />
                  <Area type="monotone" dataKey="value" stroke={acuityColor} fill="url(#acuityFill)" strokeWidth={2} dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="kpi-meta">{sessionCount} session{sessionCount !== 1 ? 's' : ''} · {lastSeen}</div>
        </div>

        {/* ── Mood KPI tile ── */}
        <div className={`tile ${moodTileClass} kpi-tile`}>
          <div className="kpi-label">Mood Score</div>
          <div className="kpi-value" style={{ color: moodColor }}>{moodDisplay}</div>
          <div className="kpi-sub">{moodLabel}</div>
          {moodTsData.length > 1 && (
            <div className="kpi-sparkline">
              <ResponsiveContainer width="100%" height={48}>
                <AreaChart data={moodTsData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="moodFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={moodColor} stopOpacity={0.35} />
                      <stop offset="95%" stopColor={moodColor} stopOpacity={0}    />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="value" stroke={moodColor} fill="url(#moodFill)" strokeWidth={2} dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="kpi-meta">emotion score</div>
        </div>

        {/* ── Radar snapshot tile — col span 2 ── */}
        <div className="tile radar-tile">
          <div className="tile-header">
            <h3 className="tile-title"><RadarIcon size={14} strokeWidth={2} /> Wellbeing Snapshot</h3>
            <span className="tile-sub">Outer = better · click labels for research</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} outerRadius={100}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={<RadarTick />} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="Baseline" dataKey="baseline" stroke={DIM} fill={DIM} fillOpacity={0.05} strokeDasharray="5 3" />
              <Radar name="Current"  dataKey="current"  stroke={BLUE} fill={BLUE} fillOpacity={0.18} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
              <Tooltip
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }}
                formatter={(value, name) => [value.toFixed(0), name]}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Multi-metric trend tile — col span 3 ── */}
        <div className="tile trend-tile">
          <div className="trend-header">
            <h3 className="tile-title"><TrendingUp size={14} strokeWidth={2} /> Trend Over Time</h3>
            <p className="trend-hint">Select up to 4 metrics to compare · dashed line = baseline</p>
            <div className="metric-pills">
              {METRIC_OPTIONS.map(m => {
                const isActive = !!selectedMetrics.find(s => s.key === m.key)
                return (
                  <button
                    key={m.key}
                    className={`metric-pill${isActive ? ' active' : ''}`}
                    style={isActive ? { background: m.color + '1a', borderColor: m.color, color: m.color } : {}}
                    onClick={() => toggleMetric(m)}
                  >
                    {m.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div
            className="side-by-side-charts"
            style={{ gridTemplateColumns: `repeat(${selectedMetrics.length}, 1fr)` }}
          >
            {selectedMetrics.map(m => (
              <SingleMetricChart
                key={m.key}
                metric={m}
                current={current}
                history={history}
                isOnly={selectedMetrics.length === 1}
                onMaximize={() => setSelectedMetrics([m])}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
