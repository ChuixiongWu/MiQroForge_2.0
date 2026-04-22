"""Gaussian 节点 Schema 校验测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from nodes.schemas import NodeSpec, NodeType
from nodes.schemas.io import (
    GateDefault,
    PhysicalQuantityType,
    ReportObjectType,
    SoftwareDataPackageType,
)
from nodes.schemas.resources import ComputeResources

GAUSSIAN_DIR = Path("nodes/chemistry/gaussian")


@pytest.fixture(scope="module")
def gaussian_nodes() -> dict[str, NodeSpec]:
    return {
        "single-point": NodeSpec.from_yaml(GAUSSIAN_DIR / "gaussian-single-point" / "nodespec.yaml"),
        "geo-opt": NodeSpec.from_yaml(GAUSSIAN_DIR / "gaussian-geo-opt" / "nodespec.yaml"),
        "freq": NodeSpec.from_yaml(GAUSSIAN_DIR / "gaussian-freq" / "nodespec.yaml"),
    }


class TestGaussianNodeLoading:

    def test_all_nodes_load(self, gaussian_nodes):
        assert len(gaussian_nodes) == 3

    def test_names(self, gaussian_nodes):
        assert gaussian_nodes["single-point"].metadata.name == "gaussian-single-point"
        assert gaussian_nodes["geo-opt"].metadata.name == "gaussian-geo-opt"
        assert gaussian_nodes["freq"].metadata.name == "gaussian-freq"

    def test_base_image_ref(self, gaussian_nodes):
        for spec in gaussian_nodes.values():
            assert spec.metadata.base_image_ref == "g16"

    def test_all_compute_type(self, gaussian_nodes):
        for spec in gaussian_nodes.values():
            assert spec.metadata.node_type == NodeType.COMPUTE

    def test_parametrize_present(self, gaussian_nodes):
        """Gaussian 用 %nprocshared 而非 MPI，但应声明 cpu_cores 参数化。"""
        for spec in gaussian_nodes.values():
            assert isinstance(spec.resources, ComputeResources)
            assert "cpu_cores" in spec.resources.parametrize


class TestGaussianSinglePoint:

    def test_fchk_is_sdp_gaussian(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        fchk = next(p for p in spec.stream_outputs if p.name == "fchk_file")
        assert isinstance(fchk.io_type, SoftwareDataPackageType)
        assert fchk.io_type.ecosystem == "gaussian"
        assert fchk.io_type.data_type == "formatted-checkpoint"

    def test_total_energy_is_pq_ha(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        energy = next(p for p in spec.stream_outputs if p.name == "total_energy")
        assert isinstance(energy.io_type, PhysicalQuantityType)
        assert energy.io_type.unit == "Ha"

    def test_scf_converged_quality_gate(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "scf_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_method_param(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        method = next((p for p in spec.onboard_inputs if p.name == "method"), None)
        assert method is not None
        assert method.default == "B3LYP"

    def test_basis_set_param(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        basis = next((p for p in spec.onboard_inputs if p.name == "basis_set"), None)
        assert basis is not None
        assert basis.default == "6-31G*"

    def test_population_param(self, gaussian_nodes):
        spec = gaussian_nodes["single-point"]
        pop = next((p for p in spec.onboard_inputs if p.name == "population"), None)
        assert pop is not None
        assert pop.default == "Full"


class TestGaussianGeoOpt:

    def test_opt_converged_quality_gate(self, gaussian_nodes):
        spec = gaussian_nodes["geo-opt"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "opt_converged"
        assert gates[0].gate_default == GateDefault.MUST_PASS

    def test_outputs(self, gaussian_nodes):
        spec = gaussian_nodes["geo-opt"]
        names = {p.name for p in spec.stream_outputs}
        assert "optimized_xyz" in names
        assert "fchk_file" in names
        assert "total_energy" in names


class TestGaussianFreq:

    def test_is_true_minimum_quality_gate(self, gaussian_nodes):
        spec = gaussian_nodes["freq"]
        gates = spec.quality_gates
        assert len(gates) == 1
        assert gates[0].name == "is_true_minimum"

    def test_thermo_outputs(self, gaussian_nodes):
        spec = gaussian_nodes["freq"]
        names = {p.name for p in spec.stream_outputs}
        assert "zpe" in names
        assert "gibbs_free_energy" in names
        assert "enthalpy" in names
        assert "thermo_report" in names

    def test_thermo_report_is_report_object(self, gaussian_nodes):
        spec = gaussian_nodes["freq"]
        report = next(p for p in spec.stream_outputs if p.name == "thermo_report")
        assert isinstance(report.io_type, ReportObjectType)
