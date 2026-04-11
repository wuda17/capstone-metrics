import { useMemo } from 'react'
import { LineChart, Line, BarChart, Bar, ResponsiveContainer } from 'recharts'
import { Clock, ChevronRight } from 'lucide-react'
import { GREEN, AMBER, RED } from '../theme.js'
import './ActivityStrip.css'

function emotionColor(score) {
  if (score == null) return AMBER
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

export default function ActivityStrip({ current, status, onNavigate }) {
  const segmentMinutes = current?.meta?.segment_minutes ?? 1
  const timeSeries     = current?.metrics?.time_series ?? []
  const totalMinutes   = (current?.meta?.snapshot_count ?? 0) * segmentMinutes

  const moodData = useMemo(() => (
    timeSeries
      .filter(seg => seg.values?.emotion_score != null)
      .map((seg, i) => ({ i, value: +seg.values.emotion_score.toFixed(3) }))
      .slice(-15)
  ), [timeSeries])

  const weekData = useMemo(
    () => buildWeekUsage(timeSeries, segmentMinutes),
    [timeSeries, segmentMinutes]
  )

  return (
    <div className="tile activity-strip">

      {/* Patient identity */}
      <div className="as-identity">
        <span className="as-patient-name">Emily</span>
        {status?.recording && <span className="as-live-dot" />}
      </div>

      <div className="as-divider" />

      {/* Minutes counter */}
      <div className="as-stat">
        <Clock size={12} strokeWidth={2} className="as-stat-icon" />
        <span className="as-stat-value">{totalMinutes}</span>
        <span className="as-stat-label">min</span>
      </div>

      <div className="as-divider" />

      {/* Mood mini-chart */}
      <div className="as-chart">
        <div className="as-chart-label">Mood</div>
        <ResponsiveContainer width="100%" height={38}>
          <LineChart data={moodData} margin={{ top: 3, right: 3, bottom: 3, left: 3 }}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={AMBER}
              strokeWidth={1.5}
              dot={({ cx, cy, payload }) => {
                const c = emotionColor(payload.value)
                return <circle key={payload.i} cx={cx} cy={cy} r={2.5} fill={c} />
              }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="as-divider" />

      {/* Week usage mini-chart */}
      <div className="as-chart">
        <div className="as-chart-label">This week</div>
        <ResponsiveContainer width="100%" height={38}>
          <BarChart data={weekData} margin={{ top: 3, right: 3, bottom: 0, left: 3 }} barSize={7}>
            <Bar dataKey="minutes" fill={AMBER} radius={[2, 2, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* CTA */}
      <button className="as-cta" onClick={() => onNavigate('activity')}>
        See all activity
        <ChevronRight size={13} strokeWidth={2.5} />
      </button>

    </div>
  )
}
