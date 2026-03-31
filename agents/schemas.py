"""agents/schemas.py — Phase 2 Agent 层共享数据结构。

定义 Planner、YAML Coder、Node Generator 之间传递的核心数据模型：
  - SemanticStep / SemanticEdge / SemanticWorkflow — Planner 输出（抽象语义计划）
  - NodeResolution / ConcretizationResult — YAML Coder 输出（具体节点映射）
  - EvaluationResult — Generator-Evaluator 模式的通用评判结果
  - NodeGenRequest / NodeGenResult — Node Generator I/O
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Generator-Evaluator 通用 ──────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    """Generator-Evaluator 模式的通用评判结果。"""

    passed: bool = Field(..., description="是否通过评判")
    issues: list[str] = Field(default_factory=list, description="发现的问题列表")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    iteration: int = Field(default=0, description="当前迭代轮次")


# ─── Planner Agent 输出 ────────────────────────────────────────────────────────

class SemanticStep(BaseModel):
    """语义工作流中的一个计算步骤（抽象，不指定具体软件）。"""

    id: str = Field(..., description="步骤唯一标识，如 'step-1'")
    semantic_type: str = Field(..., description="对应 semantic_registry.yaml 中的类型键")
    display_name: str = Field(..., description="前端显示名称")
    description: str = Field(default="", description="步骤功能描述")
    rationale: str = Field(default="", description="选择此步骤的理由（Planner 解释）")
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="对 YAML Coder 的约束提示（如 {'method': 'B3LYP', 'basis': 'def2-SVP'}）",
    )

    @field_validator("constraints", mode="before")
    @classmethod
    def _coerce_constraint_values(cls, v: Any) -> dict[str, str]:
        """LLM 有时会把数值型约束输出为 int/float，统一转成字符串。"""
        if not isinstance(v, dict):
            return {}
        return {str(k): str(val) for k, val in v.items()}


class SemanticEdge(BaseModel):
    """语义工作流中的数据流边（步骤间的依赖关系）。"""

    from_step: str = Field(..., description="源步骤 ID")
    to_step: str = Field(..., description="目标步骤 ID")
    data_description: str = Field(default="", description="传递的数据描述")


class SemanticWorkflow(BaseModel):
    """Planner Agent 的输出：抽象语义工作流（不含具体节点）。

    前端将此映射为 ❓ PendingNodes + 语义边，
    YAML Coder 将此翻译为具体 MF YAML。
    """

    name: str = Field(default="", description="工作流名称（Planner 推荐）")
    description: str = Field(default="", description="工作流整体描述")
    target_molecule: str = Field(default="", description="目标分子（从用户意图提取）")
    steps: list[SemanticStep] = Field(default_factory=list, description="按拓扑顺序排列的步骤")
    edges: list[SemanticEdge] = Field(default_factory=list, description="步骤间的数据流边")
    planner_notes: str = Field(default="", description="Planner 的附加说明")
    available_implementations: dict[str, list[str]] = Field(
        default_factory=dict,
        description="step_id → [node_name...]，RAG 检索到的候选实现",
    )


# ─── YAML Coder Agent 输出 ─────────────────────────────────────────────────────

class NodeResolution(BaseModel):
    """单个语义步骤到具体节点的解析结果。"""

    step_id: str = Field(..., description="对应的 SemanticStep.id")
    resolved_node: Optional[str] = Field(default=None, description="选定的节点名称")
    resolved_nodespec_path: Optional[str] = Field(default=None, description="节点 nodespec.yaml 的相对路径")
    onboard_params: dict[str, Any] = Field(default_factory=dict, description="节点的 on-board 参数值")
    needs_new_node: bool = Field(default=False, description="是否需要生成新节点")
    new_node_request: Optional[str] = Field(default=None, description="新节点需求描述（触发 Node Generator）")


class ConcretizationResult(BaseModel):
    """YAML Coder Agent 的完整输出。"""

    resolutions: list[NodeResolution] = Field(default_factory=list)
    mf_yaml: str = Field(default="", description="生成的 MF YAML 字符串")
    missing_nodes: list[str] = Field(default_factory=list, description="缺少实现的语义步骤")
    new_image_requests: list[str] = Field(default_factory=list, description="需要新 Docker 镜像的请求")
    validation_passed: bool = Field(default=False, description="Phase 1 validator 是否通过")
    validation_errors: list[str] = Field(default_factory=list, description="校验错误列表")
    evaluation: Optional[EvaluationResult] = Field(default=None, description="LLM 评判结果")


# ─── Node Generator Agent I/O ──────────────────────────────────────────────────

class NodeGenRequest(BaseModel):
    """Node Generator Agent 的输入请求。"""

    semantic_type: str = Field(..., description="语义类型（如 'geometry-optimization'）")
    description: str = Field(..., description="详细功能描述（YAML Coder 提供）")
    target_software: Optional[str] = Field(default=None, description="目标软件（如 'ORCA'）")
    target_method: Optional[str] = Field(default=None, description="目标计算方法（如 'B3LYP'）")
    reference_nodes: list[str] = Field(default_factory=list, description="同软件的参考节点名（few-shot）")
    category: str = Field(default="chemistry", description="节点分类目录")


class NodeGenResult(BaseModel):
    """Node Generator Agent 的输出结果。"""

    node_name: str = Field(..., description="生成的节点名称")
    nodespec_yaml: str = Field(..., description="生成的 nodespec.yaml 内容")
    run_sh: Optional[str] = Field(default=None, description="生成的 profile/run.sh 内容")
    input_templates: dict[str, str] = Field(default_factory=dict, description="输入模板文件 {文件名: 内容}")
    saved_path: Optional[str] = Field(default=None, description="保存到 userdata/nodes/ 的路径")
    evaluation: Optional[EvaluationResult] = Field(default=None, description="评判结果")
