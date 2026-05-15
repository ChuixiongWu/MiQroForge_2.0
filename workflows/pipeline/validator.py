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
from typing import Any, Literal

from pydantic import BaseModel, Field

from nodes.schemas import (
    NodeSpec,
    StreamInputPort,
    StreamOutputPort,
    validate_connection,
)
from nodes.schemas.base import NodeMetadata, NodeType, NodeCategory, NodeTags
from nodes.schemas.io import (
    SoftwareDataPackageType,
    StreamIOCategory,
)
from nodes.schemas.resources import LightweightResources
from nodes.schemas.node import LightweightExecutionConfig

from .loader import resolve_nodespec
from .models import MFWorkflow, MFNodeInstance, QualityGateOverride


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
# 临时节点 → 虚拟 NodeSpec 构建
# ═══════════════════════════════════════════════════════════════════════════


def _gen_port_names(prefix: str, count: int) -> list[str]:
    """生成端口名称列表，如 _gen_port_names('I', 2) → ['I1', 'I2']。"""
    return [f"{prefix}{i+1}" for i in range(count)]


def _build_ephemeral_nodespec(node_inst: MFNodeInstance) -> NodeSpec:
    """为临时节点构建虚拟 NodeSpec，用于连接校验和 DAG 构建。

    临时节点没有真实的 nodespec.yaml，但需要一个 NodeSpec 来让
    连接校验和编译器能够统一处理。虚拟 NodeSpec 使用 lightweight
    执行配置（inline_script 模式，脚本内容为占位符）。

    端口类型统一使用 software_data_package（临时节点不做语义类型检查）。
    """
    ports = node_inst.ports
    assert ports is not None  # 已由 model_validator 保证

    # 统一使用 software_data_package 作为默认类型
    default_io_type = SoftwareDataPackageType(
        category=StreamIOCategory.SOFTWARE_DATA_PACKAGE,
        ecosystem="generic",
        data_type="text",
    )

    # 从整数计数生成端口名
    stream_inputs: list[StreamInputPort] = []
    for name in _gen_port_names("I", ports.inputs):
        stream_inputs.append(StreamInputPort(
            name=name,
            display_name=name,
            io_type=default_io_type,
            required=True,
        ))

    stream_outputs: list[StreamOutputPort] = []
    for name in _gen_port_names("O", ports.outputs):
        stream_outputs.append(StreamOutputPort(
            name=name,
            display_name=name,
            io_type=default_io_type,
        ))

    # 构造 OnBoardInput 列表
    from nodes.schemas.io import OnBoardInput, OnBoardInputKind
    onboard_inputs: list[OnBoardInput] = []
    for ob in node_inst.onboard_inputs:
        kind = OnBoardInputKind(ob.kind) if ob.kind in {k.value for k in OnBoardInputKind} else OnBoardInputKind.STRING
        onboard_inputs.append(OnBoardInput(
            name=ob.name,
            kind=kind,
            default=ob.default,
        ))

    # 使用 lightweight inline_script 执行配置（脚本内容为占位符，编译时替换）
    metadata = NodeMetadata(
        name=node_inst.id,
        version="0.0.0",
        display_name=node_inst.id.replace("-", " ").title(),
        description=node_inst.description or f"Ephemeral node {node_inst.id}",
        node_type=NodeType.LIGHTWEIGHT,
        category=NodeCategory.UTILITY,
        tags=NodeTags(keywords=["ephemeral"]),
    )

    # 使用 model_validate(dict) 而非直接构造，确保 _inject_type_discriminators 正确运行
    spec_dict = {
        "metadata": metadata.model_dump(),
        "stream_inputs": [p.model_dump() for p in stream_inputs],
        "stream_outputs": [p.model_dump() for p in stream_outputs],
        "onboard_inputs": [o.model_dump() for o in onboard_inputs],
        "quality_gates": [],
        "resources": LightweightResources().model_dump(),
        "execution": LightweightExecutionConfig(
            inline_script="# placeholder — compiled by ephemeral compiler"
        ).model_dump(),
    }
    return NodeSpec.model_validate(spec_dict)


# ═══════════════════════════════════════════════════════════════════════════
# 主校验函数
# ═══════════════════════════════════════════════════════════════════════════


def validate_workflow(
    workflow: MFWorkflow,
    *,
    project_root: Path | None = None,
    project_id: str = "",
    username: str = "",
) -> ValidationReport:
    """对 MF 工作流进行全量校验。

    Parameters:
        workflow: 已加载的 MFWorkflow 实例。
        project_root: 项目根目录，用于解析 nodespec 路径。
        project_id: 当前项目 ID，用于搜索项目 tmp 目录中的未 Accept 节点。
        username: 当前用户名，用于多用户项目路径。

    Returns:
        ValidationReport，包含所有问题和解析后的 NodeSpec。
    """
    issues: list[ValidationIssue] = []
    resolved_nodes: dict[str, NodeSpec] = {}

    # ── Step 1: 解析每个节点的 NodeSpec ──────────────────────────────────
    for node_inst in workflow.nodes:
        # sweep 校验：sweep 节点必须通过 node 名称引用正式节点
        if node_inst.parallel_sweep is not None:
            if node_inst.node is None:
                issues.append(ValidationIssue(
                    severity="error",
                    location=f"node: {node_inst.id}",
                    message="parallel_sweep 节点必须使用 'node' 字段引用正式节点",
                ))

        if node_inst.ephemeral or node_inst.prefab:
            label = "prefab" if node_inst.prefab else "ephemeral"
            # ── Prefab 节点：pregenerate 非空时才去 disk 读预生成 nodespec ──
            if node_inst.prefab and node_inst.pregenerate is not None:
                try:
                    spec = _resolve_nodegen_tmp_spec(node_inst, project_root, project_id, username)
                    resolved_nodes[node_inst.id] = spec
                    issues.append(ValidationIssue(
                        severity="info",
                        location=f"node: {node_inst.id}",
                        message=f"Prefab 节点 (pregenerated, node_id={node_inst.id!r}): "
                                f"从 tmp/userdata 读取预生成 nodespec",
                    ))
                except FileNotFoundError as e:
                    issues.append(ValidationIssue(
                        severity="error",
                        location=f"node: {node_inst.id}",
                        message=f"Prefab tmp nodespec 未找到: {e}",
                    ))
                    resolved_nodes[node_inst.id] = _build_ephemeral_nodespec(node_inst)
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity="error",
                        location=f"node: {node_inst.id}",
                        message=f"Prefab tmp nodespec 解析失败: {e}",
                    ))
                    resolved_nodes[node_inst.id] = _build_ephemeral_nodespec(node_inst)
            elif node_inst.prefab:
                # Prefab from scratch（直接运行）— 不读 disk，运行时 Agent 将从零生成
                spec = _build_ephemeral_nodespec(node_inst)
                resolved_nodes[node_inst.id] = spec
                issues.append(ValidationIssue(
                    severity="info",
                    location=f"node: {node_inst.id}",
                    message=f"Prefab 节点 (from scratch, node_id={node_inst.id!r}): "
                            f"运行时 Agent 将从零生成 nodespec",
                ))
            else:
                # 普通 ephemeral — 不读 disk
                spec = _build_ephemeral_nodespec(node_inst)
                resolved_nodes[node_inst.id] = spec
                issues.append(ValidationIssue(
                    severity="info",
                    location=f"node: {node_inst.id}",
                    message=f"临时节点 (ephemeral): {node_inst.get_generation_description()}",
                ))
        else:
            try:
                spec = resolve_nodespec(node_inst, project_root=project_root, project_id=project_id)
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

    # 生成类节点集合：跳过连接类型校验（端口统一 software_data_package，类型检查无意义）
    generated_ids = {n.id for n in workflow.nodes if n.ephemeral or n.prefab}

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

        # 调用 validate_connection（临时节点间或与临时节点的连接跳过类型检查）
        if src_node_id not in generated_ids and tgt_node_id not in generated_ids:
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


def _resolve_nodegen_tmp_spec(
    node_inst: MFNodeInstance,
    project_root: Path | None,
    project_id: str,
    username: str = "",
) -> NodeSpec:
    """为 prefab 节点从 proj/tmp/ 或 userdata/nodes/ 读取预生成 nodespec。

    仅在 pregenerate 非空时调用（-1 循环已执行）。
    使用 node_inst.id 作为 tmp 目录名（而非已弃用的 nodegen_tmp_ref）。

    Returns:
        解析后的 NodeSpec。

    Raises:
        FileNotFoundError: 两处均未找到。
    """
    if project_root is None:
        project_root = Path.cwd()
    name = node_inst.id  # 直接使用节点 ID

    # 1. 搜索 userdata/users/{username}/nodes/（用户自定义节点）
    if username:
        user_nodes = project_root / "userdata" / "users" / username / "nodes"
        if user_nodes.exists():
            for spec_path in user_nodes.rglob(f"{name}/nodespec.yaml"):
                if "schemas" in spec_path.parts or "base_images" in spec_path.parts:
                    continue
                return NodeSpec.from_yaml(spec_path)

    # 2. 搜索 userdata/nodes/（共享节点 / 向后兼容）
    shared_nodes = project_root / "userdata" / "nodes"
    if shared_nodes.exists():
        for spec_path in shared_nodes.rglob(f"{name}/nodespec.yaml"):
            if "schemas" in spec_path.parts or "base_images" in spec_path.parts:
                continue
            return NodeSpec.from_yaml(spec_path)

    # 3. 搜索 userdata/users/{username}/projects/{project_id}/tmp/{name}/
    if project_id:
        if username:
            tmp_dir = project_root / "userdata" / "users" / username / "projects" / project_id / "tmp" / name
        else:
            tmp_dir = project_root / "userdata" / "projects" / project_id / "tmp" / name
        spec_path = tmp_dir / "nodespec.yaml"
        if spec_path.exists():
            return NodeSpec.from_yaml(spec_path)

    raise FileNotFoundError(
        f"prefab 节点 {name!r} 的 nodespec 在 userdata/nodes/ 和 "
        f"proj/{project_id}/tmp/ 中均未找到"
    )


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
