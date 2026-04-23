import type {
  RunListResponse,
  RunDetailResponse,
  RunLogsResponse,
} from '../types/index-types'

const BASE = '/api/v1'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const argoApi = {
  listRuns(projectId?: string): Promise<RunListResponse> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    return fetchJSON(`${BASE}/runs${q}`)
  },

  getRun(name: string): Promise<RunDetailResponse> {
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}`)
  },

  getLogs(name: string, nodeId?: string): Promise<RunLogsResponse> {
    const q = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : ''
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/logs${q}`)
  },

  async deleteRun(name: string, projectId?: string): Promise<void> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    const res = await fetch(`${BASE}/runs/${encodeURIComponent(name)}${q}`, { method: 'DELETE' })
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    // 204 No Content — don't call res.json()
  },

  /** 将运行输出参数写入服务器 runs/{name}/outputs.json（终态时调用），可附带画布状态 */
  saveOutputs(
    name: string,
    projectId?: string,
    canvas?: Record<string, unknown>,
  ): Promise<{ saved: boolean; outputs_count: number; error_texts?: Record<string, string> }> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    const init: RequestInit = { method: 'POST' }
    if (canvas) {
      init.headers = { 'Content-Type': 'application/json' }
      init.body = JSON.stringify(canvas)
    }
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/save-outputs${q}`, init)
  },

  /** 获取 run 后保存的画布状态（含节点输出值）*/
  getAfterrunCanvas(name: string, projectId: string): Promise<Record<string, unknown>> {
    return fetchJSON(
      `${BASE}/runs/${encodeURIComponent(name)}/afterrun-canvas?project_id=${encodeURIComponent(projectId)}`,
    )
  },

  /** 获取失败节点的完整 Pod 日志 */
  getNodeLogs(runName: string, nodeId: string): Promise<{ node_id: string; logs: string }> {
    return fetchJSON(
      `${BASE}/runs/${encodeURIComponent(runName)}/node-logs/${encodeURIComponent(nodeId)}`,
    )
  },
}
