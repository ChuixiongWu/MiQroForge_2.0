// ─── Port / Stream I/O ──────────────────────────────────────────────────────

export type PortCategory =
  | 'physical_quantity'
  | 'software_data_package'
  | 'logic_value'
  | 'report_object'

export interface StreamPort {
  name: string
  display_name: string
  category: PortCategory
  detail: string          // e.g. "orca/gbw-file" or "energy/Ha/scalar"
  required?: boolean
  description?: string
}

// ─── OnBoard Parameter ──────────────────────────────────────────────────────

export type ParamType = 'string' | 'integer' | 'float' | 'boolean' | 'enum' | 'textarea'

export type GateDefault = 'must_pass' | 'warn' | 'ignore'

export interface OnBoardParam {
  name: string
  display_name: string
  type: ParamType
  default?: unknown
  description?: string
  enum_values?: string[]
  min?: number
  max?: number
  unit?: string
  multiple_input?: boolean
}

export interface OnBoardOutput {
  name: string
  display_name: string
  kind: ParamType
  unit?: string
  description?: string
  quality_gate?: boolean
  gate_default?: GateDefault
  gate_description?: string
}

// ─── Resource Spec ──────────────────────────────────────────────────────────

export interface ResourceSpec {
  cpu: number
  memory_gb: number
  gpu: number
  estimated_walltime_hours: number
}

// ─── NodeSpec ───────────────────────────────────────────────────────────────

export type NodeType = 'compute' | 'lightweight'

export interface NodeSpec {
  name: string
  version: string
  display_name: string
  description: string
  node_type: NodeType
  category: string
  software?: string
  base_image_ref?: string
  stream_inputs: StreamPort[]
  stream_outputs: StreamPort[]
  onboard_inputs: OnBoardParam[]
  onboard_outputs: OnBoardOutput[]
  resources?: ResourceSpec
  tags?: string[]
}
