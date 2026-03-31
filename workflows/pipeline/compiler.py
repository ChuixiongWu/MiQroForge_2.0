"""MF 工作流编译器。

将校验通过的 MFWorkflow + resolved NodeSpecs 编译为 Argo Workflow YAML。

映射规则：
- 每个 MFNodeInstance → 一个 Argo template
  - compute → container template (base_image + resources + profile ConfigMap 挂载)
  - lightweight → script template (python + inline_script)
- 每个 StreamOutputPort → Argo output parameter, valueFrom.path: /mf/output/{port_name}
- 每个 MFConnection → DAG task argument ("{{tasks.src_id.outputs.parameters.port_name}}")
- onboard_params → DAG task argument（直接传值）
- resources → Argo resources.requests/limits
- 自动计算 DAG dependencies 从 connections
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from nodes.schemas import (
    BaseImageRegistry,
    ComputeExecutionConfig,
    LightweightExecutionConfig,
    NodeSpec,
)
from nodes.schemas.io import GateDefault
from nodes.schemas.resources import ComputeResources
from nodes.schemas.resource_defaults import get_resource_defaults

from .models import MFWorkflow


# ═══════════════════════════════════════════════════════════════════════════
# 模块常量
# ═══════════════════════════════════════════════════════════════════════════

# Workspace PVC 名称（与 infrastructure/k8s/workspace.yaml 保持一致）
_WORKSPACE_PVC_NAME = "mf-workspace"


# ═══════════════════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════════════════


def _slugify(name: str) -> str:
    """将任意字符串转换为合法的 Kubernetes RFC 1123 subdomain 名称。

    规则：全小写，空格/下划线/特殊字符→连字符，首尾必须是字母或数字，
    连续连字符折叠为单个，最长 52 字符（为随机后缀留余量）。
    """
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)   # 非法字符 → 连字符
    s = re.sub(r"-{2,}", "-", s)         # 连续连字符折叠
    s = s.strip("-")                      # 去除首尾连字符
    return s[:52] or "workflow"           # 兜底不能为空


def compile_to_argo(
    workflow: MFWorkflow,
    resolved_nodes: dict[str, NodeSpec],
    *,
    project_root: Path | None = None,
    docker_hub_mirror: str = "",
) -> dict[str, Any]:
    """将 MFWorkflow 编译为 Argo Workflow YAML dict。

    Parameters:
        workflow: 已校验的 MFWorkflow。
        resolved_nodes: 节点 ID → NodeSpec 映射（来自 ValidationReport）。
        project_root: 项目根目录，用于查找 base_images/registry.yaml 和 workspace/ 文件。
        docker_hub_mirror: Docker Hub 国内镜像加速站域名（如 docker.m.daocloud.io）。
            设置后，无 registry.yaml 条目的 Docker Hub 官方镜像将通过该镜像站拉取。

    Returns:
        Argo Workflow YAML 结构（可直接 yaml.dump）。

    Raises:
        ValueError: 编译错误（如镜像找不到）。
    """
    if project_root is None:
        project_root = Path.cwd()

    registry = _load_image_registry(project_root)

    # 将工作流名称规范化为合法的 Kubernetes 资源名（RFC 1123 subdomain）
    slug = _slugify(workflow.name)

    # 构建 DAG dependencies
    dep_map = _build_dependency_map(workflow)

    # 构建 connection 信息：target (node_id, port_name) → (src_node_id, src_port_name)
    conn_map: dict[tuple[str, str], tuple[str, str]] = {}
    for conn in workflow.connections:
        key = (conn.target_node_id, conn.target_port_name)
        conn_map[key] = (conn.source_node_id, conn.source_port_name)

    # 计算被连接的输出端口集合：{(src_node_id, src_port_name)}
    # 只有被下游节点消费的端口才需要作为 Argo output parameter 收集
    # 未连接的大型二进制输出（如 gbw_file）跳过，避免 "request entity too large" 错误
    connected_outputs: set[tuple[str, str]] = set()
    for conn in workflow.connections:
        connected_outputs.add((conn.source_node_id, conn.source_port_name))

    # 构建 templates 和 DAG tasks
    templates: list[dict[str, Any]] = []
    dag_tasks: list[dict[str, Any]] = []

    for node_inst in workflow.nodes:
        spec = resolved_nodes[node_inst.id]
        template_name = f"mf-{node_inst.id}"

        # 构建 template
        template = _build_template(
            node_inst=node_inst,
            node_inst_id=node_inst.id,
            template_name=template_name,
            spec=spec,
            registry=registry,
            workflow=workflow,
            connected_outputs=connected_outputs,
            docker_hub_mirror=docker_hub_mirror,
            project_root=project_root,
        )
        templates.append(template)

        # 构建 DAG task
        task = _build_dag_task(
            node_inst=node_inst,
            template_name=template_name,
            spec=spec,
            dep_map=dep_map,
            conn_map=conn_map,
            resolved_nodes=resolved_nodes,
            workflow=workflow,
            project_root=project_root,
        )
        dag_tasks.append(task)

    # 组装 Argo Workflow
    argo_wf: dict[str, Any] = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": f"{slug}-",
            "namespace": workflow.namespace,
            "labels": {
                "miqroforge.io/workflow": slug,
                "miqroforge.io/mf-version": workflow.mf_version,
            },
        },
        "spec": {
            "entrypoint": "mf-dag",
            "serviceAccountName": f"{workflow.namespace}-workflow-sa",
            "templates": [
                {
                    "name": "mf-dag",
                    "dag": {
                        "tasks": dag_tasks,
                    },
                },
                *templates,
            ],
        },
    }

    return argo_wf


def compile_to_yaml_str(
    workflow: MFWorkflow,
    resolved_nodes: dict[str, NodeSpec],
    *,
    project_root: Path | None = None,
    docker_hub_mirror: str = "",
) -> str:
    """编译并返回 YAML 字符串。"""
    argo_dict = compile_to_argo(
        workflow, resolved_nodes, project_root=project_root, docker_hub_mirror=docker_hub_mirror
    )
    return yaml.dump(
        argo_dict,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ConfigMap 生成
# ═══════════════════════════════════════════════════════════════════════════


def generate_configmaps(
    workflow: MFWorkflow,
    resolved_nodes: dict[str, NodeSpec],
    *,
    project_root: Path | None = None,
) -> list[dict[str, Any]]:
    """为所有 compute 节点生成 ConfigMap 清单。

    Parameters:
        workflow: 已校验的 MFWorkflow。
        resolved_nodes: 节点 ID → NodeSpec。
        project_root: 项目根目录。

    Returns:
        ConfigMap YAML dict 列表。
    """
    if project_root is None:
        project_root = Path.cwd()

    configmaps: list[dict[str, Any]] = []

    for node_inst in workflow.nodes:
        spec = resolved_nodes[node_inst.id]

        # compute 节点始终生成 ConfigMap
        # lightweight 节点仅在 entrypoint_script 模式下生成 ConfigMap
        if isinstance(spec.execution, LightweightExecutionConfig):
            if not spec.execution.entrypoint_script:
                continue
        elif not isinstance(spec.execution, ComputeExecutionConfig):
            continue

        cm_name = _configmap_name(spec)

        # 从 nodespec 旁的 profile/ 目录读取文件
        profile_data = _load_profile_files(node_inst, spec, project_root)
        if not profile_data:
            continue

        cm: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "namespace": workflow.namespace,
                "labels": {
                    "miqroforge.io/node": spec.metadata.name,
                    "miqroforge.io/version": spec.metadata.version,
                },
            },
            "data": profile_data,
        }
        configmaps.append(cm)

    return configmaps


# ═══════════════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════════════


def _load_image_registry(project_root: Path) -> BaseImageRegistry:
    """加载 base_images/registry.yaml。"""
    registry_path = project_root / "nodes" / "base_images" / "registry.yaml"
    if not registry_path.exists():
        return BaseImageRegistry(images=[])
    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return BaseImageRegistry.model_validate(data)


def _resolve_resources(
    spec: NodeSpec,
    onboard_params: dict[str, Any],
) -> dict[str, Any]:
    """解析 resource_bindings，返回实际资源值。

    优先级：onboard_params 实例覆盖 > nodespec default > nodespec 静态值。
    """
    res = spec.resources
    if not isinstance(res, ComputeResources) or not res.resource_bindings:
        return {}

    defaults_config = get_resource_defaults()
    overrides: dict[str, Any] = {}
    onboard_map = {p.name: p for p in spec.onboard_inputs}

    for res_field in res.resource_bindings:
        param_name = defaults_config.get(res_field, {}).get("param_name", res_field)
        raw = onboard_params.get(param_name)
        if raw is not None and str(raw).strip() != "":
            overrides[res_field] = raw
            continue
        # 回退到 onboard input 默认值
        param = onboard_map.get(param_name)
        if param is not None and param.default is not None:
            overrides[res_field] = param.default

    return overrides


def _build_dependency_map(workflow: MFWorkflow) -> dict[str, set[str]]:
    """从 connections 构建 DAG 依赖关系。

    Returns:
        dict[target_node_id, set[source_node_id]]
    """
    dep_map: dict[str, set[str]] = defaultdict(set)
    for conn in workflow.connections:
        dep_map[conn.target_node_id].add(conn.source_node_id)
    return dep_map


def _build_template(
    *,
    node_inst,  # MFNodeInstance
    node_inst_id: str,
    template_name: str,
    spec: NodeSpec,
    registry: BaseImageRegistry,
    workflow: MFWorkflow,
    connected_outputs: set[tuple[str, str]],
    docker_hub_mirror: str = "",
    project_root: Path | None = None,
) -> dict[str, Any]:
    """为单个节点构建 Argo template。

    只为有下游连接的 stream output 生成 Argo output parameter 收集规则。
    未连接的大型二进制输出（如 gbw_file）会被跳过，避免参数体积超限错误。
    Quality gate 输出始终收集（DAG depends 条件所需）。
    """

    # 收集所有 input 参数名（stream inputs + onboard inputs）
    input_params: list[dict[str, str]] = []
    for port in spec.stream_inputs:
        input_params.append({"name": port.name})
    for param in spec.onboard_inputs:
        input_params.append({"name": param.name})

    # 只收集被下游节点连接的 stream output 端口
    output_params: list[dict[str, Any]] = []
    for port in spec.stream_outputs:
        if (node_inst_id, port.name) in connected_outputs:
            output_params.append({
                "name": port.name,
                "valueFrom": {"path": f"/mf/output/{port.name}"},
            })
    # Quality gate 输出始终收集（DAG depends 条件所需，前缀 _qg_）
    for gate in spec.quality_gates:
        output_params.append({
            "name": f"_qg_{gate.name}",
            "valueFrom": {"path": f"/mf/output/{gate.name}"},
        })
    # Onboard outputs（非 quality gate）—— 始终收集，供 UI 和 runs/outputs.json 展示
    for ob_out in spec.onboard_outputs:
        if not ob_out.quality_gate:
            output_params.append({
                "name": ob_out.name,
                "valueFrom": {"path": f"/mf/output/{ob_out.name}"},
            })

    # 解析 resource_bindings（用实例的 onboard_params 覆盖静态资源值）
    resource_overrides = _resolve_resources(spec, node_inst.onboard_params)

    if isinstance(spec.execution, ComputeExecutionConfig):
        return _build_compute_template(
            template_name=template_name,
            spec=spec,
            registry=registry,
            workflow=workflow,
            input_params=input_params,
            output_params=output_params,
            resource_overrides=resource_overrides,
        )
    elif isinstance(spec.execution, LightweightExecutionConfig):
        if spec.execution.entrypoint_script:
            # Profile-based shell 入口模式 — container template
            return _build_lightweight_profile_template(
                template_name=template_name,
                spec=spec,
                registry=registry,
                docker_hub_mirror=docker_hub_mirror,
                input_params=input_params,
                output_params=output_params,
            )
        else:
            # inline_script / script_path 模式 — script template（原有逻辑）
            spec_dir: Path | None = None
            if project_root and node_inst.nodespec_path:
                spec_dir = (project_root / node_inst.nodespec_path).parent
            return _build_lightweight_script_template(
                template_name=template_name,
                spec=spec,
                spec_dir=spec_dir,
                registry=registry,
                docker_hub_mirror=docker_hub_mirror,
                input_params=input_params,
                output_params=output_params,
            )
    else:
        raise ValueError(
            f"未知的执行配置类型: {type(spec.execution)}"
        )


def _build_compute_template(
    *,
    template_name: str,
    spec: NodeSpec,
    registry: BaseImageRegistry,
    workflow: MFWorkflow,
    input_params: list[dict[str, str]],
    output_params: list[dict[str, Any]],
    resource_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建 compute 节点的 container template。"""
    exec_cfg = spec.execution  # ComputeExecutionConfig

    # 解析镜像
    image_ref = _resolve_image(spec, registry, workflow)

    cm_name = _configmap_name(spec)

    # 将 resource_bindings 覆盖应用到静态资源值
    overrides = resource_overrides or {}
    cpu_cores = int(overrides.get("cpu_cores", spec.resources.cpu_cores))
    memory_gb = float(overrides.get("memory_gb", spec.resources.memory_gb))
    gpu_count = int(overrides.get("gpu_count", getattr(spec.resources, "gpu_count", 0)))

    # 构建写入参数到文件的 shell 命令
    # 先把所有 input 参数写到 /mf/input/{param_name}，然后运行 profile 脚本
    write_cmds: list[str] = ["mkdir -p /mf/input /mf/output"]
    for p in input_params:
        name = p["name"]
        write_cmds.append(
            f'echo -n "{{{{inputs.parameters.{name}}}}}" > /mf/input/{name}'
        )
    write_cmds.append(f"{exec_cfg.profile_mount_path}/{exec_cfg.entrypoint_script}")

    template: dict[str, Any] = {
        "name": template_name,
        "inputs": {"parameters": input_params} if input_params else {},
        "outputs": {"parameters": output_params} if output_params else {},
        "container": {
            "image": image_ref,
            "command": ["sh", "-c"],
            "args": [" && ".join(write_cmds)],
            "resources": {
                "requests": {
                    "cpu": str(cpu_cores),
                    "memory": f"{memory_gb}Gi",
                },
                "limits": {
                    "cpu": str(cpu_cores),
                    "memory": f"{memory_gb}Gi",
                },
            },
            "volumeMounts": [
                {
                    "name": "profile",
                    "mountPath": exec_cfg.profile_mount_path,
                },
                {
                    "name": "workspace",
                    "mountPath": "/mf/workspace",
                },
            ],
        },
        "volumes": [
            {
                "name": "profile",
                "configMap": {
                    "name": cm_name,
                    "defaultMode": 0o755,
                },
            },
            {
                "name": "workspace",
                "persistentVolumeClaim": {"claimName": _WORKSPACE_PVC_NAME},
            },
        ],
    }

    # GPU 资源
    if gpu_count > 0:
        template["container"]["resources"]["limits"][
            "nvidia.com/gpu"
        ] = str(gpu_count)

    # 环境变量
    if exec_cfg.environment:
        template["container"]["env"] = [
            {"name": k, "value": v}
            for k, v in exec_cfg.environment.items()
        ]

    return template


def _build_lightweight_script_template(
    *,
    template_name: str,
    spec: NodeSpec,
    spec_dir: Path | None = None,
    registry: BaseImageRegistry,
    docker_hub_mirror: str = "",
    input_params: list[dict[str, str]],
    output_params: list[dict[str, Any]],
) -> dict[str, Any]:
    """构建 lightweight 节点的 script template（inline_script / script_path 模式）。

    Python 镜像优先级：
      1. registry.yaml 中有 python-{version} 条目 → 使用私有仓库地址
      2. 配置了 DOCKER_HUB_MIRROR → 使用镜像站（{mirror}/library/python:{version}-slim）
      3. 回退到 Docker Hub 直连（python:{version}-slim）

    脚本来源优先级：
      1. exec_cfg.inline_script（直接内联）
      2. exec_cfg.script_path（相对于节点目录的文件路径，编译时读入）

    参数注入：
      所有 input_params（stream inputs + onboard inputs）均以 env var 形式注入容器，
      脚本通过 os.environ.get() 读取。MF_OUTPUT_DIR 固定为 /mf/output。
    """
    exec_cfg = spec.execution  # LightweightExecutionConfig

    # ── 读取脚本内容 ──────────────────────────────────────────────────────────
    if exec_cfg.inline_script:
        script_source = exec_cfg.inline_script
    elif exec_cfg.script_path and spec_dir is not None:
        script_file = spec_dir / exec_cfg.script_path
        script_source = script_file.read_text(encoding="utf-8")
    elif exec_cfg.script_path:
        # spec_dir 未知时降级警告
        import warnings
        warnings.warn(
            f"[lightweight] {template_name}: script_path={exec_cfg.script_path!r} "
            "但未提供 spec_dir，脚本内容为空",
            stacklevel=2,
        )
        script_source = ""
    else:
        script_source = ""  # schema 已保证不会到这里

    # ── Python 镜像解析 ───────────────────────────────────────────────────────
    reg_key = f"python-{exec_cfg.python_version}"
    reg_entry = next((img for img in registry.images if img.name == reg_key), None)
    if reg_entry:
        python_image = f"{reg_entry.image}:{reg_entry.tag}"
    elif docker_hub_mirror:
        python_image = f"{docker_hub_mirror}/library/python:{exec_cfg.python_version}-slim"
    else:
        python_image = f"python:{exec_cfg.python_version}-slim"

    # ── 环境变量注入：所有 input 参数 + MF 路径约定 ──────────────────────────
    # 脚本通过 os.environ.get(param_name) 读取参数，Argo 在容器启动前解析模板表达式
    env_vars: list[dict[str, str]] = [
        {"name": "MF_OUTPUT_DIR", "value": "/mf/output"},
        {"name": "MF_WORKSPACE_DIR", "value": "/mf/workspace"},
    ]
    for param in input_params:
        env_vars.append({
            "name": param["name"],
            "value": f"{{{{inputs.parameters.{param['name']}}}}}",
        })

    template: dict[str, Any] = {
        "name": template_name,
        "inputs": {"parameters": input_params} if input_params else {},
        "outputs": {"parameters": output_params} if output_params else {},
        "script": {
            "image": python_image,
            "command": ["python"],
            "env": env_vars,
            "source": script_source,
            "resources": {
                "requests": {
                    "cpu": str(spec.resources.cpu_cores),
                    "memory": f"{spec.resources.memory_gb}Gi",
                },
                "limits": {
                    "cpu": str(spec.resources.cpu_cores),
                    "memory": f"{spec.resources.memory_gb}Gi",
                },
            },
            "volumeMounts": [
                {
                    "name": "workspace",
                    "mountPath": "/mf/workspace",
                },
            ],
        },
        "volumes": [
            {
                "name": "workspace",
                "persistentVolumeClaim": {"claimName": _WORKSPACE_PVC_NAME},
            },
        ],
    }

    return template


def _build_lightweight_profile_template(
    *,
    template_name: str,
    spec: NodeSpec,
    registry: BaseImageRegistry,
    docker_hub_mirror: str = "",
    input_params: list[dict[str, str]],
    output_params: list[dict[str, Any]],
) -> dict[str, Any]:
    """构建 lightweight 节点的 container template（entrypoint_script 模式）。

    使用 profile ConfigMap + container 模板模式，与 compute 节点行为一致，
    只是镜像替换为 python:{version}-slim（自带 bash，无需额外安装）。

    适用场景：需要 shell 脚本编排、调用命令行工具或复杂初始化逻辑，
    但不需要 compute 节点那样的重型容器镜像。

    参数注入方式与 compute 节点相同：所有 input 参数写入 /mf/input/ 文件，
    脚本通过 source /mf/profile/mf2_init.sh + mf_param() 读取。
    """
    exec_cfg = spec.execution  # LightweightExecutionConfig

    # ── Python 镜像解析（复用 script 模式逻辑）───────────────────────────────
    reg_key = f"python-{exec_cfg.python_version}"
    reg_entry = next((img for img in registry.images if img.name == reg_key), None)
    if reg_entry:
        python_image = f"{reg_entry.image}:{reg_entry.tag}"
    elif docker_hub_mirror:
        python_image = f"{docker_hub_mirror}/library/python:{exec_cfg.python_version}-slim"
    else:
        python_image = f"python:{exec_cfg.python_version}-slim"

    # Profile 配置
    cm_name = _configmap_name(spec)
    profile_mount_path = "/mf/profile"
    entrypoint = exec_cfg.entrypoint_script  # 已由 schema 确保非空

    # 构建写参数 + 执行脚本的 shell 命令（与 compute 节点一致）
    write_cmds: list[str] = ["mkdir -p /mf/input /mf/output"]
    for p in input_params:
        name = p["name"]
        write_cmds.append(
            f'echo -n "{{{{inputs.parameters.{name}}}}}" > /mf/input/{name}'
        )
    write_cmds.append(f"{profile_mount_path}/{entrypoint}")

    template: dict[str, Any] = {
        "name": template_name,
        "inputs": {"parameters": input_params} if input_params else {},
        "outputs": {"parameters": output_params} if output_params else {},
        "container": {
            "image": python_image,
            "command": ["sh", "-c"],
            "args": [" && ".join(write_cmds)],
            "resources": {
                "requests": {
                    "cpu": str(spec.resources.cpu_cores),
                    "memory": f"{spec.resources.memory_gb}Gi",
                },
                "limits": {
                    "cpu": str(spec.resources.cpu_cores),
                    "memory": f"{spec.resources.memory_gb}Gi",
                },
            },
            "volumeMounts": [
                {
                    "name": "profile",
                    "mountPath": profile_mount_path,
                },
                {
                    "name": "workspace",
                    "mountPath": "/mf/workspace",
                },
            ],
        },
        "volumes": [
            {
                "name": "profile",
                "configMap": {
                    "name": cm_name,
                    "defaultMode": 0o755,
                },
            },
            {
                "name": "workspace",
                "persistentVolumeClaim": {"claimName": _WORKSPACE_PVC_NAME},
            },
        ],
    }

    # 额外环境变量（如有）
    if exec_cfg.environment:
        template["container"]["env"] = [
            {"name": k, "value": v}
            for k, v in exec_cfg.environment.items()
        ]

    return template


def _build_dag_task(
    *,
    node_inst,  # MFNodeInstance
    template_name: str,
    spec: NodeSpec,
    dep_map: dict[str, set[str]],
    conn_map: dict[tuple[str, str], tuple[str, str]],
    resolved_nodes: dict[str, NodeSpec],
    workflow: MFWorkflow,
    project_root: Path,
) -> dict[str, Any]:
    """构建 DAG task 条目。

    依赖表达式规则（统一使用 ``depends`` 字段）：
    - Argo 不允许同一 DAG 内混用 ``depends`` 和 ``dependencies`` 两种写法，
      因此无论上游是否有 quality gate，均使用 ``depends`` 字段。
    - 上游有 must_pass quality gate → ``upstream.Succeeded``（保证上游实际成功）
    - 上游无 must_pass gate → 裸任务名 ``upstream``（任意终止态即可触发）
    ``depends: "taskA"`` 与 ``dependencies: ["taskA"]`` 语义等价。
    """
    task: dict[str, Any] = {
        "name": node_inst.id,
        "template": template_name,
    }

    # ── Dependencies / depends ─────────────────────────────────────────────
    deps = dep_map.get(node_inst.id, set())
    if deps:
        gate_policy = _resolve_gate_policy(workflow)

        # 判断每个上游是否有 must_pass gate；有则需要 .Succeeded 语义
        must_succeed: set[str] = set()
        for dep_node_id in deps:
            dep_spec = resolved_nodes.get(dep_node_id)
            if dep_spec is None:
                continue
            for gate in dep_spec.quality_gates:
                effective = gate_policy.get(
                    (dep_node_id, gate.name), gate.gate_default
                )
                if effective == GateDefault.MUST_PASS:
                    must_succeed.add(dep_node_id)
                    break

        if must_succeed:
            # 至少一个上游要求 Succeeded — 添加 .Succeeded 后缀
            dep_exprs = []
            for dep_node_id in sorted(deps):
                if dep_node_id in must_succeed:
                    dep_exprs.append(f"{dep_node_id}.Succeeded")
                else:
                    dep_exprs.append(dep_node_id)
            task["depends"] = " && ".join(dep_exprs)
        else:
            # 无质量门控要求 — 裸任务名，仍使用 depends 字段保持 DAG 内格式统一
            # （Argo 不允许同一 DAG 内混用 depends 和 dependencies）
            task["depends"] = " && ".join(sorted(deps))

    # ── Arguments: stream inputs + onboard params ──────────────────────────
    arguments: list[dict[str, Any]] = []

    for port in spec.stream_inputs:
        key = (node_inst.id, port.name)
        if key in conn_map:
            src_node_id, src_port_name = conn_map[key]
            arguments.append({
                "name": port.name,
                "value": f"{{{{tasks.{src_node_id}.outputs.parameters.{src_port_name}}}}}",
            })

    for param in spec.onboard_inputs:
        raw = node_inst.onboard_params.get(param.name)
        # 优先使用实例值；空字符串实例值回退到 nodespec 默认值
        # 注意：default="" 的参数也必须传入 arguments，否则 Argo 报 "not supplied"
        if raw is not None and str(raw).strip() != "":
            value = raw
        elif param.default is not None:
            value = param.default
        else:
            continue
        value = str(value)
        arguments.append({
            "name": param.name,
            "value": value,
        })

    if arguments:
        task["arguments"] = {"parameters": arguments}

    # ── When conditions — from upstream must_pass quality gates ────────────
    gate_policy = _resolve_gate_policy(workflow)
    when_conditions: list[str] = []

    for dep_node_id in dep_map.get(node_inst.id, set()):
        dep_spec = resolved_nodes.get(dep_node_id)
        if dep_spec is None:
            continue
        for gate in dep_spec.quality_gates:
            effective_action = gate_policy.get((dep_node_id, gate.name), gate.gate_default)
            if effective_action == GateDefault.MUST_PASS:
                when_conditions.append(
                    f"{{{{tasks.{dep_node_id}.outputs.parameters._qg_{gate.name}}}}} == true"
                )

    if when_conditions:
        task["when"] = " && ".join(when_conditions)

    return task


def _resolve_gate_policy(
    workflow: MFWorkflow,
) -> dict[tuple[str, str], GateDefault]:
    """构建 (node_id, gate_name) → 生效 GateDefault 映射。

    只包含 quality_policy 中明确 override 的条目；
    未 override 的 gate 由调用方回退到 gate.gate_default。
    """
    return {
        (o.node_id, o.gate_name): o.action
        for o in workflow.quality_policy
    }


def _resolve_image(
    spec: NodeSpec,
    registry: BaseImageRegistry,
    workflow: MFWorkflow,
) -> str:
    """解析 compute 节点的容器镜像引用。"""
    ref = spec.metadata.base_image_ref
    if ref is None:
        raise ValueError(
            f"Compute 节点 {spec.metadata.name!r} 缺少 base_image_ref"
        )

    img_spec = registry.get(ref)
    if img_spec is None:
        raise ValueError(
            f"BaseImageRegistry 中未找到镜像 {ref!r}。"
            f"请确认 nodes/base_images/registry.yaml 中已注册该镜像。"
        )

    full_ref = img_spec.full_image_ref()

    # 如果 global_params 中有 image-registry，作为前缀注入
    image_registry = workflow.global_params.get("image-registry")
    if image_registry:
        # image-registry/image:tag
        image_name = img_spec.image.split("/")[-1]
        full_ref = f"{image_registry}/{image_name}:{img_spec.tag}"

    return full_ref


def _configmap_name(spec: NodeSpec) -> str:
    """生成 ConfigMap 名称。"""
    return f"mf-profile-{spec.metadata.name}-{spec.metadata.version}"


def _load_profile_files(
    node_inst,
    spec: NodeSpec,
    project_root: Path,
) -> dict[str, str]:
    """从 nodespec 旁的 profile/ 目录加载文件，并注入公共库和节点参数。

    额外处理：
    - run.sh 中的 ``# MF2 init`` 指令替换为 ``source /mf/profile/mf2_init.sh``
    - 将 ``nodes/common/mf2_init.sh`` 注入 ConfigMap（作为 mf2_init.sh）
    - 根据 spec.onboard_inputs 生成 ``mf_node_params.sh`` 并注入 ConfigMap
    """
    # 找到 nodespec 所在目录
    if node_inst.nodespec_path:
        spec_dir = (project_root / node_inst.nodespec_path).parent
    elif node_inst.node:
        # 需要找到节点目录 — 搜索 nodes/ 下的 nodespec.yaml
        spec_dir = _find_node_dir(spec.metadata.name, project_root)
        if spec_dir is None:
            return {}
    else:
        return {}

    profile_dir = spec_dir / "profile"
    if not profile_dir.exists():
        return {}

    data: dict[str, str] = {}
    for filepath in sorted(profile_dir.iterdir()):
        if filepath.is_file():
            content = filepath.read_text(encoding="utf-8")
            if filepath.name == "run.sh":
                content = _process_run_sh(content)
            data[filepath.name] = content

    # 注入公共运行时库 mf2_init.sh
    common_init = project_root / "nodes" / "common" / "mf2_init.sh"
    if common_init.exists():
        data["mf2_init.sh"] = common_init.read_text(encoding="utf-8")

    # 注入编译器生成的节点参数加载文件
    data["mf_node_params.sh"] = _generate_node_params_sh(spec)

    return data


def _process_run_sh(content: str) -> str:
    """处理 run.sh 中的 ``# MF2 init`` 指令，替换为 source 命令。

    匹配整行（允许行尾空白），只替换第一次出现。
    未找到该指令时原样返回（兼容未使用该约定的旧脚本）。
    """
    return re.sub(
        r"^# MF2 init[^\S\n]*$",
        "source /mf/profile/mf2_init.sh",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def _generate_node_params_sh(spec: NodeSpec) -> str:
    """从 spec.onboard_inputs 生成 mf_node_params.sh 内容。

    为每个 onboard input 生成一行 BASH 变量赋值：
        UPPER_CASE_NAME=$(mf_param param_name "default")

    resource_bindings（如 n_cores）已由 NodeSpec 校验器自动注入到
    spec.onboard_inputs，因此无需特殊处理，直接遍历即可覆盖所有参数。
    """
    lines = [
        "# Auto-generated by MiQroForge compiler — do not edit manually",
        f"# Node: {spec.metadata.name}  v{spec.metadata.version}",
        "",
    ]
    for param in spec.onboard_inputs:
        default = "" if param.default is None else str(param.default)
        # 对默认值中的反斜杠和双引号做最小转义，确保 shell 赋值安全
        escaped = default.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{param.name}=$(mf_param {param.name} "{escaped}")')

    return "\n".join(lines) + "\n"


def _find_node_dir(name: str, project_root: Path) -> Path | None:
    """按名称查找节点目录。"""
    nodes_dir = project_root / "nodes"
    for spec_path in nodes_dir.rglob("nodespec.yaml"):
        if "schemas" in spec_path.parts:
            continue
        try:
            with spec_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data.get("metadata", {}).get("name") == name:
                return spec_path.parent
        except Exception:
            continue
    return None
