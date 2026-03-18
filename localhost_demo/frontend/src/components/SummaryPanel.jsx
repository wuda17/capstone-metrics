import { Sun, CalendarDays, CalendarRange, RefreshCw } from 'lucide-react'
import { useSummary } from '../hooks/useApi.js'
import './SummaryPanel.css'

const PERIODS = [
  {
    key:   'today',
    label: 'Today',
    sub:   'Past 24 hours',
    Icon:  Sun,
    color: '#5ab8a0',
  },
  {
    key:   'week',
    label: 'This Week',
    sub:   'Past 7 days',
    Icon:  CalendarDays,
    color: '#c8695a',
  },
  {
    key:   'month',
    label: 'This Month',
    sub:   'Past 30 days',
    Icon:  CalendarRange,
    color: '#c4a882',
  },
]

function SummaryCard({ period, text, loading }) {
  const isEmpty = !text && !loading

  return (
    <div className="summary-card">
      <div className="summary-card-header">
        <period.Icon size={20} strokeWidth={1.75} style={{ color: period.color, flexShrink: 0 }} />
        <div>
          <div className="summary-period">{period.label}</div>
          <div className="summary-period-sub">{period.sub}</div>
        </div>
      </div>

      <div className="summary-body">
        {loading ? (
          <div className="summary-skeleton">
            <div className="skeleton-line" style={{ width: '92%' }} />
            <div className="skeleton-line" style={{ width: '78%' }} />
            <div className="skeleton-line" style={{ width: '85%' }} />
          </div>
        ) : isEmpty ? (
          <p className="summary-empty">No summary available.</p>
        ) : (
          <p className="summary-text">{text}</p>
        )}
      </div>
    </div>
  )
}

export default function SummaryPanel() {
  const { data, loading, refresh } = useSummary()

  return (
    <div className="summary-panel">
      <div className="summary-header">
        <div>
          <h2 className="panel-title">Summaries</h2>
          <p className="panel-sub">
            AI-generated overviews of Emily's recent conversations — today, this week, and this month.
          </p>
        </div>
        <button className="ctrl-btn" onClick={refresh} title="Regenerate summaries">
          <RefreshCw size={14} strokeWidth={2} />
        </button>
      </div>

      <div className="summary-grid">
        {PERIODS.map(p => (
          <SummaryCard
            key={p.key}
            period={p}
            text={data?.[p.key]}
            loading={loading}
          />
        ))}
      </div>

      {!loading && data && (
        <p className="summary-hint">
          Summaries are cached for 30 minutes — click <RefreshCw size={11} strokeWidth={2} style={{ display: 'inline', verticalAlign: 'middle' }} /> to regenerate.
        </p>
      )}
    </div>
  )
}
