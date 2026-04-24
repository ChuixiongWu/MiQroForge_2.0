"""共享参数表 — canonical name 到软件原生关键字的编译时映射。

``shared_params.yaml`` 是节点 OnBoardInput 参数的**唯一事实来源**。
当节点设置 ``_shared_param`` 时，以下字段从本表推导，无需在 nodespec 中重复声明：

- ``kind`` — 参数数据类型（从 categories 元数据）
- ``display_name`` — 显示名称（从 categories 元数据）
- ``description`` — 参数说明（从 categories 元数据）
- ``allow_other`` — 是否允许自定义输入（从 categories 元数据）
- ``allowed_values`` — 可选值列表（从条目按 software 过滤）

编译器在生成 mf_node_params.sh 时，将 canonical 值翻译为软件原生关键字。

用法::

    from nodes.schemas.shared_params import load_shared_params

    sp = load_shared_params()
    native = sp.resolve("PBE0", "gaussian", "functionals")
    # → "PBE1PBE"

    meta = sp.get_category_meta("functionals")
    # → CategoryMeta(kind="string", display_name="DFT Functional", allow_other=True)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


_CONFIG_PATH = Path(__file__).parent / "shared_params.yaml"


# ── 数据模型 ─────────────────────────────────────────────────────────────

class CategoryMeta(BaseModel):
    """共享参数类别的元数据。"""

    kind: str = Field(
        default="string",
        description="参数数据类型（string / integer / float / boolean / enum）",
    )
    display_name: str = Field(
        default="",
        description="该类别的默认显示名称，用于自动填充 OnBoardInput.display_name",
    )
    description: str = Field(
        default="",
        description="该类别的默认参数说明，用于自动填充 OnBoardInput.description",
    )
    allow_other: bool = Field(
        default=True,
        description="是否允许用户输入不在列表中的自定义值",
    )


class SharedParamEntry(BaseModel):
    """单个 canonical 参数值的跨软件映射。"""

    display_name: str = Field(description="人类可读名称")
    gaussian: Optional[str] = Field(default=None, description="Gaussian 原生关键字")
    psi4: Optional[str] = Field(default=None, description="Psi4 原生关键字")
    orca: Optional[str] = Field(default=None, description="ORCA 原生关键字")
    cp2k: Optional[str] = Field(default=None, description="CP2K 原生关键字")

    def for_software(self, software: str) -> Optional[str]:
        """获取指定软件的原生关键字。不存在返回 None。"""
        return getattr(self, software, None)


class SharedParams(BaseModel):
    """完整的共享参数表。"""

    categories: dict[str, CategoryMeta] = Field(
        default_factory=dict,
        description="每个参数类别的元数据（kind / display_name / description / allow_other）",
    )
    functionals: dict[str, SharedParamEntry] = Field(
        default_factory=dict,
        description="DFT 泛函 canonical name → 跨软件映射",
    )
    basis_sets: dict[str, SharedParamEntry] = Field(
        default_factory=dict,
        description="基组 canonical name → 跨软件映射",
    )
    dispersions: dict[str, SharedParamEntry] = Field(
        default_factory=dict,
        description="色散校正 canonical name → 跨软件映射",
    )

    def resolve(
        self,
        canonical: str,
        software: str,
        category: str,
    ) -> Optional[str]:
        """将 canonical name 翻译为软件原生关键字。

        Parameters:
            canonical: canonical name (如 "PBE0", "def2-SVP", "D3BJ")
            software: 软件名 (gaussian / psi4 / orca / cp2k)
            category: 参数类别 (functionals / basis_sets / dispersions)

        Returns:
            软件原生关键字，或 None（canonical 不存在或该软件不支持）
        """
        table: dict[str, SharedParamEntry] = getattr(self, category, {})
        entry = table.get(canonical)
        if entry is None:
            return None
        return entry.for_software(software)

    def available_canonical_names(self, category: str) -> list[str]:
        """列出指定类别下所有 canonical name。"""
        table: dict[str, SharedParamEntry] = getattr(self, category, {})
        return list(table.keys())

    def available_for_software(
        self, software: str, category: str,
    ) -> list[str]:
        """列出指定软件+类别下可用的 canonical name（过滤掉 null 映射）。"""
        table: dict[str, SharedParamEntry] = getattr(self, category, {})
        return [
            name
            for name, entry in table.items()
            if entry.for_software(software) is not None
        ]

    def get_category_meta(self, category: str) -> CategoryMeta:
        """获取指定类别的元数据。不存在时返回默认值。"""
        return self.categories.get(category, CategoryMeta())


# ── 加载器 ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_shared_params() -> SharedParams:
    """加载并缓存 shared_params.yaml。

    Returns:
        校验后的 SharedParams 实例。

    Raises:
        FileNotFoundError: 配置文件不存在。
        pydantic.ValidationError: 数据格式校验失败。
    """
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"共享参数表不存在: {_CONFIG_PATH}\n"
            f"请创建 shared_params.yaml。"
        )
    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # 去掉顶层 version 字段，只保留 categories/functionals/basis_sets/dispersions
    data.pop("version", None)
    return SharedParams.model_validate(data)
