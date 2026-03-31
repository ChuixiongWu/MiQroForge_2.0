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
