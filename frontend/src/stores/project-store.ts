/**
 * stores/project-store.ts — 项目状态管理 (Zustand)
 *
 * 不使用 persist middleware（数据来自后端）。
 * 管理当前项目元数据、对话列表、当前对话 ID。
 */

import { create } from 'zustand'
import { projectsApi } from '../api/projects-api'
import type { ProjectMeta, ConversationMeta, CanvasState } from '../api/projects-api'

interface ProjectState {
  // 当前项目
  currentProjectId: string | null
  currentProjectMeta: ProjectMeta | null

  // 对话
  conversations: ConversationMeta[]
  currentConversationId: string | null

  // Loading
  isLoading: boolean

  // Actions
  loadProject: (id: string) => Promise<void>
  createProject: (name?: string, description?: string) => Promise<ProjectMeta>
  deleteProject: (id: string) => Promise<void>
  renameProject: (id: string, name: string) => Promise<void>
  duplicateProject: (id: string, name?: string) => Promise<ProjectMeta>
  saveCanvas: () => Promise<void>
  loadCanvas: () => Promise<CanvasState | null>
  createConversation: (title?: string) => Promise<ConversationMeta | null>
  switchConversation: (convId: string) => void
  setCurrentProjectId: (id: string | null) => void
  clearProject: () => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProjectId: null,
  currentProjectMeta: null,
  conversations: [],
  currentConversationId: null,
  isLoading: false,

  setCurrentProjectId: (id) => set({ currentProjectId: id }),

  clearProject: () => set({
    currentProjectId: null,
    currentProjectMeta: null,
    conversations: [],
    currentConversationId: null,
  }),

  loadProject: async (id) => {
    set({ isLoading: true })
    try {
      const [meta, conversations] = await Promise.all([
        projectsApi.get(id),
        projectsApi.listConversations(id),
      ])
      set({
        currentProjectId: id,
        currentProjectMeta: meta,
        conversations,
        currentConversationId: conversations[0]?.id ?? null,
      })
    } catch (err) {
      console.error(`Failed to load project ${id}:`, err)
      set({
        currentProjectId: id,
        currentProjectMeta: null,
        conversations: [],
        currentConversationId: null,
      })
    } finally {
      set({ isLoading: false })
    }
  },

  createProject: async (name, description) => {
    const meta = await projectsApi.create({
      name: name || 'Untitled Project',
      description: description || '',
    })
    return meta
  },

  deleteProject: async (id) => {
    await projectsApi.delete(id)
    if (get().currentProjectId === id) {
      set({ currentProjectId: null, currentProjectMeta: null })
    }
  },

  renameProject: async (id, name) => {
    const meta = await projectsApi.update(id, { name })
    if (get().currentProjectId === id) {
      set({ currentProjectMeta: meta })
    }
  },

  duplicateProject: async (id, name) => {
    const meta = await projectsApi.duplicate(id, name)
    return meta
  },

  saveCanvas: async () => {
    const { currentProjectId } = get()
    if (!currentProjectId) return
    // Import store dynamically to avoid circular dependency
    const { useWorkflowStore } = await import('./workflow-store')
    const { meta, nodes, edges } = useWorkflowStore.getState()
    const canvas: CanvasState = {
      meta: meta as unknown as Record<string, unknown>,
      nodes: nodes.map((n) => JSON.parse(JSON.stringify(n))) as Array<Record<string, unknown>>,
      edges: edges.map((e) => JSON.parse(JSON.stringify(e))) as Array<Record<string, unknown>>,
    }
    await projectsApi.saveCanvas(currentProjectId, canvas)
  },

  loadCanvas: async () => {
    const { currentProjectId } = get()
    if (!currentProjectId) return null
    return projectsApi.getCanvas(currentProjectId)
  },

  createConversation: async (title) => {
    const { currentProjectId, conversations } = get()
    if (!currentProjectId) return null
    const conv = await projectsApi.createConversation(currentProjectId, title)
    set({
      conversations: [...conversations, conv],
      currentConversationId: conv.id,
    })
    return conv
  },

  switchConversation: (convId) => {
    set({ currentConversationId: convId })
  },
}))
