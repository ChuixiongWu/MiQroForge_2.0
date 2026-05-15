/** 统一 API 客户端封装 — 自动附加认证 token。 */

import { getToken, clearToken } from '../lib/auth'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

export async function fetchJSON<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {}

  if (options.headers) {
    for (const [k, v] of Object.entries(options.headers)) {
      headers[k] = v as string
    }
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    clearToken()
    // Only redirect if we're on a protected page (not login)
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new ApiError(401, 'Authentication required')
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail || detail
    } catch {
      // Use default status text
    }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  return res.json() as Promise<T>
}

export function postJSON<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return fetchJSON<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

export function putJSON<T>(path: string, body: unknown): Promise<T> {
  return fetchJSON<T>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function patchJSON<T>(path: string, body: unknown): Promise<T> {
  return fetchJSON<T>(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function deleteJSON<T>(path: string): Promise<T> {
  return fetchJSON<T>(path, { method: 'DELETE' })
}
