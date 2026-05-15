import type {
  WorkflowValidateResponse,
  WorkflowCompileResponse,
  WorkflowSubmitResponse,
} from '../types/index-types'
import { fetchJSON } from './client'

function jsonBody(body: unknown) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export const workflowsApi = {
  validate(yamlContent: string, projectId?: string): Promise<WorkflowValidateResponse> {
    return fetchJSON(`/workflows/validate`, jsonBody({ yaml_content: yamlContent, project_id: projectId || undefined }))
  },

  compile(yamlContent: string, projectId?: string): Promise<WorkflowCompileResponse> {
    return fetchJSON(`/workflows/compile`, jsonBody({ yaml_content: yamlContent, project_id: projectId || undefined }))
  },

  submit(yamlContent: string, projectId?: string): Promise<WorkflowSubmitResponse> {
    return fetchJSON(`/workflows/submit`, jsonBody({ yaml_content: yamlContent, project_id: projectId || undefined }))
  },
}
