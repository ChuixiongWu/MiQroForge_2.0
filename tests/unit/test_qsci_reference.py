"""QSCI reference tests: bit ordering, subspace construction, H₂ energy, performance.

Covers:
- ``hf_config_int`` produces correct interleaved α-β integers
- Asymmetric ``(3,2,1)`` test catches block-ordering bug
- ``build_subspace_hamiltonian`` correctly evaluates Pauli matrix elements
- ``qsci_energy`` matches FCI for H₂ / STO-3G within 1e-3 Ha
- 16-qubit synthetic performance: subspace build + diag < 1s, zero dense 2^n
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from scipy.linalg import eigh

from nodes.quantum._reference.qsci_reference import (
    build_subspace_hamiltonian,
    counts_to_selected_configs,
    hf_config_int,
    qsci_energy,
)


# ═══════════════════════════════════════════════════════════════════════════════
# hf_config_int — interleaved α-β ordering
# ═══════════════════════════════════════════════════════════════════════════════


class TestHFConfigInt:
    """Corrected interleaved Jordan-Wigner HF configuration encoding."""

    def test_h2_hf(self):
        """H₂: 2 spatial orbitals, 1 α, 1 β → |1100⟩ = 12."""
        assert hf_config_int(2, 1, 1) == 12

    def test_full_occupancy(self):
        """All orbitals filled: 2 spatial, 2 α, 2 β → |1111⟩ = 15."""
        assert hf_config_int(2, 2, 2) == 15

    def test_empty(self):
        """No electrons: all qubits 0 → integer 0."""
        assert hf_config_int(2, 0, 0) == 0
        assert hf_config_int(5, 0, 0) == 0

    def test_asymmetric_catches_block_ordering_bug(self):
        """(3 spatial, 2 α, 1 β) — interleaved vs block ordering differ.

        Interleaved:  |α₀ β₀ α₁ β₁ α₂ β₂⟩ = |111000⟩ → int("111000",2) = 56
        Block (bug):  α-block "110", β-block "100" → "110100" → 52
        """
        val = hf_config_int(3, 2, 1)
        assert val == 56, (
            f"Expected 56 (interleaved |111000⟩), got {val}. "
            "Block ordering (buggy) would give 52."
        )
        # Explicitly verify the buggy value is different
        block_buggy = int("110100", 2)  # what the block-ordering code produces
        assert val != block_buggy, "Value must differ from block-ordering result"

    def test_single_spatial_orbital(self):
        """1 spatial orbital, 1 electron: |10⟩ = 2 for α, |01⟩ = 1 for β."""
        assert hf_config_int(1, 1, 0) == 2   # |10⟩
        assert hf_config_int(1, 0, 1) == 1   # |01⟩
        assert hf_config_int(1, 1, 1) == 3   # |11⟩

    def test_large_symmetric(self):
        """Symmetric occupancy of 5 orbitals: first 3 α + first 3 β filled."""
        # |1111110000⟩ → α0,β0,α1,β1,α2,β2 filled, rest empty
        assert hf_config_int(5, 3, 3) == int("1111110000", 2)


# ═══════════════════════════════════════════════════════════════════════════════
# counts_to_selected_configs
# ═══════════════════════════════════════════════════════════════════════════════


class TestCountsToSelectedConfigs:
    def test_top_k_basic(self):
        counts = {0: 5, 1: 10, 2: 3, 3: 8}
        selected = counts_to_selected_configs(counts, K=2)
        assert selected == [1, 3]  # highest counts first

    def test_fewer_than_k(self):
        counts = {10: 5, 20: 3}
        selected = counts_to_selected_configs(counts, K=10)
        assert len(selected) == 2
        assert 10 in selected and 20 in selected

    def test_empty_counts(self):
        assert counts_to_selected_configs({}, K=5) == []

    def test_single_entry(self):
        assert counts_to_selected_configs({42: 1}, K=5) == [42]

    def test_ties_stable(self):
        """Multiple entries with same count — first-seen wins (deterministic)."""
        counts = {0: 1, 1: 1, 2: 1}
        selected = counts_to_selected_configs(counts, K=2)
        assert len(selected) == 2
        assert set(selected) == {0, 1}  # ties resolved by dict iteration order


# ═══════════════════════════════════════════════════════════════════════════════
# build_subspace_hamiltonian — Pauli-term sparse construction
# ═══════════════════════════════════════════════════════════════════════════════


def _pack_terms(term_list):
    """Convert list of ((q,op), coeff) or ({(q:op)}, coeff) to OpenFermion format."""
    result = {}
    for spec, coeff in term_list:
        if isinstance(spec, dict):
            result[tuple(sorted(spec.items()))] = coeff
        else:
            result[spec] = coeff
    return result


class TestBuildSubspaceHamiltonian:
    """Sparse subspace construction from Pauli terms using Slater-Condon."""

    # ── Diagonal (Z / I) terms ──

    def test_single_z_term(self):
        """H = Z₀: diagonal elements ±1 depending on qubit-0 occupation."""
        # qubit 0 = MSB: |0xxx⟩→ +1, |1xxx⟩→ -1
        terms = _pack_terms([({0: "Z"}, 1.0)])
        configs = [0, 8]  # |0000⟩, |1000⟩   (4-qubit)
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        assert H.shape == (2, 2)
        assert abs(H[0, 0] - 1.0) < 1e-12   # qubit0=0 → +1
        assert abs(H[1, 1] - (-1.0)) < 1e-12  # qubit0=1 → -1
        assert abs(H[0, 1]) < 1e-12  # diagonal only
        assert abs(H[1, 0]) < 1e-12

    def test_multiple_z_terms(self):
        """H = Z₀ + 2·Z₁ — check summed diagonal."""
        terms = _pack_terms([({0: "Z"}, 1.0), ({1: "Z"}, 2.0)])
        configs = [0, 4, 8, 12]  # all 2-bit combos for qubits 0,1 (4-qubit)
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        # |0000⟩: Z₀(+1) + 2·Z₁(+1) = 3
        # |0100⟩: Z₀(+1) + 2·Z₁(-1) = -1  (qubit1=1, bit pos 2)
        # |1000⟩: Z₀(-1) + 2·Z₁(+1) = 1
        # |1100⟩: Z₀(-1) + 2·Z₁(-1) = -3
        expected = [3.0, -1.0, 1.0, -3.0]
        for i, exp in enumerate(expected):
            assert abs(H[i, i] - exp) < 1e-12, f"config {configs[i]:04b}: exp {exp}, got {H[i,i]}"

    # ── Off-diagonal (X) terms ──

    def test_single_x_connects_states(self):
        """H = X₁ connects |x0y⟩ ↔ |x1y⟩ for the middle qubit."""
        terms = _pack_terms([({1: "X"}, 1.0)])
        # qubit 1 at bit position 2 (n_qubits-1-1 = 2 for 4 qubits)
        # |0000⟩↔|0100⟩, |1000⟩↔|1100⟩
        configs = [0, 4, 8, 12]
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        assert abs(H[0, 1] - 1.0) < 1e-12  # |0000⟩ → |0100⟩
        assert abs(H[1, 0] - 1.0) < 1e-12  # |0100⟩ → |0000⟩
        assert abs(H[2, 3] - 1.0) < 1e-12  # |1000⟩ → |1100⟩
        assert abs(H[3, 2] - 1.0) < 1e-12  # |1100⟩ → |1000⟩
        # Diagonal must be zero
        for i in range(4):
            assert abs(H[i, i]) < 1e-12

    def test_x_only_connects_selected_configs(self):
        """If a flipped config is not in the subspace, no contribution."""
        terms = _pack_terms([({0: "X"}, 2.0)])
        # X₀ flips MSB: |0000⟩→|1000⟩, |1000⟩→|0000⟩
        # Only include |0000⟩, NOT |1000⟩ → no connection
        configs = [0, 3]  # |0000⟩ and |0011⟩ (unrelated)
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        # All zero — no term connects configs in subspace
        assert np.allclose(H, 0.0)

    # ── Y phase ──

    def test_y_phases(self):
        """Y₀: ⟨0|Y|1⟩ = -i, ⟨1|Y|0⟩ = +i."""
        terms = _pack_terms([({0: "Y"}, 1.0)])
        configs = [0, 8]  # |0000⟩↔|1000⟩
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        # Input |0000⟩ (qubit0=0), output |1000⟩: ⟨1000|Y₀|0000⟩ = +i
        assert abs(H[1, 0] - 1j) < 1e-12
        # Input |1000⟩ (qubit0=1), output |0000⟩: ⟨0000|Y₀|1000⟩ = -i
        assert abs(H[0, 1] - (-1j)) < 1e-12

    def test_z_plus_x_combined(self):
        """Z₀ X₁: Z diagonal phase + X flip."""
        terms = _pack_terms([({0: "Z"}, 3.0), ({1: "X"}, 5.0)])
        # These are separate terms — H = 3·Z₀ + 5·X₁
        configs = [0, 4, 8, 12]  # |0000⟩, |0100⟩, |1000⟩, |1100⟩
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        # Check Z₀ diagonal: +3 for qubit0=0, -3 for qubit0=1
        assert abs(H[0, 0] - 3.0) < 1e-12   # |0000⟩ qubit0=0
        assert abs(H[2, 2] - (-3.0)) < 1e-12  # |1000⟩ qubit0=1
        # Check X₁ connections (amplitude 5.0)
        assert abs(H[0, 1] - 5.0) < 1e-12
        assert abs(H[2, 3] - 5.0) < 1e-12

    # ── Hermiticity ──

    def test_hermiticity_real_coefficients(self):
        """Physically valid Hamiltonians (real coeffs) produce Hermitian H_sub."""
        rng = np.random.default_rng(42)
        n_qubits = 6
        terms = {}
        for _ in range(200):
            n_active = rng.integers(1, 4)
            qubits = sorted(rng.choice(n_qubits, size=n_active, replace=False).tolist())
            ops = rng.choice(["X", "Y", "Z"], size=n_active).tolist()
            coeff = float(rng.normal(0.0, 1.0))
            pauli_tuple = tuple(zip(qubits, ops))
            terms[pauli_tuple] = coeff
        configs = [int(f"{i:06b}", 2) for i in [0, 7, 15, 23, 31, 39, 47, 55, 63]]
        H = build_subspace_hamiltonian(configs, terms, n_qubits)
        assert H.shape == (len(configs), len(configs))
        assert np.allclose(H, H.conj().T), "H_sub must be Hermitian"


# ═══════════════════════════════════════════════════════════════════════════════
# qsci_energy — full pipeline test with H₂ / STO-3G
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def h2_data():
    """H₂ / STO-3G molecule, qubit Hamiltonian, exact energies."""
    from openfermion import jordan_wigner, get_sparse_operator
    from openfermion.chem import MolecularData
    from openfermionpyscf import run_pyscf

    geometry = [("H", (0.0, 0.0, -0.7414 / 2)), ("H", (0.0, 0.0, 0.7414 / 2))]
    mol = MolecularData(geometry, "sto-3g", 1, 0)
    mol = run_pyscf(mol, run_scf=True, run_ccsd=True, run_fci=True)

    fermion_H = mol.get_molecular_hamiltonian()
    qubit_H = jordan_wigner(fermion_H)
    H_dense = get_sparse_operator(qubit_H).toarray()
    exact_evals, exact_evecs = eigh(H_dense)
    E_fci = float(exact_evals[0].real)

    # Exact ground-state probabilities → integer counts
    wfn = exact_evecs[:, 0]
    probs = np.abs(wfn) ** 2
    counts = {int(i): int(round(probs[i] * 1_000_000)) for i in range(16) if probs[i] > 1e-12}

    return {
        "mol": mol,
        "qubit_H": qubit_H,
        "E_fci": E_fci,
        "counts": counts,
        "n_qubits": mol.n_qubits,
    }


class TestQSCIEnergyH2:
    """End-to-end QSCI on H₂: energy must match FCI within 1e-3 Ha."""

    def test_k2_recovers_fci(self, h2_data):
        """Two configurations (|1100⟩ + |0011⟩) span the H₂ ground-state space."""
        result = qsci_energy(h2_data["counts"], h2_data["qubit_H"],
                             h2_data["n_qubits"], K=2)
        delta = abs(result["E_qsci"] - h2_data["E_fci"])
        assert delta < 1e-10, f"Δ = {delta:.2e} Ha, must be zero for K=2 spanning"

    def test_energy_within_threshold(self, h2_data):
        """Even with K=1 (HF only), energy should be close to FCI."""
        result = qsci_energy(h2_data["counts"], h2_data["qubit_H"],
                             h2_data["n_qubits"], K=1)
        delta = abs(result["E_qsci"] - h2_data["E_fci"])
        assert delta < 0.03, f"HF energy Δ = {delta:.2e} should be within 30 mHa"

    def test_increasing_k_never_worse(self, h2_data):
        """More configurations should never increase the energy."""
        prev = float("inf")
        for K in [1, 2, 4]:
            result = qsci_energy(h2_data["counts"], h2_data["qubit_H"],
                                 h2_data["n_qubits"], K=K)
            assert result["E_qsci"] <= prev + 1e-12, (
                f"K={K} energy {result['E_qsci']:.8f} > K-1 energy {prev:.8f}"
            )
            prev = result["E_qsci"]

    def test_return_structure(self, h2_data):
        """qsci_energy returns all expected keys."""
        result = qsci_energy(h2_data["counts"], h2_data["qubit_H"],
                             h2_data["n_qubits"], K=2)
        assert "E_qsci" in result
        assert "configs" in result
        assert "eigenvalues" in result
        assert "subspace_dim" in result
        assert isinstance(result["E_qsci"], float)
        assert isinstance(result["configs"], list)
        assert len(result["eigenvalues"]) == result["subspace_dim"]

    # ── HF config consistency ──

    def test_hf_config_matches_openfermion(self, h2_data):
        """Our hf_config_int produces integer compatible with OpenFermion dense matrix."""
        from openfermion import jordan_wigner, get_sparse_operator
        from openfermion.ops import FermionOperator

        hf_int = hf_config_int(2, 1, 1)
        # Build number operator sum for both occupied spin-orbitals
        ne_op = FermionOperator("0^ 0") + FermionOperator("1^ 1")
        ne_jw = jordan_wigner(ne_op)
        mat = get_sparse_operator(ne_jw, n_qubits=4).toarray()
        n_elec = mat[hf_int, hf_int].real
        assert abs(n_elec - 2.0) < 1e-10, f"HF config should have 2 electrons, got {n_elec}"

    def test_hf_config_is_top_count(self, h2_data):
        """In H₂ ground state, HF config dominates the probability distribution."""
        counts = h2_data["counts"]
        hf_int = hf_config_int(2, 1, 1)
        top = max(counts, key=counts.get)  # type: ignore[arg-type]
        assert top == hf_int, f"Top config {top:04b} ≠ HF {hf_int:04b}"


# ═══════════════════════════════════════════════════════════════════════════════
# 16-qubit synthetic performance test
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def synthetic_16q():
    """Synthetic 16-qubit Pauli Hamiltonian (chemistry-like structure)."""
    rng = np.random.default_rng(42)
    n_qubits = 16
    terms = {}
    # Generate chemistry-structured terms: 1-body (~n), 2-body (~n²)
    # Each term has 1–4 active qubits with X, Y, Z operators.
    n_terms = 1000
    for _ in range(n_terms):
        n_active = rng.integers(1, min(5, n_qubits + 1))
        qubits = sorted(rng.choice(n_qubits, size=n_active, replace=False).tolist())
        ops = rng.choice(["X", "Y", "Z"], size=n_active).tolist()
        coeff = float(rng.normal(0.0, 1.0))
        term = tuple((int(q), str(o)) for q, o in zip(qubits, ops))
        terms[term] = complex(coeff)
    # Configs: 50 random bitstrings, diverse occupation patterns
    configs = [int(f"{rng.integers(0, 2**n_qubits):016b}", 2) for _ in range(50)]
    return {"terms": terms, "configs": configs, "n_qubits": n_qubits}


class Test16QubitPerformance:
    """Synthetic 16-qubit performance — must complete < 1s, no dense 2^n."""

    def test_subspace_build_fast(self, synthetic_16q):
        """build_subspace_hamiltonian on 16 qubits, 1000 terms, 50 configs < 1s."""
        t0 = time.perf_counter()
        H = build_subspace_hamiltonian(
            synthetic_16q["configs"],
            synthetic_16q["terms"],
            synthetic_16q["n_qubits"],
        )
        elapsed = time.perf_counter() - t0
        assert H.shape == (50, 50)
        assert elapsed < 1.0, (
            f"build_subspace_hamiltonian took {elapsed:.3f}s, must be < 1s"
        )
        # Must be non-trivial (not all zeros)
        assert np.any(np.abs(H) > 1e-12), "H_sub should have non-zero elements"

    def test_full_pipeline_fast(self, synthetic_16q):
        """qsci_energy (select + build + diagonalize) < 1s."""
        counts = {c: np.random.default_rng(42).integers(1, 100)
                  for c in synthetic_16q["configs"]}

        # Create a mock qubit Hamiltonian with .terms attribute
        class MockQubitHam:
            def __init__(self, terms):
                self.terms = terms

        ham = MockQubitHam(synthetic_16q["terms"])

        t0 = time.perf_counter()
        result = qsci_energy(counts, ham, synthetic_16q["n_qubits"], K=20)
        elapsed = time.perf_counter() - t0
        assert result["subspace_dim"] <= 20
        assert elapsed < 1.0, (
            f"qsci_energy took {elapsed:.3f}s, must be < 1s"
        )

    def test_no_dense_2n_allocation(self, synthetic_16q):
        """Verify build_subspace_hamiltonian never allocates a 2^n dense matrix.

        We do this by monkey-patching numpy.zeros to detect any allocation
        with the 'dangerous' shape (2^n_qubits, 2^n_qubits).
        """
        n_qubits = synthetic_16q["n_qubits"]
        dangerous_shape = (2**n_qubits, 2**n_qubits)
        original_zeros = np.zeros

        violation = []

        def _patched_zeros(shape_or_like, *args, **kwargs):
            result = original_zeros(shape_or_like, *args, **kwargs)
            if (hasattr(result, "shape")
                    and result.shape == dangerous_shape
                    and result.dtype == complex):
                violation.append(f"Allocated dense {dangerous_shape} complex matrix!")
            return result

        np.zeros = _patched_zeros
        try:
            build_subspace_hamiltonian(
                synthetic_16q["configs"],
                synthetic_16q["terms"],
                n_qubits,
            )
        finally:
            np.zeros = original_zeros

        assert len(violation) == 0, (
            f"Dense 2^n allocation detected: {violation}"
        )

    def test_hermiticity_16q(self, synthetic_16q):
        """Subspace Hamiltonian must be Hermitian for real-coeff Pauli terms."""
        H = build_subspace_hamiltonian(
            synthetic_16q["configs"],
            synthetic_16q["terms"],
            synthetic_16q["n_qubits"],
        )
        assert np.allclose(H, H.conj().T), "H_sub must be Hermitian"


# ═══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_empty_configs(self):
        """Empty config list → empty subspace matrix."""
        H = build_subspace_hamiltonian([], {}, n_qubits=4)
        assert H.shape == (0, 0)

    def test_single_config(self):
        """Single config → 1×1 matrix (diagonal expectation value)."""
        terms = _pack_terms([({0: "Z"}, 0.5)])
        H = build_subspace_hamiltonian([12], terms, n_qubits=4)
        # config 12 = |1100⟩, qubit0=1 → Z₀ = -1 → -0.5
        assert H.shape == (1, 1)
        assert abs(H[0, 0] - (-0.5)) < 1e-12

    def test_empty_pauli_terms(self):
        """No Pauli terms → zero subspace matrix."""
        H = build_subspace_hamiltonian([0, 8], {}, n_qubits=4)
        assert np.allclose(H, 0.0)

    def test_no_counts_returns_empty(self):
        """qsci_energy with empty counts returns empty result."""
        result = qsci_energy({}, None, n_qubits=4, K=10)
        assert result["subspace_dim"] == 0
        assert result["configs"] == []

    def test_identity_only_term(self):
        """Identity terms don't flip bits and have unit phase."""
        # I₀ = 0.5·I - 0.5·Z₀?  No, pure I: ⟨a|I|b⟩ = δ_{a,b}
        # An I-only Pauli string has zero active qubits.
        terms = {(): 2.0}  # pure identity term (empty tuple)
        configs = [0, 8]
        H = build_subspace_hamiltonian(configs, terms, n_qubits=4)
        # Only diagonal, all 2.0
        assert abs(H[0, 0] - 2.0) < 1e-12
        assert abs(H[1, 1] - 2.0) < 1e-12
        assert abs(H[0, 1]) < 1e-12
        assert abs(H[1, 0]) < 1e-12
