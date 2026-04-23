"""运行状态 API 模型。"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class RunSummaryResponse(BaseModel):
    name: str
    namespace: str
    uid: str
    phase: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    labels: dict[str, str] = {}


class RunListResponse(BaseModel):
    total: int
    runs: list[RunSummaryResponse]


class RunDetailResponse(BaseModel):
    name: str
    namespace: str
    phase: str
    raw: dict[str, Any] = {}


class RunLogsResponse(BaseModel):
    name: str
    logs: str
