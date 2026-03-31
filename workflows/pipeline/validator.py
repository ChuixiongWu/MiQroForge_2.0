"""MF 工作流校验器。

对加载后的 :class:`MFWorkflow` 进行全量校验：
1. 解析每个节点的 NodeSpec
2. 节点 ID 唯一性（已由模型校验）
3. 连接校验（类型匹配 via validate_connection）
4. 必填 stream input 是否都有传入连接
5. 必填 on-board 参数完整性 + 值域检查
6. DAG 无环检查（拓扑排序）
7. 未连接的输出端口 → info 提示
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from nodes.schemas import (
    NodeSpec,
    StreamInputPort,
    StreamOutputPort,
    validate_connection,
)

from .loader import resolve_nodespec
from .models import MFWorkflow, QualityGateOverride


# ═══════════════════════════════════════════════════════════════════════════
# 校验结果模型
# ═══════════════════════════════════════════════════════════════════════════


class ValidationIssue(BaseModel):
    """单条校验问题。"""

    severity: Literal["error", "warning", "info"]
    location: str = Field(
        ...,
        description="问题位置，如 'connection: geo-opt.converged → freq.opt_converged'",
    )
    message: str


class ValidationReport(BaseModel):
    """完整的校验报告。"""

    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    resolved_nodes: dict[str, NodeSpec] = Field(
        default_factory=dict,
        description="节点 ID → 解析后的 NodeSpec（供 compiler 使用）。",
    )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "info"]


# ═══════════════════════════════════════════════════════════════════════════
# 主校验函数
# ═══════════════════════════════════════════════════════════════════════════


def validate_workflow(
    workflow: MFWorkflow,
    *,
    project_root: Path | None = None,
) -> ValidationReport:
    """对 MF 工作流进行全量校验。

    Parameters:
        workflow: 已加载的 MFWorkflow 实例。
        project_root: 项目根目录，用于解析 nodespec 路径。

    Returns:
        ValidationReport，包含所有问题和解析后的 NodeSpec。
    """
    issues: list[ValidationIssue] = []
    resolved_nodes: dict[str, NodeSpec] = {}

    # ── Step 1: 解析每个节点的 NodeSpec ──────────────────────────────────
    for node_inst in workflow.nodes:
        try:
            spec = resolve_nodespec(node_inst, project_root=project_root)
            resolved_nodes[node_inst.id] = spec
        except FileNotFoundError as e:
            issues.append(ValidationIssue(
                severity="error",
                location=f"node: {node_inst.id}",
                message=f"NodeSpec 文件未找到: {e}",
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                location=f"node: {node_inst.id}",
                message=f"NodeSpec 解析失败: {e}",
            ))

    # 如果有节点解析失败，后续校验无法进行
    if len(resolved_nodes) != len(workflow.nodes):
        return ValidationReport(
            valid=False,
            issues=issues,
            resolved_nodes=resolved_nodes,
        )

    # ── Step 2: 连接校验 ─────────────────────────────────────────────────
    # 记录哪些 stream input 已被连接
    connected_inputs: set[tuple[str, str]] = set()  # (node_id, port_name)
    connected_outputs: set[tuple[str, str]] = set()

    for conn in workflow.connections:
        loc = f"connection: {conn.from_} → {conn.to}"

        # 解析 from/to
        src_node_id = conn.source_node_id
        src_port_name = conn.source_port_name
        tgt_node_id = conn.target_node_id
        tgt_port_name = conn.target_port_name

        # 检查节点是否存在
        if src_node_id not in resolved_nodes:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"源节点 {src_node_id!r} 不存在",
            ))
            continue
        if tgt_node_id not in resolved_nodes:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"目标节点 {tgt_node_id!r} 不存在",
            ))
            continue

        src_spec = resolved_nodes[src_node_id]
        tgt_spec = resolved_nodes[tgt_node_id]

        # 查找端口
        src_port = _find_output_port(src_spec, src_port_name)
        tgt_port = _find_input_port(tgt_spec, tgt_port_name)

        if src_port is None:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"源节点 {src_node_id!r} 没有输出端口 {src_port_name!r}",
            ))
            continue
        if tgt_port is None:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"目标节点 {tgt_node_id!r} 没有输入端口 {tgt_port_name!r}",
            ))
            continue

        # 调用 validate_connection
        result = validate_connection(src_port, tgt_port)
        if not result.valid:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"连接类型不匹配: {result.message}",
            ))
        for warn in result.warnings:
            issues.append(ValidationIssue(
                severity="warning",
                location=loc,
                message=warn,
            ))

        connected_inputs.add((tgt_node_id, tgt_port_name))
        connected_outputs.add((src_node_id, src_port_name))

    # ── Step 3: 必填 stream input 检查 ───────────────────────────────────
    for node_inst in workflow.nodes:
        spec = resolved_nodes[node_inst.id]
        for port in spec.stream_inputs:
            if port.required and (node_inst.id, port.name) not in connected_inputs:
                issues.append(ValidationIssue(
                    severity="error",
                    location=f"node: {node_inst.id}.{port.name}",
                    message=f"必填 stream input {port.name!r} 未连接",
                ))

    # ── Step 4: On-board 参数完整性检查 ───────────────────────────────────
    for node_inst in workflow.nodes:
        spec = resolved_nodes[node_inst.id]
        _validate_onboard_params(node_inst, spec, issues)

    # ── Step 5: DAG 无环检查 ──────────────────────────────────────────────
    _validate_dag_acyclic(workflow, issues)

    # ── Step 6: 未连接的输出端口 → info ──────────────────────────────────
    for node_inst in workflow.nodes:
        spec = resolved_nodes[node_inst.id]
        for port in spec.stream_outputs:
            if (node_inst.id, port.name) not in connected_outputs:
                issues.append(ValidationIssue(
                    severity="info",
                    location=f"node: {node_inst.id}.{port.name}",
                    message=f"输出端口 {port.name!r} 未被任何下游节点连接",
                ))

    # ── Step 7: Quality Policy 校验 ───────────────────────────────────────
    _validate_quality_policy(workflow, resolved_nodes, issues)

    has_errors = any(i.severity == "error" for i in issues)
    return ValidationReport(
        valid=not has_errors,
        issues=issues,
        resolved_nodes=resolved_nodes,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════


def _find_output_port(spec: NodeSpec, name: str) -> StreamOutputPort | None:
    """在 NodeSpec 中查找指定名称的输出端口。"""
    for port in spec.stream_outputs:
        if port.name == name:
            return port
    return None


def _find_input_port(spec: NodeSpec, name: str) -> StreamInputPort | None:
    """在 NodeSpec 中查找指定名称的输入端口。"""
    for port in spec.stream_inputs:
        if port.name == name:
            return port
    return None


def _validate_onboard_params(
    node_inst,  # MFNodeInstance
    spec: NodeSpec,
    issues: list[ValidationIssue],
) -> None:
    """校验 on-board 参数完整性和值域。"""
    provided = node_inst.onboard_params

    for param in spec.onboard_inputs:
        loc = f"node: {node_inst.id} param: {param.name}"

        if param.name not in provided:
            if param.default is None:
                issues.append(ValidationIssue(
                    severity="error",
                    location=loc,
                    message=f"必填参数 {param.name!r} 未提供且无默认值",
                ))
            continue

        value = provided[param.name]

        # enum 值域检查
        if param.allowed_values is not None:
            if str(value) not in param.allowed_values:
                issues.append(ValidationIssue(
                    severity="error",
                    location=loc,
                    message=(
                        f"参数 {param.name!r} 的值 {value!r} "
                        f"不在允许范围内: {param.allowed_values}"
                    ),
                ))

        # 数值范围检查
        if param.min_value is not None and isinstance(value, (int, float)):
            if value < param.min_value:
                issues.append(ValidationIssue(
                    severity="error",
                    location=loc,
                    message=(
                        f"参数 {param.name!r} 的值 {value} "
                        f"小于最小值 {param.min_value}"
                    ),
                ))
        if param.max_value is not None and isinstance(value, (int, float)):
            if value > param.max_value:
                issues.append(ValidationIssue(
                    severity="error",
                    location=loc,
                    message=(
                        f"参数 {param.name!r} 的值 {value} "
                        f"大于最大值 {param.max_value}"
                    ),
                ))

    # 检查是否提供了 nodespec 中未定义的参数
    known_params = {p.name for p in spec.onboard_inputs}
    for name in provided:
        if name not in known_params:
            issues.append(ValidationIssue(
                severity="warning",
                location=f"node: {node_inst.id} param: {name}",
                message=f"参数 {name!r} 未在 NodeSpec 中定义，将被忽略",
            ))


def _validate_dag_acyclic(
    workflow: MFWorkflow,
    issues: list[ValidationIssue],
) -> None:
    """使用拓扑排序检查 DAG 是否无环。"""
    # 构建邻接表
    adjacency: dict[str, set[str]] = defaultdict(set)
    in_degree: dict[str, int] = {node.id: 0 for node in workflow.nodes}

    for conn in workflow.connections:
        src = conn.source_node_id
        tgt = conn.target_node_id
        if src in in_degree and tgt in in_degree:
            if tgt not in adjacency[src]:
                adjacency[src].add(tgt)
                in_degree[tgt] += 1

    # Kahn's algorithm
    queue: deque[str] = deque()
    for node_id, deg in in_degree.items():
        if deg == 0:
            queue.append(node_id)

    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for neighbor in adjacency[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(workflow.nodes):
        issues.append(ValidationIssue(
            severity="error",
            location="workflow",
            message="工作流 DAG 中存在环路，无法执行拓扑排序",
        ))


def _validate_quality_policy(
    workflow: MFWorkflow,
    resolved_nodes: dict[str, NodeSpec],
    issues: list[ValidationIssue],
) -> None:
    """校验 quality_policy 中的每个 override 是否合法，并 info 列出生效策略。"""
    from nodes.schemas.io import GateDefault

    for override in workflow.quality_policy:
        loc = f"quality_policy: {override.node_id}.{override.gate_name}"

        # 检查 node_id 是否存在
        if override.node_id not in resolved_nodes:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=f"quality_policy 引用的节点 {override.node_id!r} 不存在",
            ))
            continue

        spec = resolved_nodes[override.node_id]
        gate_names = {g.name for g in spec.quality_gates}

        # 检查 gate_name 是否是该节点的 quality gate
        if override.gate_name not in gate_names:
            issues.append(ValidationIssue(
                severity="error",
                location=loc,
                message=(
                    f"节点 {override.node_id!r} 没有名为 {override.gate_name!r} 的 quality gate。"
                    f"该节点的 quality gates: {sorted(gate_names) or '(无)'}"
                ),
            ))

    # Info：列出所有节点的 quality gate 生效策略
    # 构建 (node_id, gate_name) → 生效 action 的映射
    override_map: dict[tuple[str, str], GateDefault] = {
        (o.node_id, o.gate_name): o.action
        for o in workflow.quality_policy
    }
    for node_inst in workflow.nodes:
        spec = resolved_nodes.get(node_inst.id)
        if spec is None:
            continue
        for gate in spec.quality_gates:
            effective = override_map.get(
                (node_inst.id, gate.name), gate.gate_default
            )
            issues.append(ValidationIssue(
                severity="info",
                location=f"quality_gate: {node_inst.id}.{gate.name}",
                message=(
                    f"Quality gate '{gate.display_name}' → 生效策略: {effective.value}"
                    + (" [overridden]" if (node_inst.id, gate.name) in override_map else "")
                ),
            ))
