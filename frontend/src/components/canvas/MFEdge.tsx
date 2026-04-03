import { memo, useState } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
} from '@xyflow/react'
import type { EdgeProps } from '@xyflow/react'
import { PORT_COLORS } from '../../lib/port-type-utils'

export const MFEdge = memo((props: EdgeProps) => {
  const {
    id,
    sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition,
    data,
  } = props

  const [hovered, setHovered] = useState(false)

  const sourcePort = (data?.sourcePort as { name: string; category: string } | undefined)
  const color = sourcePort ? PORT_COLORS[sourcePort.category as keyof typeof PORT_COLORS] ?? '#6b7280' : '#6b7280'

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  })

  return (
    <>
      {/* 宽透明击中区域，便于鼠标捕捉 */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      {/* 可见边 */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: hovered ? '#ef4444' : color,
          strokeWidth: hovered ? 2.5 : 2,
          opacity: hovered ? 1 : 0.8,
          transition: 'stroke 0.15s, stroke-width 0.15s',
          pointerEvents: 'none',
        }}
      />

      {/* Hover 时在中点显示 × 删除按钮 */}
      {hovered && (
        <EdgeLabelRenderer>
          <button
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nopan nodrag w-4 h-4 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center shadow-lg hover:bg-red-500 transition-colors leading-none"
            data-edge-id={id}
            title="Delete connection"
          >
            ×
          </button>
        </EdgeLabelRenderer>
      )}
    </>
  )
})
MFEdge.displayName = 'MFEdge'

// ─── Semantic Edge (Phase 2) — 虚线琥珀色语义边 ─────────────────────────────

export const SemanticEdgeComponent = memo((props: EdgeProps) => {
  const {
    id, sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition, label,
  } = props

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: '#92400e',
          strokeWidth: 2,
          strokeDasharray: '6 4',
          opacity: 0.7,
        }}
        markerEnd="url(#semantic-arrow)"
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'none',
            }}
            className="text-[9px] text-amber-700/80 bg-mf-base/80 px-1 rounded font-mono"
          >
            {String(label)}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
})
SemanticEdgeComponent.displayName = 'SemanticEdgeComponent'
