import { Home, Brain, HeartPulse } from 'lucide-react'
import './TopNav.css'

const TABS = [
  { id: 'home',      label: 'Home',      Icon: Home      },
  { id: 'memories',  label: 'Memories',  Icon: Brain     },
  { id: 'wellbeing', label: 'Wellbeing', Icon: HeartPulse },
]

function emotionMeta(emo) {
  if (emo == null) return { color: '#555', label: null }
  if (emo > 0.1)   return { color: '#5cbd88', label: 'Positive' }
  if (emo < -0.1)  return { color: '#c94040', label: 'Concerning' }
  return              { color: '#e8a84a', label: 'Neutral' }
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

      {/* Logo — company.png if available, text fallback */}
      <div className="topnav-logo">
        <img
          src="/brand/company.png"
          alt="FerbAI"
          className="topnav-logo-img"
          onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'flex' }}
        />
        <div className="topnav-logo-fallback">
          <span className="topnav-logo-text">FerbAI</span>
        </div>
      </div>

      {/* Segmented control */}
      <div className="topnav-seg-wrap">
        <div className="topnav-seg">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={`topnav-seg-btn${page === id ? ' active' : ''}`}
              onClick={() => onNavigate(id)}
            >
              <Icon size={13} strokeWidth={2} />
              {label}
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
