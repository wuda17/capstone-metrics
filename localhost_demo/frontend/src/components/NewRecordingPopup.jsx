import { useEffect } from 'react'
import { Mic, X } from 'lucide-react'
import './NewRecordingPopup.css'

const AUTO_DISMISS_MS = 8_000

function emotionLabel(score) {
  if (score == null) return null
  if (score > 0.1)  return { label: 'Positive mood', color: 'var(--success, #2a9d5c)' }
  if (score < -0.1) return { label: 'Concerning mood', color: 'var(--danger, #bf3030)' }
  return               { label: 'Neutral mood',    color: 'var(--warning, #c47f17)' }
}

export default function NewRecordingPopup({ data, onDismiss }) {
  useEffect(() => {
    if (!data) return
    const id = setTimeout(onDismiss, AUTO_DISMISS_MS)
    return () => clearTimeout(id)
  }, [data, onDismiss])

  if (!data) return null

  const emo = emotionLabel(data.emotionScore)
  const timeStr = new Date(data.eventTime).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
  const excerpt = data.text?.length > 120
    ? data.text.slice(0, 120).trimEnd() + '…'
    : data.text

  return (
    <div className="nrp-wrap" role="status" aria-live="polite">
      <div className="nrp-body">
        <div className="nrp-header">
          <Mic size={14} className="nrp-icon" />
          <span className="nrp-title">New Recording</span>
          <button className="nrp-close" onClick={onDismiss} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>

        {excerpt && <p className="nrp-text">"{excerpt}"</p>}

        <div className="nrp-pills">
          {data.wordCount != null && (
            <span className="nrp-pill">{data.wordCount} words</span>
          )}
          {emo && (
            <span className="nrp-pill">
              <span className="nrp-pill-dot" style={{ background: emo.color }} />
              {emo.label}
            </span>
          )}
          <span className="nrp-pill">{timeStr}</span>
        </div>
      </div>
      <div className="nrp-progress" />
    </div>
  )
}
