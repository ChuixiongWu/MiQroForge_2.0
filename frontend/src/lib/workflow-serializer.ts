import yaml from 'js-yaml'
import type { Node as RFNode, Edge as RFEdge } from '@xyflow/react'
import type { WorkflowDocument, WorkflowNode, WorkflowConnection, WorkflowMeta } from '../types/workflow'
import type { MFNodeData } from '../stores/workflow-store'

// ─── React Flow state → MF YAML ──────────────────────────────────────────────

export function rfStateToWorkflowDoc(
  rfNodes: RFNode<MFNodeData>[],
  rfEdges: RFEdge[],
  meta: WorkflowMeta,
): WorkflowDocument {
  const nodes: WorkflowNode[] = rfNodes.map((n) => ({
    id: n.id,
    nodespec_path: n.data.nodespec_path,
    nodespec_name: n.data.name,
    display_name: n.data.display_name,
    onboard_params: n.data.onboard_params,
    position: n.position,
  }))

  const connections: WorkflowConnection[] = rfEdges.map((e) => ({
    from: `${e.source}.${e.sourceHandle}`,
    to: `${e.target}.${e.targetHandle}`,
  }))

  return { meta, nodes, connections }
}

export function workflowDocToYaml(doc: WorkflowDocument): string {
  // Build flat top-level structure that matches backend MFWorkflow model:
  //   name / description / mf_version / nodes / connections
  // _ui position metadata stored per-node is ignored by Pydantic (extra="ignore")
  const yamlObj: Record<string, unknown> = {
    mf_version: '1.0',
    name: doc.meta.name,
    description: doc.meta.description ?? '',
    nodes: doc.nodes.map((n) => {
      const nodeObj: Record<string, unknown> = {
        id: n.id,
        nodespec_path: n.nodespec_path,
        onboard_params: n.onboard_params,
      }
      if (n.position) {
        nodeObj._ui = { position: n.position }
      }
      return nodeObj
    }),
    connections: doc.connections.map((c) => ({ from: c.from, to: c.to })),
  }
  return yaml.dump(yamlObj, { lineWidth: 120, noRefs: true })
}

// ─── MF YAML → React Flow state ──────────────────────────────────────────────

interface ParsedYamlNode {
  id: string
  nodespec_path: string
  onboard_params?: Record<string, unknown>
  _ui?: { position?: { x: number; y: number } }
}

interface ParsedYamlConnection {
  from: string
  to: string
}

interface ParsedYamlDoc {
  // flat format (MFWorkflow-compatible, used for API calls)
  name?: string
  description?: string
  mf_version?: string
  // legacy meta-wrapper format (kept for import back-compat)
  meta?: WorkflowMeta
  nodes?: ParsedYamlNode[]
  connections?: ParsedYamlConnection[]
}

export interface ParsedWorkflow {
  meta: WorkflowMeta
  nodes: WorkflowNode[]
  connections: WorkflowConnection[]
}

export function parseWorkflowYaml(yamlStr: string): ParsedWorkflow {
  const doc = yaml.load(yamlStr) as ParsedYamlDoc

  // Support both flat format (MFWorkflow) and legacy meta-wrapper format
  const meta: WorkflowMeta = doc?.meta ?? {
    name: doc?.name ?? 'Untitled Workflow',
    description: doc?.description,
  }

  const nodes: WorkflowNode[] = (doc?.nodes ?? []).map((n, idx) => ({
    id: n.id ?? `node-${idx}`,
    nodespec_path: n.nodespec_path ?? '',
    nodespec_name: n.nodespec_path?.split('/').slice(-2, -1)[0] ?? n.id,
    display_name: n.id,
    onboard_params: n.onboard_params ?? {},
    position: n._ui?.position ?? autoLayout(idx, (doc?.nodes ?? []).length),
  }))

  const connections: WorkflowConnection[] = (doc?.connections ?? []).map((c) => ({
    from: c.from,
    to: c.to,
  }))

  return { meta, nodes, connections }
}

// ─── Auto-layout helper ───────────────────────────────────────────────────────
// Simple left-to-right layout for nodes loaded from YAML without position info

function autoLayout(index: number, total: number): { x: number; y: number } {
  const cols = Math.ceil(Math.sqrt(total))
  const col = index % cols
  const row = Math.floor(index / cols)
  return {
    x: 100 + col * 340,
    y: 100 + row * 220,
  }
}

// ─── WorkflowNode → React Flow Node ──────────────────────────────────────────

export function workflowNodeToRF(
  wfNode: WorkflowNode,
  nodespecData: Partial<MFNodeData>,
): RFNode<MFNodeData> {
  return {
    id: wfNode.id,
    type: 'mfNode',
    position: wfNode.position ?? { x: 100, y: 100 },
    data: {
      ...nodespecData,
      nodespec_path: wfNode.nodespec_path,
      onboard_params: wfNode.onboard_params,
    } as MFNodeData,
  }
}

// ─── WorkflowConnection → React Flow Edge ────────────────────────────────────

export function connectionToRFEdge(conn: WorkflowConnection): RFEdge {
  const [sourceNode, sourceHandle] = conn.from.split('.')
  const [targetNode, targetHandle] = conn.to.split('.')
  return {
    id: `e-${conn.from}-${conn.to}`,
    source: sourceNode,
    sourceHandle,
    target: targetNode,
    targetHandle,
    type: 'mfEdge',
  }
}
