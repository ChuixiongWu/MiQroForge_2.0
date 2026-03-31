/**
 * lib/semantic-to-canvas.ts — 语义工作流 → React Flow 画布状态
 *
 * 将 Planner 输出的 SemanticWorkflow 转换为 React Flow 节点 + 边，
 * 节点为 ❓ PendingNodeCard，边为虚线琥珀色语义边。
 */

import type { Node as RFNode, Edge as RFEdge } from '@xyflow/react'
import type { SemanticWorkflow } from '../types/semantic'
import type { MFNodeData } from '../stores/workflow-store'

// 语义边类型标记
export const SEMANTIC_EDGE_TYPE = 'semanticEdge'

const LAYOUT_SPACING_X = 280
const LAYOUT_SPACING_Y = 160
const LAYOUT_ORIGIN_X = 100
const LAYOUT_ORIGIN_Y = 100

/**
 * 将 SemanticWorkflow 映射为 React Flow 画布状态。
 *
 * 每个 SemanticStep → PendingNodeCard (pending=true)
 * 每个 SemanticEdge → 虚线琥珀色 animated 边
 */
export function semanticWorkflowToCanvasState(
  sw: SemanticWorkflow,
  onSelectImplementation: (stepId: string, nodeName: string) => void,
): { nodes: RFNode<MFNodeData>[], edges: RFEdge[] } {
  if (!sw.steps || sw.steps.length === 0) {
    return { nodes: [], edges: [] }
  }

  // ─── 简单拓扑排序确定布局位置 ─────────────────────────────────────────────
  const positions = _computePositions(sw)

  // ─── 节点 ──────────────────────────────────────────────────────────────────
  const nodes: RFNode<MFNodeData>[] = sw.steps.map((step) => {
    const pos = positions[step.id] ?? { x: LAYOUT_ORIGIN_X, y: LAYOUT_ORIGIN_Y }
    const implementations = sw.available_implementations[step.id] ?? []

    return {
      id: step.id,
      type: 'mfNode',
      position: pos,
      data: {
        // PendingNodeCard 专用字段
        pending: true,
        name: step.id,
        version: '?',
        display_name: step.display_name,
        description: step.description ?? '',
        node_type: 'compute',
        category: '',
        nodespec_path: '',
        stream_inputs: [],
        stream_outputs: [],
        onboard_inputs: [],
        onboard_outputs: [],
        onboard_params: {},
        // 语义扩展字段
        pending_step_id: step.id,
        semantic_type: step.semantic_type,
        semantic_description: step.description,
        semantic_rationale: step.rationale,
        // 供 PendingNodeCard 使用
        pending_implementations: implementations.map((name) => ({
          nodeName: name,
          label: name,
          software: name.split('-')[0]?.toUpperCase() ?? name,
        })),
        pending_on_select: (nodeName: string) => onSelectImplementation(step.id, nodeName),
      },
    }
  })

  // ─── 边 ────────────────────────────────────────────────────────────────────
  const edges: RFEdge[] = sw.edges.map((edge, i) => ({
    id: `sem-edge-${i}-${edge.from_step}-${edge.to_step}`,
    source: edge.from_step,
    target: edge.to_step,
    type: SEMANTIC_EDGE_TYPE,
    animated: true,
    label: edge.data_description ?? '',
    style: {
      stroke: '#92400e',
      strokeWidth: 2,
      strokeDasharray: '6 4',
    },
    labelStyle: {
      fill: '#b45309',
      fontSize: 10,
    },
  }))

  return { nodes, edges }
}

// ─── 简单层级布局 ──────────────────────────────────────────────────────────────

function _computePositions(sw: SemanticWorkflow): Record<string, { x: number; y: number }> {
  // 计算每个节点的"层级"（入度为0的在第0层）
  const stepIds = sw.steps.map((s) => s.id)
  const inDegree: Record<string, number> = Object.fromEntries(stepIds.map((id) => [id, 0]))
  const children: Record<string, string[]> = Object.fromEntries(stepIds.map((id) => [id, []]))

  for (const edge of sw.edges) {
    if (edge.to_step in inDegree) inDegree[edge.to_step]++
    if (edge.from_step in children) children[edge.from_step].push(edge.to_step)
  }

  const layers: string[][] = []
  const queue = stepIds.filter((id) => inDegree[id] === 0)
  const placed = new Set<string>()

  while (queue.length > 0) {
    const layer: string[] = []
    const nextQueue: string[] = []
    for (const id of queue) {
      if (placed.has(id)) continue
      layer.push(id)
      placed.add(id)
      for (const child of children[id]) {
        inDegree[child]--
        if (inDegree[child] === 0) nextQueue.push(child)
      }
    }
    layers.push(layer)
    queue.length = 0
    queue.push(...nextQueue)
  }

  // 未被分配的节点加到最后一层
  for (const id of stepIds) {
    if (!placed.has(id)) {
      if (layers.length === 0) layers.push([])
      layers[layers.length - 1].push(id)
    }
  }

  const positions: Record<string, { x: number; y: number }> = {}
  layers.forEach((layer, layerIdx) => {
    layer.forEach((id, nodeIdx) => {
      const totalHeight = layer.length * LAYOUT_SPACING_Y
      const startY = LAYOUT_ORIGIN_Y - totalHeight / 2 + LAYOUT_SPACING_Y / 2
      positions[id] = {
        x: LAYOUT_ORIGIN_X + layerIdx * LAYOUT_SPACING_X,
        y: startY + nodeIdx * LAYOUT_SPACING_Y,
      }
    })
  })

  return positions
}
