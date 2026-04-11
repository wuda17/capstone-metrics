import { useState, useEffect } from 'react'
import { BookOpen, FlaskConical, ExternalLink, AlertTriangle, ChevronRight } from 'lucide-react'
import { METRIC_REFS, ALERT_REFS } from '../references.js'
import { METRICS } from './MetricsPanel.jsx'
import './LiteraturePanel.css'

const SEVERITY_COLORS = {
  'Poverty of Speech (Alogia)': 'warning',
  'Affective Flattening': 'warning',
  'Apathy Signature': 'warning',
  'Stress Response Peak': 'warning',
  'Suicide Risk Marker': 'danger',
  'Longitudinal Deviation': 'accent',
}

export default function LiteraturePanel({ initialMetric }) {
  const [selected, setSelected] = useState(
    initialMetric && METRIC_REFS[initialMetric] ? initialMetric : METRICS[0].key
  )

  useEffect(() => {
    if (initialMetric && METRIC_REFS[initialMetric]) setSelected(initialMetric)
  }, [initialMetric])

  const metric = METRICS.find(m => m.key === selected)
  const detail = METRIC_REFS[selected]

  return (
    <div className="lit-panel">
      <div className="lit-header">
        <h2 className="lit-title">
          <BookOpen size={18} strokeWidth={2} />
          Evidence Base
        </h2>
        <p className="lit-sub">
          Peer-reviewed citations for every biomarker and clinical pattern used in this system.
        </p>
      </div>

      {/* ── Vocal Biomarkers (main widget) ── */}
      <section className="lit-section">
        <h3 className="lit-section-title">
          <FlaskConical size={14} strokeWidth={2} />
          Vocal Biomarkers
        </h3>

        <div className="lit-biomarker-widget">
          {/* Selector */}
          <div className="lit-selector">
            {METRICS.map(m => (
              <button
                key={m.key}
                className={`lit-sel-btn${selected === m.key ? ' active' : ''}`}
                onClick={() => setSelected(m.key)}
              >
                <span
                  className="lit-sel-dot"
                  style={{ background: m.color }}
                />
                <span className="lit-sel-label">{m.label}</span>
                {m.unit && <span className="lit-sel-unit">{m.unit}</span>}
                <ChevronRight size={12} className="lit-sel-arrow" />
              </button>
            ))}
          </div>

          {/* Detail */}
          {detail && (
            <div className="lit-detail">
              <div className="lit-detail-header">
                <span
                  className="lit-detail-dot"
                  style={{ background: metric?.color }}
                />
                <span className="lit-detail-name">{metric?.label}</span>
                {metric?.unit && (
                  <span className="lit-detail-unit">{metric.unit}</span>
                )}
              </div>
              <p className="lit-detail-desc">{detail.description}</p>
              <blockquote className="lit-detail-claim">
                "{detail.claim}"
              </blockquote>
              <a
                className="lit-detail-cite"
                href={detail.doi}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink size={12} />
                {detail.citation}
              </a>
            </div>
          )}
        </div>
      </section>

      {/* ── Clinical Interpretations (secondary) ── */}
      <section className="lit-section">
        <h3 className="lit-section-title">
          <AlertTriangle size={14} strokeWidth={2} />
          Potential Clinical Interpretations
        </h3>
        <p className="lit-section-sub">
          Patterns of vocal deviation that, in aggregate, may correspond to known clinical presentations.
          These are observational signals — not diagnostic conclusions.
        </p>
        <div className="lit-interp-list">
          {ALERT_REFS.map(ref => {
            const severity = SEVERITY_COLORS[ref.name] ?? 'accent'
            return (
              <div key={ref.name} className={`lit-interp-card lit-interp-${severity}`}>
                <div className="lit-interp-header">
                  <span className={`lit-interp-dot lit-interp-dot-${severity}`} />
                  <span className="lit-interp-name">{ref.name}</span>
                </div>
                <p className="lit-interp-desc">{ref.description}</p>
                <p className="lit-interp-claim">"{ref.claim}"</p>
                <a
                  className="lit-interp-cite"
                  href={ref.doi}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink size={10} />
                  {ref.citation}
                </a>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
