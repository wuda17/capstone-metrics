import { useRef, useCallback, useState, useEffect, useMemo } from 'react'
import { Brain, CalendarClock, ZoomIn, ZoomOut, Maximize2, RefreshCw, X } from 'lucide-react'
import { useMemories } from '../hooks/useApi.js'
import { ACCENT, SUCCESS, WARNING, DANGER, TEAL, BG, LINK, LINK_CO } from '../theme.js'
import './MemoriesPanel.css'
import { PATIENT_NAME } from '../config.js'

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

const GRAPH_BG = BG

function makeNodeRenderer(selected, hoveredRef) {
  return (node, ctx, globalScale) => {
    const isSelected = selected?.id === node.id
    const isHovered  = hoveredRef.current?.id === node.id
    const size       = node.size ?? 14
    const nodeColor  = node.color ?? FACT_COLOR

    ctx.save()

    // Outer bloom ring (selected / hovered)
    if (isSelected || isHovered) {
      const rings = isSelected ? 3 : 2
      for (let i = rings; i >= 1; i--) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, size + i * 6, 0, 2 * Math.PI)
        ctx.fillStyle = nodeColor + Math.round((0.12 / i) * 255).toString(16).padStart(2, '0')
        ctx.fill()
      }
    }

    // Bloom glow via shadow
    ctx.shadowBlur   = isSelected ? 24 : isHovered ? 18 : 10
    ctx.shadowColor  = nodeColor

    // Circle node
    ctx.beginPath()
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
    ctx.fillStyle = nodeColor
    ctx.fill()

    // Bright inner highlight spot
    ctx.shadowBlur = 0
    ctx.beginPath()
    ctx.arc(node.x - size * 0.28, node.y - size * 0.28, size * 0.28, 0, 2 * Math.PI)
    ctx.fillStyle = 'rgba(255,255,255,0.22)'
    ctx.fill()

    ctx.restore()

    // Label below node — always visible, dims when not active
    if (node.primary_keyword) {
      const fontSize = Math.max(10, 12 / globalScale)
      ctx.font        = `500 ${fontSize}px -apple-system, sans-serif`
      ctx.textAlign   = 'center'
      ctx.globalAlpha = isSelected || isHovered ? 1.0 : 0.55
      ctx.fillStyle   = '#2a1f18'
      ctx.fillText(node.primary_keyword, node.x, node.y + size + fontSize + 2)
    }

    // Hover tooltip pill with full keyword
    if (isHovered && node.primary_keyword) {
      const fontSize = Math.max(11, 13 / globalScale)
      ctx.font = `600 ${fontSize}px -apple-system, sans-serif`
      const textW = ctx.measureText(node.primary_keyword).width
      const pad = 7
      const boxW = textW + pad * 2
      const boxH = fontSize + pad * 1.4
      const bx = node.x - boxW / 2
      const by = node.y - size - boxH - 10
      ctx.globalAlpha = 1.0
      ctx.fillStyle = 'rgba(250,246,242,0.92)'
      ctx.beginPath()
      ctx.roundRect(bx, by, boxW, boxH, 5)
      ctx.fill()
      ctx.strokeStyle = nodeColor + 'aa'
      ctx.lineWidth = 1
      ctx.stroke()
      ctx.fillStyle = '#2a1f18'
      ctx.fillText(node.primary_keyword, node.x, by + boxH - pad * 0.55)
    }

    ctx.globalAlpha = 1.0
  }
}

// ── Source drawer (shared for facts and timeline clusters) ────────────────────

function SourceDrawer({ node, onClose }) {
  if (!node) return null
  const isFact     = node.type === 'fact'
  const color      = isFact ? (node.color ?? FACT_COLOR) : tlColor(node)
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

function TimelineBubble({ cluster, isSelected, onClick, isNew }) {
  const color    = tlColor(cluster)
  const diameter = Math.min(72, 22 + (cluster.recurrence_count - 1) * 10)
  const label    = cluster.content.length > 42 ? cluster.content.slice(0, 42) + '…' : cluster.content

  return (
    <button
      className={`tl-bubble${isSelected ? ' tl-bubble--selected' : ''}${isNew ? ' tl-bubble--new' : ''}`}
      onClick={onClick}
      title={cluster.content}
    >
      <div className="tl-circle-wrap" style={{ width: diameter + 16, height: diameter + 16 }}>
        <div
          className={`tl-circle${isNew ? ' tl-circle--new' : ''}`}
          style={{
            width: diameter,
            height: diameter,
            background: color + '28',
            border: `2px solid ${color}`,
            boxShadow: isSelected
              ? `0 0 0 3px ${color}44`
              : isNew
              ? `0 0 0 3px ${color}66, 0 0 10px ${color}44`
              : undefined,
          }}
        />
        {isNew && (
          <div className="tl-new-ring" style={{ '--ring-color': color }} />
        )}
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

export default function MemoriesPanel({ onNavigate }) {
  const { data, loading, refresh } = useMemories()
  const graphRef     = useRef()
  const containerRef = useRef()
  const [dims, setDims]           = useState({ w: 800, h: 400 })
  const [selected, setSelected]   = useState(null)
  const hoveredNodeRef            = useRef(null)
  const [tlFilter, setTlFilter]   = useState('all')
  const [GraphComp, setGraphComp] = useState(null)
  const seenIdsRef                = useRef(null)
  const [newIds, setNewIds]       = useState(new Set())

  useEffect(() => {
    import('react-force-graph-2d')
      .then(m => setGraphComp(() => m.default))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!data) return
    const currentIds = new Set([
      ...(data.timeline ?? []).map(c => c.id),
      ...(data.graph?.nodes ?? []).map(n => n.id),
    ])
    if (seenIdsRef.current === null) {
      seenIdsRef.current = currentIds
      return
    }
    const fresh = [...currentIds].filter(id => !seenIdsRef.current.has(id))
    if (fresh.length === 0) return
    fresh.forEach(id => seenIdsRef.current.add(id))
    setNewIds(prev => new Set([...prev, ...fresh]))
    const timer = setTimeout(() => {
      setNewIds(prev => {
        const next = new Set(prev)
        fresh.forEach(id => next.delete(id))
        return next
      })
    }, 2 * 60 * 1000)
    return () => clearTimeout(timer)
  }, [data])

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(([e]) => {
      setDims({ w: e.contentRect.width, h: e.contentRect.height })
    })
    ro.observe(containerRef.current)
    setDims({ w: containerRef.current.clientWidth, h: containerRef.current.clientHeight })
    return () => ro.disconnect()
  }, [])

  const nodeCanvasObject = useCallback(makeNodeRenderer(selected, hoveredNodeRef), [selected])
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


  const handleNodeHover = useCallback(node => { hoveredNodeRef.current = node ?? null }, [])

  const handleNodeClick = useCallback(node => {
    setSelected(prev => prev?.id === node.id ? null : node)
    if (node.source_event_time) onNavigate?.('activity', node.source_event_time)
  }, [onNavigate])

  const handleTlClick = useCallback(cluster => {
    setSelected(prev => prev?.id === cluster.id ? null : cluster)
    if (cluster.source_event_time) onNavigate?.('activity', cluster.source_event_time)
  }, [onNavigate])

  const linkColor = useCallback(link => link.co_session ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.12)', [])
  const linkWidth = useCallback(link => link.co_session ? 1.5 : Math.max(0.5, (link.value ?? 0.5) * 1.5), [])

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
          <div className="graph-legend">
            {[
              { label: 'People',     color: '#d4856a' },
              { label: 'Health',     color: '#6aaa82' },
              { label: 'Activity',   color: '#d4a84b' },
              { label: 'Place',      color: '#5a9eb5' },
              { label: 'Preference', color: '#a07ab5' },
            ].map(({ label, color }) => (
              <div key={label} className="graph-legend-item">
                <span className="graph-legend-dot" style={{ background: color }} />
                <span className="graph-legend-label">{label}</span>
              </div>
            ))}
          </div>
          {(loading || !GraphComp) && (
            <div className="graph-overlay">
              {loading ? 'Loading memories…' : 'Initialising…'}
            </div>
          )}
          {!loading && GraphComp && graphData.nodes.length === 0 && (
            <div className="graph-overlay">
              <p>No facts yet.</p>
              <p className="hint">Record conversations to build {PATIENT_NAME}'s knowledge graph.</p>
            </div>
          )}
          {!loading && GraphComp && graphData.nodes.length > 0 && (
            <GraphComp
              ref={graphRef}
              graphData={graphData}
              width={dims.w}
              height={dims.h}
              backgroundColor={GRAPH_BG}
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => 'replace'}
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkOpacity={1}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              nodeLabel={() => ''}
              warmupTicks={0}
              cooldownTicks={150}
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
                isNew={newIds.has(cluster.id)}
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
