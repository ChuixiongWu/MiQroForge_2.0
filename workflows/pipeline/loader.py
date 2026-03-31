"""MF 工作流加载器。

将用户编写的 MF YAML 文件加载为 :class:`MFWorkflow` 模型，
并为每个节点实例解析对应的 :class:`NodeSpec`。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nodes.schemas import NodeSpec

from .models import MFNodeInstance, MFWorkflow


def load_workflow(path: str | Path) -> MFWorkflow:
    """从 YAML 文件加载 MF 工作流。

    Parameters:
        path: MF 工作流 YAML 文件路径。

    Returns:
        校验后的 MFWorkflow 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        pydantic.ValidationError: Schema 校验失败。
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return MFWorkflow.model_validate(data)


def resolve_nodespec(
    node_instance: MFNodeInstance,
    *,
    project_root: Path | None = None,
) -> NodeSpec:
    """解析 MFNodeInstance 对应的 NodeSpec。

    解析优先级：``node`` → ``nodespec_path`` → ``inline_nodespec``。

    Parameters:
        node_instance: 工作流中的节点实例。
        project_root: 项目根目录，用于解析相对路径。默认为当前工作目录。

    Returns:
        校验后的 NodeSpec 实例。

    Raises:
        ValueError: 无法解析节点。
        FileNotFoundError: nodespec 文件不存在。
    """
    if project_root is None:
        project_root = Path.cwd()

    if node_instance.nodespec_path is not None:
        spec_path = project_root / node_instance.nodespec_path
        if not spec_path.exists():
            raise FileNotFoundError(
                f"NodeSpec 文件不存在: {spec_path}"
            )
        return NodeSpec.from_yaml(spec_path)

    if node_instance.inline_nodespec is not None:
        return NodeSpec.model_validate(node_instance.inline_nodespec)

    if node_instance.node is not None:
        return _find_nodespec_by_name(node_instance.node, project_root)

    raise ValueError(
        f"节点 {node_instance.id!r}: 未指定 node, nodespec_path 或 inline_nodespec"
    )


def _find_nodespec_by_name(name: str, project_root: Path) -> NodeSpec:
    """按名称在节点库中查找 NodeSpec。

    遍历 nodes/ 和 userdata/nodes/ 目录下所有 nodespec.yaml 文件，
    找到 metadata.name 匹配的节点。

    Parameters:
        name: 节点名称（metadata.name）。
        project_root: 项目根目录。

    Returns:
        匹配的 NodeSpec。

    Raises:
        ValueError: 未找到匹配的节点。
    """
    # 搜索目录列表：系统节点库 + 用户数据目录
    search_dirs = [
        project_root / "nodes",
        project_root / "userdata" / "nodes",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for spec_path in search_dir.rglob("nodespec.yaml"):
            # 跳过 schemas 目录
            if "schemas" in spec_path.parts or "base_images" in spec_path.parts:
                continue
            try:
                spec = NodeSpec.from_yaml(spec_path)
                if spec.metadata.name == name:
                    return spec
            except Exception:
                # 解析失败的 nodespec 跳过
                continue

    raise ValueError(
        f"节点库中未找到名为 {name!r} 的节点。"
        f"请确认节点已注册在 nodes/ 或 userdata/nodes/ 目录下。"
    )
