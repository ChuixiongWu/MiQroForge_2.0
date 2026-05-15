import type {
  RunListResponse,
  RunDetailResponse,
  RunLogsResponse,
} from '../types/index-types'
import { fetchJSON } from './client'
import { getToken } from '../lib/auth'

export const argoApi = {
  listRuns(projectId?: string): Promise<RunListResponse> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    return fetchJSON(`/runs${q}`)
  },

  getRun(name: string): Promise<RunDetailResponse> {
    return fetchJSON(`/runs/${encodeURIComponent(name)}`)
  },

  getLogs(name: string, nodeId?: string): Promise<RunLogsResponse> {
    const q = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : ''
    return fetchJSON(`/runs/${encodeURIComponent(name)}/logs${q}`)
  },

  async deleteRun(name: string, projectId?: string): Promise<void> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`/api/v1/runs/${encodeURIComponent(name)}${q}`, {
      method: 'DELETE',
      headers,
    })
    if (!res.ok && res.status !== 204) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
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
    return fetchJSON(`/runs/${encodeURIComponent(name)}/save-outputs${q}`, init)
  },

  /** 获取 run 后保存的画布状态（含节点输出值）*/
  getAfterrunCanvas(name: string, projectId: string): Promise<Record<string, unknown>> {
    return fetchJSON(
      `/runs/${encodeURIComponent(name)}/afterrun-canvas?project_id=${encodeURIComponent(projectId)}`,
    )
  },

  /** 中止运行中的工作流 */
  async stopRun(name: string, projectId?: string): Promise<{ stopped: string; project_id: string }> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    const token = getToken()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`/api/v1/runs/${encodeURIComponent(name)}/stop${q}`, {
      method: 'POST',
      headers,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.json()
  },

  /** 获取失败节点的完整 Pod 日志 */
  getNodeLogs(runName: string, nodeId: string): Promise<{ node_id: string; logs: string }> {
    return fetchJSON(
      `/runs/${encodeURIComponent(runName)}/node-logs/${encodeURIComponent(nodeId)}`,
    )
  },
}
