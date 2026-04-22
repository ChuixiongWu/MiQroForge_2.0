"""CP2K 节点 Schema 校验测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from nodes.schemas import NodeSpec, NodeType
from nodes.schemas.io import (
    GateDefault,
    OnBoardInputKind,
    PhysicalQuantityType,
    ReportObjectType,
)
from nodes.schemas.resources import ComputeResources

CP2K_DIR = Path("nodes/chemistry/cp2k")


@pytest.fixture(scope="module")
def cp2k_nodes() -> dict[str, NodeSpec]:
    return {
        "single-point": NodeSpec.from_yaml(CP2K_DIR / "cp2k-single-point" / "nodespec.yaml"),
        "geo-opt": NodeSpec.from_yaml(CP2K_DIR / "cp2k-geo-opt" / "nodespec.yaml"),
        "cell-opt": NodeSpec.from_yaml(CP2K_DIR / "cp2k-cell-opt" / "nodespec.yaml"),
    }


class TestCP2KNodeLoading:

    def test_all_nodes_load(self, cp2k_nodes):
        assert len(cp2k_nodes) == 3

    def test_names(self, cp2k_nodes):
        assert cp2k_nodes["single-point"].metadata.name == "cp2k-single-point"
        assert cp2k_nodes["geo-opt"].metadata.name == "cp2k-geo-opt"
        assert cp2k_nodes["cell-opt"].metadata.name == "cp2k-cell-opt"

    def test_base_image_ref(self, cp2k_nodes):
        for spec in cp2k_nodes.values():
            assert spec.metadata.base_image_ref == "cp2k-2025.2"

    def test_all_compute_type(self, cp2k_nodes):
        for spec in cp2k_nodes.values():
            assert spec.metadata.node_type == NodeType.COMPUTE


class TestCP2KSinglePoint:

    def test_stream_input(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        assert len(spec.stream_inputs) == 1
        assert spec.stream_inputs[0].name == "xyz_geometry"

    def test_stream_outputs(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        names = {p.name for p in spec.stream_outputs}
        assert "total_energy" in names
        assert "cell_parameters" in names

    def test_scf_converged_quality_gate(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "scf_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_periodic_specific_params(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        param_names = {p.name for p in spec.onboard_inputs}
        assert "cutoff" in param_names
        assert "rel_cutoff" in param_names
        assert "cell_abc" in param_names
        assert "smearing" in param_names
        assert "electronic_temperature" in param_names

    def test_cutoff_is_integer(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        cutoff = next(p for p in spec.onboard_inputs if p.name == "cutoff")
        assert cutoff.kind == OnBoardInputKind.INTEGER
        assert cutoff.default == 400

    def test_xc_functional_is_enum(self, cp2k_nodes):
        spec = cp2k_nodes["single-point"]
        xc = next(p for p in spec.onboard_inputs if p.name == "xc_functional")
        assert xc.kind == OnBoardInputKind.ENUM
        assert "PBE" in xc.allowed_values
        assert "PBE0" in xc.allowed_values

    def test_uses_mpi(self, cp2k_nodes):
        """MPI 环境变量在基础镜像中设置，不在 nodespec 中重复声明。"""
        spec = cp2k_nodes["single-point"]
        # execution.environment 为空（已移至镜像层）
        assert spec.execution.environment == {}

    def test_memory_higher_than_orca(self, cp2k_nodes):
        """CP2K 周期性 DFT 需要比 ORCA 分子 DFT 更多的内存。"""
        res = cp2k_nodes["single-point"].resources
        assert isinstance(res, ComputeResources)
        assert res.mem_gb >= 16.0


class TestCP2KGeoOpt:

    def test_opt_converged_quality_gate(self, cp2k_nodes):
        spec = cp2k_nodes["geo-opt"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "opt_converged"

    def test_optimized_xyz_output(self, cp2k_nodes):
        spec = cp2k_nodes["geo-opt"]
        names = {p.name for p in spec.stream_outputs}
        assert "optimized_xyz" in names
        assert "total_energy" in names
        assert "cell_parameters" in names

    def test_opt_params(self, cp2k_nodes):
        spec = cp2k_nodes["geo-opt"]
        param_names = {p.name for p in spec.onboard_inputs}
        assert "opt_algorithm" in param_names
        assert "max_opt_iter" in param_names
        assert "opt_max_force" in param_names

    def test_opt_algorithm_is_enum(self, cp2k_nodes):
        spec = cp2k_nodes["geo-opt"]
        algo = next(p for p in spec.onboard_inputs if p.name == "opt_algorithm")
        assert algo.kind == OnBoardInputKind.ENUM
        assert "BFGS" in algo.allowed_values
        assert "CG" in algo.allowed_values


class TestCP2KCellOpt:
    """cp2k-cell-opt: 最具特色的节点，同时优化原子位置和晶胞。"""

    def test_semantic_type_is_cell_optimization(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        assert spec.metadata.semantic_type == "cell-optimization"

    def test_opt_converged_quality_gate(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "opt_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_four_stream_outputs(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        names = {p.name for p in spec.stream_outputs}
        assert names == {"optimized_xyz", "total_energy", "optimized_cell", "cell_volume"}

    def test_optimized_cell_is_pq(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        cell = next(p for p in spec.stream_outputs if p.name == "optimized_cell")
        assert isinstance(cell.io_type, PhysicalQuantityType)
        assert cell.io_type.unit == "Ang"

    def test_cell_volume_is_report_object(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        vol = next(p for p in spec.stream_outputs if p.name == "cell_volume")
        assert isinstance(vol.io_type, ReportObjectType)

    def test_cell_opt_type_param(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        cot = next(p for p in spec.onboard_inputs if p.name == "cell_opt_type")
        assert cot.kind == OnBoardInputKind.ENUM
        assert "DIRECT_CELL_OPT" in cot.allowed_values
        assert "GEO_OPT" in cot.allowed_values

    def test_external_pressure_param(self, cp2k_nodes):
        spec = cp2k_nodes["cell-opt"]
        ep = next(p for p in spec.onboard_inputs if p.name == "external_pressure")
        assert ep.kind == OnBoardInputKind.FLOAT
        assert ep.default == 0.0
        assert ep.unit == "GPa"

    def test_most_onboard_inputs(self, cp2k_nodes):
        """cell-opt 应该是所有节点中 onboard inputs 最多的。"""
        cell_opt = cp2k_nodes["cell-opt"]
        sp = cp2k_nodes["single-point"]
        assert len(cell_opt.onboard_inputs) > len(sp.onboard_inputs)
