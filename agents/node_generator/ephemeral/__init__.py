"""agents/node_generator/ephemeral/ — 临时节点生成子模块。

提供 Ephemeral 模式的完整生成-评估-执行流程：
  - state:     EphemeralGenState 状态定义
  - generator: ReAct Agent 内循环（sandbox_execute + pip_install）
  - evaluator: 程序化检查 + 执行结果 + 视觉评估
  - sandbox:   Docker 容器沙箱执行环境
  - graph:     LangGraph 图组装与入口
"""

from .graph import run_ephemeral_node_generator

__all__ = ["run_ephemeral_node_generator"]
