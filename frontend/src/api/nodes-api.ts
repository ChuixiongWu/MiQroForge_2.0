import type {
  NodeListResponse,
  NodeDetailResponse,
  NodeIndexInfoResponse,
  SemanticRegistryResponse,
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

export const nodesApi = {
  list(): Promise<NodeListResponse> {
    return fetchJSON(`${BASE}/nodes`)
  },

  search(query: string): Promise<NodeListResponse> {
    return fetchJSON(`${BASE}/nodes/search?q=${encodeURIComponent(query)}`)
  },

  get(name: string): Promise<NodeDetailResponse> {
    return fetchJSON(`${BASE}/nodes/${encodeURIComponent(name)}`)
  },

  indexInfo(): Promise<NodeIndexInfoResponse> {
    return fetchJSON(`${BASE}/nodes/index-info`)
  },

  reindex(): Promise<NodeIndexInfoResponse> {
    return fetchJSON(`${BASE}/nodes/reindex`, { method: 'POST' })
  },

  semanticRegistry(): Promise<SemanticRegistryResponse> {
    return fetchJSON(`${BASE}/nodes/semantic-registry`)
  },
}
