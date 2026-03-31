/**
 * stores/agent-store.ts — Agent 状态管理 (Zustand)
 *
 * 管理：
 * - 聊天消息列表（持久化到 localStorage）
 * - Agent 运行状态
 * - 当前语义工作流（持久化）
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type {
  ChatMessage, AgentStatus,
  SemanticWorkflow, YAMLResponse,
} from '../types/semantic'

interface AgentState {
  // Chat UI
  messages: ChatMessage[]
  isOpen: boolean
  agentStatus: AgentStatus

  // Current semantic workflow
  currentSemanticWorkflow: SemanticWorkflow | null
  currentYamlResult: YAMLResponse | null

  // Actions — chat
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void

  // Actions — panel
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void

  // Actions — agent state
  setAgentStatus: (status: AgentStatus) => void
  setSemanticWorkflow: (workflow: SemanticWorkflow | null) => void
  setYamlResult: (result: YAMLResponse | null) => void
}

let _msgId = 0
const nextId = () => `msg-${Date.now()}-${_msgId++}`

export const useAgentStore = create<AgentState>()(
  persist(
    (set) => ({
      messages: [],
      isOpen: false,
      agentStatus: 'idle',
      currentSemanticWorkflow: null,
      currentYamlResult: null,

      addMessage: (msg) => {
        const id = nextId()
        set((s) => ({
          messages: [...s.messages, { ...msg, id, timestamp: Date.now() }],
        }))
        return id
      },

      updateMessage: (id, updates) =>
        set((s) => ({
          messages: s.messages.map((m) => m.id === id ? { ...m, ...updates } : m),
        })),

      clearMessages: () => set({ messages: [], currentSemanticWorkflow: null, currentYamlResult: null }),

      toggleChat: () => set((s) => ({ isOpen: !s.isOpen })),
      openChat: () => set({ isOpen: true }),
      closeChat: () => set({ isOpen: false }),

      setAgentStatus: (status) => set({ agentStatus: status }),
      setSemanticWorkflow: (workflow) => set({ currentSemanticWorkflow: workflow }),
      setYamlResult: (result) => set({ currentYamlResult: result }),
    }),
    {
      name: 'mf-agent-v1',
      storage: createJSONStorage(() => localStorage),
      // 恢复时 agentStatus 始终重置为 idle（避免持久化 "planning" 等中间状态）
      partialize: (state) => ({
        messages: state.messages.filter((m) => !m.loading),
        currentSemanticWorkflow: state.currentSemanticWorkflow,
        currentYamlResult: state.currentYamlResult,
      }),
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<AgentState>),
        agentStatus: 'idle',   // 运行时状态不恢复
        isOpen: false,         // 面板默认收起
      }),
    },
  ),
)
