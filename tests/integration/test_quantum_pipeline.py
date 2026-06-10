"""Quantum pipeline integration test — H2 QSCI e2e with local backend.

Pipeline: chem-prep → ewf-decompose → qsci-prep → hardware-execute(local) → qsci-assemble

Test strategy:
  - test_quantum_pipeline_local: Runs the full QSCI pipeline locally using
    PySCF RHF, mock cluster Hamiltonian, OpenFermion JW mapping, synthetic
    measurement counts from FCI wavefunction amplitudes, and QSCI subspace
    diagonalisation. Asserts |E_qsci - E_fci| < 1e-3 Ha.
  - test_quantum_pipeline_argo_sv1: Submits the full pipeline through Argo
    with SV1 hardware backend. Guarded by MF_RUN_SV1=1 env var.
    Requires Argo cluster + AWS Braket credentials.

Acceptance criteria (from qsci-assemble nodespec):
  - energy_validated = True when |E_qsci - E_fci| < 1e-3
  - qsci_report produced with E_qsci, E_fci, delta_Ha fields
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest
import yaml

from workflows.pipeline.loader import load_workflow
from workflows.pipeline.validator import validate_workflow
from workflows.pipeline.compiler import compile_to_argo, generate_configmaps


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUANTUM_MF_YAML = PROJECT_ROOT / "workflows" / "examples" / "h2-quantum-pipeline-mf.yaml"
NAMESPACE = os.environ.get("ARGO_NAMESPACE", "miqroforge-v2")

# H2 molecule parameters (small molecule — 2 electrons, 2 spatial orbitals)
H2_ATOM = "H 0 0 0; H 0 0 0.7414"
H2_BASIS = "sto-3g"
H2_CHARGE = 0
H2_N_ELECTRONS = 2

# Tolerance for |E_qsci - E_fci| acceptance
ENERGY_TOLERANCE_HA = 1e-3


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: env guard for SV1 tests
# ═══════════════════════════════════════════════════════════════════════════════

def _sv1_enabled() -> bool:
    """Check if SV1 pipeline test should run."""
    return os.environ.get("MF_RUN_SV1", "").strip() in ("1", "true", "yes")


skip_no_sv1 = pytest.mark.skipif(
    not _sv1_enabled(),
    reason="MF_RUN_SV1 not set (cost guard: set MF_RUN_SV1=1 to run SV1 tests)"
)


def _argo_available() -> bool:
    """Check if argo CLI is available."""
    try:
        result = subprocess.run(
            ["argo", "version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _kubectl_available() -> bool:
    """Check if kubectl is available."""
    try:
        result = subprocess.run(
            ["kubectl", "version", "--client"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


skip_no_argo = pytest.mark.skipif(
    not _argo_available(), reason="argo CLI not available"
)
skip_no_kubectl = pytest.mark.skipif(
    not _kubectl_available(), reason="kubectl not available"
)


# ═══════════════════════════════════════════════════════════════════════════════
# Local pipeline implementation (no Docker, no Argo, no AWS credentials)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_local_qsci_pipeline(
    atom: str = H2_ATOM,
    basis: str = H2_BASIS,
    charge: int = H2_CHARGE,
    K: int = 10,
    rng_seed: int = 42,
) -> dict:
    """Run the full quantum pipeline locally using PySCF + OpenFermion + QSCI.

    Pipeline steps:
      1. PySCF RHF + OpenFermion integration → qubit Hamiltonian
      2. PySCF FCI → exact wavefunction + measurement probabilities
      3. Synthetic measurement counts (sampled from FCI probabilities)
      4. QSCI subspace diagonalisation → E_qsci
      5. Total energy assembly: E_total = e_mf + (E_qsci - e_core_baseline)
      6. FCI reference → E_fci → delta = |E_total - E_fci|

    Uses openfermionpyscf for correct Hamiltonian construction,
    matching the approach in the argo pipeline's qsci-prep node.

    Returns
    -------
    dict with keys: E_qsci, E_fci, delta_Ha, energy_validated,
                    total_energy, e_mf, e_core_baseline, subspace_dim,
                    n_qubits, n_spatial, n_electrons, K, fci_skipped,
                    top_configs
    """
    from pyscf import gto, scf, fci as pyscf_fci
    from openfermion import MolecularData, jordan_wigner
    from openfermionpyscf import run_pyscf
    from scipy.linalg import eigh
    from itertools import combinations

    ref_path = str(PROJECT_ROOT / "nodes" / "quantum" / "qsci-assemble" / "profile")
    import sys
    if ref_path not in sys.path:
        sys.path.insert(0, ref_path)
    from qsci_reference import (
        hf_config_int,
        counts_to_selected_configs,
        build_subspace_hamiltonian,
    )

    rng = np.random.default_rng(rng_seed)
    multiplicity = 1

    # ── Step 1: PySCF RHF + OpenFermion Hamiltonian ─────────────────────
    mol = gto.M(atom=atom, basis=basis, charge=charge, spin=0, verbose=0)
    mf = scf.RHF(mol)
    e_mf = mf.kernel()
    assert mf.converged, "RHF did not converge"

    n_spatial = mol.nao
    n_qubits = 2 * n_spatial
    n_electrons = mol.nelectron

    # Build qubit Hamiltonian via openfermionpyscf (same as argo pipeline)
    mol_data = MolecularData(atom, basis, multiplicity=multiplicity)
    mol_data = run_pyscf(mol_data, run_scf=True, run_fci=False)
    fermion_H = mol_data.get_molecular_hamiltonian()
    qubit_hamiltonian = jordan_wigner(fermion_H)
    assert mol_data.n_qubits == n_qubits

    # ── Step 2: PySCF FCI → exact wavefunction ─────────────────────────
    cisolver = pyscf_fci.FCI(mf)
    E_fci, fci_vec = cisolver.kernel()
    E_fci = float(E_fci)

    # ── Step 3: Generate synthetic measurement counts ───────────────────
    n_alpha = n_electrons // 2
    n_beta = n_alpha  # closed-shell, RHF

    alpha_orbs = list(range(n_spatial))
    beta_orbs = list(range(n_spatial))
    alpha_dets = list(combinations(alpha_orbs, n_alpha))
    beta_dets = list(combinations(beta_orbs, n_beta))

    config_probs: dict[int, float] = {}
    for ai, adet in enumerate(alpha_dets):
        for bi, bdet in enumerate(beta_dets):
            coeff = fci_vec[ai, bi]
            bits = []
            for orb in range(n_spatial):
                bits.append("1" if orb in adet else "0")
                bits.append("1" if orb in bdet else "0")
            config_int = int("".join(bits), 2)
            prob = abs(coeff) ** 2
            if prob > 1e-15:
                config_probs[config_int] = prob

    n_shots = 10000
    configs_list = list(config_probs.keys())
    probs_list = np.array([config_probs[c] for c in configs_list])
    probs_list /= probs_list.sum()
    sampled = rng.choice(configs_list, size=n_shots, p=probs_list)
    counts: dict[int, int] = {}
    for c in sampled:
        counts[c] = counts.get(c, 0) + 1

    # ── Step 4: QSCI subspace diagonalisation ──────────────────────────
    selected = counts_to_selected_configs(counts, K)
    hf_cfg = hf_config_int(n_spatial, n_alpha, n_beta)
    if hf_cfg not in selected:
        selected.insert(0, hf_cfg)

    H_sub = build_subspace_hamiltonian(selected, qubit_hamiltonian.terms, n_qubits)
    eigenvalues, _ = eigh(H_sub)
    E_qsci_cluster = float(eigenvalues[0].real)

    hf_index = selected.index(hf_cfg)
    e_core_baseline = float(H_sub[hf_index, hf_index].real)

    # ── Step 5: Assemble total energy ──────────────────────────────────
    total_energy = e_mf + (E_qsci_cluster - e_core_baseline)

    # ── Step 6: Compare with FCI ───────────────────────────────────────
    delta_Ha = abs(total_energy - E_fci)
    energy_validated = delta_Ha < ENERGY_TOLERANCE_HA

    return {
        "E_qsci": total_energy,
        "E_fci": E_fci,
        "delta_Ha": delta_Ha,
        "energy_validated": energy_validated,
        "total_energy": total_energy,
        "e_mf": e_mf,
        "e_core_baseline": e_core_baseline,
        "E_qsci_cluster": E_qsci_cluster,
        "subspace_dim": len(selected),
        "n_qubits": n_qubits,
        "n_spatial": n_spatial,
        "n_electrons": n_electrons,
        "K": K,
        "fci_skipped": False,
        "top_configs": selected,
        "n_shots": n_shots,
        "seed": rng_seed,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Local pipeline (always runs)
# ═══════════════════════════════════════════════════════════════════════════════


class TestQuantumPipelineLocal:
    """H2 QSCI pipeline e2e with local (synthetic) backend."""

    @pytest.fixture(scope="class")
    def pipeline_result(self) -> dict:
        """Run the local pipeline once, reuse for all assertions."""
        return _run_local_qsci_pipeline(K=10, rng_seed=42)

    def test_energy_validated(self, pipeline_result):
        """energy_validated must be True: |E_qsci - E_fci| < 1e-3 Ha."""
        assert pipeline_result["energy_validated"], (
            f"QSCI energy validation failed: "
            f"|{pipeline_result['E_qsci']:.10f} - {pipeline_result['E_fci']:.10f}| "
            f"= {pipeline_result['delta_Ha']:.3e} Ha"
        )

    def test_total_energy_produced(self, pipeline_result):
        """total_energy must be a finite float."""
        e = pipeline_result["total_energy"]
        assert isinstance(e, float)
        assert np.isfinite(e)

    def test_delta_below_tolerance(self, pipeline_result):
        """|E_qsci - E_fci| < 1e-3 Ha (hard acceptance criterion)."""
        assert pipeline_result["delta_Ha"] < ENERGY_TOLERANCE_HA, (
            f"Energy delta {pipeline_result['delta_Ha']:.3e} Ha "
            f"exceeds tolerance {ENERGY_TOLERANCE_HA} Ha"
        )

    def test_subspace_dimension(self, pipeline_result):
        """Subspace dimension must be positive."""
        assert pipeline_result["subspace_dim"] > 0

    def test_qubit_count(self, pipeline_result):
        """H2/sto-3g → 2 spatial orbitals → 4 qubits."""
        assert pipeline_result["n_spatial"] == 2
        assert pipeline_result["n_qubits"] == 4

    def test_fci_not_skipped(self, pipeline_result):
        """For H2 with 2 orbitals, FCI must not be skipped."""
        assert not pipeline_result["fci_skipped"]

    def test_report_structure(self, pipeline_result):
        """All required report fields present."""
        required = [
            "E_qsci", "E_fci", "delta_Ha", "energy_validated",
            "total_energy", "e_mf", "e_core_baseline",
            "subspace_dim", "n_qubits", "n_spatial", "n_electrons",
        ]
        for k in required:
            assert k in pipeline_result, f"Missing key: {k}"

    def test_e_mf_negative(self, pipeline_result):
        """Mean-field energy must be negative (bound molecule)."""
        assert pipeline_result["e_mf"] < 0, (
            f"e_mf={pipeline_result['e_mf']} should be negative"
        )

    def test_energy_conservation_assembly(self, pipeline_result):
        """E_total = e_mf + (E_qsci_cluster - e_core_baseline)."""
        pr = pipeline_result
        assembled = pr["e_mf"] + (pr["E_qsci_cluster"] - pr["e_core_baseline"])
        assert abs(pr["total_energy"] - assembled) < 1e-12

    def test_reproducibility(self):
        """Same seed → same result (deterministic for given counts)."""
        r1 = _run_local_qsci_pipeline(rng_seed=123)
        r2 = _run_local_qsci_pipeline(rng_seed=123)
        assert r1["total_energy"] == r2["total_energy"]
        assert r1["E_qsci"] == r2["E_qsci"]

    def test_hf_config_in_subspace(self, pipeline_result):
        """HF configuration must be present in selected configs."""
        import sys
        ref_path = str(PROJECT_ROOT / "nodes" / "quantum" / "qsci-assemble" / "profile")
        if ref_path not in sys.path:
            sys.path.insert(0, ref_path)
        from qsci_reference import hf_config_int
        n_spatial = pipeline_result["n_spatial"]
        n_elec = pipeline_result["n_electrons"]
        n_alpha = n_elec // 2
        hf = hf_config_int(n_spatial, n_alpha, n_alpha)
        assert hf in pipeline_result["top_configs"]


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Argo SV1 pipeline (guarded by MF_RUN_SV1)
# ═══════════════════════════════════════════════════════════════════════════════


class TestQuantumPipelineArgoSV1:
    """H2 QSCI pipeline via Argo with SV1 backend.

    Requires:
      - Argo cluster running
      - AWS Braket credentials staged in workspace PVC
      - MF_RUN_SV1=1 env var set (cost guard)
    """

    @skip_no_sv1
    @skip_no_kubectl
    @skip_no_argo
    def test_step1_validate_quantum_workflow(self):
        """Validate the quantum pipeline MF YAML."""
        assert QUANTUM_MF_YAML.exists(), (
            f"Quantum workflow YAML not found: {QUANTUM_MF_YAML}"
        )
        wf = load_workflow(QUANTUM_MF_YAML)
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid, (
            f"Validation failed: {[e.message for e in report.errors]}"
        )

    @skip_no_sv1
    @skip_no_kubectl
    @skip_no_argo
    def test_step2_compile_quantum_workflow(self):
        """Compile quantum pipeline → valid Argo YAML."""
        wf = load_workflow(QUANTUM_MF_YAML)
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid

        argo = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        # Verify structure
        dag_template = next(
            t for t in argo["spec"]["templates"] if t["name"] == "mf-dag"
        )
        tasks = dag_template["dag"]["tasks"]
        assert len(tasks) >= 3, f"Expected >= 3 DAG tasks, got {len(tasks)}"

        task_names = {t["name"] for t in tasks}
        assert "qsci-assemble" in task_names, "qsci-assemble missing from DAG"

    @skip_no_sv1
    @skip_no_kubectl
    @skip_no_argo
    def test_step3_argo_submit_and_succeed(self):
        """Submit quantum pipeline to Argo → Succeeded."""
        wf = load_workflow(QUANTUM_MF_YAML)
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid

        argo_dict = compile_to_argo(wf, report.resolved_nodes, project_root=PROJECT_ROOT)

        # Apply ConfigMaps
        configmaps = generate_configmaps(wf, report.resolved_nodes, project_root=PROJECT_ROOT)
        for cm in configmaps:
            _apply_resource(cm)

        # Submit workflow
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="mf-quantum-"
        ) as f:
            yaml.dump(argo_dict, f, default_flow_style=False, allow_unicode=True)
            tmp_path = f.name

        wf_name = None
        try:
            result = subprocess.run(
                ["argo", "submit", tmp_path, "--namespace", NAMESPACE, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"argo submit failed: {result.stderr}"

            submit_data = json.loads(result.stdout)
            wf_name = submit_data["metadata"]["name"]

            # Wait for completion (10 min timeout for SV1)
            completed, phase = _wait_for_workflow_status(wf_name, timeout=600)
            assert completed, f"Workflow {wf_name} did not complete in time"
            assert phase == "Succeeded", f"Expected Succeeded, got {phase}"

            # Extract outputs
            get_result = subprocess.run(
                ["argo", "get", wf_name, "--namespace", NAMESPACE, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert get_result.returncode == 0
            wf_status = json.loads(get_result.stdout)

            outputs = _extract_outputs(wf_status)

            # Verify qsci-assemble outputs
            assert "qsci-assemble" in outputs, (
                f"qsci-assemble output missing. Available: {list(outputs.keys())}"
            )
            qa = outputs["qsci-assemble"]

            assert "total_energy" in qa, "total_energy missing"
            total_e = float(qa["total_energy"])
            assert np.isfinite(total_e), f"total_energy={total_e} not finite"

            # energy_validated
            ev = qa.get("energy_validated", "false")
            assert ev.lower() in ("true", "false"), f"Bad energy_validated: {ev}"

            # qsci_report
            if "qsci_report" in qa:
                report_data = json.loads(qa["qsci_report"])
                assert "E_qsci" in report_data
                assert "delta_Ha" in report_data

        finally:
            os.unlink(tmp_path)
            if wf_name:
                subprocess.run(
                    ["argo", "delete", wf_name, "--namespace", NAMESPACE],
                    capture_output=True,
                    timeout=10,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Argo helpers (adapted from test_h2o_pipeline.py)
# ═══════════════════════════════════════════════════════════════════════════════


def _apply_resource(resource: dict) -> None:
    """Create K8s resource via kubectl apply."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(resource, f)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", tmp_path, "--namespace", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"kubectl apply failed: {result.stderr}"
    finally:
        os.unlink(tmp_path)


def _wait_for_workflow_status(name: str, timeout: int = 300) -> tuple[bool, str]:
    """Wait for Argo workflow to complete. Returns (completed, phase)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["argo", "get", name, "--namespace", NAMESPACE, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            phase = data.get("status", {}).get("phase", "")
            if phase in ("Succeeded", "Failed", "Error"):
                return True, phase
        time.sleep(10)
    return False, "Unknown"


def _extract_outputs(wf_status: dict) -> dict[str, dict[str, str]]:
    """Extract per-task output parameters from Argo workflow status."""
    outputs: dict[str, dict[str, str]] = {}
    for node_info in wf_status.get("status", {}).get("nodes", {}).values():
        display = node_info.get("displayName", "")
        params = node_info.get("outputs", {}).get("parameters", [])
        if params:
            outputs[display] = {
                p["name"]: p.get("value", "")
                for p in params
            }
    return outputs
