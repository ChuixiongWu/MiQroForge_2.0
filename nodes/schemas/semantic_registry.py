"""语义类型注册表。

提供 ``semantic_registry.yaml`` 的 Pydantic 模型和加载器，
确保节点的 ``semantic_type`` 字段来自已知的注册类型，
同时为前端和 RAG 提供统一的 display_name / description。
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# 注册表文件路径（与本文件同目录）
_REGISTRY_PATH = Path(__file__).parent / "semantic_registry.yaml"


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class SemanticTypeEntry(BaseModel):
    """单个语义类型的元数据。"""

    display_name: str = Field(
        ...,
        description="人类可读的显示名称。",
    )
    description: str = Field(
        default="",
        description="该语义类型的详细描述。",
    )
    domain: str = Field(
        default="",
        description="所属领域，如 'computational-chemistry'。",
    )


class SemanticRegistry(BaseModel):
    """完整的语义类型注册表。"""

    version: str = Field(default="1.0")
    types: dict[str, SemanticTypeEntry] = Field(default_factory=dict)

    def is_valid(self, semantic_type: str) -> bool:
        """返回 semantic_type 是否在注册表中。"""
        return semantic_type in self.types

    def get(self, semantic_type: str) -> Optional[SemanticTypeEntry]:
        """获取注册表条目，不存在时返回 None。"""
        return self.types.get(semantic_type)

    def display_name(self, semantic_type: str) -> str:
        """获取 display_name，不存在时回退到 kebab-case 转换。"""
        entry = self.types.get(semantic_type)
        if entry:
            return entry.display_name
        return semantic_type.replace("-", " ").title()

    def all_keys(self) -> list[str]:
        """返回所有已注册的语义类型 key（有序）。"""
        return sorted(self.types.keys())


# ---------------------------------------------------------------------------
# 加载器（带 lru_cache）
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def load_semantic_registry(
    registry_path: str | None = None,
) -> SemanticRegistry:
    """加载并解析 semantic_registry.yaml。

    Parameters:
        registry_path: 注册表文件路径。为 None 时使用默认路径。

    Returns:
        SemanticRegistry 实例（lru_cache 缓存，避免重复磁盘读取）。
    """
    path = Path(registry_path) if registry_path else _REGISTRY_PATH
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SemanticRegistry.model_validate(data)


def reload_semantic_registry(
    registry_path: str | None = None,
) -> SemanticRegistry:
    """清除缓存并重新加载注册表。

    在注册表文件被修改后调用此函数以获取最新内容。

    Parameters:
        registry_path: 注册表文件路径。为 None 时使用默认路径。

    Returns:
        SemanticRegistry 实例。
    """
    load_semantic_registry.cache_clear()
    return load_semantic_registry(registry_path)
