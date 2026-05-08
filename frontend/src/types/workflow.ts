// ─── Workflow Node (canvas element) ─────────────────────────────────────────

export interface WorkflowNode {
  id: string
  nodespec_path: string
  nodespec_name: string
  display_name: string
  onboard_params: Record<string, unknown>
  /** Canvas position stored in _ui metadata */
  position?: { x: number; y: number }
  // Phase 2 fields
  ephemeral?: boolean
  description?: string
  ports?: { inputs: Array<{ name: string; type: string }>; outputs: Array<{ name: string; type: string }> }
  node?: string
  nodegen_tmp_ref?: string
  parallel_sweep?: { values: unknown[] }
  sweep_values?: unknown[]
  stream_inputs?: Array<{ name: string; category?: string; display_name?: string }>
  stream_outputs?: Array<{ name: string; category?: string; display_name?: string }>
  onboard_inputs?: Record<string, unknown>[]
  resources?: Record<string, unknown>
  /** Prefab -1 cycle pre-generated node info (stream_io, onboard, resources from nodespec) */
  pregenerate?: Record<string, unknown>
  /** Raw node_generator data (for serialization round-trip) */
  node_generator?: Record<string, unknown>
}

// ─── Connection ──────────────────────────────────────────────────────────────

export interface WorkflowConnection {
  from: string   // "node-id.port-name"
  to: string     // "node-id.port-name"
}

// ─── Workflow Document ───────────────────────────────────────────────────────

export interface WorkflowMeta {
  name: string
  description?: string
  version?: string
  author?: string
}

export interface WorkflowDocument {
  meta: WorkflowMeta
  nodes: WorkflowNode[]
  connections: WorkflowConnection[]
}

// ─── Validation ──────────────────────────────────────────────────────────────

export type IssueSeverity = 'error' | 'warning' | 'info'

export interface ValidationIssue {
  severity: IssueSeverity
  message: string
  node_id?: string
  port?: string
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  infos: ValidationIssue[]
}
