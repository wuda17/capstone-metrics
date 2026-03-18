import { useState, useRef, useEffect } from 'react'
import { sendChatMessage } from '../hooks/useApi.js'
import './EntryPage.css'

const SUGGESTIONS = [
  'How has Emily been feeling this week?',
  'Are there any concerning trends?',
  'What topics has she been discussing most?',
  'Give me a summary of last month',
]

export default function EntryPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef = useRef()
  const inputRef  = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setLoading(true)
    try {
      const res = await sendChatMessage(msg)
      setMessages(prev => [...prev, { role: 'assistant', text: res.response }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Something went wrong — please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="home-chat">

      {/* Scrollable body */}
      <div className="home-body">
        {!hasMessages ? (
          <div className="home-empty">
            <span className="home-logo">◈</span>
            <h1 className="home-heading">What would you like to know about Emily?</h1>
            <p className="home-sub">
              Ask anything about her recent conversations, mood patterns, or speech trends.
            </p>
          </div>
        ) : (
          <div className="home-messages">
            {messages.map((m, i) => (
              <div key={i} className={`hm hm--${m.role}`}>
                {m.role === 'assistant' && <span className="hm-avatar">◈</span>}
                <div className="hm-bubble">{m.text}</div>
              </div>
            ))}

            {loading && (
              <div className="hm hm--assistant">
                <span className="hm-avatar">◈</span>
                <div className="hm-bubble hm-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Suggestion chips — only on empty state */}
      {!hasMessages && (
        <div className="home-chips">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="home-chip" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="home-input-wrap">
        <div className="home-input-row">
          <input
            ref={inputRef}
            className="home-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Ask about Emily…"
            disabled={loading}
          />
          <button
            className="home-send"
            onClick={() => send()}
            disabled={loading || !input.trim()}
          >
            ↑
          </button>
        </div>
        <p className="home-input-hint">FerbAI may make mistakes. Always verify clinical decisions independently.</p>
      </div>

    </div>
  )
}
