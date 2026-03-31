"""工作流 API 请求/响应模型。"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class WorkflowValidateRequest(BaseModel):
    yaml_content: str


class ValidationIssueResponse(BaseModel):
    location: str
    message: str


class ResolvedNodeResponse(BaseModel):
    name: str
    version: str
    node_type: str


class WorkflowValidateResponse(BaseModel):
    valid: bool
    errors: list[ValidationIssueResponse] = []
    warnings: list[ValidationIssueResponse] = []
    infos: list[ValidationIssueResponse] = []
    resolved_nodes: dict[str, ResolvedNodeResponse] = {}


class WorkflowCompileRequest(BaseModel):
    yaml_content: str


class WorkflowCompileResponse(BaseModel):
    valid: bool
    argo_yaml: str
    configmaps_count: int
    workflow: dict[str, Any] = {}
    configmaps: list[dict[str, Any]] = []


class WorkflowSubmitRequest(BaseModel):
    yaml_content: str


class WorkflowSubmitResponse(BaseModel):
    workflow_name: str
    namespace: str
    uid: str
