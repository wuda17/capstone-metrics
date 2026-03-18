import { useSummary } from '../hooks/useApi.js'
import './SummaryPanel.css'

const PERIODS = [
  {
    key:   'today',
    label: 'Today',
    sub:   'Past 24 hours',
    icon:  '◑',
    color: '#14c8a8',
  },
  {
    key:   'week',
    label: 'This Week',
    sub:   'Past 7 days',
    icon:  '◕',
    color: '#7c6af7',
  },
  {
    key:   'month',
    label: 'This Month',
    sub:   'Past 30 days',
    icon:  '●',
    color: '#f5a623',
  },
]

function SummaryCard({ period, text, loading }) {
  const isEmpty = !text && !loading

  return (
    <div className="summary-card">
      <div className="summary-card-header">
        <span className="summary-icon" style={{ color: period.color }}>{period.icon}</span>
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
        <button className="ctrl-btn" onClick={refresh} title="Regenerate summaries">↻</button>
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
          Summaries are cached for 30 minutes — click ↻ to regenerate.
        </p>
      )}
    </div>
  )
}
