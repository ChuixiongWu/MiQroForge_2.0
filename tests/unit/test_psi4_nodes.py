"""Psi4 节点 Schema 校验测试。"""

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

PSI4_DIR = Path("nodes/chemistry/psi4")


@pytest.fixture(scope="module")
def psi4_nodes() -> dict[str, NodeSpec]:
    return {
        "single-point": NodeSpec.from_yaml(PSI4_DIR / "psi4-single-point" / "nodespec.yaml"),
        "geo-opt": NodeSpec.from_yaml(PSI4_DIR / "psi4-geo-opt" / "nodespec.yaml"),
        "freq": NodeSpec.from_yaml(PSI4_DIR / "psi4-freq" / "nodespec.yaml"),
    }


class TestPsi4NodeLoading:

    def test_all_nodes_load(self, psi4_nodes):
        assert len(psi4_nodes) == 3

    def test_names(self, psi4_nodes):
        assert psi4_nodes["single-point"].metadata.name == "psi4-single-point"
        assert psi4_nodes["geo-opt"].metadata.name == "psi4-geo-opt"
        assert psi4_nodes["freq"].metadata.name == "psi4-freq"

    def test_base_image_ref(self, psi4_nodes):
        for spec in psi4_nodes.values():
            assert spec.metadata.base_image_ref == "psi4-1.10"

    def test_all_compute_type(self, psi4_nodes):
        for spec in psi4_nodes.values():
            assert spec.metadata.node_type == NodeType.COMPUTE


class TestPsi4SinglePoint:

    def test_stream_input(self, psi4_nodes):
        spec = psi4_nodes["single-point"]
        assert len(spec.stream_inputs) == 1
        assert spec.stream_inputs[0].name == "xyz_geometry"
        xyz = spec.stream_inputs[0]
        assert isinstance(xyz.io_type, PhysicalQuantityType)
        assert xyz.io_type.unit == "Ang"

    def test_stream_outputs(self, psi4_nodes):
        spec = psi4_nodes["single-point"]
        names = {p.name for p in spec.stream_outputs}
        assert "total_energy" in names
        assert "wavefunction_data" in names

    def test_total_energy_is_pq_ha(self, psi4_nodes):
        spec = psi4_nodes["single-point"]
        energy = next(p for p in spec.stream_outputs if p.name == "total_energy")
        assert isinstance(energy.io_type, PhysicalQuantityType)
        assert energy.io_type.unit == "Ha"

    def test_scf_converged_quality_gate(self, psi4_nodes):
        spec = psi4_nodes["single-point"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "scf_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_onboard_params(self, psi4_nodes):
        spec = psi4_nodes["single-point"]
        param_names = {p.name for p in spec.onboard_inputs}
        assert "method" in param_names
        assert "basis_set" in param_names
        assert "charge" in param_names
        assert "multiplicity" in param_names
        assert "reference" in param_names
        assert "scf_type" in param_names

    def test_resources(self, psi4_nodes):
        res = psi4_nodes["single-point"].resources
        assert isinstance(res, ComputeResources)
        assert res.cpu_cores >= 1


class TestPsi4GeoOpt:

    def test_opt_converged_quality_gate(self, psi4_nodes):
        spec = psi4_nodes["geo-opt"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "opt_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_optimized_xyz_is_pq(self, psi4_nodes):
        spec = psi4_nodes["geo-opt"]
        xyz = next(p for p in spec.stream_outputs if p.name == "optimized_xyz")
        assert isinstance(xyz.io_type, PhysicalQuantityType)
        assert xyz.io_type.unit == "Ang"
        assert xyz.io_type.shape == "array"

    def test_has_max_iter(self, psi4_nodes):
        spec = psi4_nodes["geo-opt"]
        param = next((p for p in spec.onboard_inputs if p.name == "max_iter"), None)
        assert param is not None
        assert param.kind == OnBoardInputKind.INTEGER


class TestPsi4Freq:

    def test_is_true_minimum_quality_gate(self, psi4_nodes):
        spec = psi4_nodes["freq"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "is_true_minimum"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_thermo_outputs(self, psi4_nodes):
        spec = psi4_nodes["freq"]
        names = {p.name for p in spec.stream_outputs}
        assert "zpe" in names
        assert "gibbs_free_energy" in names
        assert "enthalpy" in names
        assert "thermo_report" in names

    def test_zpe_is_pq_ha(self, psi4_nodes):
        spec = psi4_nodes["freq"]
        zpe = next(p for p in spec.stream_outputs if p.name == "zpe")
        assert isinstance(zpe.io_type, PhysicalQuantityType)
        assert zpe.io_type.unit == "Ha"

    def test_thermo_report_is_report_object(self, psi4_nodes):
        spec = psi4_nodes["freq"]
        report = next(p for p in spec.stream_outputs if p.name == "thermo_report")
        assert isinstance(report.io_type, ReportObjectType)
