import { fetchJSON } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ProjectMeta {
  id: string
  name: string
  description: string
  icon: string
  created_at: string
  updated_at: string
  order: number
  canvas_node_count: number
  run_count: number
  conversation_count: number
}

export interface ProjectListResponse {
  total: number
  projects: ProjectMeta[]
}

export interface ProjectCreateRequest {
  name: string
  description?: string
  icon?: string
}

export interface ProjectUpdateRequest {
  name?: string
  description?: string
  icon?: string
  order?: number
}

export interface CanvasState {
  meta: Record<string, unknown>
  nodes: Array<Record<string, unknown>>
  edges: Array<Record<string, unknown>>
}

export interface ConversationMeta {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface SnapshotMeta {
  id: string
  name: string
  created_at: string
  canvas_node_count: number
}

export interface SnapshotListResponse {
  total: number
  snapshots: SnapshotMeta[]
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const projectsApi = {
  list(): Promise<ProjectListResponse> {
    return fetchJSON<ProjectListResponse>(`/projects`)
  },

  create(req: ProjectCreateRequest): Promise<ProjectMeta> {
    return fetchJSON<ProjectMeta>(`/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  get(id: string): Promise<ProjectMeta> {
    return fetchJSON<ProjectMeta>(`/projects/${id}`)
  },

  update(id: string, req: ProjectUpdateRequest): Promise<ProjectMeta> {
    return fetchJSON<ProjectMeta>(`/projects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  delete(id: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(`/projects/${id}`, {
      method: 'DELETE',
    })
  },

  duplicate(id: string, name?: string): Promise<ProjectMeta> {
    return fetchJSON<ProjectMeta>(`/projects/${id}/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(name ? { name } : {}),
    })
  },

  reorder(ids: string[]): Promise<{ reordered: number }> {
    return fetchJSON(`/projects/reorder`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    })
  },

  batchDelete(ids: string[]): Promise<{ deleted: string[] }> {
    return fetchJSON(`/projects/batch-delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    })
  },

  getCanvas(id: string): Promise<CanvasState> {
    return fetchJSON<CanvasState>(`/projects/${id}/canvas`)
  },

  saveCanvas(id: string, canvas: CanvasState): Promise<{ saved: boolean }> {
    return fetchJSON<{ saved: boolean }>(`/projects/${id}/canvas`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(canvas),
    })
  },

  // Conversations
  listConversations(id: string): Promise<ConversationMeta[]> {
    return fetchJSON<ConversationMeta[]>(`/projects/${id}/conversations`)
  },

  createConversation(id: string, title?: string): Promise<ConversationMeta> {
    return fetchJSON<ConversationMeta>(`/projects/${id}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(title ? { title } : {}),
    })
  },

  // Snapshots
  listSnapshots(id: string): Promise<SnapshotListResponse> {
    return fetchJSON<SnapshotListResponse>(`/projects/${id}/snapshots`)
  },

  createSnapshot(id: string, name: string, canvas: Record<string, unknown>): Promise<SnapshotMeta> {
    return fetchJSON<SnapshotMeta>(`/projects/${id}/snapshots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, canvas }),
    })
  },

  deleteSnapshot(id: string, snapshotId: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(`/projects/${id}/snapshots/${snapshotId}`, {
      method: 'DELETE',
    })
  },
}
