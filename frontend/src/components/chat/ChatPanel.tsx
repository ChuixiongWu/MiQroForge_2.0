/**
 * components/chat/ChatPanel.tsx — AI 助手聊天面板
 *
 * 可折叠侧面板，提供：
 * - 消息列表（用户 / Agent / 系统）
 * - 自然语言输入框
 * - 调用 Planner → 显示 SemanticWorkflow → 调用 YAML Coder
 */

import { useState, useRef, useEffect, memo, useCallback } from 'react'
import { Send, X, Trash2, Loader2, Square } from 'lucide-react'
import { useAgentStore } from '../../stores/agent-store'
import { useWorkflowStore } from '../../stores/workflow-store'
import { useUIStore } from '../../stores/ui-store'
import { agentsApi } from '../../api/agents-api'
import { nodesApi } from '../../api/nodes-api'
import { semanticWorkflowToCanvasState, SEMANTIC_EDGE_TYPE } from '../../lib/semantic-to-canvas'
import { buildNodeData } from '../../lib/node-utils'
import { buildResolvedEdges } from '../../lib/yaml-to-edges'
import { ChatMessageBubble } from './ChatMessage'
import { AgentThinking } from './AgentThinking'
import type { SemanticWorkflow } from '../../types/semantic'

// ─── ChatPanel ────────────────────────────────────────────────────────────────

export const ChatPanel = memo(() => {
  const {
    messages, agentStatus, isOpen,
    addMessage, updateMessage, clearMessages,
    setAgentStatus, setSemanticWorkflow, setYamlResult,
    closeChat,
  } = useAgentStore()

  const { loadFromNodes, nodes, edges, updateNodeWithHistory } = useWorkflowStore()
  const { showNotification } = useUIStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortCtrlRef = useRef<AbortController | null>(null)

  const isRunning = agentStatus !== 'idle'

  // 取消当前正在运行的 Agent 请求
  const handleStop = useCallback(() => {
    abortCtrlRef.current?.abort()
    abortCtrlRef.current = null
    setAgentStatus('idle')
  }, [setAgentStatus])

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, agentStatus])

  // ── 显示到画布 ────────────────────────────────────────────────────────────
  const handleShowOnCanvas = useCallback((workflow: SemanticWorkflow) => {
    const { nodes: newNodes, edges: newEdges } = semanticWorkflowToCanvasState(
      workflow,
      (stepId, nodeName) => {
        // 用户手动选择实现 → 触发 YAML Coder
        handleAutoResolve(workflow, { [stepId]: nodeName })
      },
    )

    // 保留现有画布节点，追加语义节点
    loadFromNodes([...nodes, ...newNodes], [...edges, ...newEdges])
    showNotification('success', `已添加 ${newNodes.length} 个语义节点到画布`)
    setSemanticWorkflow(workflow)
  }, [nodes, edges, loadFromNodes, showNotification, setSemanticWorkflow])

  // ── 自动解析（触发 YAML Coder）────────────────────────────────────────────
  const handleAutoResolve = useCallback(async (
    workflow: SemanticWorkflow,
    selectedImplementations?: Record<string, string>,
  ) => {
    const loadingId = addMessage({ role: 'agent', content: '', loading: true })
    abortCtrlRef.current = new AbortController()
    const { signal } = abortCtrlRef.current

    try {
      setAgentStatus('generating_yaml')

      const result = await agentsApi.generateYaml({
        semantic_workflow: workflow,
        selected_implementations: selectedImplementations ?? {},
      }, signal)

      // ── Replace pending canvas nodes with resolved implementations ──────────
      const resolutions = result.result?.resolutions ?? []
      let resolvedCount = 0

      // Build a lookup: pending_step_id → canvas node id
      const currentNodes = useWorkflowStore.getState().nodes
      const pendingByStepId = new Map(
        currentNodes
          .filter((n) => n.data.pending && n.data.pending_step_id)
          .map((n) => [n.data.pending_step_id as string, n.id]),
      )

      for (const resolution of resolutions) {
        if (!resolution.resolved_node || !resolution.step_id) continue
        const canvasNodeId = pendingByStepId.get(resolution.step_id)
        if (!canvasNodeId) continue

        try {
          const detail = await nodesApi.get(resolution.resolved_node)
          const newData = {
            ...buildNodeData(detail),
            // Carry over any onboard param overrides from YAML Coder
            onboard_params: {
              ...buildNodeData(detail).onboard_params,
              ...resolution.onboard_params,
            },
          }
          updateNodeWithHistory(canvasNodeId, newData)
          resolvedCount++
        } catch {
          console.warn(`Failed to load node detail for ${resolution.resolved_node}`)
        }
      }

      // ── Replace semantic edges with real port-level edges ───────────────────
      if (result.mf_yaml && resolvedCount > 0) {
        const newEdges = buildResolvedEdges(result.mf_yaml, resolutions)
        if (newEdges.length > 0) {
          const currentEdges = useWorkflowStore.getState().edges
          const keptEdges = currentEdges.filter((e) => e.type !== SEMANTIC_EDGE_TYPE)
          useWorkflowStore.setState({ edges: [...keptEdges, ...newEdges] })
        }
      }

      const resolveNote = resolvedCount > 0
        ? `（已自动替换画布上 ${resolvedCount} 个待定节点）`
        : ''

      updateMessage(loadingId, {
        loading: false,
        content: result.validation_report.valid
          ? `✓ MF YAML 已生成并通过校验。${resolveNote}`
          : `⚠ MF YAML 已生成，但存在校验问题：${result.validation_report.errors.join('; ')}${resolveNote}`,
        yaml_result: result,
      })

      setYamlResult(result)

      if (result.validation_report.valid) {
        showNotification('success', resolvedCount > 0
          ? `MF YAML 生成成功，已替换 ${resolvedCount} 个节点`
          : 'MF YAML 生成成功',
        )
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        updateMessage(loadingId, { loading: false, role: 'system', content: '⏹ 已取消' })
        return
      }
      updateMessage(loadingId, {
        loading: false,
        role: 'error',
        content: `YAML Coder 失败: ${err instanceof Error ? err.message : String(err)}`,
      })
    } finally {
      abortCtrlRef.current = null
      setAgentStatus('idle')
    }
  }, [addMessage, updateMessage, setAgentStatus, setYamlResult, showNotification, updateNodeWithHistory])

  // ── 发送消息 ──────────────────────────────────────────────────────────────
  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isRunning) return

    setInput('')

    // 添加用户消息
    addMessage({ role: 'user', content: trimmed })

    // 添加 loading 消息
    const loadingId = addMessage({ role: 'agent', content: '', loading: true })

    abortCtrlRef.current = new AbortController()
    const { signal } = abortCtrlRef.current

    try {
      setAgentStatus('planning')

      const result = await agentsApi.plan({
        intent: trimmed,
      }, signal)

      if (result.error && !result.semantic_workflow) {
        updateMessage(loadingId, {
          loading: false,
          role: 'error',
          content: `Planner 失败: ${result.error}`,
        })
        return
      }

      const workflow = result.semantic_workflow
      const stepCount = workflow.steps.length
      const implCount = workflow.steps.filter(
        (s) => (workflow.available_implementations[s.id] ?? []).length > 0
      ).length

      updateMessage(loadingId, {
        loading: false,
        content: `已生成 ${stepCount} 步语义工作流（${implCount}/${stepCount} 步找到实现）。`,
        semantic_workflow: workflow,
      })

      setSemanticWorkflow(workflow)

    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        updateMessage(loadingId, { loading: false, role: 'system', content: '⏹ 已取消' })
        return
      }
      updateMessage(loadingId, {
        loading: false,
        role: 'error',
        content: `Planner Agent 错误: ${err instanceof Error ? err.message : String(err)}`,
      })
    } finally {
      abortCtrlRef.current = null
      setAgentStatus('idle')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) return null

  return (
    <div className="flex flex-col border-l border-mf-border bg-mf-panel flex-shrink-0 overflow-hidden"
         style={{ width: 320 }}>

      {/* Header */}
      <div className="flex items-center justify-between px-3 h-10 border-b border-mf-border flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-base">🤖</span>
          <span className="text-sm font-semibold text-mf-text-primary">AI Assistant</span>
          {agentStatus !== 'idle' && (
            <Loader2 size={12} className="animate-spin text-blue-400" />
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearMessages}
            className="p-1 text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded"
            title="Clear messages"
          >
            <Trash2 size={12} />
          </button>
          <button
            onClick={closeChat}
            className="p-1 text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded"
            title="Close chat"
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="text-center text-mf-text-muted text-xs py-8">
            <div className="text-2xl mb-2">🔬</div>
            <div className="font-medium text-mf-text-secondary mb-1">MiQroForge AI Assistant</div>
            <div className="text-mf-text-muted">
              Describe your computational chemistry goal and I'll design a workflow for you.
            </div>
            <div className="mt-3 text-[10px] text-mf-text-muted/70">
              Example: "Calculate thermodynamic properties of H₂O"
            </div>
          </div>
        )}

        {messages.map((msg) => (
          msg.loading ? (
            <div key={msg.id} className="flex gap-2">
              <div className="w-6 h-6 rounded-full bg-mf-hover flex items-center justify-center flex-shrink-0">
                <span className="text-xs">🤖</span>
              </div>
              <AgentThinking status={
                agentStatus === 'idle' || agentStatus === 'error'
                  ? 'thinking'
                  : agentStatus
              } />
            </div>
          ) : (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              onShowOnCanvas={handleShowOnCanvas}
              onAutoResolve={(wf) => handleAutoResolve(wf)}
            />
          )
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-mf-border px-3 py-2 flex-shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isRunning}
            placeholder="Describe your computation goal… (Enter to send)"
            rows={2}
            className="flex-1 text-xs bg-mf-input border border-mf-border rounded px-2 py-1.5 text-mf-text-primary placeholder-mf-text-muted focus:outline-none focus:border-blue-500 resize-none disabled:opacity-50"
          />
          {isRunning ? (
            <button
              onClick={handleStop}
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded bg-red-600 hover:bg-red-500 transition-colors"
              title="Stop (cancel current request)"
            >
              <Square size={11} className="text-white fill-white" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Send (Enter)"
            >
              <Send size={13} className="text-white" />
            </button>
          )}
        </div>
        <div className="text-[9px] text-mf-text-muted mt-1">
          Enter = send · Shift+Enter = newline{isRunning ? ' · ⏹ click red button to stop' : ''}
        </div>
      </div>
    </div>
  )
})
ChatPanel.displayName = 'ChatPanel'
