import { Home, Brain, HeartPulse } from 'lucide-react'
import './TopNav.css'

const TABS = [
  { id: 'home',      label: 'Home',      Icon: Home      },
  { id: 'memories',  label: 'Memories',  Icon: Brain     },
  { id: 'wellbeing', label: 'Wellbeing', Icon: HeartPulse },
]

export default function TopNav({ page, onNavigate }) {
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

      {/* Spacer to keep segmented control centered */}
      <div className="topnav-spacer" />

    </nav>
  )
}
