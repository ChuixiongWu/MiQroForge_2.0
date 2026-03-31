import { create } from 'zustand'
import type { RunPhase } from '../types/index-types'

export interface NodeRunStatus {
  phase: RunPhase
  startedAt?: string
  finishedAt?: string
  outputs: Record<string, string>   // { total_energy: "-76.123 Ha", opt_converged: "true" }
}

interface RunOverlayState {
  activeRunName: string | null
  workflowPhase: RunPhase | null
  nodeStatuses: Record<string, NodeRunStatus>   // key = canvas nodeId

  setActiveRun: (name: string) => void
  updateFromArgo: (raw: Record<string, unknown>) => void
  clearOverlay: () => void
}

// ─── Argo JSON helpers ────────────────────────────────────────────────────────

interface ArgoNode {
  type?: string
  templateName?: string
  phase?: string
  startedAt?: string
  finishedAt?: string
  outputs?: {
    parameters?: Array<{ name: string; value: string }>
  }
}

/**
 * Parse raw Argo workflow JSON and extract per-canvas-node statuses.
 *
 * Argo status.nodes is a flat object keyed by Argo node ID.
 * Pod-type nodes have templateName = "mf-{canvasNodeId}" by MiQroForge convention.
 *
 * Skipped-type nodes (phase "Omitted") occur when a `when` condition evaluated
 * to false — i.e. a quality gate blocked downstream execution.  We surface these
 * so the canvas can show the Omitted badge rather than silently hiding the node.
 *
 * If the Argo workflow phase is Succeeded but ≥1 canvas node was Omitted, the
 * effective workflow phase is promoted to the synthetic "PartialSuccess" so the
 * UI does not falsely report a clean green success.
 */
function parseArgoNodes(raw: Record<string, unknown>): {
  workflowPhase: RunPhase
  nodeStatuses: Record<string, NodeRunStatus>
} {
  const status = (raw.status ?? {}) as Record<string, unknown>
  let workflowPhase = (status.phase as RunPhase | undefined) ?? 'Unknown'
  const rawNodes = (status.nodes ?? {}) as Record<string, ArgoNode>

  const nodeStatuses: Record<string, NodeRunStatus> = {}
  let hasOmitted = false

  for (const argoNode of Object.values(rawNodes)) {
    // Process Pod nodes (actual computation steps) and Skipped nodes (omitted
    // because a `when` condition was false — e.g. quality gate not passed).
    const isCompute = argoNode.type === 'Pod'
    const isSkipped = argoNode.type === 'Skipped'
    if (!isCompute && !isSkipped) continue

    const templateName = argoNode.templateName ?? ''
    // Template name format: "mf-{canvasNodeId}"
    if (!templateName.startsWith('mf-')) continue
    const canvasId = templateName.slice(3)   // strip "mf-"
    if (!canvasId) continue

    const nodePhase = (argoNode.phase as RunPhase | undefined) ?? 'Unknown'
    if (nodePhase === 'Omitted') hasOmitted = true

    // Extract output parameters (only present on Pod nodes that ran)
    const outputs: Record<string, string> = {}
    for (const param of argoNode.outputs?.parameters ?? []) {
      if (param.name && param.value !== undefined) {
        outputs[param.name] = String(param.value)
      }
    }

    nodeStatuses[canvasId] = {
      phase:      nodePhase,
      startedAt:  argoNode.startedAt,
      finishedAt: argoNode.finishedAt,
      outputs,
    }
  }

  // Promote Succeeded → PartialSuccess when quality gates blocked downstream nodes
  if (workflowPhase === 'Succeeded' && hasOmitted) {
    workflowPhase = 'PartialSuccess'
  }

  return { workflowPhase, nodeStatuses }
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useRunOverlayStore = create<RunOverlayState>((set) => ({
  activeRunName: null,
  workflowPhase: null,
  nodeStatuses: {},

  setActiveRun: (name) => set({ activeRunName: name, workflowPhase: null, nodeStatuses: {} }),

  updateFromArgo: (raw) => {
    set((state) => {
      const { workflowPhase, nodeStatuses: next } = parseArgoNodes(raw)

      // Preserve existing object references for unchanged nodes to avoid N re-renders
      let statusesChanged = false
      const merged: Record<string, NodeRunStatus> = {}

      for (const [canvasId, nextStatus] of Object.entries(next)) {
        const prev = state.nodeStatuses[canvasId]
        if (
          prev &&
          prev.phase      === nextStatus.phase &&
          prev.startedAt  === nextStatus.startedAt &&
          prev.finishedAt === nextStatus.finishedAt &&
          JSON.stringify(prev.outputs) === JSON.stringify(nextStatus.outputs)
        ) {
          merged[canvasId] = prev   // reuse same reference
        } else {
          merged[canvasId] = nextStatus
          statusesChanged = true
        }
      }

      const phaseChanged = state.workflowPhase !== workflowPhase

      if (!statusesChanged && !phaseChanged) return state

      return {
        workflowPhase,
        nodeStatuses: statusesChanged ? merged : state.nodeStatuses,
      }
    })
  },

  clearOverlay: () => set({ activeRunName: null, workflowPhase: null, nodeStatuses: {} }),
}))
