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

  // Actions
  setMeta: (meta: Partial<WorkflowMeta>) => void
  onNodesChange: (changes: NodeChange<RFNode<MFNodeData>>[]) => void
  onEdgesChange: (changes: EdgeChange[]) => void
  onConnect: (connection: Connection) => void
  addNode: (node: RFNode<MFNodeData>) => void
  removeNode: (nodeId: string) => void
  updateNodeParams: (nodeId: string, params: Record<string, unknown>) => void

  // Implementation undo/redo
  updateNodeWithHistory: (nodeId: string, newData: MFNodeData) => void
  undoNode: (nodeId: string) => void
  redoNode: (nodeId: string) => void

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

// ─── Store implementation ─────────────────────────────────────────────────────

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, _get) => ({
      meta: { name: 'Untitled Workflow', description: '', version: '1.0.0' },
      nodes: [],
      edges: [],
      nodeHistory: {},
      validationResult: null,
      isValidating: false,

      setMeta: (partial) =>
        set((s) => ({ meta: { ...s.meta, ...partial } })),

      onNodesChange: (changes) =>
        set((s) => ({ nodes: applyNodeChanges(changes, s.nodes) })),

      onEdgesChange: (changes) =>
        set((s) => ({ edges: applyEdgeChanges(changes, s.edges) })),

      onConnect: (connection) =>
        set((s) => ({
          edges: [
            ...s.edges,
            {
              ...connection,
              id: `e-${connection.source}.${connection.sourceHandle}-${connection.target}.${connection.targetHandle}`,
              type: 'mfEdge',
            } as RFEdge,
          ],
        })),

      addNode: (node) =>
        set((s) => ({ nodes: [...s.nodes, node] })),

      removeNode: (nodeId) =>
        set((s) => {
          const { [nodeId]: _dropped, ...restHistory } = s.nodeHistory
          return {
            nodes: s.nodes.filter((n) => n.id !== nodeId),
            edges: s.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
            nodeHistory: restHistory,
          }
        }),

      updateNodeParams: (nodeId, params) =>
        set((s) => ({
          nodes: s.nodes.map((n) =>
            n.id === nodeId
              ? { ...n, data: { ...n.data, onboard_params: { ...n.data.onboard_params, ...params } } }
              : n,
          ),
        })),

      // ── Implementation history actions ──────────────────────────────────────

      updateNodeWithHistory: (nodeId, newData) =>
        set((s) => {
          const currentNode = s.nodes.find((n) => n.id === nodeId)
          if (!currentNode) return {}
          const hist = s.nodeHistory[nodeId] ?? { past: [], future: [] }
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

      loadFromNodes: (nodes, edges) =>
        set({ nodes, edges, nodeHistory: {}, validationResult: null }),

      clearCanvas: () =>
        set({
          nodes: [],
          edges: [],
          nodeHistory: {},
          meta: { name: 'Untitled Workflow', description: '', version: '1.0.0' },
          validationResult: null,
        }),
    }),
    {
      name: 'mf-canvas-v1',
      storage: createJSONStorage(() => localStorage),
      // 只持久化画布内容（nodes/edges/meta），运行时状态不存
      partialize: (state) => ({
        meta: state.meta,
        nodes: state.nodes.map(_stripCallbacks),
        edges: state.edges,
      }),
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
