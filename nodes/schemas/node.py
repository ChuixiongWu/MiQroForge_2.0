"""完整节点定义 (NodeSpec) 与执行配置。

:class:`NodeSpec` 是 ``nodespec.yaml`` 的 Pydantic 镜像，是节点的
**Single Source of Truth**。支持从 YAML 加载（`from_yaml`）和序列化
（`to_yaml`）。

执行配置分两种：
- :class:`ComputeExecutionConfig` — 计算节点（基础镜像 + Profile 注入）
- :class:`LightweightExecutionConfig` — 轻量节点（内联脚本或外置 .py）
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, model_validator

from .base import NodeMetadata, NodeType
from .io import (
    OnBoardInput,
    OnBoardOutput,
    StreamInputPort,
    StreamOutputPort,
)
from .resources import (
    ComputeResources,
    LightweightResources,
    ResourceType,
)
from .io import OnBoardInputKind

from .resource_defaults import get_resource_defaults


# ═══════════════════════════════════════════════════════════════════════════
# 执行配置
# ═══════════════════════════════════════════════════════════════════════════

class ExecutionType(str):
    """仅用于辨别器字段值。"""
    COMPUTE = "compute"
    LIGHTWEIGHT = "lightweight"


class ComputeExecutionConfig(BaseModel):
    """计算节点的执行配置 — 基础镜像 + Profile 注入。"""

    type: Literal["compute"] = "compute"

    profile_configmap_name: Optional[str] = Field(
        default=None,
        description=(
            "Profile ConfigMap 名称。留空时自动生成为 "
            "'mf-profile-{node_name}-{version}'。"
        ),
    )
    profile_mount_path: str = Field(
        default="/mf/profile",
        description="Profile 在容器内的挂载路径。",
    )
    input_mount_path: str = Field(
        default="/mf/input",
        description="上游 Artifact 在容器内的挂载路径。",
    )
    output_mount_path: str = Field(
        default="/mf/output",
        description="节点输出文件的存放目录。",
    )
    entrypoint_script: str = Field(
        default="run.sh",
        description="入口脚本文件名（位于 profile_mount_path 下）。",
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="注入到容器的额外环境变量。",
    )
    mpi_enabled: bool = Field(
        default=False,
        description="是否启用 MPI 并行。",
    )
    profile_templates: list[str] = Field(
        default_factory=list,
        description=(
            "需要 string.Template 预渲染的 Profile 文件列表，如 ['INCAR.template', 'KPOINTS.template']。"
            "这些文件在提交管线中被渲染，渲染后去掉 .template 后缀。"
        ),
    )


class LightweightExecutionConfig(BaseModel):
    """轻量节点的执行配置 — Python 脚本或 Profile-based shell 入口。

    支持三种互斥模式：
    - **inline_script**：直接内联 Python 代码字符串（最常用）
    - **script_path**：外置 .py 文件路径（相对于节点目录），编译时读入内联
    - **entrypoint_script**：Profile-based shell 入口（如 ``run.sh``），
      使用 container 模板模式（等同于 compute 节点，只换了镜像）。
      节点目录下须有 ``profile/`` 子目录和对应脚本文件。
    """

    type: Literal["lightweight"] = "lightweight"

    python_version: str = Field(
        default="3.10",
        description="Python 基础镜像版本（python:{version}-slim）。",
    )
    pip_dependencies: list[str] = Field(
        default_factory=list,
        description="运行时 pip 依赖列表（仅对 inline/script_path 模式有效）。",
    )

    # 模式 A: Python 内联脚本（现有）
    script_path: Optional[str] = Field(
        default=None,
        description="外置脚本路径（相对于节点目录）。",
    )
    inline_script: Optional[str] = Field(
        default=None,
        description="内联 Python 脚本内容。",
    )

    # 模式 B: Profile-based shell 入口（新增）
    entrypoint_script: Optional[str] = Field(
        default=None,
        description=(
            "Profile-based 入口脚本文件名（位于 profile/ 子目录下，如 'run.sh'）。"
            "使用 container 模板模式，与 compute 节点行为一致，只换了镜像。"
        ),
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="注入容器的额外环境变量（仅 entrypoint_script 模式使用）。",
    )

    @model_validator(mode="after")
    def _check_script_source(self) -> LightweightExecutionConfig:
        modes = [
            bool(self.script_path),
            bool(self.inline_script),
            bool(self.entrypoint_script),
        ]
        if sum(modes) == 0:
            raise ValueError(
                "必须提供 script_path、inline_script、entrypoint_script 三者之一"
            )
        if sum(modes) > 1:
            raise ValueError(
                "script_path、inline_script、entrypoint_script 三者互斥，只能选一种"
            )
        return self


# 执行配置的辨别联合体
ExecutionConfig = Annotated[
    Union[ComputeExecutionConfig, LightweightExecutionConfig],
    Field(discriminator="type"),
]

# 资源配置的辨别联合体
Resources = Annotated[
    Union[ComputeResources, LightweightResources],
    Field(discriminator="type"),
]


# ═══════════════════════════════════════════════════════════════════════════
# NodeSpec — 完整节点定义
# ═══════════════════════════════════════════════════════════════════════════

class NodeSpec(BaseModel):
    """完整的节点规格定义。

    对应磁盘上的 ``nodespec.yaml``，是节点的 Single Source of Truth。
    """

    metadata: NodeMetadata

    # ── Stream I/O ──
    stream_inputs: list[StreamInputPort] = Field(default_factory=list)
    stream_outputs: list[StreamOutputPort] = Field(default_factory=list)

    # ── On-Board I/O ──
    onboard_inputs: list[OnBoardInput] = Field(default_factory=list)
    onboard_outputs: list[OnBoardOutput] = Field(default_factory=list)

    # ── 资源与执行 ──
    resources: Resources
    execution: ExecutionConfig

    # ── 反膨胀元数据 ──
    semantic_identity: str = Field(
        default="",
        description=(
            "用一句话说明此节点的语义身份。"
            "如果描述中需要提及具体参数值，说明这应该是参数变更而非新节点。"
            "为空时自动从 metadata.name + description 生成。"
        ),
    )
    distinguishing_ports: list[str] = Field(
        default_factory=list,
        description="使此节点区别于同一基础镜像上其他节点的关键端口名。",
    )

    # ── RAG 摘要 ──
    rag_summary: str = Field(
        default="",
        description="供向量检索使用的节点摘要（可由 generate_rag_summary() 自动生成）。",
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 校验器
    # ═══════════════════════════════════════════════════════════════════════

    @model_validator(mode="before")
    @classmethod
    def _inject_type_discriminators(cls, data: Any) -> Any:
        """从 metadata.node_type 自动注入 resources.type 和 execution.type。

        nodespec.yaml 中无需重复声明这两个辨别器字段；
        若已显式写明则保留原值（向后兼容）。
        """
        if not isinstance(data, dict):
            return data
        node_type = data.get("metadata", {}).get("node_type")
        if not node_type:
            return data
        if isinstance(data.get("resources"), dict):
            data["resources"].setdefault("type", node_type)
        if isinstance(data.get("execution"), dict):
            data["execution"].setdefault("type", node_type)
        return data

    @model_validator(mode="after")
    def _validate_type_consistency(self) -> NodeSpec:
        """确保 metadata.node_type 与 resources / execution 类型一致。"""
        nt = self.metadata.node_type

        if nt == NodeType.COMPUTE:
            if not isinstance(self.resources, ComputeResources):
                raise ValueError(
                    "compute 节点的 resources 必须为 ComputeResources"
                )
            if not isinstance(self.execution, ComputeExecutionConfig):
                raise ValueError(
                    "compute 节点的 execution 必须为 ComputeExecutionConfig"
                )
        elif nt == NodeType.LIGHTWEIGHT:
            if not isinstance(self.resources, LightweightResources):
                raise ValueError(
                    "lightweight 节点的 resources 必须为 LightweightResources"
                )
            if not isinstance(self.execution, LightweightExecutionConfig):
                raise ValueError(
                    "lightweight 节点的 execution 必须为 LightweightExecutionConfig"
                )

        # parametrize 自动注入 + 校验（仅 compute 节点可用）
        if isinstance(self.resources, ComputeResources) and self.resources.parametrize:
            valid_resource_fields = set(ComputeResources.model_fields.keys()) - {"type", "parametrize"}
            onboard_input_names = {p.name for p in self.onboard_inputs}
            numeric_kinds = {OnBoardInputKind.INTEGER, OnBoardInputKind.FLOAT}
            defaults_config = get_resource_defaults()

            for res_field in self.resources.parametrize:
                if res_field not in valid_resource_fields:
                    raise ValueError(
                        f"parametrize 中 {res_field!r} 不是 ComputeResources 的有效字段。"
                        f"合法字段：{sorted(valid_resource_fields)}"
                    )
                # 从 resource_defaults.yaml 解析 param_name，默认与字段同名
                param_name = defaults_config.get(res_field, {}).get("param_name", res_field)

                # 自动注入：如果 param_name 不在 onboard_inputs 中，自动生成
                if param_name not in onboard_input_names:
                    static_value = getattr(self.resources, res_field, None)
                    auto_input = self._make_auto_onboard_input(
                        param_name, res_field, static_value, defaults_config,
                    )
                    self.onboard_inputs.append(auto_input)
                    onboard_input_names.add(param_name)

            # 校验所有绑定的 onboard input kind 必须为数值类型
            onboard_input_map = {p.name: p for p in self.onboard_inputs}
            for res_field in self.resources.parametrize:
                param_name = defaults_config.get(res_field, {}).get("param_name", res_field)
                param = onboard_input_map[param_name]
                if param.kind not in numeric_kinds:
                    raise ValueError(
                        f"parametrize 绑定的 onboard input {param_name!r} "
                        f"kind 必须为 integer 或 float，当前为 {param.kind.value!r}"
                    )

        return self

    @model_validator(mode="after")
    def _validate_port_name_uniqueness(self) -> NodeSpec:
        """确保所有端口/参数名在节点内唯一。"""
        seen: dict[str, str] = {}
        sources = [
            ("stream_inputs", self.stream_inputs),
            ("stream_outputs", self.stream_outputs),
            ("onboard_inputs", self.onboard_inputs),
            ("onboard_outputs", self.onboard_outputs),
        ]
        for source_name, ports in sources:
            for port in ports:
                key = port.name
                if key in seen:
                    raise ValueError(
                        f"端口名 {key!r} 在 {source_name} 和 {seen[key]} 中重复"
                    )
                seen[key] = source_name
        return self

    @model_validator(mode="after")
    def _auto_semantic_identity(self) -> NodeSpec:
        """semantic_identity 为空时，自动从 name + description 生成。"""
        if not self.semantic_identity:
            m = self.metadata
            prefix = f"[{m.semantic_type}] " if m.semantic_type else ""
            desc = m.description or m.name
            self.semantic_identity = f"{prefix}{m.display_name}: {desc}"
        return self

    # ═══════════════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_auto_onboard_input(
        param_name: str,
        res_field: str,
        static_value: Any,
        defaults_config: dict[str, dict[str, Any]],
    ) -> OnBoardInput:
        """根据 parametrize 自动生成 OnBoardInput。

        优先级：resource_defaults.yaml 配置 > 硬编码推断。
        ``default`` 值来自 ComputeResources 中的静态声明（如 cpu_cores: 4）。
        """
        cfg = defaults_config.get(res_field, {})

        # 推断 kind：整数字段用 integer，浮点字段用 float
        kind_str = cfg.get("kind")
        if kind_str:
            kind = OnBoardInputKind(kind_str)
        elif isinstance(static_value, float):
            kind = OnBoardInputKind.FLOAT
        else:
            kind = OnBoardInputKind.INTEGER

        return OnBoardInput(
            name=param_name,
            display_name=cfg.get("display_name"),  # None → auto-gen from name
            kind=kind,
            default=static_value,
            min_value=cfg.get("min_value"),
            max_value=cfg.get("max_value"),
            unit=cfg.get("unit"),
            description=cfg.get("description", ""),
            resource_param=True,
        )

    @property
    def quality_gates(self) -> list[OnBoardOutput]:
        """返回所有标记为 quality_gate=True 的 onboard outputs。"""
        return [o for o in self.onboard_outputs if o.quality_gate]

    def generate_rag_summary(self) -> str:
        """基于元数据和端口信息自动生成 RAG 摘要。

        摘要包含：节点名称、描述、分类、标签、端口列表等，
        用于向量检索时提供充分上下文。
        """
        parts: list[str] = []
        m = self.metadata

        parts.append(f"Node: {m.display_name} ({m.name} v{m.version})")
        parts.append(f"Type: {m.node_type.value} | Category: {m.category.value}")
        if m.semantic_type:
            parts.append(f"Semantic Type: {m.semantic_type}")
            # 从注册表追加描述
            try:
                from .semantic_registry import load_semantic_registry
                registry = load_semantic_registry()
                entry = registry.get(m.semantic_type)
                if entry and entry.description:
                    parts.append(f"Semantic Description: {entry.description}")
            except Exception:
                pass
        parts.append(f"Description: {m.description}")
        parts.append(f"Semantic Identity: {self.semantic_identity}")

        if m.tags.software:
            parts.append(f"Software: {m.tags.software} {m.tags.version or ''}")
        if m.tags.method:
            parts.append(f"Methods: {', '.join(m.tags.method)}")
        if m.tags.capabilities:
            parts.append(f"Capabilities: {', '.join(m.tags.capabilities)}")
        if m.tags.domain:
            parts.append(f"Domain: {', '.join(m.tags.domain)}")
        if m.tags.keywords:
            parts.append(f"Keywords: {', '.join(m.tags.keywords)}")

        if self.stream_inputs:
            names = [p.name for p in self.stream_inputs]
            parts.append(f"Stream Inputs: {', '.join(names)}")
        if self.stream_outputs:
            names = [p.name for p in self.stream_outputs]
            parts.append(f"Stream Outputs: {', '.join(names)}")
        if self.onboard_inputs:
            names = [p.name for p in self.onboard_inputs]
            parts.append(f"On-Board Inputs: {', '.join(names)}")
        if self.onboard_outputs:
            names = [p.name for p in self.onboard_outputs]
            parts.append(f"On-Board Outputs: {', '.join(names)}")

        # Quality gates
        gates = self.quality_gates
        if gates:
            gate_descs = [
                f"{g.name} ({g.gate_default.value})"
                + (f": {g.gate_description}" if g.gate_description else "")
                for g in gates
            ]
            parts.append(f"Quality Gates: {', '.join(gate_descs)}")

        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════════════════
    # YAML 序列化 / 反序列化
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def from_yaml(cls, path: str | Path) -> NodeSpec:
        """从 YAML 文件加载并校验 NodeSpec。

        Parameters:
            path: nodespec.yaml 的文件路径。

        Returns:
            校验后的 NodeSpec 实例。

        Raises:
            FileNotFoundError: 文件不存在。
            pydantic.ValidationError: Schema 校验失败。
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def to_yaml(self, path: str | Path) -> None:
        """将 NodeSpec 序列化为 YAML 文件。

        Parameters:
            path: 输出文件路径。
        """
        path = Path(path)
        data = self.model_dump(mode="json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def to_dict(self) -> dict[str, Any]:
        """导出为 JSON 兼容的字典。"""
        return self.model_dump(mode="json")
