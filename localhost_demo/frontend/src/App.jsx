import { useState, useRef, useEffect, useCallback } from 'react'
import TopNav from './components/TopNav.jsx'
import ProfileStrip from './components/ProfileStrip.jsx'
import EntryPage from './components/EntryPage.jsx'
import MetricsPanel from './components/MetricsPanel.jsx'
import MemoriesPanel from './components/MemoriesPanel.jsx'
import ChatBot from './components/ChatBot.jsx'
import NewRecordingPopup from './components/NewRecordingPopup.jsx'
import { useCurrentData, useHistory, useStatus } from './hooks/useApi.js'
import './App.css'

export default function App() {
  const [page, setPage] = useState('home')
  const [chatOpen, setChatOpen] = useState(false)
  const { data: current } = useCurrentData()
  const { data: history } = useHistory()
  const { data: status } = useStatus()

  const [popup, setPopup] = useState(null)
  const prevCountRef = useRef(null)
  const dismissPopup = useCallback(() => setPopup(null), [])

  useEffect(() => {
    if (!current) return
    const newCount = current?.meta?.snapshot_count ?? 0
    if (prevCountRef.current !== null && newCount > prevCountRef.current) {
      const latest = current?.transcripts?.items?.at(-1)
      if (latest) {
        setPopup({
          text: latest.text,
          wordCount: latest.word_count,
          eventTime: latest.event_time,
          emotionScore: current?.metrics?.current?.values?.emotion_score ?? null,
        })
      }
    }
    prevCountRef.current = newCount
  }, [current])

  return (
    <div className="app-shell">
      <TopNav page={page} onNavigate={setPage} recording={status?.recording ?? false} />
      <ProfileStrip current={current} />
      <div className="page-content">
        {page === 'home'      && <EntryPage />}
        {page === 'memories'  && <MemoriesPanel />}
        {page === 'wellbeing' && <MetricsPanel current={current} history={history} />}
      </div>
      {page !== 'home' && <ChatBot open={chatOpen} onToggle={() => setChatOpen(o => !o)} />}
      <NewRecordingPopup data={popup} onDismiss={dismissPopup} />
    </div>
  )
}
