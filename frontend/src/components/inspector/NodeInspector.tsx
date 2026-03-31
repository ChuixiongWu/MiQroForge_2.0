import React from 'react'
import { useForm } from 'react-hook-form'
import { useWorkflowStore } from '../../stores/workflow-store'
import { useUIStore } from '../../stores/ui-store'
import { useRunOverlayStore } from '../../stores/run-overlay-store'
import type { NodeRunStatus } from '../../stores/run-overlay-store'
import { PORT_COLORS, portCategoryLabel } from '../../lib/port-type-utils'
import type { OnBoardOutput } from '../../types/nodespec'
import { phaseEmoji, phaseBadgeClass, formatElapsed } from '../../lib/phase-utils'
import { X, Cpu, MemoryStick, Clock } from 'lucide-react'

// ─── Parameter form ───────────────────────────────────────────────────────────

function OnBoardParamForm({ nodeId }: { nodeId: string }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const updateNodeParams = useWorkflowStore((s) => s.updateNodeParams)

  const inputs = node?.data.onboard_inputs ?? []
  const storedParams = node?.data.onboard_params ?? {}

  // Bug fix #1: fall back to nodespec defaults when onboard_params is empty
  // (happens when a second node of the same type is placed — store may not have
  //  applied defaults yet, so we derive them from onboard_inputs directly)
  const defaults: Record<string, unknown> = React.useMemo(() => {
    return Object.fromEntries(
      inputs.map((param) => {
        const stored = storedParams[param.name]
        if (stored !== undefined && stored !== null && stored !== '') return [param.name, stored]
        return [param.name, param.default ?? '']
      })
    )
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId])  // recompute only when the node changes (component is already keyed by nodeId)

  const { register, handleSubmit } = useForm({ defaultValues: defaults })

  if (inputs.length === 0) {
    return <p className="text-xs text-mf-text-muted px-3 py-2">No parameters</p>
  }

  const onSubmit = (data: Record<string, unknown>) => {
    updateNodeParams(nodeId, data)
  }

  return (
    <form onChange={handleSubmit(onSubmit)} className="space-y-2 px-3 py-2">
      {inputs.map((param) => (
        <div key={param.name}>
          <label className="block text-[11px] text-mf-text-secondary mb-0.5">
            {param.display_name}
            {param.default == null && <span className="text-red-400 ml-0.5">*</span>}
            {param.unit && <span className="text-mf-text-muted ml-1">({param.unit})</span>}
          </label>

          {param.type === 'textarea' ? (
            <textarea
              rows={5}
              {...register(param.name)}
              placeholder={String(param.default ?? '')}
              className="w-full px-2 py-1 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary focus:outline-none focus:border-gray-400 font-mono resize-y"
            />
          ) : param.type === 'boolean' ? (
            <input
              type="checkbox"
              {...register(param.name)}
              className="accent-blue-500"
            />
          ) : param.type === 'enum' && param.enum_values ? (
            <select
              {...register(param.name)}
              className="w-full px-2 py-1 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary focus:outline-none focus:border-gray-400"
            >
              {param.enum_values.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          ) : (
            // Bug fix #2: use setValueAs for numeric types so values are stored as
            // numbers rather than strings (HTML inputs always yield strings by default)
            <input
              type={param.type === 'integer' || param.type === 'float' ? 'number' : 'text'}
              step={param.type === 'float' ? 'any' : undefined}
              {...register(param.name, {
                setValueAs: (v: string) => {
                  if (param.type === 'integer') {
                    const n = parseInt(v, 10)
                    return isNaN(n) ? v : n
                  }
                  if (param.type === 'float') {
                    const n = parseFloat(v)
                    return isNaN(n) ? v : n
                  }
                  return v
                },
              })}
              placeholder={String(param.default ?? '')}
              className="w-full px-2 py-1 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary focus:outline-none focus:border-gray-400 font-mono"
            />
          )}

          {param.description && (
            <p className="text-[10px] text-mf-text-muted mt-0.5">{param.description}</p>
          )}
        </div>
      ))}
    </form>
  )
}

// ─── Port list ────────────────────────────────────────────────────────────────

function PortList({ nodeId, direction }: { nodeId: string; direction: 'input' | 'output' }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const ports = direction === 'input' ? (node?.data.stream_inputs ?? []) : (node?.data.stream_outputs ?? [])

  if (ports.length === 0) return <p className="text-xs text-mf-text-muted px-3 py-1">None</p>

  return (
    <div className="px-3 space-y-1">
      {ports.map((p) => (
        <div key={p.name} className="flex items-center gap-2 text-xs">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: PORT_COLORS[p.category] ?? '#6b7280' }}
          />
          <span className="text-mf-text-secondary truncate">{p.display_name}</span>
          <span className="text-mf-text-muted font-mono text-[10px] ml-auto">{portCategoryLabel(p.category)}</span>
          {p.required && direction === 'input' && (
            <span className="text-red-400 text-[10px]">req</span>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Onboard output list (definitions + optional run values) ─────────────────

function OnboardOutputList({
  outputs,
  runStatus,
}: {
  outputs: OnBoardOutput[]
  runStatus?: NodeRunStatus
}) {
  if (outputs.length === 0) {
    return <p className="text-xs text-mf-text-muted px-3 py-2">No outputs defined</p>
  }

  return (
    <div className="px-3 py-1.5 space-y-2.5">
      {outputs.map((o) => {
        // Look up run value: quality-gate outputs are prefixed _qg_, others are plain name
        const isQg = o.quality_gate
        const runKey = isQg ? `_qg_${o.name}` : o.name
        const runValue = runStatus?.outputs[runKey]
        const hasValue = runValue !== undefined
        const isBool = runValue === 'true' || runValue === 'false'

        return (
          <div key={o.name}>
            {/* Label row + run value */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-1.5 flex-wrap min-w-0">
                <span className="text-xs text-mf-text-secondary font-medium">{o.display_name}</span>
                {o.unit && (
                  <span className="text-[10px] text-mf-text-muted">({o.unit})</span>
                )}
                {o.quality_gate && o.gate_default && (
                  <span className={`text-[9px] font-mono px-1 rounded border ${
                    o.gate_default === 'must_pass'
                      ? 'border-red-500/40 bg-red-500/10 text-red-400'
                      : o.gate_default === 'warn'
                      ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                      : 'border-mf-border text-mf-text-muted'
                  }`}>
                    {o.gate_default === 'must_pass' ? '● must pass' : o.gate_default === 'warn' ? '◐ warn' : '○ ignore'}
                  </span>
                )}
              </div>
              {/* Run result value */}
              {hasValue && (
                <span className={`text-xs font-mono flex-shrink-0 ${
                  isBool
                    ? (runValue === 'true' ? 'text-green-400' : 'text-red-400')
                    : 'text-green-300'
                }`}>
                  {isBool ? (runValue === 'true' ? '✓ true' : '✗ false') : runValue}
                </span>
              )}
            </div>
            {/* Descriptions */}
            {o.description && (
              <p className="text-[10px] text-mf-text-muted mt-0.5 leading-relaxed">{o.description}</p>
            )}
            {o.gate_description && (
              <p className={`text-[10px] mt-0.5 leading-relaxed ${
                o.gate_default === 'must_pass' ? 'text-red-400/70' :
                o.gate_default === 'warn'      ? 'text-amber-400/70' :
                'text-mf-text-muted'
              }`}>
                Gate: {o.gate_description}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Run summary section ──────────────────────────────────────────────────────

function RunSummarySection({ runStatus }: { runStatus: NodeRunStatus }) {
  const elapsed = formatElapsed(runStatus.startedAt, runStatus.finishedAt)
  return (
    <div className="px-3 py-2 flex items-center gap-2">
      <span className={`${phaseBadgeClass(runStatus.phase)} text-xs`}>
        {phaseEmoji(runStatus.phase)} {runStatus.phase}
      </span>
      {elapsed && <span className="text-[11px] text-mf-text-muted">{elapsed}</span>}
    </div>
  )
}

// ─── Section ──────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-mf-border/50">
      <div className="mf-panel-section-header">{title}</div>
      {children}
    </div>
  )
}

// ─── NodeInspector ────────────────────────────────────────────────────────────

export function NodeInspector() {
  const selectedNodeId = useUIStore((s) => s.selectedNodeId)
  const { selectNode } = useUIStore()
  const removeNode = useWorkflowStore((s) => s.removeNode)
  const node = useWorkflowStore((s) =>
    selectedNodeId ? s.nodes.find((n) => n.id === selectedNodeId) : null,
  )
  // Connect to run overlay for this node
  const runStatus = useRunOverlayStore((s) =>
    selectedNodeId ? s.nodeStatuses[selectedNodeId] : undefined,
  )

  if (!node) {
    return (
      <div className="w-72 mf-panel border-l border-r-0">
        <div className="flex items-center justify-between px-3 py-2 border-b border-mf-border">
          <span className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">Inspector</span>
        </div>
        <div className="px-3 py-6 text-xs text-mf-text-muted text-center">
          Select a node to inspect
        </div>
      </div>
    )
  }

  const d = node.data
  const res = d.resources
  const onboardOutputs = (d.onboard_outputs ?? []) as OnBoardOutput[]
  const hasRunData = !!runStatus

  return (
    <div className="w-72 mf-panel border-l border-r-0 flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-mf-border">
        <span className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">Inspector</span>
        <button
          onClick={() => selectNode(null)}
          className="text-mf-text-muted hover:text-mf-text-primary"
        >
          <X size={13} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto mf-scroll">
        {/* Node header */}
        <div className="px-3 py-2 border-b border-mf-border">
          <div className="text-sm font-semibold text-mf-text-primary">{d.display_name}</div>
          <div className="text-[11px] text-mf-text-muted font-mono mt-0.5">{d.name} v{d.version}</div>
          <div className="text-xs text-mf-text-secondary mt-1 leading-relaxed">{d.description}</div>
        </div>

        {/* Run status (when available) */}
        {runStatus && (
          <Section title="Run Status">
            <RunSummarySection runStatus={runStatus} />
          </Section>
        )}

        {/* Resources */}
        {res && (
          <Section title="Resources">
            <div className="px-3 py-1.5 flex gap-4 text-xs text-mf-text-secondary">
              <span className="flex items-center gap-1"><Cpu size={11} />{res.cpu} CPU</span>
              <span className="flex items-center gap-1"><MemoryStick size={11} />{res.memory_gb} GiB</span>
              <span className="flex items-center gap-1"><Clock size={11} />{res.estimated_walltime_hours}h</span>
            </div>
          </Section>
        )}

        {/* Inputs */}
        <Section title="Stream Inputs">
          <div className="py-1">
            <PortList nodeId={node.id} direction="input" />
          </div>
        </Section>

        {/* Outputs */}
        <Section title="Stream Outputs">
          <div className="py-1">
            <PortList nodeId={node.id} direction="output" />
          </div>
        </Section>

        {/*
          Section order:
          - After run: Outputs (with results) → Parameters
          - Before run: Parameters → Outputs (definitions only)
        */}
        {hasRunData ? (
          <>
            {onboardOutputs.length > 0 && (
              <Section title="Outputs">
                <OnboardOutputList outputs={onboardOutputs} runStatus={runStatus} />
              </Section>
            )}
            <Section title="Parameters">
              <OnBoardParamForm key={node.id} nodeId={node.id} />
            </Section>
          </>
        ) : (
          <>
            <Section title="Parameters">
              <OnBoardParamForm key={node.id} nodeId={node.id} />
            </Section>
            {onboardOutputs.length > 0 && (
              <Section title="Outputs">
                <OnboardOutputList outputs={onboardOutputs} />
              </Section>
            )}
          </>
        )}
      </div>

      {/* Delete button */}
      <div className="px-3 py-2 border-t border-mf-border">
        <button
          onClick={() => { removeNode(node.id); selectNode(null) }}
          className="w-full py-1 bg-red-900/30 border border-red-700/50 text-red-400 text-xs rounded hover:bg-red-900/50 transition-colors"
        >
          Remove Node
        </button>
      </div>
    </div>
  )
}
