import type {
  NodeListResponse,
  NodeDetailResponse,
  NodeIndexInfoResponse,
  SemanticRegistryResponse,
} from '../types/index-types'
import type { DirectoryListResponse } from './files-api'
import { fetchJSON } from './client'

export const nodesApi = {
  list(): Promise<NodeListResponse> {
    return fetchJSON(`/nodes`)
  },

  search(query: string): Promise<NodeListResponse> {
    return fetchJSON(`/nodes/search?q=${encodeURIComponent(query)}`)
  },

  get(name: string): Promise<NodeDetailResponse> {
    return fetchJSON(`/nodes/${encodeURIComponent(name)}`)
  },

  indexInfo(): Promise<NodeIndexInfoResponse> {
    return fetchJSON(`/nodes/index-info`)
  },

  reindex(): Promise<NodeIndexInfoResponse> {
    return fetchJSON(`/nodes/reindex`, { method: 'POST' })
  },

  semanticRegistry(): Promise<SemanticRegistryResponse> {
    return fetchJSON(`/nodes/semantic-registry`)
  },

  getPreferences(): Promise<{ version: string; node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }> {
    return fetchJSON(`/nodes/preferences`)
  },

  putPreferences(body: { node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }): Promise<{ version: string; node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> }> {
    return fetchJSON(`/nodes/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },
}

export const nodeFilesApi = {
  list(): Promise<DirectoryListResponse> {
    return fetchJSON(`/nodes/files`)
  },

  async read(path: string): Promise<string> {
    const res = await fetch(`/nodes/files/read?path=${encodeURIComponent(path)}`)
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.text()
  },

  async write(path: string, content: string): Promise<{ written: string }> {
    return fetchJSON(`/nodes/files/write`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    })
  },
}
