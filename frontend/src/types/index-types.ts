// ─── Node Index API types ─────────────────────────────────────────────────────

import type { PortCategory } from './nodespec'

export interface PortSummaryResponse {
  name: string
  display_name: string
  category: PortCategory
  detail: string
  direction: 'input' | 'output'
}

export interface OnBoardParamResponse {
  name: string
  display_name: string
  kind: 'string' | 'integer' | 'float' | 'boolean' | 'enum' | 'textarea'
  default?: unknown
  description?: string
  allowed_values?: string[]
  min_value?: number
  max_value?: number
  unit?: string
}

export interface OnBoardOutputResponse {
  name: string
  display_name: string
  kind: 'string' | 'integer' | 'float' | 'boolean' | 'enum' | 'textarea'
  unit?: string
  description: string
  quality_gate: boolean
  gate_default: 'must_pass' | 'warn' | 'ignore'
  gate_description: string
}

export interface NodeSummaryResponse {
  name: string
  version: string
  display_name: string
  description: string
  node_type: string
  category: string
  semantic_type?: string
  semantic_display_name?: string
  software?: string
  keywords: string[]
  resources_cpu: number
  resources_memory_gb: number
  stream_inputs: PortSummaryResponse[]
  stream_outputs: PortSummaryResponse[]
  onboard_inputs_count: number
  onboard_outputs_count: number
}

export interface NodeDetailResponse extends NodeSummaryResponse {
  base_image_ref?: string
  nodespec_path: string
  methods: string[]
  domains: string[]
  capabilities: string[]
  onboard_inputs: OnBoardParamResponse[]
  onboard_outputs: OnBoardOutputResponse[]
}

export interface NodeListResponse {
  total: number
  nodes: NodeSummaryResponse[]
}

export interface NodeIndexInfoResponse {
  generated_at: string
  mf_version: string
  total_nodes: number
  last_scan_duration_ms?: number
}

// ─── Semantic Registry types ──────────────────────────────────────────────────

export interface SemanticTypeEntry {
  display_name: string
  description: string
  domain: string
}

export interface SemanticRegistryResponse {
  version: string
  types: Record<string, SemanticTypeEntry>
}

// ─── Workflow API types ───────────────────────────────────────────────────────

export interface ValidationIssueResponse {
  location: string
  message: string
}

export interface WorkflowValidateResponse {
  valid: boolean
  errors: ValidationIssueResponse[]
  warnings: ValidationIssueResponse[]
  infos: ValidationIssueResponse[]
  resolved_nodes: Record<string, { name: string; version: string; node_type: string }>
}

export interface WorkflowCompileResponse {
  valid: boolean
  argo_yaml: string
  error_count: number
  warning_count: number
  issues: Array<{
    severity: string
    message: string
  }>
}

export interface WorkflowSubmitResponse {
  workflow_name: string
  namespace: string
  submitted_at: string
}

// ─── Runs API types ───────────────────────────────────────────────────────────

export type RunPhase =
  | 'Pending'
  | 'Running'
  | 'Succeeded'
  | 'Failed'
  | 'Error'
  | 'Unknown'
  // Individual node was skipped because a `when` condition evaluated to false
  | 'Omitted'
  // Workflow-level synthetic phase: Argo reported Succeeded, but ≥1 node was
  // Omitted (downstream step blocked by a failed quality gate)
  | 'PartialSuccess'

export interface RunSummaryResponse {
  name: string
  namespace: string
  phase: RunPhase
  started_at?: string
  finished_at?: string
  duration_seconds?: number
  message?: string
}

export interface RunListResponse {
  total: number
  runs: RunSummaryResponse[]
}

export interface RunDetailResponse {
  name: string
  namespace: string
  phase: RunPhase
  // Full raw Argo workflow object returned by the backend
  raw: Record<string, unknown>
}

export interface RunLogsResponse {
  workflow_name: string
  node_id?: string
  logs: string
}

// ─── Files API types ──────────────────────────────────────────────────────────

export interface FileEntry {
  name: string
  size_bytes: number
  modified_at: string
}

export interface FileListResponse {
  files: FileEntry[]
}
