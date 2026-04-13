import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { MFNodeData } from '../../stores/workflow-store'
import { useWorkflowStore } from '../../stores/workflow-store'
import type { OnBoardOutput, PortCategory } from '../../types/nodespec'
import { PORT_COLORS, nodeTypeEmoji } from '../../lib/port-type-utils'
import type { PickerOption } from '../../lib/semantic-labels'
import { useRunOverlayStore } from '../../stores/run-overlay-store'
import type { NodeRunStatus } from '../../stores/run-overlay-store'
import { phaseBorderClass, phaseBadgeClass, formatElapsed } from '../../lib/phase-utils'

// ─── Type alias for our custom node ──────────────────────────────────────────

export type MFNodeType = Node<MFNodeData, 'mfNode'>

// ─── Single port row ──────────────────────────────────────────────────────────

interface PortRowProps {
  name: string
  displayName: string
  category: string
  required?: boolean
  direction: 'input' | 'output'
  ephemeral?: boolean
}

const PortRow = memo(({ name, displayName, category, required, direction, ephemeral }: PortRowProps) => {
  const color = PORT_COLORS[category as keyof typeof PORT_COLORS] ?? '#6b7280'
  const isInput = direction === 'input'

  // Ephemeral ports get a vivid orange handle (wildcard — connects to anything)
  const labelColor = ephemeral ? '#fb923c' : color

  return (
    <div
      className={`relative flex items-center gap-1 py-0.5 text-xs ${isInput ? 'pr-1 pl-4' : 'pl-1 pr-4 flex-row-reverse'}`}
    >
      <Handle
        type={isInput ? 'target' : 'source'}
        position={isInput ? Position.Left : Position.Right}
        id={name}
        style={ephemeral ? {
          background: 'linear-gradient(135deg, #f97316, #22c55e, #3b82f6)',
          width: 12,
          height: 12,
          border: '2px solid rgb(var(--mf-bg-base))',
        } : {
          background: color,
          width: 10,
          height: 10,
          border: '2px solid rgb(var(--mf-bg-base))',
        }}
        className="transition-transform hover:scale-125"
      />

      <span
        className="font-mono truncate max-w-[80px]"
        style={{ color: labelColor }}
        title={displayName}
      >
        {displayName}
      </span>

      {required && (
        <span className="text-red-400 text-[9px] flex-shrink-0" title="Required">*</span>
      )}
    </div>
  )
})
PortRow.displayName = 'PortRow'

// ─── Quality gate badge (static + optional run result) ───────────────────────

interface GateBadgeProps {
  gate: OnBoardOutput
  runValue?: string   // 'true' | 'false' | undefined
}

function GateBadge({ gate, runValue }: GateBadgeProps) {
  const color =
    gate.gate_default === 'must_pass' ? '#ef4444' :
    gate.gate_default === 'warn'      ? '#f59e0b' :
    '#6b7280'

  const hasResult = runValue !== undefined
  const passed    = runValue === 'true'

  return (
    <span
      className="flex items-center gap-1 text-[9px] font-mono px-1 rounded"
      style={{ color, background: `${color}20` }}
      title={gate.gate_description || gate.display_name}
    >
      <span
        className="inline-block rounded-full flex-shrink-0"
        style={{ width: 5, height: 5, background: color }}
      />
      {gate.display_name}
      {hasResult && (
        <span className={passed ? 'text-green-400' : 'text-red-400'}>
          {passed ? '✓' : '✗'}
        </span>
      )}
    </span>
  )
}

// ─── Run overlay section ──────────────────────────────────────────────────────

function RunOverlaySection({ status }: { status: NodeRunStatus }) {
  const elapsed = formatElapsed(status.startedAt, status.finishedAt)

  // Exclude quality-gate keys (_qg_*) and internal mf keys (_mf_*) — shown integrated in the gate badges above
  const outputEntries = Object.entries(status.outputs).filter(
    ([k]) => !k.startsWith('_internal_') && !k.startsWith('_qg_') && !k.startsWith('_mf_'),
  )

  return (
    <div className="border-t border-mf-border/50 px-2 py-1.5 space-y-0.5">
      {/* Elapsed time — only show when there's something to report */}
      {elapsed && (
        <div className="text-[10px] text-mf-text-muted text-right">{elapsed}</div>
      )}

      {/* Output values — only shown on success */}
      {status.phase === 'Succeeded' && outputEntries.length > 0 && (
        <div className="space-y-0.5">
          {outputEntries.map(([key, value]) => {
            const isBool = value === 'true' || value === 'false'
            // Show tooltip only for long values that exceed 2 visible lines (~80 chars)
            const needsTooltip = !isBool && value.length > 80

            return (
              <div key={key} className="text-[9px] font-mono">
                <span className="text-mf-text-muted">{key}: </span>
                {isBool ? (
                  <span className={value === 'true' ? 'text-green-400' : 'text-red-400'}>
                    {value === 'true' ? '✓' : '✗'}
                  </span>
                ) : (
                  <span
                    className="text-green-300 break-all line-clamp-2"
                    title={needsTooltip ? value : undefined}
                  >
                    {value}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Pending node (semantic type dropped, implementation not yet chosen) ──────

const PendingNodeCard = memo(({ data, selected }: { data: MFNodeData; selected: boolean }) => {
  const options = (data.pending_implementations as PickerOption[] | undefined) ?? []
  const onSelect = data.pending_on_select as ((n: string) => void) | undefined
  const semanticType = data.semantic_type as string | undefined
  const rationale = data.semantic_rationale as string | undefined

  return (
    <div
      className={`bg-mf-card rounded-lg shadow-xl select-none${selected ? ' ring-1 ring-amber-400' : ''}`}
      style={{
        minWidth: 200,
        maxWidth: 280,
        border: '1.5px dashed',
        borderColor: selected ? '#fbbf24' : '#92400e',
      }}
    >
      {/* Header */}
      <div className="px-2.5 py-2 bg-amber-900/20 rounded-t-lg flex items-start gap-1.5">
        <span className="text-base leading-none mt-0.5">❓</span>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold text-amber-200 truncate leading-tight">
            {data.display_name}
          </div>
          <div className="text-[10px] text-amber-600 font-mono truncate">
            {semanticType ?? 'select implementation'}
          </div>
        </div>
      </div>

      {/* Rationale (tooltip-style info) */}
      {rationale && (
        <div className="px-2.5 py-1 bg-amber-950/20 text-[10px] text-amber-700/80 italic border-t border-amber-900/20">
          {rationale}
        </div>
      )}

      {/* Software options */}
      <div className="border-t border-amber-900/30 py-0.5">
        {options.length > 0 ? (
          options.map((opt) => (
            <button
              key={opt.nodeName}
              onClick={() => onSelect?.(opt.nodeName)}
              className="w-full text-left px-2.5 py-1.5 text-xs hover:bg-mf-hover/60 transition-colors flex items-center justify-between gap-2 group nodrag"
            >
              <span className="text-blue-400 group-hover:text-blue-300 font-medium truncate">
                {opt.software ?? opt.label}
              </span>
              <span className="text-[10px] text-mf-text-muted font-mono shrink-0">
                {opt.nodeName}
              </span>
            </button>
          ))
        ) : (
          <div className="px-2.5 py-1.5 text-[10px] text-mf-text-muted italic">
            No implementations found
          </div>
        )}
      </div>

      {/* 不可见 Handle：让语义边（琥珀色虚线）能连接到 PendingNode */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-0 !h-0 !min-w-0 !min-h-0 !border-0 !bg-transparent"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-0 !h-0 !min-w-0 !min-h-0 !border-0 !bg-transparent"
      />
    </div>
  )
})
PendingNodeCard.displayName = 'PendingNodeCard'

// ─── MFNode ───────────────────────────────────────────────────────────────────

export const MFNode = memo(({ id, data, selected }: NodeProps<MFNodeType>) => {
  // Each node selects only its own status; stable reference preserved by run-overlay-store
  const runStatus = useRunOverlayStore((s) => s.nodeStatuses[id])
  const isCompiling = useWorkflowStore((s) => s.compilingNodeIds.includes(id))

  // ── Pending variant ────────────────────────────────────────────────────────
  if (data.pending) {
    return <PendingNodeCard data={data} selected={!!selected} />
  }

  // ── Normal variant ─────────────────────────────────────────────────────────
  // For formal nodes: stream_inputs/stream_outputs from nodespec
  // For ephemeral nodes: derive from ports field (simpler {name, type} shape)
  let inputPorts  = data.stream_inputs  ?? []
  let outputPorts = data.stream_outputs ?? []
  if (inputPorts.length === 0 && outputPorts.length === 0 && data.ports) {
    const rawPorts = data.ports as Record<string, unknown>
    const rawInputs = rawPorts.inputs
    const rawOutputs = rawPorts.outputs
    // Handle both array format [{name, type}, ...] and int-count format (legacy/stale)
    if (Array.isArray(rawInputs) && Array.isArray(rawOutputs)) {
      const toStreamPort = (p: { name: string; type: string }) => ({
        name: p.name,
        display_name: p.name,
        category: p.type as PortCategory,
        detail: '',
      })
      inputPorts = rawInputs.map(toStreamPort)
      outputPorts = rawOutputs.map(toStreamPort)
    } else if (typeof rawInputs === 'number' || typeof rawOutputs === 'number') {
      const numIn = (rawInputs as number) ?? 0
      const numOut = (rawOutputs as number) ?? 0
      inputPorts = Array.from({ length: numIn }, (_, i) => ({
        name: `I${i + 1}`, display_name: `I${i + 1}`, category: 'software_data_package', detail: '',
      }))
      outputPorts = Array.from({ length: numOut }, (_, i) => ({
        name: `O${i + 1}`, display_name: `O${i + 1}`, category: 'software_data_package', detail: '',
      }))
    }
  }
  const paramCount  = data.onboard_inputs?.length ?? 0
  const cpu = data.resources?.cpu
  const mem = data.resources?.memory_gb
  const qualityGates = (data.onboard_outputs as OnBoardOutput[] | undefined)?.filter(
    (o) => o.quality_gate,
  ) ?? []

  const emoji = nodeTypeEmoji(data.category ?? '')

  // Phase-based border override
  const nodeClass = [
    'mf-node',
    isCompiling ? 'compiling' : '',
    !isCompiling && runStatus ? phaseBorderClass(runStatus.phase) : '',
    !isCompiling && !runStatus && selected ? 'selected' : '',
    runStatus && selected ? 'ring-1 ring-blue-400' : '',
  ].filter(Boolean).join(' ')

  const hasPorts = inputPorts.length > 0 || outputPorts.length > 0
  const hasBoth  = inputPorts.length > 0 && outputPorts.length > 0

  return (
    <div className={nodeClass}>
      {/* Header */}
      <div className="mf-node-header bg-mf-hover/50">
        <div className="flex items-start gap-1.5">
          <span className="text-base leading-none mt-0.5">{emoji}</span>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-mf-text-primary truncate leading-tight">
              {data.display_name}
            </div>
            {data.ephemeral ? (
              <div className="text-[10px] text-orange-400 font-mono">ephemeral</div>
            ) : (
              <div className="text-[10px] text-mf-text-muted truncate font-mono">
                {data.name} v{data.version}
              </div>
            )}
          </div>
          {/* Sweep badge */}
          {data.parallel_sweep && (
            <span className="text-[10px] bg-purple-900/40 text-purple-300 px-1.5 py-0.5 rounded flex-shrink-0">
              sweep &times;{data.parallel_sweep.values.length}
            </span>
          )}
          {/* Phase badge */}
          {runStatus && !isCompiling && (
            <span className={`${phaseBadgeClass(runStatus.phase)} flex-shrink-0`}>
              {runStatus.phase}
            </span>
          )}
          {/* Compiling indicator */}
          {isCompiling && (
            <span className="flex items-center gap-1 text-[10px] text-purple-300 flex-shrink-0">
              <span className="inline-block w-3 h-3 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin" />
              Generating…
            </span>
          )}
        </div>
      </div>

      {/* Stream I/O — left (inputs) / right (outputs) */}
      {hasPorts && (
        <div className={`mf-node-ports border-b border-mf-border/50 flex py-1`}>
          {inputPorts.length > 0 && (
            <div className={hasBoth ? 'flex-1 border-r border-mf-border/30 min-w-0' : 'w-full'}>
              {inputPorts.map((port) => (
                <PortRow
                  key={port.name}
                  name={port.name}
                  displayName={port.display_name}
                  category={port.category}
                  required={port.required}
                  direction="input"
                  ephemeral={!!data.ephemeral}
                />
              ))}
            </div>
          )}
          {outputPorts.length > 0 && (
            <div className={hasBoth ? 'flex-1 min-w-0' : 'w-full'}>
              {outputPorts.map((port) => (
                <PortRow
                  key={port.name}
                  name={port.name}
                  displayName={port.display_name}
                  category={port.category}
                  direction="output"
                  ephemeral={!!data.ephemeral}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quality Gate indicators — static label + run result (✓/✗) when available */}
      {qualityGates.length > 0 && (
        <div className="border-b border-mf-border/50 px-2 py-1 flex flex-wrap gap-1">
          {qualityGates.map((gate) => (
            <GateBadge
              key={gate.name}
              gate={gate}
              runValue={runStatus?.outputs[`_qg_${gate.name}`]}
            />
          ))}
        </div>
      )}

      {/* Run overlay section */}
      {runStatus && <RunOverlaySection status={runStatus} />}

      {/* Footer */}
      <div className="mf-node-footer flex items-center justify-between text-[10px] text-mf-text-muted">
        <span>⚙ {paramCount} param{paramCount !== 1 ? 's' : ''}</span>
        {(cpu || mem) && (
          <span>🖥 {cpu}c {mem}G</span>
        )}
      </div>
    </div>
  )
})
MFNode.displayName = 'MFNode'
