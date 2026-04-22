"""项目管理 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    icon: str = ""
    created_at: str
    updated_at: str
    order: int = 0
    canvas_node_count: int = 0
    run_count: int = 0
    conversation_count: int = 0


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = ""
    icon: str = ""


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    icon: str | None = None
    order: int | None = None


class ProjectDuplicateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)


class ProjectReorderRequest(BaseModel):
    ids: list[str]


class ProjectBatchDeleteRequest(BaseModel):
    ids: list[str]


class ProjectListResponse(BaseModel):
    total: int
    projects: list[ProjectMeta]


class CanvasState(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class ConversationMeta(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ConversationCreateRequest(BaseModel):
    title: str = Field("New Chat", min_length=1, max_length=200)


class SnapshotMeta(BaseModel):
    id: str
    name: str
    created_at: str
    canvas_node_count: int = 0


class SnapshotListResponse(BaseModel):
    total: int
    snapshots: list[SnapshotMeta]
