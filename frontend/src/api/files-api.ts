import type { FileEntry, FileListResponse } from '../types/index-types'

const BASE = '/api/v1'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const filesApi = {
  list(): Promise<FileListResponse> {
    return fetchJSON<FileListResponse>(`${BASE}/files`)
  },

  async upload(file: File): Promise<FileEntry> {
    const form = new FormData()
    form.append('file', file)
    return fetchJSON<FileEntry>(`${BASE}/files/upload`, {
      method: 'POST',
      body: form,
    })
  },

  async download(filename: string): Promise<Blob> {
    const res = await fetch(`${BASE}/files/${encodeURIComponent(filename)}`)
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.blob()
  },

  remove(filename: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(
      `${BASE}/files/${encodeURIComponent(filename)}`,
      { method: 'DELETE' },
    )
  },
}

export const projectFilesApi = {
  list(projectId: string): Promise<FileListResponse> {
    return fetchJSON<FileListResponse>(`${BASE}/projects/${projectId}/files`)
  },

  async upload(projectId: string, file: File): Promise<FileEntry> {
    const form = new FormData()
    form.append('file', file)
    return fetchJSON<FileEntry>(`${BASE}/projects/${projectId}/files/upload`, {
      method: 'POST',
      body: form,
    })
  },

  async download(projectId: string, filename: string): Promise<Blob> {
    const res = await fetch(
      `${BASE}/projects/${projectId}/files/${encodeURIComponent(filename)}`,
    )
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      throw new Error(`API error ${res.status}: ${text}`)
    }
    return res.blob()
  },

  remove(projectId: string, filename: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(
      `${BASE}/projects/${projectId}/files/${encodeURIComponent(filename)}`,
      { method: 'DELETE' },
    )
  },

  copyFromWorkspace(projectId: string, filename: string): Promise<FileEntry> {
    return fetchJSON<FileEntry>(
      `${BASE}/projects/${projectId}/files/copy-from-workspace`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      },
    )
  },

  listDirectory(projectId: string): Promise<DirectoryListResponse> {
    return fetchJSON<DirectoryListResponse>(`${BASE}/projects/${projectId}/directory`)
  },

  async downloadFromDirectory(projectId: string, relPath: string): Promise<Blob> {
    const res = await fetch(
      `${BASE}/projects/${projectId}/directory/download?path=${encodeURIComponent(relPath)}`,
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
