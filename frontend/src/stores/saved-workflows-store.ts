/**
 * Saved Workflows Store — localStorage-backed
 *
 * Two kinds of saved data:
 *   1. savedWorkflows — manual saves triggered by the Save button
 *   2. runSnapshots   — auto-saved canvas state when a workflow is submitted to Argo
 *                       keyed by Argo run name so RunsPanel can offer "Restore Canvas"
 */

import { create } from 'zustand'
import type { Node as RFNode, Edge as RFEdge } from '@xyflow/react'
import type { MFNodeData } from './workflow-store'
import type { WorkflowMeta } from '../types/workflow'

// ─── Data shapes ──────────────────────────────────────────────────────────────

export interface CanvasSnapshot {
  meta: WorkflowMeta
  // RF nodes stripped of non-serializable fields (pending nodes excluded)
  nodes: Array<{
    id: string
    type: string
    position: { x: number; y: number }
    data: Record<string, unknown>
  }>
  edges: Array<{
    id: string
    source: string
    sourceHandle: string | null
    target: string
    targetHandle: string | null
    type?: string
  }>
}

export interface SavedWorkflow {
  id: string
  name: string
  savedAt: string   // ISO
  snapshot: CanvasSnapshot
}

export interface RunSnapshot {
  runName: string
  savedAt: string
  snapshot: CanvasSnapshot
  /** Warnings from the validation step (errors block submission; infos included too) */
  validationWarnings?: Array<{ message: string; node_id?: string }>
  validationInfos?: Array<{ message: string; node_id?: string }>
  /** Error message for locally-recorded failures (compile/submit errors) */
  error?: string
  /** Marks this snapshot as a local-only record (not submitted to Argo) */
  localOnly?: boolean
}

// ─── localStorage helpers ─────────────────────────────────────────────────────

let WF_KEY  = 'mf2:saved-workflows'
let RUN_KEY = 'mf2:run-snapshots'

/** Set project-scoped localStorage keys */
export function setSavedWorkflowsProjectId(projectId: string | null) {
  if (projectId) {
    WF_KEY = `mf2:saved-workflows-${projectId}`
    RUN_KEY = `mf2:run-snapshots-${projectId}`
  } else {
    WF_KEY = 'mf2:saved-workflows'
    RUN_KEY = 'mf2:run-snapshots'
  }
  // Reload state from new keys
  useSavedWorkflowsStore.setState({
    savedWorkflows: loadLS<SavedWorkflow[]>(WF_KEY, []),
    runSnapshots: loadLS<Record<string, RunSnapshot>>(RUN_KEY, {}),
  })
}

function loadLS<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}
function saveLS<T>(key: string, val: T): void {
  try { localStorage.setItem(key, JSON.stringify(val)) } catch { /* quota */ }
}

// ─── Serialise canvas state ───────────────────────────────────────────────────

function serializeCanvas(
  meta: WorkflowMeta,
  nodes: RFNode<MFNodeData>[],
  edges: RFEdge[],
): CanvasSnapshot {
  // Strip pending nodes (have non-serializable `pending_on_select` callbacks)
  const savableNodes = nodes.filter((n) => !n.data?.pending)

  return {
    meta,
    nodes: savableNodes.map((n) => ({
      id: n.id,
      type: n.type ?? 'mfNode',
      position: n.position,
      // JSON.stringify silently drops undefined/function values — exactly what we want
      data: JSON.parse(JSON.stringify(n.data)) as Record<string, unknown>,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      sourceHandle: e.sourceHandle ?? null,
      target: e.target,
      targetHandle: e.targetHandle ?? null,
      type: e.type,
    })),
  }
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface SavedWorkflowsState {
  savedWorkflows: SavedWorkflow[]
  runSnapshots: Record<string, RunSnapshot>

  saveWorkflow: (meta: WorkflowMeta, nodes: RFNode<MFNodeData>[], edges: RFEdge[]) => void
  deleteWorkflow: (id: string) => void

  saveRunSnapshot: (
    runName: string,
    meta: WorkflowMeta,
    nodes: RFNode<MFNodeData>[],
    edges: RFEdge[],
    validationWarnings?: Array<{ message: string; node_id?: string }>,
    validationInfos?: Array<{ message: string; node_id?: string }>,
    error?: string,
    localOnly?: boolean,
  ) => void
  deleteRunSnapshot: (runName: string) => void
  clearAllRunSnapshots: () => void
  getRunSnapshot: (runName: string) => RunSnapshot | null
}

export const useSavedWorkflowsStore = create<SavedWorkflowsState>((set, get) => ({
  savedWorkflows: loadLS<SavedWorkflow[]>(WF_KEY, []),
  runSnapshots:   loadLS<Record<string, RunSnapshot>>(RUN_KEY, {}),

  saveWorkflow: (meta, nodes, edges) => {
    const existing = get().savedWorkflows.find((w) => w.name === meta.name)
    const entry: SavedWorkflow = {
      id: existing?.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: meta.name,
      savedAt: new Date().toISOString(),
      snapshot: serializeCanvas(meta, nodes, edges),
    }
    let updated: SavedWorkflow[]
    if (existing) {
      updated = get().savedWorkflows.map((w) => (w.id === existing.id ? entry : w))
    } else {
      updated = [entry, ...get().savedWorkflows]
    }
    saveLS(WF_KEY, updated)
    set({ savedWorkflows: updated })
  },

  deleteWorkflow: (id) => {
    const updated = get().savedWorkflows.filter((w) => w.id !== id)
    saveLS(WF_KEY, updated)
    set({ savedWorkflows: updated })
  },

  saveRunSnapshot: (runName, meta, nodes, edges, validationWarnings, validationInfos, error, localOnly) => {
    const entry: RunSnapshot = {
      runName,
      savedAt: new Date().toISOString(),
      snapshot: serializeCanvas(meta, nodes, edges),
      validationWarnings,
      validationInfos,
      error,
      localOnly,
    }
    const updated = { ...get().runSnapshots, [runName]: entry }
    saveLS(RUN_KEY, updated)
    set({ runSnapshots: updated })
  },

  deleteRunSnapshot: (runName) => {
    const { [runName]: _dropped, ...rest } = get().runSnapshots
    saveLS(RUN_KEY, rest)
    set({ runSnapshots: rest })
  },

  clearAllRunSnapshots: () => {
    saveLS(RUN_KEY, {})
    set({ runSnapshots: {} })
  },

  getRunSnapshot: (runName) => get().runSnapshots[runName] ?? null,
}))

// ─── Convenience: deserialise snapshot → RF types ────────────────────────────

export function snapshotToRF(snapshot: CanvasSnapshot): {
  meta: WorkflowMeta
  nodes: RFNode<MFNodeData>[]
  edges: RFEdge[]
} {
  return {
    meta: snapshot.meta,
    nodes: snapshot.nodes as unknown as RFNode<MFNodeData>[],
    edges: snapshot.edges as unknown as RFEdge[],
  }
}
