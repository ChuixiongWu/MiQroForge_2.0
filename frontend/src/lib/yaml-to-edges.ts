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
 * The mapping chain:
 *   MF YAML instance id  →  nodespec_path  →  node name  →  step_id (canvas node id)
 *
 * @param mfYaml       Raw MF YAML string
 * @param resolutions  Array of { step_id, resolved_node } from ConcretizationResult
 * @returns            Array of RFEdge with proper sourceHandle / targetHandle
 */
export function buildResolvedEdges(
  mfYaml: string,
  resolutions: Array<{ step_id: string; resolved_node?: string | null }>,
): RFEdge[] {
  let parsed: MFYamlParsed
  try {
    parsed = yaml.load(mfYaml) as MFYamlParsed
  } catch {
    console.warn('[yaml-to-edges] Failed to parse MF YAML')
    return []
  }

  if (!parsed?.nodes || !parsed?.connections) return []

  // 1. MF YAML instance id → node name (extracted from nodespec_path)
  //    e.g. "geo-opt" → "orca-geo-opt"  (from "nodes/chemistry/orca/orca-geo-opt/nodespec.yaml")
  const yamlIdToNodeName: Record<string, string> = {}
  for (const node of parsed.nodes) {
    if (!node.nodespec_path) continue
    const parts = node.nodespec_path.split('/')
    // The directory just before "nodespec.yaml" is the node name
    const idx = parts.lastIndexOf('nodespec.yaml')
    if (idx > 0) {
      yamlIdToNodeName[node.id] = parts[idx - 1]
    }
  }

  // 2. node name → canvas node id (= step_id from resolutions)
  //    e.g. "orca-geo-opt" → "step-1"
  const nodeNameToCanvasId: Record<string, string> = {}
  for (const res of resolutions) {
    if (res.resolved_node) {
      nodeNameToCanvasId[res.resolved_node] = res.step_id
    }
  }

  // 3. Build edges
  const edges: RFEdge[] = []
  for (const conn of parsed.connections) {
    const dotSrc = conn.from.indexOf('.')
    const dotTgt = conn.to.indexOf('.')
    if (dotSrc < 0 || dotTgt < 0) continue

    const srcYamlId = conn.from.slice(0, dotSrc)
    const srcPort   = conn.from.slice(dotSrc + 1)
    const tgtYamlId = conn.to.slice(0, dotTgt)
    const tgtPort   = conn.to.slice(dotTgt + 1)

    const srcNodeName = yamlIdToNodeName[srcYamlId]
    const tgtNodeName = yamlIdToNodeName[tgtYamlId]
    const srcCanvasId = srcNodeName ? nodeNameToCanvasId[srcNodeName] : undefined
    const tgtCanvasId = tgtNodeName ? nodeNameToCanvasId[tgtNodeName] : undefined

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
