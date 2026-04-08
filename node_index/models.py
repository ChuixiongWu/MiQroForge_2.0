"""节点索引 Pydantic 模型。

定义 :class:`NodeIndexEntry`（单个节点的索引摘要）和
:class:`NodeIndex`（完整索引文件的结构）。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PortSummary(BaseModel):
    """端口摘要 — 索引中对 Stream 端口的精简描述。"""

    name: str
    display_name: str
    category: str = Field(
        ...,
        description="Stream I/O 类别：physical_quantity / software_data_package / logic_value / report_object",
    )
    detail: str = Field(
        default="",
        description="端口细节摘要，如 'orca/gbw-file' 或 'energy/Ha/scalar'。",
    )
    direction: str = Field(
        default="input",
        description="端口方向：input / output",
    )


class OnBoardInputSummary(BaseModel):
    """On-Board 输入参数的完整摘要 — 索引中存储完整定义，供拖入画布时直接使用。"""

    name: str
    display_name: str
    kind: str = Field(..., description="string | integer | float | boolean | enum | textarea")
    default: Any = None
    description: str = ""
    allowed_values: Optional[list[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    multiple_input: bool = Field(
        default=False,
        description="是否支持多输入模式（parallel sweep）。",
    )


class OnBoardOutputSummary(BaseModel):
    """On-Board 输出参数的完整摘要 — 包含 quality gate 字段。"""

    name: str
    display_name: str
    kind: str = Field(..., description="string | integer | float | boolean | enum")
    unit: Optional[str] = None
    description: str = ""
    quality_gate: bool = False
    gate_default: str = "must_pass"   # must_pass | warn | ignore
    gate_description: str = ""


class NodeIndexEntry(BaseModel):
    """单个节点的索引条目。"""

    name: str = Field(..., description="节点唯一标识（metadata.name）")
    version: str = Field(..., description="节点版本")
    display_name: str = Field(..., description="人类可读的显示名称")
    description: str = Field(default="", description="节点功能描述")
    node_type: str = Field(..., description="compute / lightweight")
    category: str = Field(..., description="节点分类")
    base_image_ref: Optional[str] = Field(default=None, description="基础镜像引用")
    nodespec_path: str = Field(..., description="nodespec.yaml 相对于项目根目录的路径")
    source: str = Field(default="system", description="节点来源：system（系统内置）| user（AI 生成或用户自定义）")

    # 标签
    software: Optional[str] = Field(default=None, description="底层计算软件")
    semantic_type: Optional[str] = Field(default=None, description="化学语义操作类型，如 'geometry-optimization'")
    semantic_display_name: Optional[str] = Field(default=None, description="语义类型的人类可读名称（来自注册表）")
    methods: list[str] = Field(default_factory=list, description="计算方法标签")
    domains: list[str] = Field(default_factory=list, description="应用领域标签")
    capabilities: list[str] = Field(default_factory=list, description="功能标签")
    keywords: list[str] = Field(default_factory=list, description="自由关键词")

    # 资源摘要（供节点卡片底栏显示）
    resources_cpu: float = Field(default=0.0, description="CPU 核数")
    resources_memory_gb: float = Field(default=0.0, description="内存 GiB")

    # Stream 端口摘要
    stream_inputs: list[PortSummary] = Field(default_factory=list)
    stream_outputs: list[PortSummary] = Field(default_factory=list)

    # On-Board 参数完整定义（拖入画布时直接使用，无需二次读取 nodespec.yaml）
    onboard_inputs: list[OnBoardInputSummary] = Field(default_factory=list)
    onboard_outputs: list[OnBoardOutputSummary] = Field(default_factory=list)


class NodeIndex(BaseModel):
    """完整节点索引 — 对应 nodes/node_index.yaml。"""

    generated_at: str = Field(..., description="索引生成时间 (ISO 8601)")
    mf_version: str = Field(default="1.0", description="MF 格式版本")
    total_nodes: int = Field(default=0, description="索引中的节点总数")
    entries: list[NodeIndexEntry] = Field(default_factory=list, description="节点条目列表")
