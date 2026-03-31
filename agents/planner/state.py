"""agents/planner/state.py — Planner Agent 状态定义。"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from agents.schemas import SemanticWorkflow, EvaluationResult


class PlannerState(TypedDict, total=False):
    """Planner Agent 的 LangGraph 状态。"""

    # 输入
    intent: str                              # 用户意图（自然语言）
    molecule: str                            # 目标分子
    preferences: str                         # 用户偏好（可选）

    # 中间状态
    node_summaries: list[dict[str, Any]]     # RAG 检索到的节点摘要
    semantic_types: dict[str, Any]           # 从注册表加载的语义类型

    # 输出
    semantic_workflow: Optional[SemanticWorkflow]
    workflow_json: str                       # SemanticWorkflow 的 JSON 字符串（评判用）

    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int

    # 错误
    error: Optional[str]
