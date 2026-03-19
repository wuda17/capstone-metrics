import { useRef, useCallback, useState, useEffect, useMemo } from 'react'
import { Brain, CalendarClock, ZoomIn, ZoomOut, Maximize2, RefreshCw, X } from 'lucide-react'
import { useMemories } from '../hooks/useApi.js'
import { ACCENT, SUCCESS, WARNING, DANGER, TEAL, BG, LINK, LINK_CO } from '../theme.js'
import './MemoriesPanel.css'

// ── constants ─────────────────────────────────────────────────────────────────

const FACT_COLOR  = ACCENT
const TL_FILTERS  = ['all', 'event', 'mood']

function moodColor(valence) {
  const v = valence ?? 0
  if (v > 0.3)  return SUCCESS
  if (v < -0.3) return DANGER
  return WARNING
}

function tlColor(cluster) {
  return cluster.type === 'mood' ? moodColor(cluster.valence) : TEAL
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

function makeNodeRenderer(selected, hovered) {
  return (node, ctx, globalScale) => {
    const isSelected = selected?.id === node.id
    const isHovered  = hovered?.id  === node.id
    const size = node.size ?? 10

    if (isSelected) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, size + 7, 0, 2 * Math.PI)
      ctx.fillStyle = FACT_COLOR + '40'
      ctx.fill()
      ctx.strokeStyle = FACT_COLOR
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // Glow halo
    ctx.save()
    ctx.globalAlpha = 0.18
    ctx.beginPath()
    ctx.arc(node.x, node.y, size + 5, 0, 2 * Math.PI)
    ctx.fillStyle = FACT_COLOR
    ctx.fill()
    ctx.restore()

    // Diamond
    const s = size * 1.15
    ctx.beginPath()
    ctx.moveTo(node.x,     node.y - s)
    ctx.lineTo(node.x + s, node.y)
    ctx.lineTo(node.x,     node.y + s)
    ctx.lineTo(node.x - s, node.y)
    ctx.closePath()
    ctx.fillStyle = FACT_COLOR
    ctx.fill()

    // Label — only when zoomed in or selected
    if (globalScale > 1.4 || isSelected) {
      const fontSize = Math.max(8, 10 / globalScale)
      ctx.globalAlpha = isSelected ? 0.85 : 0.5
      ctx.font = `${fontSize}px -apple-system, sans-serif`
      ctx.fillStyle = '#2a1f18'
      ctx.textAlign = 'center'
      const label = node.content.length > 28 ? node.content.slice(0, 28) + '…' : node.content
      ctx.fillText(label, node.x, node.y + s + fontSize + 3)
    }

    // Hover tooltip — primary keyword + reference count
    if (isHovered && node.primary_keyword) {
      const refStr = node.reference_count > 1 ? `  ×${node.reference_count}` : ''
      const label = node.primary_keyword + refStr
      const fontSize = Math.max(9, 11 / globalScale)
      ctx.font = `600 ${fontSize}px -apple-system, sans-serif`
      const textW = ctx.measureText(label).width
      const pad = 6
      const boxW = textW + pad * 2
      const boxH = fontSize + pad * 1.4
      const bx = node.x - boxW / 2
      const by = node.y - s - boxH - 8
      ctx.globalAlpha = 1.0
      ctx.fillStyle = '#2a1f18'
      ctx.beginPath()
      ctx.roundRect(bx, by, boxW, boxH, 5)
      ctx.fill()
      ctx.fillStyle = '#faf6f2'
      ctx.textAlign = 'center'
      ctx.fillText(label, node.x, by + boxH - pad * 0.55)
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
        <button className="drawer-close" onClick={onClose}><X size={13} strokeWidth={2} /></button>
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
  const [hoveredNode, setHoveredNode] = useState(null)
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

  const nodeCanvasObject = useCallback(makeNodeRenderer(selected, hoveredNode), [selected, hoveredNode])
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

  useEffect(() => {
    const g = graphRef.current
    if (!g || !graphData.nodes.length) return
    g.d3Force('charge')?.strength(-120)
    g.d3Force('link')?.distance(60)
  }, [GraphComp, graphData])

  const handleNodeHover = useCallback(node => setHoveredNode(node ?? null), [])

  const handleNodeClick = useCallback(node => {
    setSelected(prev => prev?.id === node.id ? null : node)
  }, [])

  const handleTlClick = useCallback(cluster => {
    setSelected(prev => prev?.id === cluster.id ? null : cluster)
  }, [])

  const linkColor = useCallback(link => link.co_session ? LINK_CO : LINK_CO, [])
  const linkWidth = useCallback(link => link.co_session ? 2.5 : Math.max(1.2, (link.value ?? 1) * 2.5), [])

  return (
    <div className="memories-panel">

      {/* Header */}
      <div className="memories-header">
        <div>
          <h2 className="panel-title"><Brain size={18} strokeWidth={2} /> Memories</h2>
          <p className="panel-sub">
            Related personal details and facts.
          </p>
        </div>
        <div className="graph-controls">
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoom(1.5, 300)} title="Zoom in"><ZoomIn size={13} strokeWidth={2} /></button>
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoom(0.67, 300)} title="Zoom out"><ZoomOut size={13} strokeWidth={2} /></button>
          <button className="ctrl-btn" onClick={() => graphRef.current?.zoomToFit(400, 40)} title="Fit"><Maximize2 size={13} strokeWidth={2} /></button>
          <button className="ctrl-btn" onClick={refresh} title="Refresh"><RefreshCw size={13} strokeWidth={2} /></button>
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
              backgroundColor={BG}
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => 'replace'}
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkOpacity={1}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              nodeLabel={() => ''}
              warmupTicks={120}
              cooldownTicks={80}
              d3AlphaDecay={0.03}
              d3VelocityDecay={0.5}
              onEngineStop={() => graphRef.current?.zoomToFit(300, 60)}
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
          <div>
            <h2 className="panel-title"><CalendarClock size={18} strokeWidth={2} /> Events &amp; Moods</h2>
            <p className="panel-sub">Significant events and emotional moments clustered over time.</p>
          </div>
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
