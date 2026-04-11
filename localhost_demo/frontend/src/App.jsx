import { useState, useRef, useEffect, useCallback } from 'react'
import TopNav from './components/TopNav.jsx'
import EntryPage from './components/EntryPage.jsx'
import ActivityPanel from './components/ActivityPanel.jsx'
import MetricsPanel from './components/MetricsPanel.jsx'
import MemoriesPanel from './components/MemoriesPanel.jsx'
import ChatBot from './components/ChatBot.jsx'
import NewRecordingPopup from './components/NewRecordingPopup.jsx'
import LiteraturePanel from './components/LiteraturePanel.jsx'
import { useCurrentData, useHistory, useStatus, useMemories } from './hooks/useApi.js'
import './App.css'

export default function App() {
  const [page, setPage] = useState('home')
  const [litMetric, setLitMetric] = useState(null)
  const [activityHighlight, setActivityHighlight] = useState(null)

  const handleNavigate = useCallback((dest, key) => {
    setPage(dest)
    if (dest === 'literature' && key) setLitMetric(key)
    if (dest === 'activity'   && key) setActivityHighlight(key)
  }, [])
  const [chatOpen, setChatOpen] = useState(false)
  const { data: current  } = useCurrentData()
  const { data: history  } = useHistory()
  const { data: status   } = useStatus()
  const { data: memories } = useMemories()

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
      <div className="page-content">
        {page === 'home'       && <EntryPage current={current} history={history} memories={memories} status={status} onNavigate={handleNavigate} />}
        {page === 'memories'   && <MemoriesPanel onNavigate={handleNavigate} />}
        {page === 'wellbeing'  && <MetricsPanel current={current} history={history} onNavigate={handleNavigate} />}
        {page === 'literature' && <LiteraturePanel initialMetric={litMetric} />}
        {page === 'activity'   && <ActivityPanel current={current} status={status} onNavigate={handleNavigate} highlightTime={activityHighlight} />}
      </div>
      {page !== 'home' && <ChatBot open={chatOpen} onToggle={() => setChatOpen(o => !o)} />}
      <NewRecordingPopup data={popup} onDismiss={dismissPopup} />
      <footer className="app-footer">
        <span>Built by the FerbAI Team</span>
        <span className="app-footer-sep" />
        <span>Capstone Symposium 2026</span>
        <span className="app-footer-sep" />
        <span>For demonstration purposes only</span>
      </footer>
    </div>
  )
}
