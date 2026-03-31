"""MF 工作流数据模型。

定义用户编写的 MF 格式工作流的 Pydantic 模型：
- :class:`MFNodeInstance` — 工作流中的节点实例
- :class:`MFConnection` — 节点间的连线
- :class:`QualityGateOverride` — 单个质量门控的策略覆盖
- :class:`MFWorkflow` — 完整的 MF 工作流定义
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from nodes.schemas.io import GateDefault


class MFNodeInstance(BaseModel):
    """工作流中的一个节点实例。

    节点解析优先级：``node`` → ``nodespec_path`` → ``inline_nodespec``。
    三选一，不得同时指定多个。
    """

    id: str = Field(
        ...,
        description="节点实例 ID，在工作流内唯一。",
    )
    node: Optional[str] = Field(
        default=None,
        description="节点名称（按名称从节点库中查找）。",
    )
    nodespec_path: Optional[str] = Field(
        default=None,
        description="节点规格文件路径（相对于项目根目录）。",
    )
    inline_nodespec: Optional[dict[str, Any]] = Field(
        default=None,
        description="内联节点规格定义（仅开发/测试用）。",
    )
    onboard_params: dict[str, Any] = Field(
        default_factory=dict,
        description="On-board 参数值。",
    )

    @model_validator(mode="after")
    def _check_node_source(self) -> MFNodeInstance:
        """确保 node / nodespec_path / inline_nodespec 三选一。"""
        sources = [
            ("node", self.node),
            ("nodespec_path", self.nodespec_path),
            ("inline_nodespec", self.inline_nodespec),
        ]
        provided = [name for name, val in sources if val is not None]
        if len(provided) == 0:
            raise ValueError(
                "必须提供 node, nodespec_path 或 inline_nodespec 之一"
            )
        if len(provided) > 1:
            raise ValueError(
                f"node, nodespec_path, inline_nodespec 只能三选一，"
                f"当前同时指定了: {', '.join(provided)}"
            )
        return self


class MFConnection(BaseModel):
    """节点间的一条连线。

    格式：``node_id.port_name``
    """

    from_: str = Field(
        ...,
        alias="from",
        description="源端口，格式 'node_id.port_name'。",
    )
    to: str = Field(
        ...,
        description="目标端口，格式 'node_id.port_name'。",
    )

    model_config = {"populate_by_name": True}

    @property
    def source_node_id(self) -> str:
        """源节点 ID。"""
        return self.from_.split(".", 1)[0]

    @property
    def source_port_name(self) -> str:
        """源端口名称。"""
        return self.from_.split(".", 1)[1]

    @property
    def target_node_id(self) -> str:
        """目标节点 ID。"""
        return self.to.split(".", 1)[0]

    @property
    def target_port_name(self) -> str:
        """目标端口名称。"""
        return self.to.split(".", 1)[1]


class QualityGateOverride(BaseModel):
    """单个质量门控的策略覆盖。

    允许工作流级别对特定节点的 quality gate 行为进行 override。
    """

    node_id: str = Field(
        ...,
        description="目标节点实例 ID。",
    )
    gate_name: str = Field(
        ...,
        description="Gate 名称（onboard_output.name，quality_gate=True 的那个）。",
    )
    action: GateDefault = Field(
        ...,
        description="覆盖的策略：must_pass / warn / ignore。",
    )


class MFWorkflow(BaseModel):
    """MF 格式的完整工作流定义。

    用户只需选节点 + 填参数 + 连线，不碰容器。
    """

    mf_version: str = Field(
        default="1.0",
        description="MF 工作流格式版本。",
    )
    name: str = Field(
        ...,
        description="工作流名称。",
    )
    description: str = Field(
        default="",
        description="工作流描述。",
    )
    namespace: str = Field(
        default="miqroforge-v2",
        description="Kubernetes 命名空间。",
    )
    global_params: dict[str, Any] = Field(
        default_factory=dict,
        description="全局参数。",
    )
    nodes: list[MFNodeInstance] = Field(
        ...,
        min_length=1,
        description="节点实例列表。",
    )
    connections: list[MFConnection] = Field(
        default_factory=list,
        description="节点间连线列表。",
    )
    quality_policy: list[QualityGateOverride] = Field(
        default_factory=list,
        description=(
            "Quality Gate 策略覆盖列表。"
            "未在此列表中的 Gate 使用节点 NodeSpec 中定义的 gate_default。"
        ),
    )

    @model_validator(mode="after")
    def _validate_unique_node_ids(self) -> MFWorkflow:
        """确保节点 ID 在工作流内唯一。"""
        seen: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"节点 ID 重复: {node.id!r}")
            seen.add(node.id)
        return self
