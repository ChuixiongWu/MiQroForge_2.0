/**
 * types/semantic.ts — Phase 2 Agent 层的 TypeScript 类型定义
 * 对应 agents/schemas.py 中的 Python 数据模型
 */

// ─── Planner Agent 输出 ──────────────────────────────────────────────────────

export interface SemanticStep {
  id: string                               // 'step-1', 'step-2', ...
  semantic_type: string                    // 对应 semantic_registry.yaml 中的类型键
  display_name: string                     // 前端显示名称
  description?: string
  rationale?: string                       // Planner 选择此步骤的理由
  constraints: Record<string, string>      // 对 YAML Coder 的约束提示
}

export interface SemanticEdge {
  from_step: string
  to_step: string
  data_description?: string
}

export interface SemanticWorkflow {
  name?: string
  description?: string
  target_molecule?: string
  steps: SemanticStep[]
  edges: SemanticEdge[]
  planner_notes?: string
  available_implementations: Record<string, string[]>  // step_id → [node_name...]
}

// ─── YAML Coder Agent 输出 ────────────────────────────────────────────────────

export interface NodeResolution {
  step_id: string
  resolved_node: string | null
  resolved_nodespec_path: string | null
  onboard_params: Record<string, unknown>
  needs_new_node: boolean
  new_node_request: string | null
}

export interface ConcretizationResult {
  resolutions: NodeResolution[]
  mf_yaml: string
  missing_nodes: string[]
  validation_passed: boolean
  validation_errors: string[]
  evaluation: EvaluationResult | null
}

// ─── Generator-Evaluator ─────────────────────────────────────────────────────

export interface EvaluationResult {
  passed: boolean
  issues: string[]
  suggestions: string[]
  iteration: number
}

// ─── API Request/Response ─────────────────────────────────────────────────────

export interface PlanRequest {
  intent: string
  molecule?: string
  preferences?: string
  session_id?: string
}

export interface PlanResponse {
  semantic_workflow: SemanticWorkflow
  evaluation: EvaluationResult | null
  available_nodes: Record<string, string[]>
  error: string | null
}

export interface YAMLRequest {
  semantic_workflow: SemanticWorkflow
  user_params?: Record<string, unknown>
  selected_implementations?: Record<string, string>
  session_id?: string
}

export interface YAMLResponse {
  mf_yaml: string
  validation_report: {
    valid: boolean
    errors: string[]
    warnings: string[]
  }
  result: ConcretizationResult | null
  error: string | null
}

export interface NodeGenRequest {
  semantic_type: string
  description: string
  target_software?: string
  target_method?: string
  category?: string
}

export interface NodeGenResponse {
  node_name: string
  nodespec_yaml: string
  run_sh?: string
  input_templates: Record<string, string>
  saved_path?: string
  evaluation: EvaluationResult | null
  error: string | null
}

// ─── Chat / Agent UI ─────────────────────────────────────────────────────────

export type ChatMessageRole = 'user' | 'agent' | 'system' | 'error'

export interface ChatMessage {
  id: string
  role: ChatMessageRole
  content: string
  timestamp: number
  semantic_workflow?: SemanticWorkflow   // 内嵌工作流卡片
  yaml_result?: YAMLResponse             // 内嵌 YAML 结果
  loading?: boolean
}

export type AgentStatus = 'idle' | 'planning' | 'generating_yaml' | 'generating_node' | 'error'
