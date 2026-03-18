import { useState } from 'react'
import TopNav from './components/TopNav.jsx'
import ProfileStrip from './components/ProfileStrip.jsx'
import EntryPage from './components/EntryPage.jsx'
import MetricsPanel from './components/MetricsPanel.jsx'
import MemoriesPanel from './components/MemoriesPanel.jsx'
import ChatBot from './components/ChatBot.jsx'
import { useCurrentData, useHistory } from './hooks/useApi.js'
import './App.css'

export default function App() {
  const [page, setPage] = useState('home')
  const [chatOpen, setChatOpen] = useState(false)
  const { data: current } = useCurrentData()
  const { data: history } = useHistory()

  return (
    <div className="app-shell">
      <TopNav page={page} onNavigate={setPage} current={current} />
      <ProfileStrip current={current} />
      <div className="page-content">
        {page === 'home'      && <EntryPage />}
        {page === 'memories'  && <MemoriesPanel />}
        {page === 'wellbeing' && <MetricsPanel current={current} history={history} />}
      </div>
      {page !== 'home' && <ChatBot open={chatOpen} onToggle={() => setChatOpen(o => !o)} />}
    </div>
  )
}
