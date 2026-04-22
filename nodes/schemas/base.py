"""节点元数据基础类型。

定义节点类型枚举、分类枚举、标签结构、元数据模型。
这些类型被 ``node.py`` 中的 :class:`NodeSpec` 组合使用。
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# 枚举类型
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """节点执行模式。"""

    COMPUTE = "compute"
    """计算节点 — 依赖重量级基础镜像（VASP / Gaussian / ORCA 等）。"""

    LIGHTWEIGHT = "lightweight"
    """轻量节点 — 纯 Python 脚本，使用 python-slim 或预构建镜像。"""


class NodeCategory(str, Enum):
    """节点业务分类。"""

    QUANTUM = "quantum"
    CHEMISTRY = "chemistry"
    PREPROCESSING = "preprocessing"
    POSTPROCESSING = "postprocessing"
    UTILITY = "utility"


# ---------------------------------------------------------------------------
# 标签
# ---------------------------------------------------------------------------

class NodeTags(BaseModel):
    """节点标签 — 供检索与过滤使用。"""

    software: Optional[str] = None
    """底层计算软件名称，如 ``"vasp"``、``"gaussian"``。"""

    version: Optional[str] = None
    """底层计算软件版本，如 ``"6.4.1"``。"""

    method: list[str] = Field(default_factory=list)
    """计算方法标签，如 ``["DFT", "PBE"]``。"""

    domain: list[str] = Field(default_factory=list)
    """应用领域标签，如 ``["solid-state", "molecular"]``。"""

    capabilities: list[str] = Field(default_factory=list)
    """功能标签，如 ``["geometry-optimization", "band-structure"]``。"""

    keywords: list[str] = Field(default_factory=list)
    """自由关键词。"""


# ---------------------------------------------------------------------------
# 节点元数据
# ---------------------------------------------------------------------------

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)


class NodeMetadata(BaseModel):
    """节点的身份信息与分类元数据。"""

    name: str = Field(
        ...,
        description="唯一标识符，小写字母+连字符，如 'vasp-geo-opt'。",
    )
    version: str = Field(
        default="1.0.0",
        description="语义化版本号，如 '1.0.0'。",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="人类可读的显示名称。为空时自动从 name 生成。",
    )
    description: str = Field(
        default="",
        description="节点功能的详细描述。",
    )
    node_type: NodeType
    category: NodeCategory = NodeCategory.UTILITY
    tags: NodeTags = Field(default_factory=NodeTags)
    author: str = Field(
        default="",
        description="节点作者或维护团队。",
    )
    semantic_type: Optional[str] = Field(
        default=None,
        description=(
            "化学语义操作类型，如 'geometry-optimization'。"
            "自由填写 kebab-case，用于 Palette 两段式分组。"
        ),
    )
    base_image_ref: Optional[str] = Field(
        default=None,
        description=(
            "关联的 BaseImageRegistry 条目名称（仅 compute 节点必填）。"
        ),
    )
    deprecated: bool = Field(
        default=False,
        description=(
            "标记节点为已废弃。deprecated 节点在 Palette 中默认隐藏，"
            "但已有的工作流仍可加载和校验。"
        ),
    )

    # ── 校验器 ──────────────────────────────────────────────────────────────

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _NAME_PATTERN.match(v):
            raise ValueError(
                f"name 必须为小写字母+数字，以连字符分隔: {v!r}"
            )
        return v

    @field_validator("semantic_type")
    @classmethod
    def _validate_semantic_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _NAME_PATTERN.match(v):
            raise ValueError(
                f"semantic_type 必须为 kebab-case（小写字母+连字符）: {v!r}"
            )
        # 注册表校验（延迟导入避免循环）
        from .semantic_registry import load_semantic_registry
        registry = load_semantic_registry()
        if not registry.is_valid(v):
            valid_keys = ", ".join(registry.all_keys())
            raise ValueError(
                f"semantic_type {v!r} 未在注册表中注册。"
                f"已注册的类型：{valid_keys}"
            )
        return v

    @model_validator(mode="after")
    def _auto_display_name(self) -> NodeMetadata:
        """display_name 为空时，自动从 name 生成。"""
        if self.display_name is None:
            self.display_name = self.name.replace("-", " ").title()
        return self

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not _SEMVER_PATTERN.match(v):
            raise ValueError(
                f"version 必须符合语义化版本号 (semver): {v!r}"
            )
        return v

    @field_validator("base_image_ref")
    @classmethod
    def _validate_base_image_ref(cls, v: str | None, info) -> str | None:  # noqa: ANN001
        node_type = info.data.get("node_type")
        if node_type == NodeType.COMPUTE and v is None:
            raise ValueError("compute 节点必须指定 base_image_ref")
        if node_type == NodeType.LIGHTWEIGHT and v is not None:
            raise ValueError("lightweight 节点不应指定 base_image_ref")
        return v
