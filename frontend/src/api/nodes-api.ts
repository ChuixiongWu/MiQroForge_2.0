import type {
  NodeListResponse,
  NodeDetailResponse,
  NodeIndexInfoResponse,
  SemanticRegistryResponse,
} from '../types/index-types'
import type { DirectoryEntry, DirectoryListResponse } from './files-api'

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

  getPreferences(): Promise<{ version: string; node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }> {
    return fetchJSON(`${BASE}/nodes/preferences`)
  },

  putPreferences(body: { node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }): Promise<{ version: string; node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }> {
    return fetchJSON(`${BASE}/nodes/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },
}

export const nodeFilesApi = {
  list(): Promise<DirectoryListResponse> {
    return fetchJSON(`${BASE}/nodes/files`)
  },

  async read(path: string): Promise<string> {
    const res = await fetch(`${BASE}/nodes/files/read?path=${encodeURIComponent(path)}`)
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.text()
  },

  async write(path: string, content: string): Promise<{ written: string }> {
    return fetchJSON(`${BASE}/nodes/files/write`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    })
  },
}
