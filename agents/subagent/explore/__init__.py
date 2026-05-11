"""agents/subagent/explore/ — 研究探索子 Agent。

由父 Agent（如 Prefab Node Generator）通过 explore_manuals 工具调用。
用快速模型独立搜索手册、参考节点和 Schema，
返回结构化摘要后丢弃上下文。

父 Agent 只看到结论，不看到中间搜索过程和大量原文。
"""

from .agent import run_explore_agent

__all__ = ["run_explore_agent"]
