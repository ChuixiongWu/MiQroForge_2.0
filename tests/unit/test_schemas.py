"""节点 Schema 创建、校验、序列化测试。

覆盖所有 Schema 模型：
- NodeType / NodeCategory 枚举
- NodeTags / NodeMetadata（含名称、版本、base_image_ref 校验）
- ComputeResources / LightweightResources
- Stream I/O 四种类型 + 端口
- OnBoardInput / OnBoardOutput
- BaseImageSpec / BaseImageRegistry
- ComputeExecutionConfig / LightweightExecutionConfig
- NodeSpec（完整节点定义 + 类型一致性 + 端口唯一性 + YAML 序列化）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from nodes.schemas import (
    BaseImageRegistry,
    BaseImageSpec,
    ComputeExecutionConfig,
    ComputeResources,
    ConnectionValidationResult,
    LightweightExecutionConfig,
    LightweightResources,
    LogicValueKind,
    LogicValueType,
    NodeCategory,
    NodeMetadata,
    NodeSpec,
    NodeTags,
    NodeType,
    OnBoardInput,
    OnBoardInputKind,
    OnBoardOutput,
    PhysicalQuantityType,
    ReportFormat,
    ReportObjectType,
    ResourceType,
    SoftwareDataPackageType,
    StreamIOCategory,
    StreamInputPort,
    StreamOutputPort,
)


# ═══════════════════════════════════════════════════════════════════════════
# 枚举类型
# ═══════════════════════════════════════════════════════════════════════════

class TestEnums:

    def test_node_type_values(self):
        assert NodeType.COMPUTE == "compute"
        assert NodeType.LIGHTWEIGHT == "lightweight"
        assert len(NodeType) == 2

    def test_node_category_values(self):
        cats = [c.value for c in NodeCategory]
        assert set(cats) == {
            "quantum", "chemistry", "preprocessing",
            "postprocessing", "utility",
        }

    def test_stream_io_category_values(self):
        assert len(StreamIOCategory) == 4

    def test_logic_value_kind_values(self):
        assert set(k.value for k in LogicValueKind) == {
            "boolean", "enum", "integer", "signal",
        }

    def test_report_format_values(self):
        assert set(f.value for f in ReportFormat) == {
            "markdown", "json", "png", "csv", "pdf", "html",
        }

    def test_onboard_input_kind_values(self):
        assert set(k.value for k in OnBoardInputKind) == {
            "string", "integer", "float", "boolean", "enum", "textarea",
        }

    def test_resource_type_values(self):
        assert ResourceType.COMPUTE == "compute"
        assert ResourceType.LIGHTWEIGHT == "lightweight"


# ═══════════════════════════════════════════════════════════════════════════
# NodeTags
# ═══════════════════════════════════════════════════════════════════════════

class TestNodeTags:

    def test_default_empty(self):
        t = NodeTags()
        assert t.software is None
        assert t.method == []
        assert t.keywords == []

    def test_full_tags(self):
        t = NodeTags(
            software="vasp",
            version="6.4.1",
            method=["DFT", "PBE"],
            domain=["solid-state"],
            capabilities=["geometry-optimization"],
            keywords=["relaxation"],
        )
        assert t.software == "vasp"
        assert len(t.method) == 2

    def test_serialization_roundtrip(self):
        t = NodeTags(software="gaussian", method=["HF"])
        d = t.model_dump()
        t2 = NodeTags.model_validate(d)
        assert t == t2


# ═══════════════════════════════════════════════════════════════════════════
# NodeMetadata
# ═══════════════════════════════════════════════════════════════════════════

class TestNodeMetadata:

    def _make_compute_meta(self, **overrides) -> dict:
        defaults = dict(
            name="vasp-geo-opt",
            version="1.0.0",
            display_name="VASP Geometry Optimization",
            description="Relax crystal structure using VASP.",
            node_type=NodeType.COMPUTE,
            category=NodeCategory.CHEMISTRY,
            author="MiQroForge Team",
            base_image_ref="vasp-6.4.1",
        )
        defaults.update(overrides)
        return defaults

    def _make_lightweight_meta(self, **overrides) -> dict:
        defaults = dict(
            name="unit-converter",
            version="1.0.0",
            display_name="Unit Converter",
            description="Convert physical quantities.",
            node_type=NodeType.LIGHTWEIGHT,
            category=NodeCategory.UTILITY,
            author="MiQroForge Team",
        )
        defaults.update(overrides)
        return defaults

    def test_valid_compute_metadata(self):
        m = NodeMetadata(**self._make_compute_meta())
        assert m.name == "vasp-geo-opt"
        assert m.node_type == NodeType.COMPUTE

    def test_valid_lightweight_metadata(self):
        m = NodeMetadata(**self._make_lightweight_meta())
        assert m.base_image_ref is None

    # ── 名称校验 ──

    def test_name_uppercase_rejected(self):
        with pytest.raises(ValidationError, match="小写"):
            NodeMetadata(**self._make_compute_meta(name="VASP-Geo"))

    def test_name_underscore_rejected(self):
        with pytest.raises(ValidationError, match="小写"):
            NodeMetadata(**self._make_compute_meta(name="vasp_geo"))

    def test_name_starting_with_digit_rejected(self):
        with pytest.raises(ValidationError, match="小写"):
            NodeMetadata(**self._make_compute_meta(name="1vasp"))

    def test_name_single_word_valid(self):
        m = NodeMetadata(**self._make_lightweight_meta(name="converter"))
        assert m.name == "converter"

    # ── 版本校验 ──

    def test_version_semver_valid(self):
        m = NodeMetadata(**self._make_lightweight_meta(version="2.1.0"))
        assert m.version == "2.1.0"

    def test_version_prerelease_valid(self):
        m = NodeMetadata(**self._make_lightweight_meta(version="1.0.0-alpha.1"))
        assert m.version == "1.0.0-alpha.1"

    def test_version_invalid_format(self):
        with pytest.raises(ValidationError, match="semver"):
            NodeMetadata(**self._make_lightweight_meta(version="v1.0"))

    def test_version_missing_patch(self):
        with pytest.raises(ValidationError, match="semver"):
            NodeMetadata(**self._make_lightweight_meta(version="1.0"))

    # ── base_image_ref 交叉校验 ──

    def test_compute_without_base_image_ref_rejected(self):
        with pytest.raises(ValidationError, match="base_image_ref"):
            NodeMetadata(**self._make_compute_meta(base_image_ref=None))

    def test_lightweight_with_base_image_ref_rejected(self):
        with pytest.raises(ValidationError, match="base_image_ref"):
            NodeMetadata(**self._make_lightweight_meta(base_image_ref="some-ref"))

    # ── 序列化 ──

    def test_metadata_serialization(self):
        m = NodeMetadata(**self._make_compute_meta())
        d = m.model_dump()
        assert d["node_type"] == "compute"
        m2 = NodeMetadata.model_validate(d)
        assert m == m2


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeResources:

    def test_valid_creation(self):
        r = ComputeResources(
            cpu_cores=8,
            mem_gb=32.0,
            estimated_walltime_hours=2.0,
            gpu_count=1,
            gpu_type="nvidia-a100",
        )
        assert r.cpu_cores == 8
        assert r.type == "compute"

    def test_defaults(self):
        r = ComputeResources(
            cpu_cores=4,
            mem_gb=16.0,
            estimated_walltime_hours=1.0,
        )
        assert r.gpu_count == 0
        assert r.gpu_type is None
        assert r.scratch_disk_gb == 0
        assert r.parallel_tasks == 1

    def test_zero_cpu_rejected(self):
        with pytest.raises(ValidationError):
            ComputeResources(
                cpu_cores=0,
                mem_gb=16.0,
                estimated_walltime_hours=1.0,
            )

    def test_negative_memory_rejected(self):
        with pytest.raises(ValidationError):
            ComputeResources(
                cpu_cores=4,
                mem_gb=-1.0,
                estimated_walltime_hours=1.0,
            )


class TestLightweightResources:

    def test_all_defaults(self):
        r = LightweightResources()
        assert r.cpu_cores == 1
        assert r.memory_gb == 1.0
        assert r.estimated_walltime_hours == pytest.approx(0.083)
        assert r.timeout_seconds == 300
        assert r.type == "lightweight"

    def test_custom_values(self):
        r = LightweightResources(
            cpu_cores=2,
            memory_gb=4.0,
            timeout_seconds=600,
        )
        assert r.cpu_cores == 2


# ═══════════════════════════════════════════════════════════════════════════
# Stream I/O 类型
# ═══════════════════════════════════════════════════════════════════════════

class TestPhysicalQuantityType:

    def test_creation(self):
        pq = PhysicalQuantityType(
            category=StreamIOCategory.PHYSICAL_QUANTITY,
unit="eV",
        )
        assert pq.category == StreamIOCategory.PHYSICAL_QUANTITY
        assert pq.shape == "scalar"

    def test_with_constraints(self):
        pq = PhysicalQuantityType(
            category=StreamIOCategory.PHYSICAL_QUANTITY,
            unit="K",
            constraints={"min": 0},
        )
        assert pq.constraints == {"min": 0}


class TestSoftwareDataPackageType:

    def test_creation(self):
        sdp = SoftwareDataPackageType(
            category=StreamIOCategory.SOFTWARE_DATA_PACKAGE,
            ecosystem="vasp", data_type="wavefunction",
        )
        assert sdp.category == StreamIOCategory.SOFTWARE_DATA_PACKAGE

    def test_minimal_fields(self):
        """只需 category + ecosystem + data_type。"""
        sdp = SoftwareDataPackageType(
            category=StreamIOCategory.SOFTWARE_DATA_PACKAGE,
            ecosystem="gaussian",
            data_type="checkpoint",
        )
        assert sdp.ecosystem == "gaussian"
        assert sdp.data_type == "checkpoint"


class TestLogicValueType:

    def test_boolean(self):
        lv = LogicValueType(category=StreamIOCategory.LOGIC_VALUE, kind=LogicValueKind.BOOLEAN)
        assert lv.category == StreamIOCategory.LOGIC_VALUE

    def test_enum_with_values(self):
        lv = LogicValueType(
            category=StreamIOCategory.LOGIC_VALUE,
            kind=LogicValueKind.ENUM,
            allowed_values=["PBE", "PBEsol", "HSE06"],
        )
        assert len(lv.allowed_values) == 3

    def test_integer_with_range(self):
        lv = LogicValueType(
            category=StreamIOCategory.LOGIC_VALUE,
            kind=LogicValueKind.INTEGER,
            value_range={"min": 1, "max": 100},
        )
        assert lv.value_range["max"] == 100


class TestReportObjectType:

    def test_creation(self):
        r = ReportObjectType(category=StreamIOCategory.REPORT_OBJECT, format=ReportFormat.JSON)
        assert r.category == StreamIOCategory.REPORT_OBJECT

    def test_with_description(self):
        r = ReportObjectType(
            category=StreamIOCategory.REPORT_OBJECT,
            format=ReportFormat.MARKDOWN,
            description="Convergence report",
        )
        assert r.description == "Convergence report"


# ═══════════════════════════════════════════════════════════════════════════
# Stream 端口
# ═══════════════════════════════════════════════════════════════════════════

class TestStreamPorts:

    def test_input_port(self):
        p = StreamInputPort(
            name="structure_in",
            display_name="Input Structure",
            io_type=SoftwareDataPackageType(
                category=StreamIOCategory.SOFTWARE_DATA_PACKAGE,
                ecosystem="vasp", data_type="poscar",
            ),
            required=True,
        )
        assert p.name == "structure_in"
        assert p.io_type.category == StreamIOCategory.SOFTWARE_DATA_PACKAGE

    def test_output_port(self):
        p = StreamOutputPort(
            name="energy_out",
            display_name="Total Energy",
            io_type=PhysicalQuantityType(
                category=StreamIOCategory.PHYSICAL_QUANTITY,
    unit="eV",
            ),
        )
        assert p.io_type.unit == "eV"

    def test_discriminated_union_from_dict(self):
        """从字典构建端口，验证辨别器自动选择正确类型。"""
        data = {
            "name": "test",
            "display_name": "Test",
            "io_type": {
                "category": "logic_value",
                "kind": "boolean",
            },
        }
        p = StreamInputPort.model_validate(data)
        assert isinstance(p.io_type, LogicValueType)


# ═══════════════════════════════════════════════════════════════════════════
# On-Board I/O
# ═══════════════════════════════════════════════════════════════════════════

class TestOnBoardIO:

    def test_onboard_input_enum(self):
        oi = OnBoardInput(
            name="functional",
            display_name="Exchange-Correlation Functional",
            kind=OnBoardInputKind.ENUM,
            allowed_values=["PBE", "PBEsol", "HSE06"],
            default="PBE",
        )
        assert oi.kind == OnBoardInputKind.ENUM
        assert oi.default == "PBE"

    def test_onboard_input_float_with_range(self):
        oi = OnBoardInput(
            name="encut",
            display_name="Cutoff Energy",
            kind=OnBoardInputKind.FLOAT,
            default=520.0,
            min_value=200.0,
            max_value=1000.0,
            unit="eV",
        )
        assert oi.min_value == 200.0

    def test_onboard_output(self):
        oo = OnBoardOutput(
            name="final_energy",
            display_name="Final Energy",
            kind=OnBoardInputKind.FLOAT,
            unit="eV",
            description="Total energy after convergence.",
        )
        assert oo.unit == "eV"


# ═══════════════════════════════════════════════════════════════════════════
# BaseImageSpec / BaseImageRegistry
# ═══════════════════════════════════════════════════════════════════════════

class TestBaseImageSpec:

    def test_creation(self):
        spec = BaseImageSpec(
            name="vasp-6.4.1",
            display_name="VASP 6.4.1",
            image="registry.example.com/vasp",
            tag="6.4.1",
            software_name="vasp",
            software_version="6.4.1",
        )
        assert spec.full_image_ref() == "registry.example.com/vasp:6.4.1"

    def test_defaults(self):
        spec = BaseImageSpec(
            name="test",
            display_name="Test",
            image="docker.io/test",
            tag="latest",
            software_name="test",
            software_version="1.0",
        )
        assert spec.workdir == "/mf/workdir"
        assert spec.entrypoint_convention == "/mf/profile/run.sh"
        assert spec.source_type == "dockerhub"


class TestBaseImageRegistry:

    @pytest.fixture()
    def registry(self):
        return BaseImageRegistry(
            images=[
                BaseImageSpec(
                    name="vasp-6.4.1",
                    display_name="VASP 6.4.1",
                    image="reg/vasp",
                    tag="6.4.1",
                    software_name="vasp",
                    software_version="6.4.1",
                ),
                BaseImageSpec(
                    name="vasp-6.3.0",
                    display_name="VASP 6.3.0",
                    image="reg/vasp",
                    tag="6.3.0",
                    software_name="vasp",
                    software_version="6.3.0",
                ),
                BaseImageSpec(
                    name="gaussian-16",
                    display_name="Gaussian 16",
                    image="reg/gaussian",
                    tag="16",
                    software_name="gaussian",
                    software_version="16",
                ),
            ],
        )

    def test_get_existing(self, registry):
        img = registry.get("vasp-6.4.1")
        assert img is not None
        assert img.software_version == "6.4.1"

    def test_get_missing(self, registry):
        assert registry.get("nonexistent") is None

    def test_list_by_software(self, registry):
        vasp_images = registry.list_by_software("vasp")
        assert len(vasp_images) == 2

    def test_list_by_software_empty(self, registry):
        assert registry.list_by_software("orca") == []


# ═══════════════════════════════════════════════════════════════════════════
# ExecutionConfig
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeExecutionConfig:

    def test_defaults(self):
        c = ComputeExecutionConfig()
        assert c.type == "compute"
        assert c.profile_mount_path == "/mf/profile"
        assert c.input_mount_path == "/mf/input"
        assert c.output_mount_path == "/mf/output"
        assert c.entrypoint_script == "run.sh"
        assert c.mpi_enabled is False
        assert c.profile_templates == []

    def test_with_templates(self):
        c = ComputeExecutionConfig(
            profile_templates=["INCAR.template", "KPOINTS.template"],
            mpi_enabled=True,
        )
        assert len(c.profile_templates) == 2
        assert c.mpi_enabled


class TestLightweightExecutionConfig:

    def test_with_script_path(self):
        c = LightweightExecutionConfig(script_path="run.py")
        assert c.type == "lightweight"
        assert c.python_version == "3.10"

    def test_with_inline_script(self):
        c = LightweightExecutionConfig(inline_script="print('hello')")
        assert c.inline_script == "print('hello')"

    def test_neither_source_rejected(self):
        with pytest.raises(ValidationError, match="三者之一"):
            LightweightExecutionConfig()

    def test_both_sources_rejected(self):
        with pytest.raises(ValidationError, match="三者互斥"):
            LightweightExecutionConfig(
                script_path="run.py",
                inline_script="print(1)",
            )

    def test_with_entrypoint_script(self):
        c = LightweightExecutionConfig(entrypoint_script="run.sh")
        assert c.entrypoint_script == "run.sh"
        assert c.script_path is None
        assert c.inline_script is None

    def test_entrypoint_with_inline_rejected(self):
        with pytest.raises(ValidationError, match="三者互斥"):
            LightweightExecutionConfig(
                entrypoint_script="run.sh",
                inline_script="print(1)",
            )

    def test_environment_field(self):
        c = LightweightExecutionConfig(
            entrypoint_script="run.sh",
            environment={"MY_VAR": "hello"},
        )
        assert c.environment == {"MY_VAR": "hello"}


# ═══════════════════════════════════════════════════════════════════════════
# NodeSpec — 完整节点定义
# ═══════════════════════════════════════════════════════════════════════════

# ── Fixture 工厂 ──

def _make_compute_nodespec(**overrides) -> dict:
    """构建一个合法的 compute NodeSpec 字典。"""
    defaults = dict(
        metadata=dict(
            name="vasp-geo-opt",
            version="1.0.0",
            display_name="VASP Geometry Optimization",
            description="Relax crystal structure using VASP.",
            node_type="compute",
            category="chemistry",
            author="MiQroForge Team",
            base_image_ref="vasp-6.4.1",
        ),
        stream_inputs=[
            dict(
                name="structure_in",
                display_name="Input Structure",
                io_type=dict(
                    category="software_data_package",
                    ecosystem="vasp",
                    data_type="poscar",
                ),
            ),
        ],
        stream_outputs=[
            dict(
                name="energy_out",
                display_name="Total Energy",
                io_type=dict(
                    category="physical_quantity",
                    unit="eV",
                ),
            ),
            dict(
                name="structure_out",
                display_name="Optimized Structure",
                io_type=dict(
                    category="software_data_package",
                    ecosystem="vasp",
                    data_type="contcar",
                ),
            ),
        ],
        onboard_inputs=[
            dict(
                name="encut",
                display_name="Cutoff Energy",
                kind="float",
                default=520.0,
                unit="eV",
            ),
        ],
        onboard_outputs=[
            dict(
                name="converged",
                display_name="Convergence Status",
                kind="boolean",
            ),
        ],
        resources=dict(
            type="compute",
            cpu_cores=8,
            mem_gb=32.0,
            estimated_walltime_hours=2.0,
        ),
        execution=dict(
            type="compute",
            profile_templates=["INCAR.template", "KPOINTS.template"],
        ),
        semantic_identity=(
            "Performs geometry optimization (ionic relaxation) "
            "using VASP's conjugate gradient algorithm."
        ),
        distinguishing_ports=["structure_in", "structure_out"],
    )
    defaults.update(overrides)
    return defaults


def _make_lightweight_nodespec(**overrides) -> dict:
    """构建一个合法的 lightweight NodeSpec 字典。"""
    defaults = dict(
        metadata=dict(
            name="unit-converter",
            version="1.0.0",
            display_name="Unit Converter",
            description="Convert physical quantities between units.",
            node_type="lightweight",
            category="utility",
            author="MiQroForge Team",
        ),
        stream_inputs=[
            dict(
                name="value_in",
                display_name="Input Value",
                io_type=dict(
                    category="physical_quantity",
                    unit="eV",
                ),
            ),
        ],
        stream_outputs=[
            dict(
                name="value_out",
                display_name="Converted Value",
                io_type=dict(
                    category="physical_quantity",
                    unit="Ha",
                ),
            ),
        ],
        onboard_inputs=[
            dict(
                name="target_unit",
                display_name="Target Unit",
                kind="string",
                default="Ha",
            ),
        ],
        resources=dict(type="lightweight"),
        execution=dict(
            type="lightweight",
            script_path="run.py",
        ),
        semantic_identity="Converts a physical quantity from one unit to another.",
    )
    defaults.update(overrides)
    return defaults


class TestNodeSpec:
    """NodeSpec 创建与校验。"""

    def test_valid_compute_nodespec(self):
        ns = NodeSpec.model_validate(_make_compute_nodespec())
        assert ns.metadata.node_type == NodeType.COMPUTE
        assert isinstance(ns.resources, ComputeResources)
        assert isinstance(ns.execution, ComputeExecutionConfig)

    def test_valid_lightweight_nodespec(self):
        ns = NodeSpec.model_validate(_make_lightweight_nodespec())
        assert ns.metadata.node_type == NodeType.LIGHTWEIGHT
        assert isinstance(ns.resources, LightweightResources)
        assert isinstance(ns.execution, LightweightExecutionConfig)

    # ── 类型一致性 ──

    def test_compute_meta_with_lightweight_resources_rejected(self):
        data = _make_compute_nodespec()
        data["resources"] = {"type": "lightweight"}
        with pytest.raises(ValidationError, match="ComputeResources"):
            NodeSpec.model_validate(data)

    def test_compute_meta_with_lightweight_execution_rejected(self):
        data = _make_compute_nodespec()
        data["execution"] = {"type": "lightweight", "script_path": "run.py"}
        with pytest.raises(ValidationError, match="ComputeExecutionConfig"):
            NodeSpec.model_validate(data)

    def test_lightweight_meta_with_compute_resources_rejected(self):
        data = _make_lightweight_nodespec()
        data["resources"] = {
            "type": "compute",
            "cpu_cores": 4,
            "mem_gb": 16.0,
            "estimated_walltime_hours": 1.0,
        }
        with pytest.raises(ValidationError, match="LightweightResources"):
            NodeSpec.model_validate(data)

    # ── 端口名唯一性 ──

    def test_duplicate_port_name_rejected(self):
        data = _make_compute_nodespec()
        data["onboard_inputs"].append(
            dict(name="structure_in", display_name="Dup", kind="string")
        )
        with pytest.raises(ValidationError, match="重复"):
            NodeSpec.model_validate(data)

    def test_duplicate_within_stream_outputs_rejected(self):
        data = _make_compute_nodespec()
        data["stream_outputs"].append(
            dict(
                name="energy_out",  # 与已有输出同名
                display_name="Dup Energy",
                io_type=dict(
                    category="physical_quantity",
                    unit="eV",
                ),
            ),
        )
        with pytest.raises(ValidationError, match="重复"):
            NodeSpec.model_validate(data)

    # ── RAG 摘要 ──

    def test_generate_rag_summary(self):
        ns = NodeSpec.model_validate(_make_compute_nodespec())
        summary = ns.generate_rag_summary()
        assert "VASP Geometry Optimization" in summary
        assert "compute" in summary
        assert "structure_in" in summary
        assert "energy_out" in summary

    def test_generate_rag_summary_lightweight(self):
        ns = NodeSpec.model_validate(_make_lightweight_nodespec())
        summary = ns.generate_rag_summary()
        assert "Unit Converter" in summary
        assert "lightweight" in summary

    # ── 序列化 / 反序列化 ──

    def test_dict_roundtrip(self):
        ns = NodeSpec.model_validate(_make_compute_nodespec())
        d = ns.to_dict()
        ns2 = NodeSpec.model_validate(d)
        assert ns2.metadata.name == ns.metadata.name
        assert len(ns2.stream_inputs) == len(ns.stream_inputs)

    def test_yaml_roundtrip(self, tmp_path):
        """写入 YAML 再读回，验证全字段保真。"""
        ns = NodeSpec.model_validate(_make_compute_nodespec())
        yaml_path = tmp_path / "nodespec.yaml"
        ns.to_yaml(yaml_path)
        ns2 = NodeSpec.from_yaml(yaml_path)
        assert ns2.metadata.name == "vasp-geo-opt"
        assert ns2.metadata.node_type == NodeType.COMPUTE
        assert len(ns2.stream_outputs) == 2
        assert ns2.semantic_identity == ns.semantic_identity

    def test_yaml_roundtrip_lightweight(self, tmp_path):
        ns = NodeSpec.model_validate(_make_lightweight_nodespec())
        yaml_path = tmp_path / "nodespec.yaml"
        ns.to_yaml(yaml_path)
        ns2 = NodeSpec.from_yaml(yaml_path)
        assert ns2.metadata.name == "unit-converter"
        assert isinstance(ns2.execution, LightweightExecutionConfig)

    def test_from_yaml_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            NodeSpec.from_yaml("/nonexistent/path/nodespec.yaml")

    def test_from_yaml_invalid_content(self, tmp_path):
        """YAML 内容不符合 Schema → ValidationError。"""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("name: just-a-name\n")
        with pytest.raises(Exception):
            NodeSpec.from_yaml(bad_yaml)

    # ── 空端口列表合法 ──

    def test_no_stream_io_valid(self):
        data = _make_lightweight_nodespec()
        data["stream_inputs"] = []
        data["stream_outputs"] = []
        ns = NodeSpec.model_validate(data)
        assert len(ns.stream_inputs) == 0



# ═══════════════════════════════════════════════════════════════════════════
# NodeSpec — 从 YAML fixture 加载（集成验证）
# ═══════════════════════════════════════════════════════════════════════════

class TestNodeSpecYAMLFixture:
    """通过构造一个完整的 YAML fixture 来验证端到端加载。"""

    YAML_CONTENT = """\
metadata:
  name: vasp-band-structure
  version: 1.0.0
  display_name: VASP Band Structure
  description: Calculate electronic band structure using VASP.
  node_type: compute
  category: chemistry
  author: Expert User
  base_image_ref: vasp-6.4.1
  tags:
    software: vasp
    version: "6.4.1"
    method:
      - DFT
    capabilities:
      - band-structure

stream_inputs:
  - name: charge_density_in
    display_name: Charge Density
    io_type:
      category: software_data_package
      ecosystem: vasp
      data_type: charge_density
      file_patterns:
        - CHGCAR

stream_outputs:
  - name: band_data_out
    display_name: Band Structure Data
    io_type:
      category: report_object
      format: json
      description: Band energies along k-path

onboard_inputs:
  - name: kpath_density
    display_name: K-Point Path Density
    kind: integer
    default: 40
    min_value: 10
    max_value: 200

onboard_outputs:
  - name: band_gap
    display_name: Band Gap
    kind: float
    unit: eV
    description: Electronic band gap

resources:
  type: compute
  cpu_cores: 16
  mem_gb: 64.0
  estimated_walltime_hours: 4.0
  gpu_count: 0

execution:
  type: compute
  profile_templates:
    - INCAR.template
    - KPOINTS.template
  mpi_enabled: true
  environment:
    VASP_NCORE: "4"

semantic_identity: >-
  Calculates the electronic band structure along a specified k-point path,
  providing band energies for visualization and band gap analysis.

distinguishing_ports:
  - charge_density_in
  - band_data_out
"""

    def test_load_from_yaml_fixture(self, tmp_path):
        yaml_path = tmp_path / "nodespec.yaml"
        yaml_path.write_text(self.YAML_CONTENT)

        ns = NodeSpec.from_yaml(yaml_path)

        assert ns.metadata.name == "vasp-band-structure"
        assert ns.metadata.tags.software == "vasp"
        assert len(ns.stream_inputs) == 1
        assert ns.stream_inputs[0].io_type.ecosystem == "vasp"
        assert len(ns.onboard_inputs) == 1
        assert ns.onboard_inputs[0].default == 40
        assert ns.resources.cpu_cores == 16
        assert ns.execution.mpi_enabled is True
        assert len(ns.execution.profile_templates) == 2
        assert ns.execution.environment["VASP_NCORE"] == "4"

    def test_yaml_fixture_generates_valid_rag_summary(self, tmp_path):
        yaml_path = tmp_path / "nodespec.yaml"
        yaml_path.write_text(self.YAML_CONTENT)
        ns = NodeSpec.from_yaml(yaml_path)
        summary = ns.generate_rag_summary()
        assert "Band Structure" in summary
        assert "band_data_out" in summary
