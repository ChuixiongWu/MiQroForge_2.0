import type {
  WorkflowValidateResponse,
  WorkflowCompileResponse,
  WorkflowSubmitResponse,
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

function jsonBody(body: unknown) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export const workflowsApi = {
  validate(yamlContent: string): Promise<WorkflowValidateResponse> {
    return fetchJSON(`${BASE}/workflows/validate`, jsonBody({ yaml_content: yamlContent }))
  },

  compile(yamlContent: string): Promise<WorkflowCompileResponse> {
    return fetchJSON(`${BASE}/workflows/compile`, jsonBody({ yaml_content: yamlContent }))
  },

  submit(yamlContent: string, namespace?: string): Promise<WorkflowSubmitResponse> {
    return fetchJSON(`${BASE}/workflows/submit`, jsonBody({ yaml_content: yamlContent, namespace }))
  },
}
