// ─── Workflow Node (canvas element) ─────────────────────────────────────────

export interface WorkflowNode {
  id: string
  nodespec_path: string
  nodespec_name: string
  display_name: string
  onboard_params: Record<string, unknown>
  /** Canvas position stored in _ui metadata */
  position?: { x: number; y: number }
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
