import { useState, useRef, useEffect } from 'react'
import { sendChatMessage } from '../hooks/useApi.js'
import './ChatBot.css'

const SUGGESTIONS = [
  'What has Emily been talking about recently?',
  'Give me a weekly summary',
  'Are there any concerning trends?',
]

export default function ChatBot({ open, onToggle }) {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    text: "Hi! I'm FerbAI. Ask me anything about Emily — her recent conversations, mood patterns, or weekly summaries.",
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef()
  const inputRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 80)
  }, [open])

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
      setMessages(prev => [...prev, { role: 'assistant', text: 'Sorry, something went wrong. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Persistent FAB */}
      <button className={`ferb-fab ${open ? 'open' : ''}`} onClick={onToggle} title="Ask FerbAI">
        <span className="ferb-fab-icon">{open ? '✕' : '◈'}</span>
        {!open && <span className="ferb-fab-label">Ferb</span>}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="chat-panel">
          <div className="chat-header">
            <span className="chat-logo">◈</span>
            <span className="chat-title">FerbAI</span>
            <span className="chat-subtitle">Ask me about Emily</span>
            <button className="chat-close" onClick={onToggle}>✕</button>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role}`}>
                {m.role === 'assistant' && <span className="msg-avatar">◈</span>}
                <div className="msg-bubble">{m.text}</div>
              </div>
            ))}

            {loading && (
              <div className="chat-msg assistant">
                <span className="msg-avatar">◈</span>
                <div className="msg-bubble typing">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Suggestion chips (only when just one assistant message) */}
          {messages.length === 1 && (
            <div className="suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="chat-input-row">
            <input
              ref={inputRef}
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Ask about Emily…"
              disabled={loading}
            />
            <button
              className="chat-send"
              onClick={() => send()}
              disabled={loading || !input.trim()}
            >
              →
            </button>
          </div>
        </div>
      )}
    </>
  )
}
