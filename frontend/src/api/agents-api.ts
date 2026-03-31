/**
 * api/agents-api.ts — Agent API 客户端
 */

import type {
  PlanRequest, PlanResponse,
  YAMLRequest, YAMLResponse,
  NodeGenRequest, NodeGenResponse,
} from '../types/semantic'

const API_BASE = '/api/v1/agents'

async function post<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export const agentsApi = {
  /** Planner Agent — 意图 → 语义工作流 */
  plan: (req: PlanRequest, signal?: AbortSignal): Promise<PlanResponse> =>
    post<PlanResponse>(`${API_BASE}/plan`, req, signal),

  /** YAML Coder Agent — 语义工作流 → MF YAML */
  generateYaml: (req: YAMLRequest, signal?: AbortSignal): Promise<YAMLResponse> =>
    post<YAMLResponse>(`${API_BASE}/yaml`, req, signal),

  /** Node Generator Agent — 生成新节点 */
  generateNode: (req: NodeGenRequest, signal?: AbortSignal): Promise<NodeGenResponse> =>
    post<NodeGenResponse>(`${API_BASE}/node`, req, signal),
}
