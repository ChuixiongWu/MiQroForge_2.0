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
  listRuns(namespace?: string): Promise<RunListResponse> {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : ''
    return fetchJSON(`${BASE}/runs${q}`)
  },

  getRun(name: string): Promise<RunDetailResponse> {
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}`)
  },

  getLogs(name: string, nodeId?: string): Promise<RunLogsResponse> {
    const q = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : ''
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/logs${q}`)
  },

  deleteRun(name: string): Promise<void> {
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}`, { method: 'DELETE' })
  },

  /** 将运行输出参数写入服务器 runs/{name}/outputs.json（终态时调用）*/
  saveOutputs(name: string): Promise<{ saved: boolean; outputs_count: number }> {
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/save-outputs`, { method: 'POST' })
  },
}
