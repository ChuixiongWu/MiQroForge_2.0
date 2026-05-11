"""agents/subagent/ — 可复用的子 Agent。

每个子 Agent 作为"内部工具"被父 Agent 调用：
  - 父 Agent 传入研究问题 → 子 Agent 独立搜索 → 返回结构化摘要
  - 子 Agent 的中间上下文在返回后丢弃，不污染父 Agent 上下文

当前子 Agent：
  - explore: 软件手册 + 参考节点 + Schema 研究（用于 Prefab Node Generator）
"""

__all__ = ["run_explore_agent"]
