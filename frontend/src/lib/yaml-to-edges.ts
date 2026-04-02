/**
 * lib/yaml-to-edges.ts — Parse MF YAML connections into React Flow edges
 *
 * After auto-resolve replaces pending nodes with real MFNodes, this utility
 * parses the generated MF YAML to extract port-level connections and builds
 * proper React Flow edges with sourceHandle/targetHandle.
 */

import yaml from 'js-yaml'
import type { Edge as RFEdge } from '@xyflow/react'

/** Minimal shape of the parsed MF YAML we care about. */
interface MFYamlParsed {
  nodes?: Array<{ id: string; nodespec_path: string }>
  connections?: Array<{ from: string; to: string }>
}

/**
 * Build React Flow edges from the MF YAML's `connections` section.
 *
 * Mapping strategy (two-pass):
 *
 * **Primary** — YAML node id IS the semantic step id (step-1, step-2, …):
 *   yaml_id → pendingByStepId.get(yaml_id) → canvas node id
 *
 * **Fallback** — YAML uses descriptive ids (geo-opt, sp, …):
 *   yaml_id → nodespec_path → node name → pool of canvas ids consumed in order.
 *   Each unique node name has a pool of canvas ids (one per resolution that
 *   maps to that node name). YAML nodes are matched to pool entries in
 *   declaration order — fixing the collision where two instances of the same
 *   nodespec_path (e.g. two orca-single-point nodes) both resolved to the last
 *   overwritten entry in a single-value map.
 *
 * @param mfYaml          Raw MF YAML string
 * @param resolutions     Array of { step_id, resolved_node } from ConcretizationResult
 * @param pendingByStepId Map from semantic step_id → canvas RF node id
 * @returns               Array of RFEdge with proper sourceHandle / targetHandle
 */
export function buildResolvedEdges(
  mfYaml: string,
  resolutions: Array<{ step_id: string; resolved_node?: string | null }>,
  pendingByStepId?: Map<string, string>,
): RFEdge[] {
  let parsed: MFYamlParsed
  try {
    parsed = yaml.load(mfYaml) as MFYamlParsed
  } catch {
    console.warn('[yaml-to-edges] Failed to parse MF YAML')
    return []
  }

  if (!parsed?.nodes || !parsed?.connections) return []

  // ── Fallback pool: node_name → [canvasId, …] consumed in declaration order ─
  // Each resolution contributes one canvas id to its node name's pool.
  // Multiple resolutions with the same resolved_node each get their own slot,
  // preventing the "last write wins" collision in the original single-value map.
  const nodeNamePool: Record<string, string[]> = {}
  for (const res of resolutions) {
    if (!res.resolved_node) continue
    const canvasId = pendingByStepId?.get(res.step_id) ?? res.step_id
    ;(nodeNamePool[res.resolved_node] ??= []).push(canvasId)
  }
  const poolConsumed: Record<string, number> = {}

  // ── Resolve each YAML node id → canvas node id ────────────────────────────
  const yamlIdToCanvasId: Record<string, string> = {}

  for (const node of parsed.nodes) {
    // Primary path: YAML Coder uses step-N as the node instance id
    if (pendingByStepId?.has(node.id)) {
      yamlIdToCanvasId[node.id] = pendingByStepId.get(node.id)!
      continue
    }

    // Fallback: derive node name from nodespec_path, consume from pool in order
    if (!node.nodespec_path) continue
    const parts = node.nodespec_path.split('/')
    const idx = parts.lastIndexOf('nodespec.yaml')
    if (idx <= 0) continue
    const nodeName = parts[idx - 1]

    const pool = nodeNamePool[nodeName] ?? []
    const used = poolConsumed[nodeName] ?? 0
    if (used < pool.length) {
      yamlIdToCanvasId[node.id] = pool[used]
      poolConsumed[nodeName] = used + 1
    }
  }

  // ── Build React Flow edges ────────────────────────────────────────────────
  const edges: RFEdge[] = []
  for (const conn of parsed.connections) {
    const dotSrc = conn.from.indexOf('.')
    const dotTgt = conn.to.indexOf('.')
    if (dotSrc < 0 || dotTgt < 0) continue

    const srcYamlId = conn.from.slice(0, dotSrc)
    const srcPort   = conn.from.slice(dotSrc + 1)
    const tgtYamlId = conn.to.slice(0, dotTgt)
    const tgtPort   = conn.to.slice(dotTgt + 1)

    const srcCanvasId = yamlIdToCanvasId[srcYamlId]
    const tgtCanvasId = yamlIdToCanvasId[tgtYamlId]

    if (srcCanvasId && tgtCanvasId && srcPort && tgtPort) {
      edges.push({
        id: `e-${srcCanvasId}.${srcPort}-${tgtCanvasId}.${tgtPort}`,
        source: srcCanvasId,
        sourceHandle: srcPort,
        target: tgtCanvasId,
        targetHandle: tgtPort,
        type: 'mfEdge',
      })
    }
  }

  return edges
}
