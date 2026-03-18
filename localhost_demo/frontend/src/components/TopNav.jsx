import './TopNav.css'

const TABS = [
  { id: 'home',      label: 'Home'      },
  { id: 'memories',  label: 'Memories'  },
  { id: 'wellbeing', label: 'Wellbeing' },
]

function emotionMeta(emo) {
  if (emo == null) return { color: '#555', label: null }
  if (emo > 0.1)   return { color: '#22c87e', label: 'Positive' }
  if (emo < -0.1)  return { color: '#ef4545', label: 'Concerning' }
  return              { color: '#f5a623', label: 'Neutral' }
}

export default function TopNav({ page, onNavigate, current }) {
  const lastItem = current?.transcripts?.items?.at(-1)
  const lastTime = lastItem
    ? new Date(lastItem.event_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : null

  const emo = current?.metrics?.current?.values?.emotion_score ?? null
  const { color: emoColor, label: emoLabel } = emotionMeta(emo)

  return (
    <nav className="topnav">

      {/* Logo */}
      <div className="topnav-logo">
        <span className="topnav-logo-icon">◈</span>
        <span className="topnav-logo-text">FerbAI</span>
      </div>

      {/* Segmented control — centered via flex */}
      <div className="topnav-seg-wrap">
        <div className="topnav-seg">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`topnav-seg-btn${page === t.id ? ' active' : ''}`}
              onClick={() => onNavigate(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Patient status */}
      <div className="topnav-patient">
        <span className="patient-dot" style={{ background: emoColor }} />
        <span className="patient-name">Emily</span>
        {emoLabel && <span className="patient-status">{emoLabel}</span>}
        {lastTime  && <span className="patient-last">· {lastTime}</span>}
      </div>

    </nav>
  )
}
