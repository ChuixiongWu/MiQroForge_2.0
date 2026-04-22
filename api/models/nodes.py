"""节点 API 响应模型。"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class PortSummaryResponse(BaseModel):
    name: str
    display_name: str
    category: str
    detail: str
    direction: str


class OnBoardParamResponse(BaseModel):
    """On-Board 输入参数的完整定义，供前端动态渲染表单。"""
    name: str
    display_name: str
    kind: str                          # string | integer | float | boolean | enum | textarea
    default: Any = None
    description: str = ""
    allowed_values: Optional[list[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    multiple_input: bool = False
    resource_param: bool = False


class OnBoardOutputResponse(BaseModel):
    """On-Board 输出的完整定义，包含 quality gate 字段。"""
    name: str
    display_name: str
    kind: str                          # string | integer | float | boolean | enum
    unit: Optional[str] = None
    description: str = ""
    quality_gate: bool = False
    gate_default: str = "must_pass"    # must_pass | warn | ignore
    gate_description: str = ""


class NodeSummaryResponse(BaseModel):
    name: str
    version: str
    display_name: str
    description: str
    node_type: str
    category: str
    semantic_type: Optional[str] = None
    semantic_display_name: Optional[str] = None
    base_image_ref: Optional[str] = None
    nodespec_path: str
    software: Optional[str] = None
    methods: list[str] = []
    domains: list[str] = []
    capabilities: list[str] = []
    keywords: list[str] = []
    deprecated: bool = False
    resources_cpu: float = 0.0
    resources_memory_gb: float = 0.0
    resources_mem_gb: Optional[float] = None
    resources_gpu: float = 0.0
    resources_walltime_hours: float = 0.0
    resources_scratch_disk_gb: float = 0.0
    resources_parallel_tasks: int = 1
    stream_inputs: list[PortSummaryResponse] = []
    stream_outputs: list[PortSummaryResponse] = []
    onboard_inputs_count: int = 0
    onboard_outputs_count: int = 0


class NodeDetailResponse(NodeSummaryResponse):
    onboard_inputs: list[OnBoardParamResponse] = []
    onboard_outputs: list[OnBoardOutputResponse] = []


class NodeListResponse(BaseModel):
    total: int
    nodes: list[NodeSummaryResponse]


class NodeIndexInfoResponse(BaseModel):
    total_nodes: int
    generated_at: str
    mf_version: str


class SemanticTypeEntry(BaseModel):
    """注册表中单个语义类型的描述。"""
    display_name: str
    description: str = ""
    domain: str = ""


class SemanticRegistryResponse(BaseModel):
    """完整注册表响应 — 供前端在启动时加载。"""
    version: str
    types: dict[str, SemanticTypeEntry]


class SemanticTypeGroup(BaseModel):
    semantic_type: str
    display_name: Optional[str] = None
    nodes: list[NodeSummaryResponse]


class SemanticTypesResponse(BaseModel):
    total: int
    groups: list[SemanticTypeGroup]
