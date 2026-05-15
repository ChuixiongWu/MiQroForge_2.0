import type { FileEntry, FileListResponse } from '../types/index-types'
import { fetchJSON } from './client'
import { getToken } from '../lib/auth'

export const filesApi = {
  list(): Promise<FileListResponse> {
    return fetchJSON<FileListResponse>(`/files`)
  },

  async upload(file: File): Promise<FileEntry> {
    const form = new FormData()
    form.append('file', file)
    return fetchJSON<FileEntry>(`/files/upload`, {
      method: 'POST',
      body: form,
    })
  },

  async download(filename: string): Promise<Blob> {
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`/api/v1/files/${encodeURIComponent(filename)}`, { headers })
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.blob()
  },

  remove(filename: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(
      `/files/${encodeURIComponent(filename)}`,
      { method: 'DELETE' },
    )
  },
}

export const projectFilesApi = {
  list(projectId: string): Promise<FileListResponse> {
    return fetchJSON<FileListResponse>(`/projects/${projectId}/files`)
  },

  async upload(projectId: string, file: File): Promise<FileEntry> {
    const form = new FormData()
    form.append('file', file)
    return fetchJSON<FileEntry>(`/projects/${projectId}/files/upload`, {
      method: 'POST',
      body: form,
    })
  },

  async download(projectId: string, filename: string): Promise<Blob> {
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(
      `/api/v1/projects/${projectId}/files/${encodeURIComponent(filename)}`,
      { headers },
    )
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.blob()
  },

  remove(projectId: string, filename: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(
      `/projects/${projectId}/files/${encodeURIComponent(filename)}`,
      { method: 'DELETE' },
    )
  },

  copyFromWorkspace(projectId: string, filename: string): Promise<FileEntry> {
    return fetchJSON<FileEntry>(
      `/projects/${projectId}/files/copy-from-workspace`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      },
    )
  },

  listDirectory(projectId: string): Promise<DirectoryListResponse> {
    return fetchJSON<DirectoryListResponse>(`/projects/${projectId}/directory`)
  },

  async downloadFromDirectory(projectId: string, relPath: string): Promise<Blob> {
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(
      `/api/v1/projects/${projectId}/directory/download?path=${encodeURIComponent(relPath)}`,
      { headers },
    )
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.blob()
  },
}

export interface DirectoryEntry {
  name: string
  path: string
  size_bytes: number
  is_dir: boolean
  modified_at: string
}

export interface DirectoryListResponse {
  entries: DirectoryEntry[]
}
