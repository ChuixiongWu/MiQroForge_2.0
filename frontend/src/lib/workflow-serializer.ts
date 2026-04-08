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
  const nodes: WorkflowNode[] = rfNodes.map((n) => {
    const wfNode: WorkflowNode & Record<string, unknown> = {
      id: n.id,
      nodespec_path: n.data.nodespec_path,
      nodespec_name: n.data.name,
      display_name: n.data.display_name,
      onboard_params: n.data.onboard_params,
      position: n.position,
    }
    // Pass through optional Phase 2 fields (parallel_sweep, ephemeral, ports, node, description)
    if (n.data.parallel_sweep) wfNode.parallel_sweep = n.data.parallel_sweep
    if (n.data.ephemeral) wfNode.ephemeral = n.data.ephemeral
    if (n.data.ports) wfNode.ports = n.data.ports
    if (n.data.node) wfNode.node = n.data.node
    if (n.data.ephemeral_description) wfNode.description = n.data.ephemeral_description

    // Auto-detect multiple_input params → generate parallel_sweep + {{item}} template
    if (n.data.sweep_values?.length) {
      // Template mode: sweep_values stored separately, pattern already in onboard_params
      wfNode.parallel_sweep = { values: n.data.sweep_values }
    } else {
      // Legacy fallback: detect array in onboard_params → parallel_sweep + {{item}}
      const sweepInput = n.data.onboard_inputs?.find(
        (inp) => inp.multiple_input && Array.isArray(n.data.onboard_params?.[inp.name]),
      )
      if (sweepInput && !wfNode.parallel_sweep) {
        const values = n.data.onboard_params[sweepInput.name] as unknown[]
        wfNode.parallel_sweep = { values }
        // Replace the array value with {{item}} template in onboard_params
        const params = { ...(wfNode.onboard_params as Record<string, unknown>) }
        params[sweepInput.name] = `{{item}}`
        wfNode.onboard_params = params
      }
    }
    // Pass through stream I/O so workflowDocToYaml can derive ephemeral ports
    if (n.data.stream_inputs) wfNode.stream_inputs = n.data.stream_inputs
    if (n.data.stream_outputs) wfNode.stream_outputs = n.data.stream_outputs
    return wfNode
  })

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
        onboard_params: n.onboard_params,
      }
      // Only include nodespec_path for non-ephemeral nodes
      const extra = n as unknown as Record<string, unknown>
      const isEphemeral = !!extra.ephemeral
      const isSweep = !!extra.parallel_sweep
      if (n.position) {
        nodeObj._ui = { position: n.position }
      }
      // Unified: all non-ephemeral nodes use 'node' field (not nodespec_path)
      // Backend MFWorkflow validates node XOR nodespec_path — cannot have both
      if (!isEphemeral) {
        nodeObj.node = (extra.node as string) || n.nodespec_name
          || n.nodespec_path?.split('/').slice(-2, -1)[0]
      }
      if (isSweep) {
        nodeObj.parallel_sweep = extra.parallel_sweep
      }
      if (isEphemeral) {
        nodeObj.ephemeral = true
        // Derive ports from stream_inputs/stream_outputs if no explicit ports
        if (extra.ports) {
          nodeObj.ports = extra.ports
        } else {
          const toPort = (p: { name: string; category?: string; detail?: string }) => ({
            name: p.name,
            type: p.category ?? 'physical_quantity',
          })
          const inputs = ((extra.stream_inputs as Array<{ name: string; category?: string }>) ?? []).map(toPort)
          const outputs = ((extra.stream_outputs as Array<{ name: string; category?: string }>) ?? []).map(toPort)
          if (inputs.length || outputs.length) {
            nodeObj.ports = { inputs, outputs }
          }
        }
        // Write ephemeral_description into both description and onboard_params.description
        const desc = (extra.ephemeral_description as string) || (extra.description as string) || ''
        if (desc) {
          nodeObj.description = desc
          // Ensure onboard_params exists and has description
          const params = (nodeObj.onboard_params as Record<string, unknown>) ?? {}
          params.description = desc
          nodeObj.onboard_params = params
        }
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
  // Ephemeral fields
  ephemeral?: boolean
  description?: string
  ports?: { inputs: Array<{ name: string; type: string }>; outputs: Array<{ name: string; type: string }> }
  node?: string
  // Sweep fields
  parallel_sweep?: { values: unknown[] }
  // Stream IO (for deriving ephemeral ports)
  stream_inputs?: Array<{ name: string; category?: string; display_name?: string }>
  stream_outputs?: Array<{ name: string; category?: string; display_name?: string }>
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

  const nodes: WorkflowNode[] = (doc?.nodes ?? []).map((n, idx) => {
    const wfNode: WorkflowNode & Record<string, unknown> = {
      id: n.id ?? `node-${idx}`,
      nodespec_path: n.nodespec_path ?? '',
      nodespec_name: n.nodespec_path?.split('/').slice(-2, -1)[0] ?? n.id,
      display_name: n.id,
      onboard_params: n.onboard_params ?? {},
      position: n._ui?.position ?? autoLayout(idx, (doc?.nodes ?? []).length),
    }
    // Pass through ephemeral fields
    if (n.ephemeral) {
      wfNode.ephemeral = n.ephemeral
      // Prefer onboard_params.description over top-level description
      wfNode.description = (n.onboard_params?.description as string) ?? n.description ?? ''
    }
    if (n.ports) wfNode.ports = n.ports
    if (n.node) wfNode.node = n.node
    if (n.parallel_sweep) wfNode.parallel_sweep = n.parallel_sweep
    if (n.stream_inputs) wfNode.stream_inputs = n.stream_inputs
    if (n.stream_outputs) wfNode.stream_outputs = n.stream_outputs
    return wfNode
  })

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
  const data: Record<string, unknown> = {
    ...nodespecData,
    nodespec_path: wfNode.nodespec_path,
    onboard_params: wfNode.onboard_params,
  }
  // Pass through Phase 2 fields from parsed YAML
  if (wfNode.ephemeral) data.ephemeral = wfNode.ephemeral
  if (wfNode.description) data.ephemeral_description = wfNode.description
  if (wfNode.ports) data.ports = wfNode.ports
  if (wfNode.parallel_sweep) {
    data.parallel_sweep = wfNode.parallel_sweep
    // If onboard_params contains {{item}} template, restore sweep_values for UI display
    const hasTemplate = Object.values(wfNode.onboard_params ?? {}).some(
      (v) => typeof v === 'string' && v.includes('{{item}}'),
    )
    if (hasTemplate) {
      data.sweep_values = wfNode.parallel_sweep.values
    }
  }
  if (wfNode.node) data.node = wfNode.node
  if (wfNode.stream_inputs) data.stream_inputs = wfNode.stream_inputs
  if (wfNode.stream_outputs) data.stream_outputs = wfNode.stream_outputs

  return {
    id: wfNode.id,
    type: 'mfNode',
    position: wfNode.position ?? { x: 100, y: 100 },
    data: data as MFNodeData,
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
