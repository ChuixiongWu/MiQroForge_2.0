import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { applyNodeChanges, applyEdgeChanges } from '@xyflow/react'
import type {
  Node as RFNode,
  Edge as RFEdge,
  NodeChange,
  EdgeChange,
  Connection,
} from '@xyflow/react'
import type { StreamPort, OnBoardParam, OnBoardOutput, ResourceSpec } from '../types/nodespec'
import type { WorkflowMeta, ValidationResult } from '../types/workflow'

// ─── MFNode data shape ────────────────────────────────────────────────────────

export interface MFNodeData extends Record<string, unknown> {
  name: string
  version: string
  display_name: string
  description: string
  node_type: string
  category: string
  software?: string
  nodespec_path: string
  stream_inputs: StreamPort[]
  stream_outputs: StreamPort[]
  onboard_inputs: OnBoardParam[]
  onboard_outputs: OnBoardOutput[]
  resources?: ResourceSpec
  onboard_params: Record<string, unknown>

  // ── Sweep / Ephemeral 扩展字段 ────────────────────────────────────────────
  parallel_sweep?: { values: unknown[] }
  sweep_values?: unknown[]
  ephemeral?: boolean
  ephemeral_description?: string
  ports?: { inputs: Array<{ name: string; type: string }>; outputs: Array<{ name: string; type: string }> }
  node?: string

  // ── Phase 2 语义扩展字段 ──────────────────────────────────────────────────
  // pending=true 时显示为 ❓ PendingNodeCard
  pending?: boolean
  // 对应 SemanticWorkflow.steps[].id（用于 Auto-resolve 时匹配）
  pending_step_id?: string
  // 语义类型（来自 semantic_registry.yaml 的键）
  semantic_type?: string
  // 语义描述（Planner 生成，hover 时显示）
  semantic_description?: string
  // 选择理由（Planner 生成）
  semantic_rationale?: string
  // 候选实现节点（供 PendingNodeCard 显示）
  pending_implementations?: Array<{ nodeName: string; label: string; software?: string }>
  // 用户选择实现时的回调（函数，不持久化）
  pending_on_select?: (nodeName: string) => void

  // ── Node Generator 扩展字段 ─────────────────────────────────────────────────
  node_generator?: {
    generating: boolean
    result?: {
      node_name: string
      nodespec_yaml: string
      run_sh?: string
      input_templates: Record<string, string>
      saved_path?: string
      evaluation: { passed: boolean; issues: string[]; suggestions: string[] } | null
      error: string | null
    }
    software?: string
    semantic_type?: string
    description?: string
  }
}

// ─── Per-node implementation history ─────────────────────────────────────────

export interface NodeHistory {
  past: MFNodeData[]
  future: MFNodeData[]
}

// ─── Store state ──────────────────────────────────────────────────────────────

interface WorkflowState {
  // Metadata
  meta: WorkflowMeta

  // React Flow canvas state
  nodes: RFNode<MFNodeData>[]
  edges: RFEdge[]

  // Per-node implementation history
  nodeHistory: Record<string, NodeHistory>

  // Validation state
  validationResult: ValidationResult | null
  isValidating: boolean

  // Project-scoped persistence key
  _projectId: string | null
  setProjectId: (id: string | null) => void

  // Actions
  setMeta: (meta: Partial<WorkflowMeta>) => void
  onNodesChange: (changes: NodeChange<RFNode<MFNodeData>>[]) => void
  onEdgesChange: (changes: EdgeChange[]) => void
  onConnect: (connection: Connection) => void
  addNode: (node: RFNode<MFNodeData>) => void
  removeNode: (nodeId: string) => void
  updateNodeParams: (nodeId: string, params: Record<string, unknown>) => void
  updateNodeData: (nodeId: string, data: Partial<MFNodeData>) => void

  // Implementation undo/redo
  updateNodeWithHistory: (nodeId: string, newData: MFNodeData) => void
  undoNode: (nodeId: string) => void
  redoNode: (nodeId: string) => void

  // Compilation state (pre-Argo visual feedback)
  compilingNodeIds: string[]
  setCompilingNodeIds: (ids: string[]) => void
  clearCompilingNodeIds: () => void

  setValidationResult: (result: ValidationResult | null) => void
  setIsValidating: (v: boolean) => void
  loadFromNodes: (nodes: RFNode<MFNodeData>[], edges: RFEdge[]) => void
  clearCanvas: () => void
}

// ─── 持久化辅助：序列化时剥离不可序列化的函数 ─────────────────────────────────

function _stripCallbacks(node: RFNode<MFNodeData>): RFNode<MFNodeData> {
  const { pending_on_select: _fn, ...rest } = node.data
  return { ...node, data: rest as MFNodeData }
}

// ─── Debounced backend sync ───────────────────────────────────────────────────

let _syncTimer: ReturnType<typeof setTimeout> | null = null
let _lastSerialized = ''

function _debouncedBackendSync() {
  if (_syncTimer) clearTimeout(_syncTimer)
  _syncTimer = setTimeout(() => {
    const state = useWorkflowStore.getState()
    if (!state._projectId) return

    // Diff check — skip if nothing changed
    const serialized = JSON.stringify({
      meta: state.meta,
      nodes: state.nodes.map(_stripCallbacks),
      edges: state.edges,
    })
    if (serialized === _lastSerialized) return
    _lastSerialized = serialized

    import('./project-store').then(({ useProjectStore }) => {
      useProjectStore.getState().saveCanvas().catch(() => {})
    })
  }, 2000)
}

// ── Canvas 加载时的数据规范化 ──────────────────────────────────────────────────

/** 重置卡住的 node_generator.generating（刷新导致 fetch 中断后残留的中间状态） */
function _normalizeNodegenGenerating(n: RFNode<MFNodeData>): void {
  const data = n.data as Record<string, unknown>
  const ng = data.node_generator as Record<string, unknown> | undefined
  if (ng && ng.generating && !ng.result) {
    ng.generating = false
  }
}

// ─── Store implementation ─────────────────────────────────────────────────────

// Dynamic storage name: changes when project changes
let _storageName = 'mf-canvas-v1'

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, _get) => ({
      meta: { name: 'Untitled Workflow', description: '', version: '1.0.0' },
      nodes: [],
      edges: [],
      nodeHistory: {},
      validationResult: null,
      isValidating: false,
      compilingNodeIds: [],
      _projectId: null,

      setProjectId: (id) => {
        set({ _projectId: id })
        if (id) {
          _storageName = `mf-canvas-${id}`
        } else {
          _storageName = 'mf-canvas-v1'
        }
      },

      setMeta: (partial) =>
        set((s) => {
          const next = { meta: { ...s.meta, ...partial } }
          _debouncedBackendSync()
          return next
        }),

      onNodesChange: (changes) =>
        set((s) => {
          const next = applyNodeChanges(changes, s.nodes)
          _debouncedBackendSync()
          return { nodes: next }
        }),

      onEdgesChange: (changes) =>
        set((s) => {
          const next = applyEdgeChanges(changes, s.edges)
          _debouncedBackendSync()
          return { edges: next }
        }),

      onConnect: (connection) =>
        set((s) => {
          // Look up source port info for edge coloring
          const sourceNode = s.nodes.find((n) => n.id === connection.source)
          const sourceData = sourceNode?.data as MFNodeData | undefined
          let sourcePort: { name: string; category: string } | undefined
          if (connection.sourceHandle) {
            // Try formal stream_outputs first
            const formalPort = sourceData?.stream_outputs?.find(
              (p) => p.name === connection.sourceHandle,
            )
            if (formalPort) {
              sourcePort = { name: formalPort.name, category: formalPort.category }
            } else if (sourceData?.ephemeral && sourceData.ports) {
              // Ephemeral nodes: derive from data.ports
              const rawPorts = sourceData.ports as Record<string, unknown>
              const rawOutputs = rawPorts.outputs
              if (Array.isArray(rawOutputs)) {
                const found = rawOutputs.find((p: { name: string }) => p.name === connection.sourceHandle)
                if (found) sourcePort = { name: found.name, category: 'software_data_package' }
              }
            }
          }
          const edgeData = sourcePort
            ? { sourcePort: { name: sourcePort.name, category: sourcePort.category } }
            : undefined

          _debouncedBackendSync()
          return {
            edges: [
              ...s.edges,
              {
                ...connection,
                id: `e-${connection.source}.${connection.sourceHandle}-${connection.target}.${connection.targetHandle}`,
                type: 'mfEdge',
                data: edgeData,
              } as RFEdge,
            ],
          }
        }),

      addNode: (node) =>
        set((s) => {
          _debouncedBackendSync()
          return { nodes: [...s.nodes, node] }
        }),

      removeNode: (nodeId) =>
        set((s) => {
          const { [nodeId]: _dropped, ...restHistory } = s.nodeHistory
          _debouncedBackendSync()
          return {
            nodes: s.nodes.filter((n) => n.id !== nodeId),
            edges: s.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
            nodeHistory: restHistory,
          }
        }),

      updateNodeParams: (nodeId, params) =>
        set((s) => {
          _debouncedBackendSync()
          return {
            nodes: s.nodes.map((n) => {
              if (n.id !== nodeId) return n
              const { __sweep_values, ...rest } = params as Record<string, unknown> & { __sweep_values?: unknown[] }
              const data: MFNodeData = {
                ...n.data,
                onboard_params: { ...n.data.onboard_params, ...rest },
              }
              if (__sweep_values !== undefined) {
                data.sweep_values = __sweep_values
              }
              return { ...n, data }
            }),
          }
        }),

      updateNodeData: (nodeId, data) =>
        set((s) => {
          _debouncedBackendSync()
          return {
            nodes: s.nodes.map((n) =>
              n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n,
            ),
          }
        }),

      // ── Implementation history actions ──────────────────────────────────────

      updateNodeWithHistory: (nodeId, newData) =>
        set((s) => {
          const currentNode = s.nodes.find((n) => n.id === nodeId)
          if (!currentNode) return {}
          const hist = s.nodeHistory[nodeId] ?? { past: [], future: [] }
          _debouncedBackendSync()
          return {
            nodes: s.nodes.map((n) => n.id === nodeId ? { ...n, data: newData } : n),
            nodeHistory: {
              ...s.nodeHistory,
              [nodeId]: {
                past: [...hist.past, currentNode.data],
                future: [],
              },
            },
          }
        }),

      undoNode: (nodeId) =>
        set((s) => {
          const hist = s.nodeHistory[nodeId]
          if (!hist || hist.past.length === 0) return {}
          const currentNode = s.nodes.find((n) => n.id === nodeId)
          if (!currentNode) return {}
          const prevData = hist.past[hist.past.length - 1]
          _debouncedBackendSync()
          return {
            nodes: s.nodes.map((n) => n.id === nodeId ? { ...n, data: prevData } : n),
            nodeHistory: {
              ...s.nodeHistory,
              [nodeId]: {
                past: hist.past.slice(0, -1),
                future: [currentNode.data, ...hist.future],
              },
            },
          }
        }),

      redoNode: (nodeId) =>
        set((s) => {
          const hist = s.nodeHistory[nodeId]
          if (!hist || hist.future.length === 0) return {}
          const currentNode = s.nodes.find((n) => n.id === nodeId)
          if (!currentNode) return {}
          const nextData = hist.future[0]
          _debouncedBackendSync()
          return {
            nodes: s.nodes.map((n) => n.id === nodeId ? { ...n, data: nextData } : n),
            nodeHistory: {
              ...s.nodeHistory,
              [nodeId]: {
                past: [...hist.past, currentNode.data],
                future: hist.future.slice(1),
              },
            },
          }
        }),

      // ───────────────────────────────────────────────────────────────────────

      setValidationResult: (result) => set({ validationResult: result }),
      setIsValidating: (v) => set({ isValidating: v }),
      setCompilingNodeIds: (ids) => set({ compilingNodeIds: ids }),
      clearCompilingNodeIds: () => set({ compilingNodeIds: [] }),

      loadFromNodes: (nodes, edges) => {
        // Normalize: ensure ports are always arrays (may be int-count from old YAML import)
        // Also reset stuck generating flag (can't survive page reload)
        const normalized = nodes.map((n) => {
          _normalizeNodegenGenerating(n)

          const data = n.data as Record<string, unknown>
          if (data.ports && typeof data.ports === 'object') {
            const ports = data.ports as Record<string, unknown>
            if (!Array.isArray(ports.inputs) || !Array.isArray(ports.outputs)) {
              const numIn = (ports.inputs as number) ?? 0
              const numOut = (ports.outputs as number) ?? 0
              data.ports = {
                inputs: Array.from({ length: numIn }, (_, i) => ({ name: `I${i + 1}`, type: 'software_data_package' })),
                outputs: Array.from({ length: numOut }, (_, i) => ({ name: `O${i + 1}`, type: 'software_data_package' })),
              }
            }
          }
          return n
        })
        _debouncedBackendSync()
        set({ nodes: normalized, edges, nodeHistory: {}, validationResult: null })
      },

      clearCanvas: () => {
        _lastSerialized = ''
        _debouncedBackendSync()
        set({
          nodes: [],
          edges: [],
          nodeHistory: {},
          meta: { name: 'Untitled Workflow', description: '', version: '1.0.0' },
          validationResult: null,
        })
      },
    }),
    {
      name: _storageName,
      storage: createJSONStorage(() => localStorage),
      // 只持久化画布内容（nodes/edges/meta），运行时状态不存
      partialize: (state) => ({
        meta: state.meta,
        nodes: state.nodes.map(_stripCallbacks),
        edges: state.edges,
      }),
      // Normalize on rehydrate: ensure ports are always arrays,
      // reset stuck generating flag (transient UI state, can't survive page reload)
      merge: (persisted, current) => {
        const merged = { ...current, ...(persisted as Partial<WorkflowState>) }
        if (Array.isArray(merged.nodes)) {
          const raw = merged.nodes as Array<Record<string, unknown>>
          merged.nodes = raw.map((n) => {
            const data = n.data as Record<string, unknown> | undefined
            if (data?.node_generator) {
              const ng = data.node_generator as Record<string, unknown>
              if (ng.generating && !ng.result) {
                ng.generating = false
              }
            }
            if (data?.ports && typeof data.ports === 'object') {
              const ports = data.ports as Record<string, unknown>
              if (!Array.isArray(ports.inputs) || !Array.isArray(ports.outputs)) {
                const numIn = (ports.inputs as number) ?? 0
                const numOut = (ports.outputs as number) ?? 0
                data.ports = {
                  inputs: Array.from({ length: numIn }, (_, i) => ({ name: `I${i + 1}`, type: 'software_data_package' })),
                  outputs: Array.from({ length: numOut }, (_, i) => ({ name: `O${i + 1}`, type: 'software_data_package' })),
                }
              }
            }
            return n
          }) as typeof merged.nodes
        }
        return merged
      },
    },
  ),
)

// Convenience selector: can this node undo/redo?
export function selectCanUndo(nodeId: string): boolean {
  return (useWorkflowStore.getState().nodeHistory[nodeId]?.past.length ?? 0) > 0
}
export function selectCanRedo(nodeId: string): boolean {
  return (useWorkflowStore.getState().nodeHistory[nodeId]?.future.length ?? 0) > 0
}
