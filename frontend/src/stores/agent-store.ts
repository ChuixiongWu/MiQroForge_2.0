/**
 * stores/agent-store.ts — Agent 状态管理 (Zustand)
 *
 * 管理：
 * - 聊天消息列表（持久化到 localStorage）
 * - Agent 运行状态
 * - 当前语义工作流（持久化）
 * - 会话 ID（每次 clear 生成新 ID，Agent 调用时传入 API）
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type {
  ChatMessage, AgentStatus,
  SemanticWorkflow, YAMLResponse,
} from '../types/semantic'

/** 生成短 ID：{日期}-{随机6位} */
function generateSessionId(): string {
  const now = new Date()
  const date = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const rand = Math.random().toString(36).slice(2, 8)
  return `${date}-${rand}`
}

interface AgentState {
  // Chat UI
  messages: ChatMessage[]
  isOpen: boolean
  agentStatus: AgentStatus

  // 当前会话 ID（跨 Agent 调用共享，clear 时重置）
  sessionId: string

  // Current semantic workflow
  currentSemanticWorkflow: SemanticWorkflow | null
  currentYamlResult: YAMLResponse | null

  // Actions — chat
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  /**
   * 清空消息并重置会话。
   * 如果 onBeforeClear 回调已由调用方处理保存，直接清空即可。
   */
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
      sessionId: generateSessionId(),
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

      clearMessages: () =>
        set({
          messages: [],
          currentSemanticWorkflow: null,
          currentYamlResult: null,
          sessionId: generateSessionId(),   // 新会话开始
        }),

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
      partialize: (state) => ({
        messages: state.messages.filter((m) => !m.loading),
        sessionId: state.sessionId,
        currentSemanticWorkflow: state.currentSemanticWorkflow,
        currentYamlResult: state.currentYamlResult,
      }),
      merge: (persisted, current) => {
        const p = persisted as Partial<AgentState>
        return {
          ...current,
          ...p,
          // 运行时状态不恢复
          agentStatus: 'idle',
          isOpen: false,
          // 旧 localStorage 无 sessionId 时，保留初始生成的值
          sessionId: p.sessionId || current.sessionId,
        }
      },
    },
  ),
)
