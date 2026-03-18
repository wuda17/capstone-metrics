import './Sidebar.css'

const NAV = [
  { id: 'home',      label: 'Home',      icon: '⌂' },
  { id: 'summary',   label: 'Summaries', icon: '✦' },
  { id: 'memories',  label: 'Memories',  icon: '◈' },
  { id: 'wellbeing', label: 'Wellbeing', icon: '◉' },
]

export default function Sidebar({ page, onNavigate, current }) {
  const lastItem = current?.transcripts?.items?.at(-1)
  const lastSeenStr = lastItem
    ? new Date(lastItem.event_time).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '—'
  const sessionCount = current?.meta?.snapshot_count ?? 0

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">◈</span>
        <span className="logo-text">FerbAI</span>
      </div>

      <div className="patient-card">
        <div className="patient-avatar">E</div>
        <div className="patient-info">
          <div className="patient-name">Emily</div>
          <div className="patient-role">Patient profile</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(item => (
          <button
            key={item.id}
            className={`nav-item ${page === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-row">
          <span className="footer-label">Last session</span>
          <span className="footer-value">{lastSeenStr}</span>
        </div>
        <div className="footer-row">
          <span className="footer-label">Total sessions</span>
          <span className="footer-value">{sessionCount}</span>
        </div>
      </div>
    </aside>
  )
}
