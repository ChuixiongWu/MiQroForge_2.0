import { create } from 'zustand'
import type { RunPhase } from '../types/index-types'

/** One instance of a node's execution (a single sweep iteration, or the sole run). */
export interface NodeInstanceStatus {
  phase: RunPhase
  startedAt?: string
  finishedAt?: string
  outputs: Record<string, string>
}

export interface NodeRunStatus {
  phase: RunPhase
  startedAt?: string
  finishedAt?: string
  /** One entry per instance. For non-sweep nodes this is always length 1. */
  instances: NodeInstanceStatus[]
  /** Index of the instance currently displayed in canvas / inspector. */
  currentIndex: number
  /** Backward-compat: outputs of the current instance. */
  outputs: Record<string, string>
  /** Error message from Argo for failed nodes (from node.message). */
  error?: string
  /** Argo node ID (= pod name) for log retrieval. */
  podName?: string
}

interface RunOverlayState {
  activeRunName: string | null
  workflowPhase: RunPhase | null
  nodeStatuses: Record<string, NodeRunStatus>

  setActiveRun: (name: string) => void
  updateFromArgo: (raw: Record<string, unknown>) => void
  clearOverlay: () => void
  rotateInstance: (canvasId: string) => void
}

// ─── Argo JSON helpers ────────────────────────────────────────────────────────

interface ArgoNode {
  type?: string
  templateName?: string
  displayName?: string
  phase?: string
  message?: string
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
 * Sweep pipelines produce multiple Pod nodes with the same templateName
 * (one per sweep iteration). We collect them all into `instances[]`.
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

  // Collect instances per canvas node id
  const instancesMap: Record<string, NodeInstanceStatus[]> = {}
  const errorMap: Record<string, string> = {}
  const podNameMap: Record<string, string> = {}
  let hasOmitted = false

  for (const [argoNodeId, argoNode] of Object.entries(rawNodes)) {
    const isCompute = argoNode.type === 'Pod'
    const isSkipped = argoNode.type === 'Skipped'
    if (!isCompute && !isSkipped) continue

    const templateName = argoNode.templateName ?? ''
    if (!templateName.startsWith('mf-')) continue
    const canvasId = templateName.slice(3)
    if (!canvasId) continue

    const nodePhase = (argoNode.phase as RunPhase | undefined) ?? 'Unknown'
    if (nodePhase === 'Omitted') hasOmitted = true

    // Store Argo node ID (= pod name) for log retrieval
    if (isCompute) podNameMap[canvasId] = argoNodeId

    const outputs: Record<string, string> = {}
    for (const param of argoNode.outputs?.parameters ?? []) {
      if (param.name && param.value !== undefined) {
        outputs[param.name] = String(param.value)
      }
    }

    const instance: NodeInstanceStatus = {
      phase: nodePhase,
      startedAt: argoNode.startedAt,
      finishedAt: argoNode.finishedAt,
      outputs,
    }

    if (!instancesMap[canvasId]) {
      instancesMap[canvasId] = []
    }
    instancesMap[canvasId].push(instance)

    // Capture error message from failed nodes
    if ((nodePhase === 'Failed' || nodePhase === 'Error') && argoNode.message) {
      errorMap[canvasId] = argoNode.message
    }
  }

  // Build nodeStatuses with aggregated phase from instances
  const nodeStatuses: Record<string, NodeRunStatus> = {}
  for (const [canvasId, instances] of Object.entries(instancesMap)) {
    // Aggregate phase: if any instance failed → Failed; any running → Running; else use first
    let aggPhase: RunPhase = instances[0].phase
    if (instances.some((i) => i.phase === 'Failed' || i.phase === 'Error')) {
      aggPhase = 'Failed'
    } else if (instances.some((i) => i.phase === 'Running')) {
      aggPhase = 'Running'
    } else if (instances.every((i) => i.phase === 'Succeeded')) {
      aggPhase = 'Succeeded'
    }

    nodeStatuses[canvasId] = {
      phase: aggPhase,
      startedAt: instances[0].startedAt,
      finishedAt: instances[instances.length - 1].finishedAt,
      instances,
      currentIndex: 0,
      outputs: instances[0].outputs,
      error: errorMap[canvasId],
      podName: podNameMap[canvasId],
    }
  }

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
        // Keep the user's currentIndex if still valid
        const carryIndex = prev && prev.currentIndex < nextStatus.instances.length
          ? prev.currentIndex
          : 0
        const adjusted = { ...nextStatus, currentIndex: carryIndex, outputs: nextStatus.instances[carryIndex].outputs }

        if (
          prev &&
          prev.phase === adjusted.phase &&
          prev.currentIndex === adjusted.currentIndex &&
          JSON.stringify(prev.outputs) === JSON.stringify(adjusted.outputs) &&
          prev.instances.length === adjusted.instances.length
        ) {
          merged[canvasId] = prev
        } else {
          merged[canvasId] = adjusted
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

  rotateInstance: (canvasId) =>
    set((state) => {
      const status = state.nodeStatuses[canvasId]
      if (!status || status.instances.length <= 1) return state

      const nextIndex = (status.currentIndex + 1) % status.instances.length
      const nextInstance = status.instances[nextIndex]

      return {
        nodeStatuses: {
          ...state.nodeStatuses,
          [canvasId]: {
            ...status,
            currentIndex: nextIndex,
            outputs: nextInstance.outputs,
          },
        },
      }
    }),
}))
