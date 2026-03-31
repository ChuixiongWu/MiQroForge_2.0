"""ORCA 节点 Schema 校验测试。

验证：
- 3 个 ORCA nodespec.yaml 均可正确加载（thermo-extractor 已移除）
- 端口类型、资源、执行配置符合规范
- 工作流连接（geo-opt → freq）类型兼容
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nodes.schemas import (
    NodeSpec,
    NodeType,
    validate_connection,
)
from nodes.schemas.io import (
    GateDefault,
    LogicValueType,
    OnBoardInputKind,
    PhysicalQuantityType,
    ReportObjectType,
    SoftwareDataPackageType,
)
from nodes.schemas.node import ComputeExecutionConfig, LightweightExecutionConfig
from nodes.schemas.resources import ComputeResources, LightweightResources

# 节点目录相对于项目根
ORCA_DIR = Path("nodes/chemistry/orca")


@pytest.fixture(scope="module")
def orca_nodes() -> dict[str, NodeSpec]:
    """加载所有 ORCA 节点规格（3 个，thermo-extractor 已移除）。"""
    return {
        "single-point": NodeSpec.from_yaml(ORCA_DIR / "orca-single-point" / "nodespec.yaml"),
        "geo-opt": NodeSpec.from_yaml(ORCA_DIR / "orca-geo-opt" / "nodespec.yaml"),
        "freq": NodeSpec.from_yaml(ORCA_DIR / "orca-freq" / "nodespec.yaml"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 加载测试
# ═══════════════════════════════════════════════════════════════════════════

class TestOrcaNodeLoading:

    def test_all_nodes_load(self, orca_nodes):
        assert len(orca_nodes) == 3

    def test_names(self, orca_nodes):
        assert orca_nodes["single-point"].metadata.name == "orca-single-point"
        assert orca_nodes["geo-opt"].metadata.name == "orca-geo-opt"
        assert orca_nodes["freq"].metadata.name == "orca-freq"

    def test_versions(self, orca_nodes):
        for spec in orca_nodes.values():
            assert spec.metadata.version == "1.0.0"

    def test_compute_nodes_have_base_image_ref(self, orca_nodes):
        for name in ["single-point", "geo-opt", "freq"]:
            assert orca_nodes[name].metadata.base_image_ref == "orca-6.1"

    def test_compute_nodes_are_compute_type(self, orca_nodes):
        for name in ["single-point", "geo-opt", "freq"]:
            assert orca_nodes[name].metadata.node_type == NodeType.COMPUTE


# ═══════════════════════════════════════════════════════════════════════════
# orca-single-point
# ═══════════════════════════════════════════════════════════════════════════

class TestOrcaSinglePoint:

    def test_has_one_stream_input(self, orca_nodes):
        """xyz_geometry 已从 onboard 迁移为 stream input。"""
        spec = orca_nodes["single-point"]
        assert len(spec.stream_inputs) == 1
        assert spec.stream_inputs[0].name == "xyz_geometry"

    def test_stream_outputs(self, orca_nodes):
        spec = orca_nodes["single-point"]
        names = [p.name for p in spec.stream_outputs]
        assert "gbw_file" in names
        assert "total_energy" in names
        assert "mulliken_report" in names
        # scf_converged has been migrated to onboard quality gate
        assert "converged" not in names
        assert "scf_converged" not in names

    def test_scf_converged_is_quality_gate(self, orca_nodes):
        spec = orca_nodes["single-point"]
        gates = spec.quality_gates
        assert len(gates) == 1
        gate = gates[0]
        assert gate.name == "scf_converged"
        assert gate.kind == OnBoardInputKind.BOOLEAN
        assert gate.gate_default == GateDefault.MUST_PASS

    def test_gbw_file_is_sdp_orca(self, orca_nodes):
        spec = orca_nodes["single-point"]
        gbw = next(p for p in spec.stream_outputs if p.name == "gbw_file")
        assert isinstance(gbw.io_type, SoftwareDataPackageType)
        assert gbw.io_type.ecosystem == "orca"
        assert gbw.io_type.data_type == "gbw-file"

    def test_total_energy_is_physical_quantity_ha(self, orca_nodes):
        spec = orca_nodes["single-point"]
        energy = next(p for p in spec.stream_outputs if p.name == "total_energy")
        assert isinstance(energy.io_type, PhysicalQuantityType)
        assert energy.io_type.unit == "Ha"

    def test_compute_resources(self, orca_nodes):
        res = orca_nodes["single-point"].resources
        assert isinstance(res, ComputeResources)
        assert res.cpu_cores == 4
        assert res.memory_gb == 8.0

    def test_onboard_params_include_method_and_basis(self, orca_nodes):
        spec = orca_nodes["single-point"]
        param_names = [p.name for p in spec.onboard_inputs]
        assert "method" in param_names
        assert "basis_set" in param_names
        assert "charge" in param_names
        assert "multiplicity" in param_names


# ═══════════════════════════════════════════════════════════════════════════
# orca-geo-opt
# ═══════════════════════════════════════════════════════════════════════════

class TestOrcaGeoOpt:

    def test_has_one_stream_input(self, orca_nodes):
        """xyz_geometry 已从 onboard 迁移为 stream input。"""
        spec = orca_nodes["geo-opt"]
        assert len(spec.stream_inputs) == 1
        assert spec.stream_inputs[0].name == "xyz_geometry"

    def test_stream_outputs_contain_gbw_and_xyz(self, orca_nodes):
        spec = orca_nodes["geo-opt"]
        names = [p.name for p in spec.stream_outputs]
        assert "gbw_file" in names
        assert "optimized_xyz" in names
        assert "total_energy" in names
        # opt_converged has been migrated to onboard quality gate
        assert "opt_converged" not in names

    def test_opt_converged_is_quality_gate(self, orca_nodes):
        spec = orca_nodes["geo-opt"]
        gates = spec.quality_gates
        assert len(gates) == 1
        gate = gates[0]
        assert gate.name == "opt_converged"
        assert gate.kind == OnBoardInputKind.BOOLEAN
        assert gate.gate_default == GateDefault.MUST_PASS

    def test_has_convergence_param(self, orca_nodes):
        spec = orca_nodes["geo-opt"]
        param = next((p for p in spec.onboard_inputs if p.name == "convergence"), None)
        assert param is not None
        assert param.default == "NormalOpt"
        assert "TightOpt" in param.allowed_values

    def test_optimized_xyz_is_physical_quantity(self, orca_nodes):
        """optimized_xyz 已从 SDP 迁移至 PQ (mol_coord, Ang, array)。"""
        spec = orca_nodes["geo-opt"]
        xyz = next(p for p in spec.stream_outputs if p.name == "optimized_xyz")
        assert isinstance(xyz.io_type, PhysicalQuantityType)
        assert xyz.io_type.unit == "Ang"
        assert xyz.io_type.shape == "array"


# ═══════════════════════════════════════════════════════════════════════════
# orca-freq
# ═══════════════════════════════════════════════════════════════════════════

class TestOrcaFreq:

    def test_has_one_stream_input(self, orca_nodes):
        spec = orca_nodes["freq"]
        assert len(spec.stream_inputs) == 1

    def test_xyz_geometry_input_is_required(self, orca_nodes):
        """xyz_geometry 输入端口（统一名称，已从 optimized_xyz 重命名）是 PQ(mol_coord, Ang, array)。"""
        spec = orca_nodes["freq"]
        xyz_in = next(p for p in spec.stream_inputs if p.name == "xyz_geometry")
        assert xyz_in.required is True
        assert isinstance(xyz_in.io_type, PhysicalQuantityType)
        assert xyz_in.io_type.unit == "Ang"
        assert xyz_in.io_type.shape == "array"

    def test_gbw_file_not_in_stream_inputs(self, orca_nodes):
        spec = orca_nodes["freq"]
        names = [p.name for p in spec.stream_inputs]
        assert "gbw_file" not in names

    def test_opt_converged_not_in_stream_inputs(self, orca_nodes):
        spec = orca_nodes["freq"]
        names = [p.name for p in spec.stream_inputs]
        assert "opt_converged" not in names

    def test_charge_and_multiplicity_params(self, orca_nodes):
        spec = orca_nodes["freq"]
        param_names = [p.name for p in spec.onboard_inputs]
        assert "charge" in param_names
        assert "multiplicity" in param_names
        charge = next(p for p in spec.onboard_inputs if p.name == "charge")
        multiplicity = next(p for p in spec.onboard_inputs if p.name == "multiplicity")
        assert charge.default == 0
        assert multiplicity.default == 1
        assert multiplicity.min_value == 1

    def test_is_true_minimum_is_quality_gate(self, orca_nodes):
        spec = orca_nodes["freq"]
        gates = spec.quality_gates
        assert len(gates) == 1
        gate = gates[0]
        assert gate.name == "is_true_minimum"
        assert gate.kind == OnBoardInputKind.BOOLEAN
        assert gate.gate_default == GateDefault.MUST_PASS

    def test_thermo_package_output(self, orca_nodes):
        spec = orca_nodes["freq"]
        pkg = next(p for p in spec.stream_outputs if p.name == "thermo_package")
        assert isinstance(pkg.io_type, SoftwareDataPackageType)
        assert pkg.io_type.ecosystem == "orca"
        assert pkg.io_type.data_type == "thermo-data"

    def test_zpe_output_is_physical_ha(self, orca_nodes):
        spec = orca_nodes["freq"]
        zpe = next(p for p in spec.stream_outputs if p.name == "zpe")
        assert isinstance(zpe.io_type, PhysicalQuantityType)
        assert zpe.io_type.unit == "Ha"

    def test_temperature_param_default(self, orca_nodes):
        spec = orca_nodes["freq"]
        temp = next(p for p in spec.onboard_inputs if p.name == "temperature")
        assert temp.default == pytest.approx(298.15)
        assert temp.unit == "K"

    def test_gibbs_free_energy_output(self, orca_nodes):
        """新增：gibbs_free_energy stream output (PQ, Ha)。"""
        spec = orca_nodes["freq"]
        gibbs = next(p for p in spec.stream_outputs if p.name == "gibbs_free_energy")
        assert isinstance(gibbs.io_type, PhysicalQuantityType)
        assert gibbs.io_type.unit == "Ha"

    def test_enthalpy_output(self, orca_nodes):
        """新增：enthalpy stream output (PQ, Ha)。"""
        spec = orca_nodes["freq"]
        enth = next(p for p in spec.stream_outputs if p.name == "enthalpy")
        assert isinstance(enth.io_type, PhysicalQuantityType)
        assert enth.io_type.unit == "Ha"

    def test_thermo_report_output(self, orca_nodes):
        """新增：thermo_report stream output (report_object, json)。"""
        spec = orca_nodes["freq"]
        report = next(p for p in spec.stream_outputs if p.name == "thermo_report")
        assert isinstance(report.io_type, ReportObjectType)
        assert report.io_type.format.value == "json"

    def test_freq_has_five_stream_outputs(self, orca_nodes):
        """freq 节点共有 5 个 stream outputs: thermo_package, zpe, gibbs_free_energy, enthalpy, thermo_report。"""
        spec = orca_nodes["freq"]
        names = {p.name for p in spec.stream_outputs}
        assert names == {"thermo_package", "zpe", "gibbs_free_energy", "enthalpy", "thermo_report"}


# ═══════════════════════════════════════════════════════════════════════════
# 连接兼容性测试：geo-opt → freq
# ═══════════════════════════════════════════════════════════════════════════

class TestOrcaWorkflowConnections:
    """验证 ORCA H2O 热力学工作流的所有连接类型兼容。"""

    def _get_port(self, spec: NodeSpec, name: str, direction: str):
        if direction == "out":
            for p in spec.stream_outputs:
                if p.name == name:
                    return p
        else:
            for p in spec.stream_inputs:
                if p.name == name:
                    return p
        return None

    def test_geo_opt_xyz_to_freq_xyz(self, orca_nodes):
        """geo-opt.optimized_xyz → freq.xyz_geometry : PQ(mol_coord, Ang, array) ↔ PQ(mol_coord, Ang, array)"""
        src = self._get_port(orca_nodes["geo-opt"], "optimized_xyz", "out")
        tgt = self._get_port(orca_nodes["freq"], "xyz_geometry", "in")
        result = validate_connection(src, tgt)
        assert result.valid, f"Connection should be valid: {result.message}"

    def test_cross_dimension_pq_connection_invalid(self, orca_nodes):
        """能量 PQ (Ha, scalar) → mol_coord PQ (Ang, array) 应无效（量纲和形状均不匹配）。"""
        from nodes.schemas import StreamOutputPort
        from nodes.schemas.io import PhysicalQuantityType, StreamIOCategory

        src = StreamOutputPort(
            name="energy_out",
            display_name="Some Energy",
            io_type=PhysicalQuantityType(
                category=StreamIOCategory.PHYSICAL_QUANTITY,
                unit="Ha",
                shape="scalar",
            ),
        )
        tgt = self._get_port(orca_nodes["freq"], "xyz_geometry", "in")
        result = validate_connection(src, tgt)
        assert not result.valid, "Cross-dimension + cross-shape PQ connection should be invalid"

    def test_cross_shape_pq_connection_invalid(self, orca_nodes):
        """同量纲但形状不同的 PQ 连接应无效（scalar Ang → array Ang）。"""
        from nodes.schemas import StreamOutputPort
        from nodes.schemas.io import PhysicalQuantityType, StreamIOCategory

        src = StreamOutputPort(
            name="scalar_coord",
            display_name="Scalar Coord",
            io_type=PhysicalQuantityType(
                category=StreamIOCategory.PHYSICAL_QUANTITY,
                unit="Ang",
                shape="scalar",
            ),
        )
        tgt = self._get_port(orca_nodes["freq"], "xyz_geometry", "in")
        result = validate_connection(src, tgt)
        assert not result.valid, "Cross-shape PQ connection (scalar → array) should be invalid"


# ═══════════════════════════════════════════════════════════════════════════
# resource_bindings 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestResourceBindings:
    """验证 3 个 compute 节点的 resource_bindings 配置正确。"""

    def test_compute_nodes_have_resource_bindings(self, orca_nodes):
        """3 个 compute 节点都应声明 resource_bindings。"""
        for name in ["single-point", "geo-opt", "freq"]:
            spec = orca_nodes[name]
            assert spec.resources.resource_bindings is not None, (
                f"节点 {name} 缺少 resource_bindings"
            )

    def test_resource_bindings_is_list(self, orca_nodes):
        """resource_bindings 必须是资源字段名的列表。"""
        for name in ["single-point", "geo-opt", "freq"]:
            bindings = orca_nodes[name].resources.resource_bindings
            assert isinstance(bindings, list), f"{name}: resource_bindings 不是 list"
            assert "cpu_cores" in bindings, f"{name}: cpu_cores 未绑定"
            assert "parallel_tasks" in bindings, f"{name}: parallel_tasks 未绑定"

    def test_bindings_inject_n_cores(self, orca_nodes):
        """cpu_cores 和 parallel_tasks 均绑定到同一个 n_cores onboard input。"""
        for name in ["single-point", "geo-opt", "freq"]:
            spec = orca_nodes[name]
            onboard_names = {p.name for p in spec.onboard_inputs}
            assert "n_cores" in onboard_names, (
                f"节点 {name}: 自动注入的 n_cores 在 onboard_inputs 中不存在"
            )

    def test_auto_injected_n_cores_properties(self, orca_nodes):
        """验证 n_cores 被自动注入且属性正确（非手写）。"""
        for name in ["single-point", "geo-opt", "freq"]:
            spec = orca_nodes[name]
            n_cores = next(p for p in spec.onboard_inputs if p.name == "n_cores")
            assert n_cores.kind.value == "integer"
            # default 应等于 nodespec 中 resources.cpu_cores 的静态值
            assert n_cores.default == spec.resources.cpu_cores
            assert n_cores.display_name is not None
