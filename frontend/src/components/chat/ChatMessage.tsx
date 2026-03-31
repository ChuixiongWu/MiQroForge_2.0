/**
 * components/chat/ChatMessage.tsx — 聊天消息气泡
 */

import { memo, useState } from 'react'
import { Bot, User, AlertCircle, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react'
import type { ChatMessage } from '../../types/semantic'
import { PlanApprovalCard } from './PlanApprovalCard'
import type { SemanticWorkflow } from '../../types/semantic'

// ─── Collapsible YAML result card ─────────────────────────────────────────────

interface YamlResultCardProps {
  yamlResult: NonNullable<ChatMessage['yaml_result']>
}

const YamlResultCard = memo(({ yamlResult }: YamlResultCardProps) => {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const valid = yamlResult.validation_report.valid
  const borderColor = valid ? 'border-green-900/50' : 'border-amber-900/50'
  const bgColor = valid ? 'bg-green-950/20' : 'bg-amber-950/20'

  const handleCopy = () => {
    navigator.clipboard.writeText(yamlResult.mf_yaml).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className={`border ${borderColor} rounded-lg ${bgColor} max-w-sm overflow-hidden`}>
      {/* Header — always visible, click to toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-1 px-3 py-1.5 text-left hover:bg-white/5 transition-colors"
      >
        {expanded
          ? <ChevronDown size={12} className="text-mf-text-muted flex-shrink-0" />
          : <ChevronRight size={12} className="text-mf-text-muted flex-shrink-0" />
        }
        <span className={`text-[10px] font-medium flex-1 ${valid ? 'text-green-400' : 'text-amber-400'}`}>
          {valid ? '✓ MF YAML' : '⚠ MF YAML (validation issues)'}
        </span>
        <span className="text-[9px] text-mf-text-muted">
          {yamlResult.mf_yaml.split('\n').length} lines
        </span>
      </button>

      {/* Validation errors (always show if any) */}
      {!valid && yamlResult.validation_report.errors.length > 0 && (
        <div className="px-3 py-1 border-t border-amber-900/30">
          {yamlResult.validation_report.errors.map((err, i) => (
            <div key={i} className="text-[10px] text-red-400">• {err}</div>
          ))}
        </div>
      )}

      {/* Expanded YAML content */}
      {expanded && (
        <div className="border-t border-mf-border/30">
          <div className="flex justify-end px-2 py-0.5">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[9px] text-mf-text-muted hover:text-mf-text-primary transition-colors"
              title="Copy YAML"
            >
              {copied
                ? <><Check size={10} className="text-green-400" /> Copied</>
                : <><Copy size={10} /> Copy</>
              }
            </button>
          </div>
          <pre className="px-3 pb-2 text-[10px] text-green-300/70 font-mono overflow-x-auto max-h-64 overflow-y-auto leading-relaxed">
            {yamlResult.mf_yaml}
          </pre>
        </div>
      )}
    </div>
  )
})
YamlResultCard.displayName = 'YamlResultCard'

// ─── ChatMessageBubble ────────────────────────────────────────────────────────

interface ChatMessageProps {
  message: ChatMessage
  onShowOnCanvas: (workflow: SemanticWorkflow) => void
  onAutoResolve: (workflow: SemanticWorkflow) => void
}

export const ChatMessageBubble = memo(({
  message,
  onShowOnCanvas,
  onAutoResolve,
}: ChatMessageProps) => {
  const isUser = message.role === 'user'
  const isError = message.role === 'error'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="text-center text-[10px] text-mf-text-muted py-1">
        {message.content}
      </div>
    )
  }

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5 ${
        isUser ? 'bg-blue-700' : isError ? 'bg-red-900' : 'bg-mf-hover'
      }`}>
        {isUser
          ? <User size={11} className="text-blue-200" />
          : isError
            ? <AlertCircle size={11} className="text-red-400" />
            : <Bot size={11} className="text-mf-text-muted" />
        }
      </div>

      {/* Bubble */}
      <div className={`max-w-[85%] space-y-1.5`}>
        <div className={`px-3 py-2 rounded-lg text-xs leading-relaxed ${
          isUser
            ? 'bg-blue-700/40 text-blue-100'
            : isError
              ? 'bg-red-900/30 text-red-300'
              : 'bg-mf-hover/50 text-mf-text-secondary'
        }`}>
          {message.content}
        </div>

        {/* Embedded plan approval card */}
        {message.semantic_workflow && (
          <PlanApprovalCard
            workflow={message.semantic_workflow}
            onShowOnCanvas={onShowOnCanvas}
            onAutoResolve={onAutoResolve}
          />
        )}

        {/* Embedded YAML result — collapsible full view */}
        {message.yaml_result && message.yaml_result.mf_yaml && (
          <YamlResultCard yamlResult={message.yaml_result} />
        )}

        {/* Timestamp */}
        <div className={`text-[9px] text-mf-text-muted ${isUser ? 'text-right' : 'text-left'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
})
ChatMessageBubble.displayName = 'ChatMessageBubble'
