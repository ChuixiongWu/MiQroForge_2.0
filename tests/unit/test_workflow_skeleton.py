"""水分子热力学工作流骨架测试。

用真实的计算化学场景验证 Schema 体系的语义完整性：

  ┌─────────────┐     checkpoint     ┌──────────────┐    thermo_data    ┌──────────────────┐
  │ gaussian     │ ─────────────────▶ │ gaussian     │ ────────────────▶ │ thermo           │
  │ geo-opt      │     converged      │ freq         │   is_minimum     │ extractor         │
  │ (compute)    │ ─── (LogicValue) ─▶│ (compute)    │ ── (LogicValue) ▶│ (lightweight)     │
  └─────────────┘                    └──────────────┘                  └──────────────────┘
       ▲                                                                    │
  on-board:                                                            stream out:
  functional=B3LYP                                                     gibbs_energy (Ha)
  basis_set=6-31G*                                                     enthalpy (Ha)
  charge=0                                                             thermo_report (JSON)
  multiplicity=1

验证目标：
  1. 三个 NodeSpec 各自通过 Pydantic 校验
  2. 合法连接全部通过 validate_connection
  3. 非法跨类别 / 跨生态系统连接被正确拒绝
  4. YAML 序列化往返保持完整
"""

from __future__ import annotations

import pytest

from nodes.schemas import (
    NodeSpec,
    validate_connection,
)
from nodes.schemas.io import (
    StreamInputPort,
    StreamOutputPort,
)


# ═══════════════════════════════════════════════════════════════════════════
# 三个节点的 nodespec 字典
# ═══════════════════════════════════════════════════════════════════════════

GEO_OPT_SPEC = dict(
    metadata=dict(
        name="gaussian-geo-opt",
        version="1.0.0",
        display_name="Gaussian Geometry Optimization",
        description="使用 Gaussian 进行分子几何构型优化，寻找势能面极小点。",
        node_type="compute",
        category="chemistry",
        author="MiQroForge Team",
        base_image_ref="gaussian-16",
        tags=dict(
            software="gaussian",
            version="16",
            method=["DFT", "HF"],
            capabilities=["geometry-optimization"],
            domain=["molecular"],
        ),
    ),
    stream_inputs=[
        # 初始结构可以从上游节点传入（例如结构构建器）
        dict(
            name="initial_structure",
            display_name="Initial Molecular Structure",
            io_type=dict(
                category="software_data_package",
                ecosystem="gaussian",
                data_type="molecule-spec",
            ),
            required=False,  # 也可以用 on-board 参数手动指定
            description="上游传入的分子结构（.gjf 片段）。若不连接，由 on-board 参数指定。",
        ),
    ],
    stream_outputs=[
        dict(
            name="optimized_checkpoint",
            display_name="Optimized Checkpoint",
            io_type=dict(
                category="software_data_package",
                ecosystem="gaussian",
                data_type="checkpoint",
                file_patterns=["*.chk"],
                estimated_size_mb=50.0,
            ),
            description="含优化后波函数的 checkpoint 文件，供后续 freq 计算使用。",
        ),
        dict(
            name="total_energy",
            display_name="Total Energy",
            io_type=dict(
                category="physical_quantity",
                unit="Ha",
            ),
            description="最终 SCF 总能量。",
        ),
        dict(
            name="converged",
            display_name="Convergence Flag",
            io_type=dict(
                category="logic_value",
                kind="boolean",
            ),
            description="优化是否收敛。",
        ),
    ],
    onboard_inputs=[
        dict(name="functional", display_name="泛函", kind="enum",
             allowed_values=["B3LYP", "PBE0", "M06-2X", "wB97XD", "HF"],
             default="B3LYP"),
        dict(name="basis_set", display_name="基组", kind="string",
             default="6-31G*"),
        dict(name="charge", display_name="电荷", kind="integer",
             default=0),
        dict(name="multiplicity", display_name="自旋多重度", kind="integer",
             default=1, min_value=1),
        dict(name="max_cycles", display_name="最大优化步数", kind="integer",
             default=100, min_value=1, max_value=500),
    ],
    onboard_outputs=[
        dict(name="n_steps", display_name="优化步数", kind="integer"),
        dict(name="final_energy_display", display_name="最终能量",
             kind="float", unit="Ha"),
    ],
    resources=dict(
        cpu_cores=4,
        memory_gb=8.0,
        estimated_walltime_hours=1.0,
    ),
    execution=dict(
        profile_templates=["input.gjf.template"],
        environment={"GAUSS_SCRDIR": "/mf/workdir/scratch"},
    ),
    semantic_identity=(
        "在势能面上搜索极小点，输出优化后的分子几何构型和 checkpoint。"
    ),
    distinguishing_ports=["optimized_checkpoint"],
)


FREQ_SPEC = dict(
    metadata=dict(
        name="gaussian-freq",
        version="1.0.0",
        display_name="Gaussian Frequency Calculation",
        description=(
            "在优化后的构型上计算谐振频率。"
            "产出振动模式、零点能、热力学数据。"
            "无虚频表示该构型为真正极小点。"
        ),
        node_type="compute",
        category="chemistry",
        author="MiQroForge Team",
        base_image_ref="gaussian-16",
        tags=dict(
            software="gaussian",
            version="16",
            method=["DFT", "HF"],
            capabilities=["frequency", "thermochemistry"],
            domain=["molecular"],
        ),
    ),
    stream_inputs=[
        dict(
            name="checkpoint_in",
            display_name="Input Checkpoint",
            io_type=dict(
                category="software_data_package",
                ecosystem="gaussian",
                data_type="checkpoint",
            ),
            description="geo-opt 产出的 checkpoint，包含优化后的波函数。",
        ),
        dict(
            name="opt_converged",
            display_name="Optimization Converged",
            io_type=dict(
                category="logic_value",
                kind="boolean",
            ),
            required=False,
            description="上游优化是否收敛。可用于条件执行。",
        ),
    ],
    stream_outputs=[
        dict(
            name="thermo_data",
            display_name="Thermodynamic Data",
            io_type=dict(
                category="software_data_package",
                ecosystem="gaussian",
                data_type="thermo-data",
                file_patterns=["thermo.json"],
            ),
            description="解析后的热力学数据包（ZPE、H、G、S、频率列表）。",
        ),
        dict(
            name="is_true_minimum",
            display_name="Is True Minimum",
            io_type=dict(
                category="logic_value",
                kind="boolean",
            ),
            description="无虚频则为 true。",
        ),
        dict(
            name="zero_point_energy",
            display_name="Zero-Point Energy",
            io_type=dict(
                category="physical_quantity",
                unit="Ha",
            ),
        ),
    ],
    onboard_inputs=[
        dict(name="temperature", display_name="温度", kind="float",
             default=298.15, unit="K"),
        dict(name="pressure", display_name="压力", kind="float",
             default=1.0, unit="atm"),
        dict(name="scale_factor", display_name="频率校正因子", kind="float",
             default=0.9613, min_value=0.5, max_value=1.5),
    ],
    onboard_outputs=[
        dict(name="n_imaginary", display_name="虚频数目", kind="integer"),
        dict(name="lowest_freq", display_name="最低频率",
             kind="float", unit="cm-1"),
    ],
    resources=dict(
        cpu_cores=4,
        memory_gb=8.0,
        estimated_walltime_hours=0.5,
    ),
    execution=dict(
        profile_templates=["freq_input.gjf.template"],
    ),
    semantic_identity=(
        "计算分子的谐振频率，判断构型是否为真正极小点，"
        "并产出热力学数据供下游提取自由能。"
    ),
    distinguishing_ports=["thermo_data", "is_true_minimum"],
)


THERMO_EXTRACTOR_SPEC = dict(
    metadata=dict(
        name="thermo-extractor",
        version="1.0.0",
        display_name="Thermochemistry Extractor",
        description=(
            "从 Gaussian 频率计算的热力学数据包中提取 "
            "Gibbs 自由能、焓、熵等关键物理量，生成结构化报告。"
        ),
        node_type="lightweight",
        category="postprocessing",
        author="MiQroForge Team",
    ),
    stream_inputs=[
        dict(
            name="thermo_data_in",
            display_name="Thermodynamic Data",
            io_type=dict(
                category="software_data_package",
                ecosystem="gaussian",
                data_type="thermo-data",
            ),
            description="来自 freq 节点的热力学数据包。",
        ),
        dict(
            name="is_minimum",
            display_name="Is True Minimum",
            io_type=dict(
                category="logic_value",
                kind="boolean",
            ),
            required=False,
            description="构型是否为极小点。如果为 false，报告中标注警告。",
        ),
    ],
    stream_outputs=[
        dict(
            name="gibbs_free_energy",
            display_name="Gibbs Free Energy",
            io_type=dict(
                category="physical_quantity",
                unit="Ha",
            ),
        ),
        dict(
            name="enthalpy",
            display_name="Enthalpy",
            io_type=dict(
                category="physical_quantity",
                unit="Ha",
            ),
        ),
        dict(
            name="thermo_report",
            display_name="Thermochemistry Report",
            io_type=dict(
                category="report_object",
                format="json",
                description="包含 G, H, S, ZPE 及单位转换后的值。",
            ),
        ),
    ],
    onboard_inputs=[
        dict(name="energy_unit", display_name="输出能量单位", kind="enum",
             allowed_values=["Ha", "eV", "kcal/mol", "kJ/mol"],
             default="Ha"),
    ],
    onboard_outputs=[
        dict(name="gibbs_display", display_name="Gibbs Free Energy",
             kind="float", unit="Ha",
             description="面板直接显示的 Gibbs 自由能。"),
    ],
    resources=dict(timeout_seconds=60),
    execution=dict(
        script_path="run.py",
        pip_dependencies=["numpy"],
    ),
    semantic_identity=(
        "从频率计算产出的热力学数据中提取 Gibbs 自由能、焓、熵，"
        "并生成 JSON 格式的结构化报告。"
    ),
    distinguishing_ports=["gibbs_free_energy", "thermo_report"],
)


# ═══════════════════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestNodeSpecCreation:
    """三个 NodeSpec 各自通过 Pydantic 校验。"""

    def test_geo_opt_valid(self):
        ns = NodeSpec.model_validate(GEO_OPT_SPEC)
        assert ns.metadata.name == "gaussian-geo-opt"
        assert ns.metadata.tags.software == "gaussian"
        assert len(ns.stream_outputs) == 3
        assert len(ns.onboard_inputs) == 5

    def test_freq_valid(self):
        ns = NodeSpec.model_validate(FREQ_SPEC)
        assert ns.metadata.name == "gaussian-freq"
        assert len(ns.stream_inputs) == 2
        assert len(ns.stream_outputs) == 3

    def test_thermo_extractor_valid(self):
        ns = NodeSpec.model_validate(THERMO_EXTRACTOR_SPEC)
        assert ns.metadata.name == "thermo-extractor"
        assert ns.metadata.node_type.value == "lightweight"
        assert len(ns.stream_outputs) == 3


class TestWorkflowConnections:
    """验证工作流中相邻节点的连接合法性。"""

    @pytest.fixture()
    def geo_opt(self) -> NodeSpec:
        return NodeSpec.model_validate(GEO_OPT_SPEC)

    @pytest.fixture()
    def freq(self) -> NodeSpec:
        return NodeSpec.model_validate(FREQ_SPEC)

    @pytest.fixture()
    def extractor(self) -> NodeSpec:
        return NodeSpec.model_validate(THERMO_EXTRACTOR_SPEC)

    # ── 辅助方法 ──

    @staticmethod
    def _get_out(ns: NodeSpec, name: str) -> StreamOutputPort:
        for p in ns.stream_outputs:
            if p.name == name:
                return p
        raise KeyError(f"Output port {name!r} not found")

    @staticmethod
    def _get_in(ns: NodeSpec, name: str) -> StreamInputPort:
        for p in ns.stream_inputs:
            if p.name == name:
                return p
        raise KeyError(f"Input port {name!r} not found")

    # ── geo-opt → freq ──

    def test_checkpoint_connection(self, geo_opt, freq):
        """geo-opt 的 checkpoint 输出 → freq 的 checkpoint 输入。"""
        src = self._get_out(geo_opt, "optimized_checkpoint")
        tgt = self._get_in(freq, "checkpoint_in")
        result = validate_connection(src, tgt)
        assert result.valid, result.message

    def test_converged_to_opt_converged(self, geo_opt, freq):
        """geo-opt 的 converged (boolean) → freq 的 opt_converged (boolean)。"""
        src = self._get_out(geo_opt, "converged")
        tgt = self._get_in(freq, "opt_converged")
        result = validate_connection(src, tgt)
        assert result.valid, result.message
        assert not result.warnings  # 同 kind，无警告

    # ── freq → thermo-extractor ──

    def test_thermo_data_connection(self, freq, extractor):
        """freq 的 thermo_data → extractor 的 thermo_data_in。"""
        src = self._get_out(freq, "thermo_data")
        tgt = self._get_in(extractor, "thermo_data_in")
        result = validate_connection(src, tgt)
        assert result.valid, result.message

    def test_is_minimum_connection(self, freq, extractor):
        """freq 的 is_true_minimum → extractor 的 is_minimum。"""
        src = self._get_out(freq, "is_true_minimum")
        tgt = self._get_in(extractor, "is_minimum")
        result = validate_connection(src, tgt)
        assert result.valid, result.message


class TestInvalidConnections:
    """非法连接被正确拒绝。"""

    @pytest.fixture()
    def geo_opt(self) -> NodeSpec:
        return NodeSpec.model_validate(GEO_OPT_SPEC)

    @pytest.fixture()
    def freq(self) -> NodeSpec:
        return NodeSpec.model_validate(FREQ_SPEC)

    @pytest.fixture()
    def extractor(self) -> NodeSpec:
        return NodeSpec.model_validate(THERMO_EXTRACTOR_SPEC)

    @staticmethod
    def _get_out(ns, name):
        return next(p for p in ns.stream_outputs if p.name == name)

    @staticmethod
    def _get_in(ns, name):
        return next(p for p in ns.stream_inputs if p.name == name)

    def test_energy_to_checkpoint_rejected(self, geo_opt, freq):
        """物理量 → 软件数据包 = 跨类别，无效。"""
        src = self._get_out(geo_opt, "total_energy")
        tgt = self._get_in(freq, "checkpoint_in")
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "类别不匹配" in result.message

    def test_converged_to_checkpoint_rejected(self, geo_opt, freq):
        """逻辑量 → 软件数据包 = 跨类别，无效。"""
        src = self._get_out(geo_opt, "converged")
        tgt = self._get_in(freq, "checkpoint_in")
        result = validate_connection(src, tgt)
        assert not result.valid

    def test_checkpoint_to_thermo_data_rejected(self, geo_opt, extractor):
        """同为 SDP 但 data_type 不同 (checkpoint ≠ thermo-data)，无效。"""
        src = self._get_out(geo_opt, "optimized_checkpoint")
        tgt = self._get_in(extractor, "thermo_data_in")
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "数据类型不匹配" in result.message

    def test_zpe_to_gibbs_unit_conversion(self, freq, extractor):
        """物理量 → 物理量，同单位 (Ha → Ha) 应该合法。"""
        src = self._get_out(freq, "zero_point_energy")
        tgt_port = StreamInputPort(
            name="energy_in",
            display_name="Energy Input",
            io_type=dict(
                category="physical_quantity",
                unit="eV",  # 不同单位，同量纲
            ),
        )
        result = validate_connection(src, tgt_port)
        assert result.valid
        assert any("自动转换" in w for w in result.warnings)


class TestYAMLRoundTrip:
    """三个节点的 YAML 序列化往返。"""

    @pytest.mark.parametrize("spec_dict,expected_name", [
        (GEO_OPT_SPEC, "gaussian-geo-opt"),
        (FREQ_SPEC, "gaussian-freq"),
        (THERMO_EXTRACTOR_SPEC, "thermo-extractor"),
    ])
    def test_yaml_roundtrip(self, tmp_path, spec_dict, expected_name):
        ns = NodeSpec.model_validate(spec_dict)
        yaml_path = tmp_path / f"{expected_name}.yaml"
        ns.to_yaml(yaml_path)
        ns2 = NodeSpec.from_yaml(yaml_path)
        assert ns2.metadata.name == expected_name
        assert len(ns2.stream_inputs) == len(ns.stream_inputs)
        assert len(ns2.stream_outputs) == len(ns.stream_outputs)
        assert ns2.semantic_identity == ns.semantic_identity


class TestRAGSummaries:
    """RAG 摘要包含足够信息供检索使用。"""

    def test_geo_opt_summary_mentions_key_info(self):
        ns = NodeSpec.model_validate(GEO_OPT_SPEC)
        summary = ns.generate_rag_summary()
        assert "Gaussian" in summary
        assert "Geometry Optimization" in summary
        assert "optimized_checkpoint" in summary
        assert "compute" in summary

    def test_extractor_summary_mentions_gibbs(self):
        ns = NodeSpec.model_validate(THERMO_EXTRACTOR_SPEC)
        summary = ns.generate_rag_summary()
        assert "gibbs_free_energy" in summary
        assert "lightweight" in summary
        assert "postprocessing" in summary


class TestSemanticIdentityAntiInflation:
    """semantic_identity 反膨胀机制验证。

    好的 semantic_identity 描述 *做什么*（语义），
    不应该包含具体参数值（那是 on-board 参数的事）。
    """

    def test_geo_opt_identity_no_specific_params(self):
        """geo-opt 的 identity 不应提及 B3LYP 或 6-31G*。"""
        ns = NodeSpec.model_validate(GEO_OPT_SPEC)
        identity = ns.semantic_identity.lower()
        assert "b3lyp" not in identity
        assert "6-31g" not in identity

    def test_freq_identity_no_specific_temperature(self):
        """freq 的 identity 不应提及 298.15K。"""
        ns = NodeSpec.model_validate(FREQ_SPEC)
        identity = ns.semantic_identity
        assert "298" not in identity

    def test_different_nodes_have_different_identities(self):
        """三个节点的 semantic_identity 各不相同。"""
        identities = set()
        for spec in [GEO_OPT_SPEC, FREQ_SPEC, THERMO_EXTRACTOR_SPEC]:
            ns = NodeSpec.model_validate(spec)
            identities.add(ns.semantic_identity)
        assert len(identities) == 3
