import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { HeartPulse, AlertTriangle, TrendingUp, Radar as RadarIcon } from 'lucide-react'
import { ACCENT, SECONDARY, TEAL, SUCCESS, WARNING, DANGER, MUTED } from '../theme.js'
import './MetricsPanel.css'

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return iso }
}

/** Collect all unique time-series segments across history entries + current. */
function buildTimeSeriesData(current, history, metric) {
  const pointMap = new Map()

  const addEntry = (entry) => {
    const ts = entry?.metrics?.time_series ?? []
    for (const seg of ts) {
      const t = seg.segment_start
      if (!t) continue
      const v = seg.values?.[metric]
      if (v != null && !pointMap.has(t)) {
        pointMap.set(t, { t, value: +v.toFixed(3), label: fmtTime(t), date: fmtDate(t) })
      }
    }
  }

  // Walk oldest→newest so current.json wins on duplicates (it's the freshest)
  if (Array.isArray(history)) history.forEach(addEntry)
  if (current) addEntry(current)

  return [...pointMap.values()].sort((a, b) => a.t.localeCompare(b.t))
}

const RADAR_AXES = [
  { key: 'speech_rate_wpm',        label: 'Speaking\nSpeed',  higherIsBetter: true  },
  { key: 'phonation_to_time_ratio', label: 'Phonation',        higherIsBetter: true  },
  { key: 'type_token_ratio',        label: 'Vocabulary',       higherIsBetter: true  },
  { key: 'emotion_score',           label: 'Mood',             higherIsBetter: true  },
  { key: 'jitter_local',            label: 'Voice\nStability', higherIsBetter: false },
  { key: 'mean_pause_duration_sec', label: 'Fluency',          higherIsBetter: false },
]

function radarScore(currentVal, baselineVal, higherIsBetter) {
  if (baselineVal == null || currentVal == null || baselineVal === 0) return 50
  if (higherIsBetter) return Math.max(10, Math.min(90, (currentVal / baselineVal) * 50))
  return Math.max(10, Math.min(90, (baselineVal / currentVal) * 50))
}

function buildRadarData(current) {
  const baseline = current?.metrics?.baseline?.values ?? {}
  // Prefer current window; fall back to latest time-series segment
  const currentVals =
    current?.metrics?.current?.values ??
    current?.metrics?.time_series?.at(-1)?.values ?? {}
  const latest = current?.metrics?.time_series?.at(-1)?.values ?? {}

  return RADAR_AXES.map(m => {
    const b = baseline[m.key]
    const c = currentVals[m.key] ?? latest[m.key]
    const score = m.key === 'emotion_score'
      ? Math.max(10, Math.min(90, ((c ?? 0) + 1) / 2 * 80 + 10)) // map -1..1 → 10..90
      : radarScore(c, b, m.higherIsBetter)
    return { metric: m.label, current: score, baseline: 50 }
  })
}

function computeAcuity(current) {
  let score = 100
  const devs = current?.alerts?.deviations ?? {}
  for (const metric of ['mean_pause_duration_sec', 'type_token_ratio']) {
    const d = devs[metric]
    const pct = Math.abs(
      d?.from_current_window_pct ?? d?.from_5m_window_pct ?? d?.from_1m_window_pct ?? 0
    )
    if (pct > 40) score -= 35
    else if (pct > 20) score -= 25
  }
  return Math.max(0, Math.min(100, score))
}

const METRIC_OPTIONS = [
  { key: 'speech_rate_wpm',         label: 'Speaking Speed (wpm)',    unit: 'wpm', color: ACCENT    },
  { key: 'mean_pause_duration_sec', label: 'Mean Pause (sec)',         unit: 's',   color: WARNING   },
  { key: 'jitter_local',            label: 'Jitter (voice stability)', unit: '',    color: TEAL      },
  { key: 'type_token_ratio',        label: 'Vocabulary Diversity',     unit: '',    color: DANGER    },
  { key: 'emotion_score',           label: 'Emotion Score',            unit: '',    color: SUCCESS   },
  { key: 'f0_mean_hz',              label: 'Pitch (F0)',               unit: 'Hz',  color: SECONDARY },
]

// ── sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function AlertCard({ alerts }) {
  const active = alerts.filter(a => a.status !== 'ok')
  if (active.length === 0) {
    return (
      <div className="alert-card ok">
        <span className="alert-dot ok" />
        <span>All tracked metrics are within baseline tolerance.</span>
      </div>
    )
  }
  return (
    <div className="alert-list">
      {active.map((a, i) => (
        <div key={i} className={`alert-card ${a.severity}`}>
          <span className={`alert-dot ${a.severity}`} />
          <div>
            <div className="alert-metric">{a.metric?.replace(/_/g, ' ')}</div>
            <div className="alert-msg">{a.message}</div>
          </div>
          <span className={`alert-badge ${a.severity}`}>{a.severity}</span>
        </div>
      ))}
    </div>
  )
}

// ── main panel ────────────────────────────────────────────────────────────────

export default function MetricsPanel({ current, history }) {
  const [selectedMetric, setSelectedMetric] = useState(METRIC_OPTIONS[0])

  const tsData = useMemo(
    () => buildTimeSeriesData(current, history, selectedMetric.key),
    [current, history, selectedMetric]
  )

  const radarData = useMemo(() => buildRadarData(current), [current])

  const acuity = useMemo(() => computeAcuity(current), [current])

  const alerts = current?.alerts?.items ?? []
  const activeAlerts = alerts.filter(a => a.status !== 'ok')
  const sessionCount = current?.meta?.snapshot_count ?? 0
  const lastItem = current?.transcripts?.items?.at(-1)
  const lastSeen = lastItem
    ? new Date(lastItem.event_time).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '—'

  const acuityColor =
    acuity >= 80 ? 'var(--success)' :
    acuity >= 60 ? 'var(--warning)' :
    'var(--danger)'

  const baselineVal = current?.metrics?.baseline?.values?.[selectedMetric.key]

  return (
    <div className="metrics-panel">
      <div className="panel-header">
        <h2 className="panel-title"><HeartPulse size={18} strokeWidth={2} /> Wellbeing</h2>
        <p className="panel-sub">Speech and vocal pattern analysis for Emily</p>
      </div>

      {/* Stat row */}
      <div className="stat-row">
        <StatCard
          label="Acuity Score"
          value={acuity}
          sub="based on baseline deviation"
          color={acuityColor}
        />
        <StatCard
          label="Total Sessions"
          value={sessionCount}
          sub="recorded conversations"
          color="var(--accent)"
        />
        <StatCard
          label="Active Alerts"
          value={activeAlerts.length}
          sub={activeAlerts.length === 0 ? 'all clear' : 'need attention'}
          color={activeAlerts.length > 0 ? 'var(--warning)' : 'var(--success)'}
        />
        <StatCard
          label="Last Session"
          value={lastSeen}
          sub={lastItem ? `${lastItem.word_count} words` : ''}
          color="var(--text-muted)"
        />
      </div>

      {/* Alert strip */}
      <div className="section">
        <h3 className="section-title"><AlertTriangle size={14} strokeWidth={2} /> Alerts</h3>
        <AlertCard alerts={alerts} />
      </div>

      {/* Time series */}
      <div className="section">
        <div className="section-header">
          <h3 className="section-title"><TrendingUp size={14} strokeWidth={2} /> Trend Over Time</h3>
          <select
            className="metric-select"
            value={selectedMetric.key}
            onChange={e => setSelectedMetric(METRIC_OPTIONS.find(m => m.key === e.target.value))}
          >
            {METRIC_OPTIONS.map(m => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>
        {tsData.length === 0 ? (
          <div className="chart-empty">No time-series data yet.</div>
        ) : (
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={tsData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} axisLine={false} width={48} />
                <Tooltip
                  contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: 'var(--text-muted)' }}
                  itemStyle={{ color: selectedMetric.color }}
                  formatter={v => [`${v} ${selectedMetric.unit}`, selectedMetric.label]}
                />
                {baselineVal != null && (
                  <ReferenceLine
                    y={baselineVal}
                    stroke="var(--text-dim)"
                    strokeDasharray="6 3"
                    label={{ value: 'baseline', fill: 'var(--text-dim)', fontSize: 10, position: 'insideTopRight' }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={selectedMetric.color}
                  strokeWidth={2}
                  dot={{ r: 3, fill: selectedMetric.color }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Radar */}
      <div className="section">
        <h3 className="section-title"><RadarIcon size={14} strokeWidth={2} /> Wellbeing Snapshot</h3>
        <p className="section-sub">Outer = better</p>
        <div className="chart-wrap radar-wrap">
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} outerRadius={100}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis
                dataKey="metric"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Baseline"
                dataKey="baseline"
                stroke="var(--text-dim)"
                fill="var(--text-dim)"
                fillOpacity={0.05}
                strokeDasharray="5 3"
              />
              <Radar
                name="Current"
                dataKey="current"
                stroke="var(--accent)"
                fill="var(--accent)"
                fillOpacity={0.2}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
