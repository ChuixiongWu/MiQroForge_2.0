/**
 * components/chat/AgentThinking.tsx — Agent 思考中动画指示器
 */

import { memo } from 'react'

interface AgentThinkingProps {
  status: 'planning' | 'generating_yaml' | 'generating_node' | 'thinking'
}

const STATUS_LABELS: Record<string, string> = {
  planning: 'Planner 分析中…',
  generating_yaml: 'YAML Coder 生成中…',
  generating_node: 'Node Generator 生成中…',
  thinking: '思考中…',
}

export const AgentThinking = memo(({ status }: AgentThinkingProps) => {
  const label = STATUS_LABELS[status] ?? '处理中…'

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-mf-hover/50 text-mf-text-muted text-xs max-w-xs">
      {/* 跳动的三个点 */}
      <div className="flex items-center gap-0.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400"
            style={{
              animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>
      <span>{label}</span>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  )
})
AgentThinking.displayName = 'AgentThinking'
