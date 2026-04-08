"""节点扫描器 — 遍历 nodes/ 目录生成索引。

通过复用现有的 :class:`NodeSpec.from_yaml()` 解析 nodespec.yaml，
将其转换为 :class:`NodeIndexEntry`，生成 ``nodes/node_index.yaml``。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from nodes.schemas import NodeSpec
from nodes.schemas.io import (
    LogicValueType,
    PhysicalQuantityType,
    ReportObjectType,
    SoftwareDataPackageType,
    StreamInputPort,
    StreamOutputPort,
)
from nodes.schemas.semantic_registry import load_semantic_registry

from .models import NodeIndex, NodeIndexEntry, OnBoardInputSummary, OnBoardOutputSummary, PortSummary

# 扫描时跳过的目录名
_SKIP_DIRS = {"schemas", "base_images", "__pycache__", ".git", "node_modules"}


def scan_nodes(
    project_root: Path | None = None,
    *,
    skip_test: bool = False,
) -> NodeIndex:
    """扫描 nodes/ 和 userdata/nodes/ 目录下的所有 nodespec.yaml，生成 NodeIndex。

    Parameters:
        project_root: 项目根目录。默认为当前工作目录。
        skip_test: 是否跳过 test/ 目录下的节点。

    Returns:
        NodeIndex 实例。
    """
    if project_root is None:
        project_root = Path.cwd()

    entries: list[NodeIndexEntry] = []

    # 扫描目录列表：系统节点库 + 用户数据目录
    scan_targets: list[tuple[Path, str]] = [
        (project_root / "nodes", "system"),
        (project_root / "userdata" / "nodes", "user"),
    ]

    for nodes_dir, source in scan_targets:
        if not nodes_dir.exists():
            continue

        for spec_path in sorted(nodes_dir.rglob("nodespec.yaml")):
            # 跳过指定目录
            rel_parts = spec_path.relative_to(nodes_dir).parts
            if any(part in _SKIP_DIRS for part in rel_parts):
                continue

            # 可选跳过 test/ 目录
            if skip_test and "test" in rel_parts:
                continue

            try:
                spec = NodeSpec.from_yaml(spec_path)
            except Exception as e:
                print(f"  [WARN] 跳过无效的 nodespec: {spec_path} ({e})")
                continue

            # 计算相对路径
            nodespec_rel = str(spec_path.relative_to(project_root))

            entry = _spec_to_entry(spec, nodespec_rel, source=source)
            entries.append(entry)

    # 按 category → name 排序
    entries.sort(key=lambda e: (e.category, e.name))

    return NodeIndex(
        generated_at=_now_iso(),
        total_nodes=len(entries),
        entries=entries,
    )


def write_index(index: NodeIndex, project_root: Path | None = None) -> Path:
    """将 NodeIndex 写入 nodes/node_index.yaml。

    Returns:
        写入的文件路径。
    """
    if project_root is None:
        project_root = Path.cwd()

    output_path = project_root / "nodes" / "node_index.yaml"
    data = index.model_dump(mode="json")
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    return output_path


def load_index(project_root: Path | None = None) -> NodeIndex:
    """从 nodes/node_index.yaml 加载已有索引。

    Raises:
        FileNotFoundError: 索引文件不存在。
    """
    if project_root is None:
        project_root = Path.cwd()

    index_path = project_root / "nodes" / "node_index.yaml"
    if not index_path.exists():
        raise FileNotFoundError(
            f"索引文件不存在: {index_path}\n"
            f"请运行 'mf2 nodes reindex' 或 'python -m node_index.cli reindex' 生成。"
        )

    with index_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return NodeIndex.model_validate(data)


# ═══════════════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════════════


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _port_summary(port: StreamInputPort | StreamOutputPort, direction: str) -> PortSummary:
    """将 Stream 端口转换为 PortSummary。"""
    io_type = port.io_type
    category = io_type.category.value if hasattr(io_type.category, "value") else str(io_type.category)

    # 生成细节摘要
    detail = _io_type_detail(io_type)

    return PortSummary(
        name=port.name,
        display_name=port.display_name,
        category=category,
        detail=detail,
        direction=direction,
    )


def _io_type_detail(io_type) -> str:
    """根据 I/O 类型生成简短的细节字符串。"""
    if isinstance(io_type, PhysicalQuantityType):
        return f"{io_type.unit}/{io_type.shape}"
    elif isinstance(io_type, SoftwareDataPackageType):
        return f"{io_type.ecosystem}/{io_type.data_type}"
    elif isinstance(io_type, LogicValueType):
        return f"{io_type.kind.value}"
    elif isinstance(io_type, ReportObjectType):
        return f"{io_type.format.value}"
    return ""


def _spec_to_entry(
    spec: NodeSpec,
    nodespec_path: str,
    source: str = "system",
) -> NodeIndexEntry:
    """将 NodeSpec 转换为 NodeIndexEntry。"""
    m = spec.metadata

    stream_inputs = [
        _port_summary(p, "input") for p in spec.stream_inputs
    ]
    stream_outputs = [
        _port_summary(p, "output") for p in spec.stream_outputs
    ]

    # 从注册表填充 semantic_display_name
    semantic_display_name: str | None = None
    if m.semantic_type:
        try:
            registry = load_semantic_registry()
            semantic_display_name = registry.display_name(m.semantic_type)
        except Exception:
            pass

    # On-Board 输入完整定义
    onboard_inputs = [
        OnBoardInputSummary(
            name=p.name,
            display_name=p.display_name,
            kind=p.kind.value,
            default=p.default,
            description=p.description,
            allowed_values=p.allowed_values,
            min_value=p.min_value,
            max_value=p.max_value,
            unit=p.unit,
            multiple_input=p.multiple_input,
        )
        for p in spec.onboard_inputs
    ]

    # On-Board 输出完整定义（含 quality gate 字段）
    onboard_outputs = [
        OnBoardOutputSummary(
            name=o.name,
            display_name=o.display_name,
            kind=o.kind.value,
            unit=o.unit,
            description=o.description,
            quality_gate=o.quality_gate,
            gate_default=o.gate_default.value,
            gate_description=o.gate_description,
        )
        for o in spec.onboard_outputs
    ]

    return NodeIndexEntry(
        name=m.name,
        version=m.version,
        display_name=m.display_name or m.name.replace("-", " ").title(),
        description=m.description,
        node_type=m.node_type.value,
        category=m.category.value,
        base_image_ref=m.base_image_ref,
        nodespec_path=nodespec_path,
        source=source,
        software=m.tags.software,
        semantic_type=m.semantic_type,
        semantic_display_name=semantic_display_name,
        methods=m.tags.method,
        domains=m.tags.domain,
        capabilities=m.tags.capabilities,
        keywords=m.tags.keywords,
        resources_cpu=float(spec.resources.cpu_cores),
        resources_memory_gb=float(spec.resources.memory_gb),
        stream_inputs=stream_inputs,
        stream_outputs=stream_outputs,
        onboard_inputs=onboard_inputs,
        onboard_outputs=onboard_outputs,
    )
