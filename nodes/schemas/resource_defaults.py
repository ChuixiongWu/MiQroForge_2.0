"""Resource defaults — 加载 resource_defaults.yaml 配置。

当 ``parametrize`` 引用的参数在 ``onboard_inputs`` 中不存在时，
系统会根据此配置自动生成对应的 ``OnBoardInput``。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).parent / "resource_defaults.yaml"


@lru_cache(maxsize=1)
def get_resource_defaults() -> dict[str, dict[str, Any]]:
    """加载并缓存 resource_defaults.yaml。

    Returns:
        dict[resource_field, default_input_config]
    """
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}
