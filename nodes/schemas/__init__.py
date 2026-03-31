"""MiQroForge 2.0 节点规范 Schema 库。

本包定义了节点的完整规格体系（三层实体模型 + 双通道 I/O），
是节点库、Argo YAML 生成、Agent 检索的 **Single Source of Truth**。

Quick reference::

    from nodes.schemas import (
        # 元数据
        NodeType, NodeCategory, NodeTags, NodeMetadata,
        # 资源
        ComputeResources, LightweightResources,
        # Stream I/O
        StreamIOCategory,
        PhysicalQuantityType, SoftwareDataPackageType,
        LogicValueType, ReportObjectType,
        StreamInputPort, StreamOutputPort,
        OnBoardInput, OnBoardOutput,
        # 基础镜像
        BaseImageSpec, BaseImageRegistry,
        # 完整节点
        NodeSpec,
        ComputeExecutionConfig, LightweightExecutionConfig,
        # 连接校验
        validate_connection, ConnectionValidationResult,
        # 单位
        PhysicalUnit, KNOWN_UNITS, convert_value,
    )
"""

# ── semantic_registry.py ──────────────────────────────────────────────────
from .semantic_registry import (
    SemanticRegistry,
    SemanticTypeEntry,
    load_semantic_registry,
    reload_semantic_registry,
)

# ── base.py ──────────────────────────────────────────────────────────────
from .base import (
    NodeCategory,
    NodeMetadata,
    NodeTags,
    NodeType,
)

# ── resources.py ─────────────────────────────────────────────────────────
from .resources import (
    ComputeResources,
    LightweightResources,
    ResourceType,
)

# ── units.py ─────────────────────────────────────────────────────────────
from .units import (
    KNOWN_UNITS,
    PhysicalUnit,
    UnitConversionError,
    convert_value,
)

# ── io.py ────────────────────────────────────────────────────────────────
from .io import (
    GateDefault,
    LogicValueKind,
    LogicValueType,
    OnBoardInput,
    OnBoardInputKind,
    OnBoardOutput,
    PhysicalQuantityType,
    ReportFormat,
    ReportObjectType,
    SoftwareDataPackageType,
    StreamIOCategory,
    StreamInputPort,
    StreamOutputPort,
)

# ── base_image.py ────────────────────────────────────────────────────────
from .base_image import (
    BaseImageRegistry,
    BaseImageSpec,
)

# ── node.py ──────────────────────────────────────────────────────────────
from .node import (
    ComputeExecutionConfig,
    LightweightExecutionConfig,
    NodeSpec,
)

# ── connection.py ────────────────────────────────────────────────────────
from .connection import (
    ConnectionValidationResult,
    validate_connection,
)

__all__ = [
    # semantic_registry
    "SemanticRegistry",
    "SemanticTypeEntry",
    "load_semantic_registry",
    "reload_semantic_registry",
    # base
    "NodeType",
    "NodeCategory",
    "NodeTags",
    "NodeMetadata",
    # resources
    "ResourceType",
    "ComputeResources",
    "LightweightResources",
    # units
    "PhysicalUnit",
    "KNOWN_UNITS",
    "convert_value",
    "UnitConversionError",
    # io
    "StreamIOCategory",
    "PhysicalQuantityType",
    "SoftwareDataPackageType",
    "LogicValueKind",
    "LogicValueType",
    "ReportFormat",
    "ReportObjectType",
    "StreamInputPort",
    "StreamOutputPort",
    "OnBoardInputKind",
    "OnBoardInput",
    "OnBoardOutput",
    "GateDefault",
    # base_image
    "BaseImageSpec",
    "BaseImageRegistry",
    # node
    "ComputeExecutionConfig",
    "LightweightExecutionConfig",
    "NodeSpec",
    # connection
    "ConnectionValidationResult",
    "validate_connection",
]
