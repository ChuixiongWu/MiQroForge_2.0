"""agents/yaml_coder/state.py — YAML Coder Agent 状态定义。"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from agents.schemas import SemanticWorkflow, ConcretizationResult, EvaluationResult, NodeResolution


class YAMLCoderState(TypedDict, total=False):
    """YAML Coder Agent 的 LangGraph 状态。"""

    # 输入
    semantic_workflow: SemanticWorkflow
    user_params: dict[str, Any]               # 用户提供的参数（如 xyz_geometry, method）
    selected_implementations: dict[str, str]  # step_id → node_name（用户手动选择）

    # 中间状态
    available_nodes: list[dict[str, Any]]     # 完整 NodeSpec（Level 3）
    resolutions: list[NodeResolution]         # 步骤 → 节点映射

    # 生成状态
    mf_yaml: str                             # 当前生成的 MF YAML
    validation_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]

    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int

    # 输出
    result: Optional[ConcretizationResult]

    # 错误
    error: Optional[str]
