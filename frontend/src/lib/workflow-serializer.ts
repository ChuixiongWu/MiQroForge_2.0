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
    if (n.data.onboard_inputs) wfNode.onboard_inputs = n.data.onboard_inputs
    if (n.data.resources) wfNode.resources = n.data.resources
    // Pass through node_generator for nodegen serialization detection
    if (n.data.node_generator) wfNode.node_generator = n.data.node_generator
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
  // _ui is intentionally omitted — canvas position is UI-only metadata,
  // stored in canvas.json / localStorage, not in the reproducible MF YAML.
  const yamlObj: Record<string, unknown> = {
    mf_version: '1.0',
    name: doc.meta.name,
    description: doc.meta.description ?? '',
    nodes: doc.nodes.map((n) => {
      const nodeObj: Record<string, unknown> = {
        id: n.id,
        onboard_params: n.onboard_params,
      }
      const extra = n as unknown as Record<string, unknown>
      // Nodegen: a node from "Generate Node" drag always has node_generator
      const nodeGenerator = extra.node_generator as Record<string, unknown> | undefined
      const nodegenResult = (nodeGenerator?.result ?? {}) as Record<string, unknown>
      const hasNodegenResult = !!nodegenResult.nodespec_yaml
      const hasNodeGenerator = !!nodeGenerator
      // Nodegen nodes: ALWAYS ephemeral + nodegen_tmp_ref → calls /api/v1/agents/node/run
      //   no result → nodegen_tmp_ref="" → Agent generates from scratch at runtime
      //   has result → nodegen_tmp_ref="<name>" → Agent uses pre-generated as reference
      // Plain ephemeral nodes (palette drag): ephemeral → calls /api/v1/agents/ephemeral
      const isEphemeral = !!extra.ephemeral || hasNodeGenerator
      const isSweep = !!extra.parallel_sweep
      if (!isEphemeral) {
        nodeObj.node = (extra.node as string) || n.nodespec_name
          || n.nodespec_path?.split('/').slice(-2, -1)[0]
      }
      if (isSweep) {
        nodeObj.parallel_sweep = extra.parallel_sweep
      }
      if (isEphemeral) {
        nodeObj.ephemeral = true
        if (hasNodeGenerator) {
          // Always use canvas node ID (n.id) as nodegen_tmp_ref — unique per canvas
          // instance, avoids collisions when multiple prefab nodes share the same
          // generated node name.  API uses it as work-dir under tmp/ so generated
          // nodespec.yaml / run.sh are always persisted for after-run canvas updates.
          nodeObj.nodegen_tmp_ref = n.id as string
          // Build pregenerate key: -1 cycle parsed nodespec info for compiler/runtime port resolution
          if (hasNodegenResult) {
            const pg: Record<string, unknown> = {}
            if (extra.stream_inputs) pg.stream_inputs = extra.stream_inputs
            if (extra.stream_outputs) pg.stream_outputs = extra.stream_outputs
            if (extra.onboard_inputs) pg.onboard_inputs = extra.onboard_inputs
            if (extra.resources) pg.resources = extra.resources
            nodeObj.pregenerate = pg
          }
        }
        // Derive ports from stored ports or stream I/O
        const rawPorts = extra.ports as Record<string, unknown> | undefined
        if (rawPorts && Array.isArray(rawPorts.inputs)) {
          nodeObj.ports = {
            inputs: (rawPorts.inputs as unknown[]).length,
            outputs: (rawPorts.outputs as unknown[]).length,
          }
        } else if (rawPorts && typeof rawPorts.inputs === 'number') {
          nodeObj.ports = rawPorts
        } else {
          const nIn = ((extra.stream_inputs as unknown[]) ?? []).length
          const nOut = ((extra.stream_outputs as unknown[]) ?? []).length
          if (nIn || nOut) {
            nodeObj.ports = { inputs: nIn, outputs: nOut }
          }
        }
        // Use user's generation description and software from node_generator
        const genDesc = (nodeGenerator?.description as string) || ''
        const genSoftware = (nodeGenerator?.software as string) || ''
        const desc = genDesc || (extra.ephemeral_description as string) || (extra.description as string) || ''
        const params = { ...(nodeObj.onboard_params as Record<string, unknown>) }
        let paramsModified = false
        if (desc) {
          params.description = desc
          paramsModified = true
        }
        if (genSoftware) {
          params._software = genSoftware
          paramsModified = true
        }
        if (paramsModified) {
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
  nodegen_tmp_ref?: string
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
    if (n.ports) {
      // Normalize: new int-count format {inputs: N, outputs: N} → generate port name lists
      // for the frontend (MFNode expects arrays of {name, type})
      const rawPorts = n.ports as Record<string, unknown>
      if (typeof rawPorts.inputs === 'number' || typeof rawPorts.outputs === 'number') {
        const numIn = (rawPorts.inputs as number) ?? 0
        const numOut = (rawPorts.outputs as number) ?? 0
        wfNode.ports = {
          inputs: Array.from({ length: numIn }, (_, i) => ({ name: `I${i + 1}`, type: 'software_data_package' })),
          outputs: Array.from({ length: numOut }, (_, i) => ({ name: `O${i + 1}`, type: 'software_data_package' })),
        }
      } else {
        wfNode.ports = n.ports
      }
    }
    if (n.node) wfNode.node = n.node
    if (n.nodegen_tmp_ref) wfNode.nodegen_tmp_ref = n.nodegen_tmp_ref
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

export function connectionToRFEdge(
  conn: WorkflowConnection,
  sourceOutputs?: Array<{ name: string; category: string }>,
): RFEdge {
  const [sourceNode, sourceHandle] = conn.from.split('.')
  const [targetNode, targetHandle] = conn.to.split('.')
  const formalPort = sourceOutputs?.find((p) => p.name === sourceHandle)
  return {
    id: `e-${conn.from}-${conn.to}`,
    source: sourceNode,
    sourceHandle,
    target: targetNode,
    targetHandle,
    type: 'mfEdge',
    data: formalPort
      ? { sourcePort: { name: formalPort.name, category: formalPort.category } }
      : undefined,
  }
}
