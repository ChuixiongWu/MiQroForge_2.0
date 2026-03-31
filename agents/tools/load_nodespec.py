"""agents/tools/load_nodespec.py — 按名称加载完整 NodeSpec。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def load_nodespec_by_name(node_name: str) -> dict[str, Any]:
    """按节点名称加载完整 NodeSpec（YAML 格式序列化为字典）。

    Args:
        node_name: 节点名称（如 "orca-geo-opt"）

    Returns:
        完整 NodeSpec 字典，若未找到则返回 {"error": "..."}
    """
    from pathlib import Path
    from api.config import get_settings

    settings = get_settings()
    project_root = settings.project_root
    userdata_root = settings.userdata_root

    # 在 nodes/ 和 userdata/nodes/ 中搜索
    search_dirs = [project_root / "nodes", userdata_root / "nodes"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for spec_path in search_dir.rglob("nodespec.yaml"):
            if "schemas" in spec_path.parts or "base_images" in spec_path.parts:
                continue
            try:
                from nodes.schemas import NodeSpec
                spec = NodeSpec.from_yaml(spec_path)
                if spec.metadata.name == node_name:
                    return spec.model_dump(mode="json")
            except Exception:
                continue

    return {"error": f"未找到节点: {node_name}"}
