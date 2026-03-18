import { useRef, useCallback, useState, useEffect, useMemo } from 'react'
import { useMemories } from '../hooks/useApi.js'
import './MemoriesPanel.css'

// ── constants ─────────────────────────────────────────────────────────────────

const FACT_COLOR  = '#7c6af7'
const TL_FILTERS  = ['all', 'event', 'mood']

function moodColor(valence) {
  const v = valence ?? 0
  if (v > 0.3)  return '#22c87e'
  if (v < -0.3) return '#ef4545'
  return '#f5a623'
}

function tlColor(cluster) {
  return cluster.type === 'mood' ? moodColor(cluster.valence) : '#14c8a8'
}

function fmtDate(iso) {
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }
  catch { return iso }
}

function fmtFull(iso) {
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }
  catch { return iso }
}

// ── fact graph node renderer ──────────────────────────────────────────────────

function makeNodeRenderer(selected) {
  return (node, ctx, globalScale) => {
    const isSelected = selected?.id === node.id
    const size = node.size ?? 6

    if (isSelected) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, size + 5, 0, 2 * Math.PI)
      ctx.fillStyle = FACT_COLOR + '40'
      ctx.fill()
      ctx.strokeStyle = FACT_COLOR
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    // Diamond
    const s = size * 1.1
    ctx.beginPath()
    ctx.moveTo(node.x,     node.y - s)
    ctx.lineTo(node.x + s, node.y)
    ctx.lineTo(node.x,     node.y + s)
    ctx.lineTo(node.x - s, node.y)
    ctx.closePath()
    ctx.fillStyle = FACT_COLOR
    ctx.fill()

    ctx.save()
    ctx.globalAlpha = 0.12
    ctx.beginPath()
    ctx.arc(node.x, node.y, size + 3, 0, 2 * Math.PI)
    ctx.fillStyle = FACT_COLOR
    ctx.fill()
    ctx.restore()

    if (globalScale > 1.6 || isSelected) {
      const fontSize = Math.max(7, 9 / globalScale)
      ctx.globalAlpha = 1.0
      ctx.font = `${fontSize}px -apple-system, sans-serif`
      ctx.fillStyle = '#e2e2ee'
      ctx.textAlign = 'center'
      const label = node.content.length > 32 ? node.content.slice(0, 32) + '…' : node.content
      ctx.fillText(label, node.x, node.y + size + fontSize + 2)
    }

    ctx.globalAlpha = 1.0
  }
}

// ── Source drawer (shared for facts and timeline clusters) ────────────────────

function SourceDrawer({ node, onClose }) {
  if (!node) return null
  const isFact     = node.type === 'fact'
  const color      = isFact ? FACT_COLOR : tlColor(node)
  const typeLabel  = node.type.charAt(0).toUpperCase() + node.type.slice(1)
  const recurrence = node.recurrence_count ?? 1

  return (
    <div className="source-drawer">
      <div className="drawer-header">
        <span
          className="drawer-type-badge"
          style={{ background: color + '22', color, borderColor: color + '55' }}
        >
          {typeLabel}
        </span>
        {recurrence > 1 && (
          <span className="drawer-recurrence" style={{ color }}>
            {recurrence}× recurring
          </span>
        )}
        <span className="drawer-date">{fmtFull(node.source_event_time)}</span>
        <button className="drawer-close" onClick={onClose}>✕</button>
      </div>

      <div className="drawer-memory">
        <p className="drawer-content">"{node.content}"</p>

        {node.type === 'mood' && node.valence != null && (
          <div className="drawer-valence">
            <span className="valence-label">Emotional tone</span>
            <div className="valence-bar">
              <div className="valence-fill" style={{
                width: `${Math.abs(node.valence) * 100}%`,
                background: moodColor(node.valence),
                marginLeft: node.valence < 0 ? `${(1 - Math.abs(node.valence)) * 100}%` : undefined,
              }} />
            </div>
            <span className="valence-value" style={{ color: moodColor(node.valence) }}>
              {node.valence > 0 ? '+' : ''}{node.valence?.toFixed(2)}
            </span>
          </div>
        )}

        {node.keywords?.length > 0 && (
          <div className="drawer-keywords">
            {node.keywords.map(k => <span key={k} className="kw-chip">{k}</span>)}
          </div>
        )}

        {recurrence > 1 && node.dates?.length > 0 && (
          <div className="drawer-dates">
            {[...new Set(node.dates)].map(d => (
              <span key={d} className="date-chip">{d}</span>
            ))}
          </div>
        )}
      </div>

      <div className="drawer-divider">Source conversation</div>
      <div className="drawer-transcript">
        {node.source_text || <span className="no-text">No transcript available.</span>}
      </div>
    </div>
  )
}

// ── Timeline bubble ───────────────────────────────────────────────────────────

function TimelineBubble({ cluster, isSelected, onClick }) {
  const color    = tlColor(cluster)
  const diameter = Math.min(52, 14 + (cluster.recurrence_count - 1) * 9)
  const label    = cluster.content.length > 42 ? cluster.content.slice(0, 42) + '…' : cluster.content

  return (
    <button
      className={`tl-bubble${isSelected ? ' tl-bubble--selected' : ''}`}
      onClick={onClick}
      title={cluster.content}
    >
      <div className="tl-circle-wrap" style={{ width: diameter + 16, height: diameter + 16 }}>
        <div
          className="tl-circle"
          style={{
            width: diameter,
            height: diameter,
            background: color + '28',
            border: `2px solid ${color}`,
            boxShadow: isSelected ? `0 0 0 3px ${color}44` : undefined,
          }}
        />
        {cluster.recurrence_count > 1 && (
          <span className="tl-count" style={{ color, borderColor: color }}>
            {cluster.recurrence_count}
          </span>
        )}
      </div>
      <p className="tl-label">{label}</p>
      <span className="tl-date">{fmtDate(cluster.source_event_time)}</span>
    </button>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function MemoriesPanel() {
  const { data, loading, refresh } = useMemories()
  const graphRef     = useRef()
  const containerRef = useRef()
  const [dims, setDims]           = useState({ w: 800, h: 400 })
  const [selected, setSelected]   = useState(null)
  const [tlFilter, setTlFilter]   = useState('all')
  const [GraphComp, setGraphComp] = useState(null)

  useEffect(() => {
    import('react-force-graph-2d')
      .then(m => setGraphComp(() => m.default))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(([e]) => {
      setDims({ w: e.contentRect.width, h: e.contentRect.height })
    })
    ro.observe(containerRef.current)
    setDims({ w: containerRef.current.clientWidth, h: containerRef.current.clientHeight })
    return () => ro.disconnect()
  }, [])

  const nodeCanvasObject = useCallback(makeNodeRenderer(selected), [selected])
  const graphData        = useMemo(() => data?.graph    ?? { nodes: [], links: [] }, [data])
  const timelineData     = useMemo(() => data?.timeline ?? [], [data])

  const tlCounts = useMemo(() => ({
    all:   timelineData.length,
    event: timelineData.filter(c => c.type === 'event').length,
    mood:  timelineData.filter(c => c.type === 'mood').length,
  }), [timelineData])

  const shownTimeline = useMemo(() =>
    tlFilter === 'all' ? timelineData : timelineData.filter(c => c.type === tlFilter),
    [timelineData, tlFilter]
  )

  const handleNodeClick = useCallback(node => {
    setSelected(prev => prev?.id === node.id ? null : node)
  }, [])

  const handleTlClick = useCallback(cluster => {
    setSelected(prev => prev?.id === cluster.id ? null : cluster)
  }, [])

  const linkColor = useCallback(link => link.co_session ? '#3a3a50' : '#252530', [])
  const linkWidth = useCallback(link => link.co_session ? 1.5 : Math.max(0.3, (link.value ?? 0) * 2), [])

  return (
    <div className="memories-panel">

      {/* Header */}
      <div className="memories-header">
        <div>
          <h2 className="panel-title">Memories</h2>
          <p className="panel-sub">
            Fact graph — what is known about Emily. &nbsp;·&nbsp; Events &amp; moods timeline — what happened and how she felt.
          </p>
        </div>
        <div className="graph-controls">
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoom(1.5, 300)} title="Zoom in">+</button>
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoom(0.67, 300)} title="Zoom out">−</button>
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoomToFit(400, 40)} title="Fit">⊡</button>
          <button className="ctrl-btn" onClick={refresh} title="Refresh">↻</button>
        </div>
      </div>

      {/* Fact graph + drawer */}
      <div className="graph-row">
        <div className="graph-outer" ref={containerRef}>
          {(loading || !GraphComp) && (
            <div className="graph-overlay">
              {loading ? 'Loading memories…' : 'Initialising…'}
            </div>
          )}
          {!loading && GraphComp && graphData.nodes.length === 0 && (
            <div className="graph-overlay">
              <p>No facts yet.</p>
              <p className="hint">Record conversations to build Emily's knowledge graph.</p>
            </div>
          )}
          {!loading && GraphComp && graphData.nodes.length > 0 && (
            <GraphComp
              ref={graphRef}
              graphData={graphData}
              width={dims.w}
              height={dims.h}
              backgroundColor="#09090f"
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => 'replace'}
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkOpacity={0.7}
              onNodeClick={handleNodeClick}
              nodeLabel={() => ''}
              cooldownTicks={150}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          )}
        </div>

        {selected && (
          <SourceDrawer node={selected} onClose={() => setSelected(null)} />
        )}
      </div>

      {/* Events & moods timeline */}
      <div className="timeline-section">
        <div className="timeline-header">
          <span className="tl-title">Events &amp; Moods</span>
          <div className="filter-pills">
            {TL_FILTERS.map(f => {
              const color = f === 'event' ? '#14c8a8' : f === 'mood' ? '#f5a623' : 'var(--text-muted)'
              return (
                <button
                  key={f}
                  className={`filter-pill${tlFilter === f ? ' active' : ''}`}
                  style={tlFilter === f ? { borderColor: color, color } : {}}
                  onClick={() => setTlFilter(f)}
                >
                  {f !== 'all' && <span className="pill-dot" style={{ background: color }} />}
                  {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                  <span className="pill-count">{tlCounts[f]}</span>
                </button>
              )
            })}
          </div>
        </div>

        {shownTimeline.length === 0 ? (
          <div className="tl-empty">
            No {tlFilter === 'all' ? 'events or moods' : tlFilter + 's'} yet.
          </div>
        ) : (
          <div className="tl-scroll">
            {shownTimeline.map(cluster => (
              <TimelineBubble
                key={cluster.id}
                cluster={cluster}
                isSelected={selected?.id === cluster.id}
                onClick={() => handleTlClick(cluster)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="memories-footer">
        <span>{graphData.nodes.length} fact{graphData.nodes.length !== 1 ? 's' : ''}</span>
        <span>·</span>
        <span>{graphData.links.length} connection{graphData.links.length !== 1 ? 's' : ''}</span>
        <span>·</span>
        <span>{timelineData.length} event/mood cluster{timelineData.length !== 1 ? 's' : ''}</span>
        {selected && (
          <>
            <span>·</span>
            <span className="footer-selected">
              viewing: <em>{selected.content.slice(0, 48)}{selected.content.length > 48 ? '…' : ''}</em>
            </span>
          </>
        )}
      </div>

    </div>
  )
}
