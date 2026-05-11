"""api/models/agents.py — Agent API 的 Pydantic 请求/响应模型。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from agents.schemas import (
    SemanticWorkflow,
    ConcretizationResult,
    NodeGenRequest,
    NodeGenResult,
    EvaluationResult,
)


# ─── Planner Agent ────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    """POST /api/v1/agents/plan 请求体。"""
    intent: str = Field(..., description="用户意图（自然语言），如 'Calculate thermodynamic properties of H₂O'")
    molecule: str = Field(default="", description="目标分子，如 'H₂O'")
    preferences: str = Field(default="", description="用户偏好，如 'use DFT/B3LYP'")
    session_id: Optional[str] = Field(default=None, description="会话 ID，用于日志归组（前端生成）")


class PlanResponse(BaseModel):
    """POST /api/v1/agents/plan 响应体。"""
    semantic_workflow: SemanticWorkflow
    evaluation: Optional[EvaluationResult] = None
    available_nodes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="step_id → [node_name...] 候选实现映射",
    )
    error: Optional[str] = None


# ─── YAML Coder Agent ─────────────────────────────────────────────────────────

class YAMLRequest(BaseModel):
    """POST /api/v1/agents/yaml 请求体。"""
    semantic_workflow: SemanticWorkflow
    user_params: dict[str, Any] = Field(
        default_factory=dict,
        description="用户参数，如 {'xyz_geometry': '...', 'method': 'B3LYP'}",
    )
    selected_implementations: dict[str, str] = Field(
        default_factory=dict,
        description="step_id → node_name 的手动选择（可选，覆盖 RAG 选择）",
    )
    session_id: Optional[str] = Field(default=None, description="会话 ID，用于日志归组")


class YAMLResponse(BaseModel):
    """POST /api/v1/agents/yaml 响应体。"""
    mf_yaml: str = Field(..., description="生成的 MF YAML 字符串")
    validation_report: dict[str, Any] = Field(
        default_factory=dict,
        description="校验报告：{valid, errors, warnings}",
    )
    result: Optional[ConcretizationResult] = None
    error: Optional[str] = None


# ─── Node Generator Agent ─────────────────────────────────────────────────────

class NodeGenAPIRequest(BaseModel):
    """POST /api/v1/agents/node 请求体（设计时：仅生成 nodespec，无 sandbox）。"""
    semantic_type: str = Field(..., description="语义类型，如 'geometry-optimization'")
    description: str = Field(..., description="节点功能详细描述")
    target_software: Optional[str] = Field(default=None, description="目标软件，如 'gaussian'")
    target_method: Optional[str] = Field(default=None, description="目标计算方法，如 'B3LYP'")
    category: str = Field(default="chemistry", description="节点分类目录")
    project_id: Optional[str] = Field(default=None, description="项目 ID（用于保存到 proj/tmp/）")
    node_id: Optional[str] = Field(default=None, description="Canvas node ID — 用作 tmp 目录名，避免多节点重名冲突")
    session_id: Optional[str] = Field(default=None, description="会话 ID，用于日志归组")
    resource_overrides: Optional[dict[str, Any]] = Field(default=None, description="资源参数覆盖")


class NodeRunAPIRequest(BaseModel):
    """POST /api/v1/agents/node/run 请求体（运行时：完整 generate+sandbox+evaluate 循环）。"""
    semantic_type: str = Field(..., description="语义类型")
    description: str = Field(..., description="节点功能详细描述")
    target_software: Optional[str] = Field(default=None, description="目标软件")
    target_method: Optional[str] = Field(default=None, description="目标计算方法")
    category: str = Field(default="chemistry", description="节点分类目录")
    input_data: dict[str, str] = Field(default_factory=dict, description="真实上游输入数据 {port_name: content}")
    resource_overrides: Optional[dict[str, Any]] = Field(default=None, description="资源参数覆盖")
    run_name: str = Field(default="", description="Argo workflow run 名称（用于日志关联）")
    project_id: str = Field(default="", description="项目 ID（用于日志关联）")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    # 设计时生成的节点（可选，用于继续而非重新生成）
    existing_nodespec: Optional[str] = Field(default=None, description="设计时已生成的 nodespec.yaml")
    existing_run_sh: Optional[str] = Field(default=None, description="设计时已生成的 run.sh")
    prefab_node_id: Optional[str] = Field(
        default=None,
        description="Prefab 节点 ID：API 从 proj/tmp/<node_id>/ 或 userdata/nodes/ 读取预生成 nodespec。",
    )
    output_ports: Optional[list[str]] = Field(
        default=None,
        description="输出端口名列表（如 ['O1','O2']），供 Agent port_mapping 参考",
    )
    input_ports: Optional[list[str]] = Field(
        default=None,
        description="输入端口名列表（如 ['xyz_geometry','method']），供 prompt 列出所有端口",
    )


class NodeGenAPIResponse(BaseModel):
    """POST /api/v1/agents/node 响应体。"""
    node_name: str
    nodespec_yaml: str
    run_sh: Optional[str] = None
    input_templates: dict[str, str] = Field(default_factory=dict)
    saved_path: Optional[str] = None
    evaluation: Optional[EvaluationResult] = None
    error: Optional[str] = None
    outputs: dict[str, str] = Field(
        default_factory=dict,
        description="Sandbox output port values (for Argo wrapper to write to /mf/output/).",
    )


class NodeAcceptRequest(BaseModel):
    """POST /api/v1/agents/node/accept 请求体 — 将生成的节点持久化到 userdata/nodes/。"""
    node_name: str = Field(..., description="节点名称（来自生成结果的 metadata.name）")
    nodespec_yaml: str = Field(..., description="nodespec.yaml 内容")
    run_sh: Optional[str] = Field(default=None, description="profile/run.sh 内容")
    input_templates: dict[str, str] = Field(default_factory=dict, description="输入模板 {文件名: 内容}")
    category: str = Field(default="chemistry", description="节点分类目录")


class NodeAcceptResponse(BaseModel):
    """POST /api/v1/agents/node/accept 响应体。"""
    node_name: str = Field(..., description="最终节点名（可能带后缀）")
    saved_path: str = Field(..., description="保存路径")
    collision_renamed: bool = Field(default=False, description="是否因重名而自动重命名")


# ─── Ephemeral Node Agent (Runtime) ────────────────────────────────────────────

class EphemeralGenRequest(BaseModel):
    """POST /api/v1/agents/ephemeral 请求体。"""
    description: str = Field(..., description="临时节点功能描述")
    ports: dict[str, Any] = Field(default_factory=dict, description="端口声明 {'inputs': N, 'outputs': M}")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文（upstream/downstream/sweep/onboard）")
    input_data: dict[str, str] = Field(default_factory=dict, description="真实输入数据 {port_name: content}")
    iteration: int = Field(default=0, description="第几轮（0 = 首次）")
    prev_script: str = Field(default="", description="上一轮的脚本")
    prev_stderr: str = Field(default="", description="上一轮的执行错误")
    vision_feedback: list[str] = Field(default_factory=list, description="视觉评估器的反馈")
    run_name: str = Field(default="", description="Argo workflow run 名称（用于日志关联）")
    project_id: str = Field(default="", description="项目 ID（用于日志关联）")


class EphemeralGenResponse(BaseModel):
    """POST /api/v1/agents/ephemeral 响应体。"""
    script: str = Field(..., description="生成的 Python 脚本")
    stdout: str = Field(default="", description="执行 stdout")
    stderr: str = Field(default="", description="执行 stderr")
    return_code: int = Field(default=-1, description="执行返回码")
    success: bool = Field(default=False, description="是否执行成功")
    generated_files: list[str] = Field(default_factory=list, description="生成的文件列表")
    image_files: list[str] = Field(default_factory=list, description="图片文件路径列表")


class EphemeralEvalRequest(BaseModel):
    """POST /api/v1/agents/ephemeral/evaluate 请求体。"""
    description: str = Field(..., description="临时节点功能描述")
    ports: dict[str, Any] = Field(default_factory=dict, description="端口声明")
    script: str = Field(default="", description="执行的 Python 脚本")
    stdout: str = Field(default="", description="执行 stdout")
    stderr: str = Field(default="", description="执行 stderr")
    image_base64_list: list[str] = Field(default_factory=list, description="base64 编码的图片列表")
    run_name: str = Field(default="", description="Argo workflow run 名称（用于日志关联）")
    project_id: str = Field(default="", description="项目 ID（用于日志关联）")


class EphemeralEvalResponse(BaseModel):
    """POST /api/v1/agents/ephemeral/evaluate 响应体。"""
    passed: bool = Field(default=False, description="是否通过评估")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


# ─── Save Session ─────────────────────────────────────────────────────────────

class SaveSessionRequest(BaseModel):
    """POST /api/v1/agents/save-session 请求体。"""
    session_id: str = Field(..., description="会话 ID（前端生成的唯一标识）")
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="前端 ChatMessage 列表（完整对话历史）",
    )


class SaveSessionResponse(BaseModel):
    """POST /api/v1/agents/save-session 响应体。"""
    saved: bool
    session_id: str
    path: str = Field(default="", description="保存路径（相对于项目根目录）")
    message_count: int = Field(default=0)
