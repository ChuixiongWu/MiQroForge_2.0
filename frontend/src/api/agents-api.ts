/**
 * api/agents-api.ts — Agent API 客户端
 */

import type {
  PlanRequest, PlanResponse,
  YAMLRequest, YAMLResponse,
  NodeGenRequest, NodeGenResponse,
  NodeRunRequest,
  NodeAcceptRequest, NodeAcceptResponse,
} from '../types/semantic'
import { postJSON } from './client'

export interface SaveSessionRequest {
  session_id: string
  messages: object[]
}

export interface SaveSessionResponse {
  saved: boolean
  session_id: string
  path: string
  message_count: number
}

export const agentsApi = {
  /** Planner Agent — 意图 → 语义工作流 */
  plan: (req: PlanRequest, signal?: AbortSignal): Promise<PlanResponse> =>
    postJSON<PlanResponse>(`/agents/plan`, req, signal),

  /** YAML Coder Agent — 语义工作流 → MF YAML */
  generateYaml: (req: YAMLRequest, signal?: AbortSignal): Promise<YAMLResponse> =>
    postJSON<YAMLResponse>(`/agents/yaml`, req, signal),

  /** Node Generator Agent — 设计时生成节点（无 sandbox） */
  generateNode: (req: NodeGenRequest, signal?: AbortSignal): Promise<NodeGenResponse> =>
    postJSON<NodeGenResponse>(`/agents/node`, req, signal),

  /** Node Generator Agent — 运行时节点生成循环（sandbox + evaluate） */
  runNode: (req: NodeRunRequest, signal?: AbortSignal): Promise<NodeGenResponse> =>
    postJSON<NodeGenResponse>(`/agents/node/run`, req, signal),

  /** Node Generator Agent — 将生成的节点持久化到节点库 */
  acceptNode: (req: NodeAcceptRequest, signal?: AbortSignal): Promise<NodeAcceptResponse> =>
    postJSON<NodeAcceptResponse>(`/agents/node/accept`, req, signal),

  /** 保存对话会话到 userdata/agent_sessions/ */
  saveSession: (req: SaveSessionRequest): Promise<SaveSessionResponse> =>
    postJSON<SaveSessionResponse>(`/agents/save-session`, req),
}
