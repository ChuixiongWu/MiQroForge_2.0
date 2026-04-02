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
    """POST /api/v1/agents/node 请求体。"""
    semantic_type: str = Field(..., description="语义类型，如 'geometry-optimization'")
    description: str = Field(..., description="节点功能详细描述")
    target_software: Optional[str] = Field(default=None, description="目标软件，如 'ORCA'")
    target_method: Optional[str] = Field(default=None, description="目标计算方法，如 'B3LYP'")
    category: str = Field(default="chemistry", description="节点分类目录")
    session_id: Optional[str] = Field(default=None, description="会话 ID，用于日志归组")


class NodeGenAPIResponse(BaseModel):
    """POST /api/v1/agents/node 响应体。"""
    node_name: str
    nodespec_yaml: str
    run_sh: Optional[str] = None
    input_templates: dict[str, str] = Field(default_factory=dict)
    saved_path: Optional[str] = None
    evaluation: Optional[EvaluationResult] = None
    error: Optional[str] = None


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
