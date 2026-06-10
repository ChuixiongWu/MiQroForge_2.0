"""QSCI reference implementation with corrected interleaved alpha-beta ordering.

Core algorithm (Kanno et al., arXiv:2302.11320):
  1. Sample computational basis → get bitstring counts
  2. Select top-K most frequent configurations (Slater determinants)
  3. Build subspace Hamiltonian H_S = P_S H P_S from Pauli terms (Slater-Condon)
  4. Diagonalize classically → improved ground-state energy

Corrected qubit ordering
------------------------
OpenFermion's Jordan-Wigner uses **interleaved** alpha-beta ordering:

    qubit 0 = α of spatial orbital 0  (MSB in get_sparse_operator)
    qubit 1 = β of spatial orbital 0
    qubit 2 = α of spatial orbital 1
    qubit 3 = β of spatial orbital 1
    ...

The buggy ``hf_state_int`` in qsci_infra.py used **block** ordering
(all α orbitals first, then all β orbitals), producing incorrect integer
encodings that mis-indexed diagonal Hamiltonian elements.

Subspace construction
---------------------
Subspace Hamiltonian is built element-by-element from Pauli terms using
Slater-Condon rules in the computational basis. Each ⟨a|P|b⟩ matrix
element is evaluated directly — **no dense 2^n matrix is allocated**.
For efficiency, a flip-mask lookup is used: for each Pauli term, the
X/Y operators define a bit-flip mask; configurations that map to other
selected configurations via this mask contribute to H_sub[i,j].
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from scipy.linalg import eigh


# ── Configuration construction (interleaved α-β ordering) ────────────────────


def hf_config_int(n_spatial: int, n_alpha: int, n_beta: int) -> int:
    """Hartree-Fock configuration as integer in interleaved α-β JW ordering.

    In OpenFermion's convention (compatible with ``get_sparse_operator``),
    qubit 0 is the MSB of the integer encoding.  Spin-orbitals are
    interleaved::

        qubit 0 = α_spatial_0   (MSB / bit position n_qubits-1)
        qubit 1 = β_spatial_0
        qubit 2 = α_spatial_1
        qubit 3 = β_spatial_1
        ...
        qubit (n_qubits-1) = β_spatial_{n_spatial-1}   (LSB)

    The first ``n_alpha`` α orbitals and first ``n_beta`` β orbitals
    are occupied (bit = 1), all higher orbitals are empty (bit = 0).

    Parameters
    ----------
    n_spatial : int
        Number of spatial orbitals.  Total qubits = 2 * n_spatial.
    n_alpha : int
        Number of α (spin-up) electrons.
    n_beta : int
        Number of β (spin-down) electrons.

    Returns
    -------
    int
        Configuration integer compatible with OpenFermion's dense-matrix
        indexing.

    Examples
    --------
    >>> hf_config_int(2, 1, 1)   # H₂ HF: |1100⟩ → 12
    12
    >>> hf_config_int(3, 2, 1)   # asymmetric: |111000⟩ → 56
    56
    """
    bits: List[str] = []
    for orb in range(n_spatial):
        bits.append("1" if orb < n_alpha else "0")  # α orbital at even qubit
        bits.append("1" if orb < n_beta else "0")   # β orbital at odd qubit
    return int("".join(bits), 2)


# ── Configuration selection ──────────────────────────────────────────────────


def post_select_counts(
    counts: Dict[int, int],
    n_spatial: int,
    n_alpha: int,
    n_beta: int,
) -> Dict[int, int]:
    """Discard measurement outcomes that violate particle-number conservation.

    The molecular Hamiltonian conserves the number of α and β electrons
    separately, so any sampled configuration outside the (n_alpha, n_beta)
    sector is unphysical — it can only originate from hardware noise.
    Keeping such configurations in the QSCI subspace risks an unphysical
    ground state (a noise determinant in a different particle sector may
    have a lower diagonal energy than any physical state).

    Uses the interleaved α-β JW ordering of :func:`hf_config_int`:
    qubit 0 (MSB) = α of spatial orbital 0, qubit 1 = β of spatial
    orbital 0, etc. — α spin-orbitals occupy even qubits, β odd qubits.

    Parameters
    ----------
    counts : dict[int, int]
        Raw measurement outcome counts ``{config_int: shot_count}``.
    n_spatial : int
        Number of spatial orbitals (total qubits = 2 * n_spatial).
    n_alpha : int
        Required number of α electrons.
    n_beta : int
        Required number of β electrons.

    Returns
    -------
    dict[int, int]
        Counts restricted to the (n_alpha, n_beta) sector.
    """
    alpha_mask = int("10" * n_spatial, 2)   # even qubits (MSB-first)
    beta_mask = int("01" * n_spatial, 2)    # odd qubits
    return {
        cfg: cnt
        for cfg, cnt in counts.items()
        if bin(cfg & alpha_mask).count("1") == n_alpha
        and bin(cfg & beta_mask).count("1") == n_beta
    }


def counts_to_selected_configs(
    counts: Dict[int, int],
    K: int,
) -> List[int]:
    """Select top-K configurations by measurement shot count.

    Parameters
    ----------
    counts : dict[int, int]
        Measurement outcome counts: ``{config_int: count}``.
    K : int
        Number of top configurations to retain.

    Returns
    -------
    list[int]
        Up to K configuration integers sorted by descending count.
        If fewer than K unique configs are available, returns all of them.
    """
    if not counts:
        return []
    sorted_configs = sorted(counts.items(), key=lambda kv: -kv[1])
    selected = [c for c, _ in sorted_configs[:K]]
    return selected


# ── Subspace Hamiltonian from Pauli terms (Slater-Condon) ────────────────────


def build_subspace_hamiltonian(
    configs: List[int],
    pauli_terms: dict,
    n_qubits: int,
) -> np.ndarray:
    """Build subspace Hamiltonian H_ij = ⟨config_i|H|config_j⟩ from Pauli terms.

    The subspace matrix is constructed term-by-term using Slater-Condon
    rules in the computational basis — **no dense 2^n matrix is allocated**.

    Each Pauli string P = ⊗_q σ_q connects input configuration |b⟩ to
    output configuration |a⟩ if and only if:

    * For every q where σ_q ∈ {I, Z}:  a_q == b_q  (no bit flip)
    * For every q where σ_q ∈ {X, Y}: a_q == ¬b_q  (bit flip)

    The matrix element is:

        ⟨a|P|b⟩ = ∏_q ⟨a_q|σ_q|b_q⟩

    with single-qubit elements:

        ⟨a|I|b⟩ = δ_{a,b}
        ⟨a|X|b⟩ = δ_{a,¬b}
        ⟨a|Z|b⟩ = (-1)^{b} · δ_{a,b}
        ⟨0|Y|1⟩ = -i,  ⟨1|Y|0⟩ = +i

    **Bit-ordering convention** (matches OpenFermion ``get_sparse_operator``):
    qubit 0 is the most-significant bit of the configuration integer.
    qubit q maps to bit position ``n_qubits - 1 - q``.

    Parameters
    ----------
    configs : list[int]
        Configuration integers in OpenFermion's big-endian convention.
    pauli_terms : dict
        OpenFermion ``QubitOperator.terms``: ``{((q, op), ...): coeff}``
        where each key is a tuple of ``(qubit_index, pauli_character)`` pairs
        and each value is a complex coefficient.
    n_qubits : int
        Total number of qubits.

    Returns
    -------
    H_sub : np.ndarray, shape (K, K), dtype complex
        Subspace Hamiltonian matrix.  NOT guaranteed Hermitian if the
        input Pauli terms contain non-Hermitian contributions, but will
        be Hermitian for any physically valid electronic Hamiltonian.
    """
    K = len(configs)
    H_sub = np.zeros((K, K), dtype=complex)

    if K == 0:
        return H_sub

    # Fast config → index lookup: O(1) per mapping check
    config_map: Dict[int, int] = {c: idx for idx, c in enumerate(configs)}

    # Pre-compute qubit → bit-position shift: qubit q → (n_qubits - 1 - q)
    # This maps OpenFermion qubit indexing (qubit 0 = MSB) to integer bit positions.

    for pauli_tuple, coeff in pauli_terms.items():
        # ── Parse Pauli string into flip mask and phase data ──
        flip_mask = 0          # bits where X or Y acts (must flip)
        z_qubits: List[int] = []   # qubit indices with Z operator
        y_qubits: List[int] = []   # qubit indices with Y operator

        for q, op in pauli_tuple:
            bit_shift = n_qubits - 1 - q
            if op == "X":
                flip_mask |= 1 << bit_shift
            elif op == "Y":
                flip_mask |= 1 << bit_shift
                y_qubits.append(q)
            elif op == "Z":
                z_qubits.append(q)
            # op == 'I': no effect

        # ── For each input configuration j, compute output i = j XOR flip_mask ──
        for j_bits, j_idx in config_map.items():
            i_bits = j_bits ^ flip_mask
            i_idx = config_map.get(i_bits)
            if i_idx is None:
                continue  # flipped config not in subspace

            # ── Compute phase factor ──
            phase: complex = coeff

            # Z phase:  ⟨a|Z|b⟩ = (-1)^{b} · δ_{a,b}
            for q in z_qubits:
                bit_shift = n_qubits - 1 - q
                if (j_bits >> bit_shift) & 1:  # input bit is 1
                    phase = -phase

            # Y phase:  ⟨0|Y|1⟩ = -i,  ⟨1|Y|0⟩ = +i
            for q in y_qubits:
                bit_shift = n_qubits - 1 - q
                if (j_bits >> bit_shift) & 1:  # input bit is 1 (output 0)
                    phase *= -1j  # -i
                else:                         # input bit is 0 (output 1)
                    phase *= 1j   # +i

            H_sub[i_idx, j_idx] += phase

    return H_sub


# ── Full QSCI pipeline ───────────────────────────────────────────────────────


def qsci_energy(
    counts: Dict[int, int],
    qubit_hamiltonian,  # openfermion.QubitOperator (duck-typed: needs .terms)
    n_qubits: int,
    K: int,
) -> dict:
    """Run full QSCI pipeline: select configs → build H_sub → diagonalize.

    Parameters
    ----------
    counts : dict[int, int]
        Measurement outcome counts ``{config_int: shot_count}``.
    qubit_hamiltonian
        OpenFermion ``QubitOperator`` (must have ``.terms`` attribute).
    n_qubits : int
        Total number of qubits.
    K : int
        Number of top configurations to select for the subspace.

    Returns
    -------
    dict
        Keys:
        - ``E_qsci`` : float — lowest eigenvalue of H_sub (real part).
        - ``configs`` : list[int] — selected configuration integers.
        - ``eigenvalues`` : np.ndarray — all eigenvalues (ascending).
        - ``subspace_dim`` : int — number of configurations retained.
    """
    configs = counts_to_selected_configs(counts, K)
    if not configs:
        return {
            "E_qsci": 0.0,
            "configs": [],
            "eigenvalues": np.array([]),
            "subspace_dim": 0,
        }

    H_sub = build_subspace_hamiltonian(configs, qubit_hamiltonian.terms, n_qubits)
    eigenvalues, _eigenvectors = eigh(H_sub)

    return {
        "E_qsci": float(eigenvalues[0].real),
        "configs": configs,
        "eigenvalues": eigenvalues,
        "subspace_dim": len(configs),
    }
