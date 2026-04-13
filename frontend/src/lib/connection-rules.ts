import type { PortCategory, StreamPort } from '../types/nodespec'

// ─── Connection compatibility rules ──────────────────────────────────────────
// Mirrors the logic in nodes/schemas/connection.py
//
// Rules:
// 1. Categories must match (physical_quantity ↔ physical_quantity, etc.)
// 2. For software_data_package: ecosystems must match
//    e.g. "orca/gbw-file" and "orca/xyz-geometry" are compatible (same ecosystem)
//    e.g. "orca/gbw-file" and "gaussian/chk-file" are NOT compatible
// 3. For physical_quantity: unit compatibility is checked where possible (same or unitless)
// 4. logic_value and report_object: any subtype is compatible with same category
// 5. Ephemeral node ports: compatible with ANY category (wildcard)

export type ConnectionError =
  | 'category_mismatch'
  | 'ecosystem_mismatch'
  | 'unit_mismatch'
  | 'direction_mismatch'    // output → output or input → input

export interface ConnectionCheckResult {
  compatible: boolean
  error?: ConnectionError
  warning?: string
}

function extractEcosystem(detail: string): string {
  return detail.split('/')[0] ?? ''
}

function extractUnit(detail: string): string {
  // e.g. "energy/Ha/scalar" → "Ha"
  const parts = detail.split('/')
  return parts[1] ?? ''
}

export function checkPortCompatibility(
  sourcePort: StreamPort,
  targetPort: StreamPort,
): ConnectionCheckResult {
  // Ephemeral wildcard: if either port is from an ephemeral node, always compatible
  if (sourcePort.detail === '__ephemeral__' || targetPort.detail === '__ephemeral__') {
    return { compatible: true }
  }

  // Category must match
  if (sourcePort.category !== targetPort.category) {
    return { compatible: false, error: 'category_mismatch' }
  }

  const cat: PortCategory = sourcePort.category

  if (cat === 'software_data_package') {
    const srcEco = extractEcosystem(sourcePort.detail)
    const tgtEco = extractEcosystem(targetPort.detail)
    if (srcEco && tgtEco && srcEco !== tgtEco) {
      return { compatible: false, error: 'ecosystem_mismatch' }
    }
  }

  if (cat === 'physical_quantity') {
    const srcUnit = extractUnit(sourcePort.detail)
    const tgtUnit = extractUnit(targetPort.detail)
    // If both have explicit units and they differ, warn (not hard error — unit conversion may exist)
    if (srcUnit && tgtUnit && srcUnit !== tgtUnit) {
      return {
        compatible: true,
        warning: `Unit mismatch: ${srcUnit} → ${tgtUnit}. Ensure unit conversion is handled.`,
      }
    }
  }

  // logic_value and report_object: same category = compatible
  return { compatible: true }
}

// ─── React Flow connection validator ─────────────────────────────────────────
// Used in the onConnect / isValidConnection callbacks

export interface PortLookup {
  // node_id → port_name → StreamPort
  outputs: Map<string, Map<string, StreamPort>>
  inputs: Map<string, Map<string, StreamPort>>
}

/** Ephemeral wildcard port — compatible with any category. */
const EPHEMERAL_WILDCARD_PORT: StreamPort = {
  name: '',
  display_name: '',
  category: 'software_data_package' as PortCategory,
  detail: '__ephemeral__',
}

export function buildPortLookup(
  rfNodes: Array<{
    id: string
    data: {
      stream_inputs?: StreamPort[]
      stream_outputs?: StreamPort[]
      ephemeral?: boolean
      ports?: { inputs?: Array<{ name: string; type: string }> | number; outputs?: Array<{ name: string; type: string }> | number }
    }
  }>,
): PortLookup {
  const outputs = new Map<string, Map<string, StreamPort>>()
  const inputs = new Map<string, Map<string, StreamPort>>()

  for (const node of rfNodes) {
    const outMap = new Map<string, StreamPort>()
    const inMap = new Map<string, StreamPort>()

    // Formal nodes: use stream_inputs/stream_outputs directly
    for (const p of node.data.stream_outputs ?? []) outMap.set(p.name, p)
    for (const p of node.data.stream_inputs ?? []) inMap.set(p.name, p)

    // Ephemeral nodes: derive from data.ports (same logic as MFNode.tsx)
    if (outMap.size === 0 && inMap.size === 0 && node.data.ports) {
      const rawPorts = node.data.ports
      const rawInputs = rawPorts.inputs
      const rawOutputs = rawPorts.outputs

      if (Array.isArray(rawInputs)) {
        for (const p of rawInputs) {
          inMap.set(p.name, {
            ...EPHEMERAL_WILDCARD_PORT,
            name: p.name,
            display_name: p.name,
            category: (node.data.ephemeral ? 'software_data_package' : p.type) as PortCategory,
          })
        }
      } else if (typeof rawInputs === 'number') {
        for (let i = 0; i < (rawInputs as number); i++) {
          const name = `I${i + 1}`
          inMap.set(name, { ...EPHEMERAL_WILDCARD_PORT, name, display_name: name })
        }
      }

      if (Array.isArray(rawOutputs)) {
        for (const p of rawOutputs) {
          outMap.set(p.name, {
            ...EPHEMERAL_WILDCARD_PORT,
            name: p.name,
            display_name: p.name,
            category: (node.data.ephemeral ? 'software_data_package' : p.type) as PortCategory,
          })
        }
      } else if (typeof rawOutputs === 'number') {
        for (let i = 0; i < (rawOutputs as number); i++) {
          const name = `O${i + 1}`
          outMap.set(name, { ...EPHEMERAL_WILDCARD_PORT, name, display_name: name })
        }
      }
    }

    outputs.set(node.id, outMap)
    inputs.set(node.id, inMap)
  }

  return { outputs, inputs }
}

export function isValidRFConnection(
  connection: { source: string; sourceHandle: string | null; target: string; targetHandle: string | null },
  lookup: PortLookup,
): boolean {
  if (!connection.sourceHandle || !connection.targetHandle) return false
  const srcPort = lookup.outputs.get(connection.source)?.get(connection.sourceHandle)
  const tgtPort = lookup.inputs.get(connection.target)?.get(connection.targetHandle)
  if (!srcPort || !tgtPort) return false
  return checkPortCompatibility(srcPort, tgtPort).compatible
}
