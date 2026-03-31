"""agents/node_generator/state.py — Node Generator Agent 状态定义。"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from agents.schemas import NodeGenRequest, NodeGenResult, EvaluationResult


class NodeGenState(TypedDict, total=False):
    """Node Generator Agent 的 LangGraph 状态。"""

    # 输入
    request: NodeGenRequest

    # 中间状态
    reference_nodes: list[dict[str, Any]]   # few-shot 参考节点
    available_images: list[dict[str, Any]]  # 可用 Docker 镜像
    semantic_types: dict[str, Any]          # 语义类型注册表

    # 生成状态
    nodespec_yaml: str
    run_sh: str
    input_templates: dict[str, str]         # 文件名 → 内容

    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int

    # 输出
    result: Optional[NodeGenResult]

    # 错误
    error: Optional[str]
