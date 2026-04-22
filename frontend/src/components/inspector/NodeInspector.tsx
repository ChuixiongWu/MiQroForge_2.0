import React from 'react'
import { useForm } from 'react-hook-form'
import { useWorkflowStore, type MFNodeData } from '../../stores/workflow-store'
import { useUIStore } from '../../stores/ui-store'
import { useRunOverlayStore } from '../../stores/run-overlay-store'
import type { NodeRunStatus } from '../../stores/run-overlay-store'
import { PORT_COLORS, portCategoryLabel } from '../../lib/port-type-utils'
import type { OnBoardOutput } from '../../types/nodespec'
import { phaseEmoji, phaseBadgeClass, formatElapsed } from '../../lib/phase-utils'
import { X, Cpu, MemoryStick, Clock, Settings, ChevronDown, ChevronRight, Eye, EyeOff } from 'lucide-react'
import { filesApi, projectFilesApi } from '../../api/files-api'
import { getNodePrefs, saveNodePrefs, classifyParams, onGlobalPrefsChange, type NodePreference, type ParamVisibility } from '../../lib/node-preferences'

// ─── Parameter form ───────────────────────────────────────────────────────────

function OnBoardParamForm({ nodeId }: { nodeId: string }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const updateNodeParams = useWorkflowStore((s) => s.updateNodeParams)

  const allInputs = node?.data.onboard_inputs ?? []
  // Filter out resource params — they are shown in the Resources section
  const inputs = allInputs.filter((p) => !p.resource_param)
  const storedParams = node?.data.onboard_params ?? {}
  const nodeName = node?.data.name ?? ''

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

  // ── Preference state ──
  const [prefs, setPrefs] = React.useState<NodePreference>(() => getNodePrefs(nodeName))
  const [showPrefPanel, setShowPrefPanel] = React.useState(false)

  // Reload prefs when node changes or global prefs update
  React.useEffect(() => {
    setPrefs(getNodePrefs(nodeName))
    setShowPrefPanel(false)
  }, [nodeName])

  React.useEffect(() => {
    return onGlobalPrefsChange(() => {
      if (nodeName) setPrefs(getNodePrefs(nodeName))
    })
  }, [nodeName])

  const updatePref = (paramName: string, visibility: ParamVisibility) => {
    setPrefs((prev) => {
      const next: NodePreference = {
        collapsedParams: prev.collapsedParams.filter((n) => n !== paramName),
        hiddenParams: prev.hiddenParams.filter((n) => n !== paramName),
      }
      if (visibility === 'collapsed') next.collapsedParams.push(paramName)
      else if (visibility === 'hidden') next.hiddenParams.push(paramName)
      saveNodePrefs(nodeName, next)
      return next
    })
  }

  const visibility = React.useMemo(
    () => classifyParams(inputs.map((p) => p.name), prefs),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [inputs.length, prefs],
  )

  const [showAllCollapsed, setShowAllCollapsed] = React.useState(false)

  // Track which params are in multi-input mode
  // Auto-activate if stored value is an array, or if node has parallel_sweep / sweep_values data
  const hasSweep = !!node?.data.parallel_sweep
  const hasSweepValues = !!node?.data.sweep_values
  const [multiMode, setMultiMode] = React.useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    for (const inp of inputs) {
      if (inp.multiple_input) {
        if (Array.isArray(storedParams[inp.name]) || (hasSweep && inp.name in storedParams) || hasSweepValues) {
          init[inp.name] = true
        }
      }
    }
    return init
  })

  const toggleMultiMode = (paramName: string) => {
    setMultiMode((prev) => {
      const next = !prev[paramName]
      // When switching to single mode, clear sweep data but keep the param value
      if (!next) {
        updateNodeParams(nodeId, { __sweep_values: [] })
      }
      return { ...prev, [paramName]: next }
    })
  }

  if (inputs.length === 0) {
    return <p className="text-xs text-mf-text-muted px-3 py-2">No parameters</p>
  }

  const onSubmit = (data: Record<string, unknown>) => {
    // Handle sweep mode: split __sweep_values from pattern
    for (const inp of inputs) {
      if (inp.multiple_input && multiMode[inp.name]) {
        const valuesKey = `${inp.name}__sweep_values`
        const valuesText = (data[valuesKey] as string) ?? ''
        const values = valuesText.split(/[,\n]+/).map((v) => v.trim()).filter(Boolean)
        // Move sweep values into __sweep_values for the store to extract
        data.__sweep_values = values
        // Remove the raw sweep values text; pattern stays in data[inp.name]
        delete data[valuesKey]
      }
    }
    updateNodeParams(nodeId, data)
  }

  // ── Render a single param row ──
  const renderParam = (param: typeof inputs[number]) => (
    <div key={param.name}>
      <label className="block text-[11px] text-mf-text-secondary mb-0.5">
        {param.display_name}
        {param.default == null && <span className="text-red-400 ml-0.5">*</span>}
        {param.unit && <span className="text-mf-text-muted ml-1">({param.unit})</span>}
        {param.multiple_input && (
          <button
            type="button"
            onClick={() => toggleMultiMode(param.name)}
            title={multiMode[param.name]
              ? 'Switch back to single value mode'
              : 'Enable parallel sweep — enter multiple values (one per line) to fan-out execution'}
            className={`text-[10px] ml-2 px-1.5 py-0.5 rounded border transition-colors ${
              multiMode[param.name]
                ? 'border-purple-500/60 bg-purple-900/40 text-purple-300 hover:bg-purple-900/60'
                : 'border-purple-700/30 bg-purple-950/30 text-purple-500 hover:border-purple-500/50 hover:text-purple-400'
            }`}
          >
            {multiMode[param.name] ? '\u21A9 Single' : '\u26A1 Sweep'}
          </button>
        )}
      </label>

      {param.multiple_input && multiMode[param.name] ? (
        // Sweep mode: Values + Pattern
        <div className="space-y-1.5">
          {/* Values textarea */}
          <div>
            <label className="block text-[10px] text-purple-400/80 mb-0.5">Values</label>
            <textarea
              rows={3}
              {...register(`${param.name}__sweep_values`)}
              placeholder={'0.5\n0.6\n0.7'}
              defaultValue={
                node?.data.sweep_values
                  ? (node.data.sweep_values as unknown[]).join('\n')
                  : Array.isArray(storedParams[param.name])
                    ? (storedParams[param.name] as string[]).join('\n')
                    : ''
              }
              className="w-full px-2 py-1 bg-mf-input border border-purple-700/40 rounded text-xs text-mf-text-primary focus:outline-none focus:border-purple-500 font-mono resize-y"
            />
            <p className="text-[10px] text-mf-text-muted mt-0.5">
              One value per line or comma-separated.
            </p>
          </div>
          {/* Pattern input */}
          <div>
            <label className="block text-[10px] text-purple-400/80 mb-0.5">Pattern</label>
            <input
              type="text"
              {...register(param.name)}
              placeholder={param.name === 'geometry_file' ? 'h2_{{item}}.xyz' : '{{item}}'}
              defaultValue={
                typeof storedParams[param.name] === 'string' && String(storedParams[param.name]).includes('{{item}}')
                  ? String(storedParams[param.name])
                  : '{{item}}'
              }
              className="w-full px-2 py-1 bg-mf-input border border-purple-700/40 rounded text-xs text-mf-text-primary focus:outline-none focus:border-purple-500 font-mono"
            />
            <p className="text-[10px] text-mf-text-muted mt-0.5">
              Expression with {'{{item}}'}, replaced per sweep value.
            </p>
          </div>
          {(hasSweep || hasSweepValues) && (
            <p className="text-[10px] text-purple-400/70">
              Sweep: {(node?.data.sweep_values ?? node?.data.parallel_sweep?.values ?? []).length} values configured
            </p>
          )}
        </div>
      ) : param.type === 'textarea' ? (
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
  )

  // Partition params by visibility
  const visibleParams = inputs.filter((p) => visibility[p.name] === 'visible')
  const collapsedParams = inputs.filter((p) => visibility[p.name] === 'collapsed')
  const hiddenParams = inputs.filter((p) => visibility[p.name] === 'hidden')

  return (
    <div>
      {/* Preference gear button */}
      <div className="flex items-center justify-end px-3 py-1">
        <button
          type="button"
          onClick={() => setShowPrefPanel(!showPrefPanel)}
          title="Parameter display preferences"
          className="text-mf-text-muted hover:text-mf-text-primary transition-colors p-0.5"
        >
          <Settings size={12} />
        </button>
      </div>

      {/* Preference panel */}
      {showPrefPanel && (
        <div className="mx-3 mb-2 p-2 bg-mf-surface border border-mf-border rounded text-[10px] space-y-1">
          <div className="text-mf-text-secondary font-medium mb-1">Parameter visibility</div>
          {inputs.map((param) => {
            const vis = visibility[param.name]
            return (
              <div key={param.name} className="flex items-center gap-1">
                <span className="text-mf-text-secondary flex-1 truncate">{param.display_name}</span>
                <button
                  type="button"
                  onClick={() => updatePref(param.name, 'visible')}
                  className={`px-1 py-0.5 rounded ${vis === 'visible' ? 'bg-blue-900/40 text-blue-300' : 'text-mf-text-muted hover:text-mf-text-secondary'}`}
                  title="Show"
                >
                  <Eye size={10} />
                </button>
                <button
                  type="button"
                  onClick={() => updatePref(param.name, 'collapsed')}
                  className={`px-1 py-0.5 rounded ${vis === 'collapsed' ? 'bg-amber-900/40 text-amber-300' : 'text-mf-text-muted hover:text-mf-text-secondary'}`}
                  title="Collapse"
                >
                  <ChevronDown size={10} />
                </button>
                <button
                  type="button"
                  onClick={() => updatePref(param.name, 'hidden')}
                  className={`px-1 py-0.5 rounded ${vis === 'hidden' ? 'bg-red-900/40 text-red-300' : 'text-mf-text-muted hover:text-mf-text-secondary'}`}
                  title="Hide"
                >
                  <EyeOff size={10} />
                </button>
              </div>
            )
          })}
        </div>
      )}

      <form onChange={handleSubmit(onSubmit)} className="space-y-2 px-3 py-2">
        {/* Visible params */}
        {visibleParams.map(renderParam)}

        {/* Collapsed params */}
        {collapsedParams.length > 0 && (
          showAllCollapsed ? (
            <div className="rounded bg-mf-surface border border-mf-border/30 px-1 py-1">
              <button
                type="button"
                onClick={() => setShowAllCollapsed(false)}
                className="text-[10px] text-mf-text-muted hover:text-mf-text-secondary flex items-center gap-0.5 mb-1 px-2"
              >
                <ChevronRight size={10} />
                Collapse {collapsedParams.length} advanced params
              </button>
              {collapsedParams.map(renderParam)}
            </div>
          ) : (
            <div className="rounded bg-mf-surface border border-mf-border/30 px-1 py-1">
              <button
                type="button"
                onClick={() => setShowAllCollapsed(true)}
                className="text-[10px] text-mf-text-muted hover:text-mf-text-secondary flex items-center gap-0.5 px-2"
              >
                <ChevronDown size={10} />
                {collapsedParams.length} advanced param{collapsedParams.length > 1 ? 's' : ''}
              </button>
            </div>
          )
        )}

        {/* Hidden count indicator */}
        {hiddenParams.length > 0 && (
          <p className="text-[10px] text-mf-text-muted/50 italic">
            {hiddenParams.length} hidden param{hiddenParams.length > 1 ? 's' : ''} (click gear to show)
          </p>
        )}
      </form>
    </div>
  )
}

// ─── Ephemeral description editor (as onboard param) ─────────────────────────

function EphemeralDescriptionEditor({ nodeId }: { nodeId: string }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const updateNodeParams = useWorkflowStore((s) => s.updateNodeParams)

  if (!node?.data.ephemeral) return null

  // Read from onboard_params.description, fallback to ephemeral_description
  const desc = (node.data.onboard_params?.description as string) ?? node.data.ephemeral_description ?? ''

  return (
    <div className="px-3 py-2">
      <label className="block text-[11px] text-mf-text-secondary mb-0.5">
        Description <span className="text-mf-text-muted">(ephemeral node script intent)</span>
      </label>
      <textarea
        rows={3}
        value={desc}
        onChange={(e) => updateNodeParams(nodeId, { description: e.target.value })}
        placeholder="Describe what this ephemeral node should do..."
        className="w-full px-2 py-1 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary focus:outline-none focus:border-gray-400 font-mono resize-y"
      />
      <p className="text-[10px] text-mf-text-muted mt-0.5">
        Script will be generated when you compile. Edit this before compiling.
      </p>
    </div>
  )
}

// ─── Ephemeral I/O port count editor ─────────────────────────────────────────

function EphemeralPortEditor({ nodeId }: { nodeId: string }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const updateNodeData = useWorkflowStore((s) => s.updateNodeWithHistory)

  if (!node?.data.ephemeral) return null

  const ports = node.data.ports as { inputs: { name: string; type: string }[]; outputs: { name: string; type: string }[] } | undefined
  const inputCount = ports?.inputs?.length ?? 1
  const outputCount = ports?.outputs?.length ?? 1

  const updatePorts = (dir: 'inputs' | 'outputs', count: number) => {
    const otherCount = dir === 'inputs' ? outputCount : inputCount
    // At least 1 port total; max 8 per direction
    const clamped = Math.max(0, Math.min(8, count))
    if (clamped === 0 && otherCount === 0) return // can't have 0 total
    const prefix = dir === 'inputs' ? 'I' : 'O'
    const newPorts = Array.from({ length: clamped }, (_, i) => ({
      name: `${prefix}${i + 1}`,
      type: 'software_data_package',
    }))
    const currentPorts = ports ?? { inputs: [{ name: 'I1', type: 'software_data_package' }], outputs: [{ name: 'O1', type: 'software_data_package' }] }
    updateNodeData(nodeId, {
      ...node.data,
      ports: { ...currentPorts, [dir]: newPorts },
    } as MFNodeData)
  }

  return (
    <div className="px-3 py-2 space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-[11px] text-mf-text-secondary">Inputs</label>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => updatePorts('inputs', inputCount - 1)}
            disabled={inputCount <= 0 || (inputCount === 1 && outputCount === 0)}
            className="w-5 h-5 flex items-center justify-center rounded bg-mf-input border border-mf-border text-xs text-mf-text-muted hover:text-mf-text-primary disabled:opacity-30"
          >-</button>
          <span className="text-xs text-mf-text-primary font-mono w-4 text-center">{inputCount}</span>
          <button
            onClick={() => updatePorts('inputs', inputCount + 1)}
            disabled={inputCount >= 8}
            className="w-5 h-5 flex items-center justify-center rounded bg-mf-input border border-mf-border text-xs text-mf-text-muted hover:text-mf-text-primary disabled:opacity-30"
          >+</button>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <label className="text-[11px] text-mf-text-secondary">Outputs</label>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => updatePorts('outputs', outputCount - 1)}
            disabled={outputCount <= 0 || (outputCount === 1 && inputCount === 0)}
            className="w-5 h-5 flex items-center justify-center rounded bg-mf-input border border-mf-border text-xs text-mf-text-muted hover:text-mf-text-primary disabled:opacity-30"
          >-</button>
          <span className="text-xs text-mf-text-primary font-mono w-4 text-center">{outputCount}</span>
          <button
            onClick={() => updatePorts('outputs', outputCount + 1)}
            disabled={outputCount >= 8}
            className="w-5 h-5 flex items-center justify-center rounded bg-mf-input border border-mf-border text-xs text-mf-text-muted hover:text-mf-text-primary disabled:opacity-30"
          >+</button>
        </div>
      </div>
      <p className="text-[10px] text-mf-text-muted">
        Ephemeral ports connect to any type. At least 1 total port required.
      </p>
    </div>
  )
}

// ─── Workspace image display ──────────────────────────────────────────────────

function WorkspaceImage({ filename, nodeId, projectId }: { filename: string; nodeId: string; projectId?: string | null }) {
  const [imageUrl, setImageUrl] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [expanded, setExpanded] = React.useState(false)
  const runStatus = useRunOverlayStore((s) => s.nodeStatuses[nodeId])

  React.useEffect(() => {
    let revokedUrl: string | null = null
    let cancelled = false

    async function loadImage() {
      try {
        const blob = projectId
          ? await projectFilesApi.download(projectId, filename)
          : await filesApi.download(filename)
        if (cancelled) return
        const url = URL.createObjectURL(blob)
        revokedUrl = url
        setImageUrl(url)
        setError(null)
      } catch {
        if (!cancelled) setError('Image not available')
      }
    }

    // Load when run succeeds, or on mount
    if (!runStatus || runStatus.phase === 'Succeeded') {
      loadImage()
    }

    return () => {
      cancelled = true
      if (revokedUrl) URL.revokeObjectURL(revokedUrl)
    }
  }, [filename, runStatus?.phase, projectId])

  if (error) return null
  if (!imageUrl) return null

  return (
    <div className="px-3 py-2">
      <div className="text-[11px] text-mf-text-secondary mb-1">Workspace Output</div>
      <img
        src={imageUrl}
        alt={filename}
        onClick={() => setExpanded(true)}
        className="w-full rounded border border-mf-border cursor-zoom-in hover:opacity-80 transition-opacity"
      />
      {expanded && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center cursor-zoom-out"
          onClick={() => setExpanded(false)}
        >
          <img src={imageUrl} alt={filename} className="max-w-[90vw] max-h-[90vh] object-contain" />
        </div>
      )}
    </div>
  )
}

// ─── Port list ────────────────────────────────────────────────────────────────

function PortList({ nodeId, direction }: { nodeId: string; direction: 'input' | 'output' }) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  // For formal nodes: stream_inputs/stream_outputs from nodespec
  // For ephemeral nodes: derive from ports field (simpler {name, type} shape)
  let ports = direction === 'input' ? (node?.data.stream_inputs ?? []) : (node?.data.stream_outputs ?? [])
  if (ports.length === 0 && node?.data.ports) {
    const rawPorts = node.data.ports as Record<string, unknown>
    const raw = direction === 'input' ? rawPorts.inputs : rawPorts.outputs
    if (Array.isArray(raw)) {
      ports = raw.map((p: { name: string; type: string }) => ({ name: p.name, display_name: p.name, category: p.type as never, detail: '' }))
    } else if (typeof raw === 'number') {
      const prefix = direction === 'input' ? 'I' : 'O'
      ports = Array.from({ length: raw as number }, (_, i) => ({
        name: `${prefix}${i + 1}`, display_name: `${prefix}${i + 1}`, category: 'software_data_package' as never, detail: '',
      }))
    }
  }

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

function RunSummarySection({
  runStatus,
  nodeId,
  onRotate,
}: {
  runStatus: NodeRunStatus
  nodeId?: string
  onRotate?: (canvasId: string) => void
}) {
  const elapsed = formatElapsed(runStatus.startedAt, runStatus.finishedAt)
  const multi = runStatus.instances.length > 1
  return (
    <div className="px-3 py-2 flex items-center gap-2">
      <span className={`${phaseBadgeClass(runStatus.phase)} text-xs`}>
        {phaseEmoji(runStatus.phase)} {runStatus.phase}
      </span>
      {elapsed && <span className="text-[11px] text-mf-text-muted">{elapsed}</span>}
      {multi && nodeId && onRotate && (
        <button
          className="ml-auto text-[11px] text-purple-300 hover:text-purple-200 font-mono cursor-pointer select-none"
          onClick={() => onRotate(nodeId)}
          title="Click to switch instance"
        >
          &lsaquo; {runStatus.currentIndex + 1}/{runStatus.instances.length} &rsaquo;
        </button>
      )}
    </div>
  )
}

// ─── Section ──────────────────────────────────────────────────────────────────

function Section({ title, children, bgClass }: { title: string; children: React.ReactNode; bgClass?: string }) {
  return (
    <div className={`border-b border-mf-border/50 ${bgClass ?? ''}`}>
      <div className="mf-panel-section-header">{title}</div>
      {children}
    </div>
  )
}

// ─── Resource params editor ──────────────────────────────────────────────────

function ResourceParamsEditor({
  nodeId,
  resources,
}: {
  nodeId: string
  resources: NonNullable<MFNodeData['resources']>
}) {
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === nodeId))
  const updateNodeParams = useWorkflowStore((s) => s.updateNodeParams)
  const [expanded, setExpanded] = React.useState(false)

  // Get resource param inputs (auto-generated from parametrize)
  const resourceInputs = (node?.data.onboard_inputs ?? []).filter((p) => p.resource_param)
  const storedParams = node?.data.onboard_params ?? {}

  // Map resource params to summary fields — use user edits when available
  const cpuParam = resourceInputs.find(p =>
    p.display_name?.toLowerCase().includes('core') || p.display_name?.toLowerCase().includes('cpu')
  )
  const memParam = resourceInputs.find(p =>
    p.name === 'mem_gb' || p.display_name?.toLowerCase().includes('memory')
  )
  const effectiveCpu = cpuParam
    ? ((storedParams[cpuParam.name] as number) ?? resources.cpu)
    : resources.cpu
  const effectiveMem = memParam
    ? ((storedParams[memParam.name] as number) ?? resources.mem_gb)
    : resources.mem_gb

  // Pod memory = effective mem + overhead
  const effectivePodMem = effectiveMem + resources.mem_overhead

  return (
    <div className="px-3 py-1.5">
      {/* Summary — reacts to parametrize edits */}
      <div className="flex gap-4 text-xs text-mf-text-secondary">
        <span className="flex items-center gap-1"><Cpu size={11} />{effectiveCpu} CPU</span>
        <span className="flex items-center gap-1"><MemoryStick size={11} />{effectiveMem} GiB</span>
        <span className="flex items-center gap-1"><Clock size={11} />{resources.estimated_walltime_hours}h</span>
      </div>

      {/* Resource params — collapsible box matching collapsed params style */}
      {(resourceInputs.length > 0 || resources.mem_overhead > 0) && (
        expanded ? (
          <div className="mt-1.5 bg-mf-surface border border-mf-border/30 rounded px-2 py-2 space-y-1.5">
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="text-[10px] text-mf-text-muted hover:text-mf-text-secondary flex items-center gap-0.5 mb-1"
            >
              <ChevronRight size={10} />
              Hide resource params
            </button>
            {/* Pod memory breakdown */}
            {resources.mem_overhead > 0 && (
              <div className="text-[10px] text-mf-text-muted pb-1 border-b border-mf-border/20">
                Pod memory: {effectiveMem} + {resources.mem_overhead} overhead = {effectivePodMem} GiB
              </div>
            )}

            {/* Editable resource params */}
            {resourceInputs.map((param) => {
              const current = storedParams[param.name] ?? param.default ?? ''
              return (
                <div key={param.name} className="flex items-center gap-2">
                  <label className="text-[11px] text-mf-text-secondary w-20 flex-shrink-0 truncate" title={param.display_name}>
                    {param.display_name}
                  </label>
                  <input
                    type="number"
                    step={param.type === 'float' ? 'any' : undefined}
                    value={current as string | number}
                    onChange={(e) => {
                      const val = param.type === 'integer'
                        ? parseInt(e.target.value, 10) || 0
                        : parseFloat(e.target.value) || 0
                      updateNodeParams(nodeId, { [param.name]: val })
                    }}
                    min={param.min}
                    max={param.max}
                    className="w-20 px-1.5 py-0.5 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary focus:outline-none focus:border-gray-400 font-mono"
                  />
                  {param.unit && (
                    <span className="text-[10px] text-mf-text-muted">{param.unit}</span>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="mt-1.5 bg-mf-surface border border-mf-border/30 rounded px-2 py-1">
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="text-[10px] text-mf-text-muted hover:text-mf-text-secondary flex items-center gap-0.5"
            >
              <ChevronDown size={10} />
              {resourceInputs.length} resource param{resourceInputs.length !== 1 ? 's' : ''}
            </button>
          </div>
        )
      )}
    </div>
  )
}

// ─── NodeInspector ────────────────────────────────────────────────────────────

export function NodeInspector() {
  const selectedNodeId = useUIStore((s) => s.selectedNodeId)
  const { selectNode } = useUIStore()
  const removeNode = useWorkflowStore((s) => s.removeNode)
  const projectId = useWorkflowStore((s) => s._projectId)
  const node = useWorkflowStore((s) =>
    selectedNodeId ? s.nodes.find((n) => n.id === selectedNodeId) : null,
  )
  // Connect to run overlay for this node
  const runStatus = useRunOverlayStore((s) =>
    selectedNodeId ? s.nodeStatuses[selectedNodeId] : undefined,
  )
  const rotateInstance = useRunOverlayStore((s) => s.rotateInstance)

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
  const isEphemeral = !!d.ephemeral

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
          {!isEphemeral && (
            <>
              <div className="text-[11px] text-mf-text-muted font-mono mt-0.5">{d.name} v{d.version}</div>
              <div className="text-xs text-mf-text-secondary mt-1 leading-relaxed">{d.description}</div>
            </>
          )}
        </div>

        {/* Ephemeral description editor */}
        {isEphemeral && (
          <Section title="Script Description">
            <EphemeralDescriptionEditor nodeId={node.id} />
          </Section>
        )}

        {/* Ephemeral I/O port editor */}
        {isEphemeral && (
          <Section title="I/O Ports">
            <EphemeralPortEditor nodeId={node.id} />
          </Section>
        )}

        {/* Run status (when available) */}
        {runStatus && (
          <Section title="Run Status">
            <RunSummarySection runStatus={runStatus} nodeId={node.id} onRotate={rotateInstance} />
          </Section>
        )}

        {/* Resources */}
        {res && (
          <Section title="Resources">
            <ResourceParamsEditor
              nodeId={node.id}
              resources={res}
            />
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
            {/* Ephemeral image display — driven by _mf_images output param */}
            {isEphemeral && runStatus?.outputs?._mf_images && (
              <WorkspaceImage filename={runStatus.outputs._mf_images.split('\n')[0].split('/').pop()!} nodeId={node.id} projectId={projectId} />
            )}
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
