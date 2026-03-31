"""agents/tools/semantic_registry.py — 语义类型注册表查询工具。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def query_semantic_registry(query: str = "") -> dict[str, Any]:
    """查询语义类型注册表，返回所有已知的语义计算类型。

    Args:
        query: 可选的关键词过滤（为空则返回全部）

    Returns:
        语义类型字典，格式：{type_key: {display_name, description, domain}}
    """
    from pathlib import Path
    import yaml

    registry_path = Path(__file__).parent.parent.parent / "nodes" / "schemas" / "semantic_registry.yaml"

    if not registry_path.exists():
        return {"error": "语义类型注册表不存在"}

    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    types = data.get("types", {})

    if query:
        query_lower = query.lower()
        types = {
            k: v for k, v in types.items()
            if query_lower in k.lower()
            or query_lower in v.get("display_name", "").lower()
            or query_lower in v.get("description", "").lower()
        }

    return types
