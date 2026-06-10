"""qsci-assemble — QSCI subspace diagonalisation & energy assembly.

Reads measurement counts, qubit Hamiltonian, and mean-field energy; applies
Slater-Condon rules to build a sparse subspace Hamiltonian and assembles the
total embedded energy via E_total = e_mf + (E_qsci - e_core_baseline).
"""
import json
import os
import sys

import h5py
import numpy as np
from scipy.linalg import eigh

# Import reference QSCI functions from the profile mount
sys.path.insert(0, "/mf/profile")
from qsci_reference import (
    hf_config_int,
    counts_to_selected_configs,
    build_subspace_hamiltonian,
    post_select_counts,
)

INPUT_DIR = os.environ.get("MF_INPUT_DIR", "/mf/input")
OUTPUT_DIR = os.environ.get("MF_OUTPUT_DIR", "/mf/output")
K = int(os.environ["MF_K"])

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Load stream inputs
# ═══════════════════════════════════════════════════════════════════════════════

# 1a.  Measurement counts JSON
counts_path = os.path.join(INPUT_DIR, "measurement_counts")
with open(counts_path) as fh:
    raw_counts = json.load(fh)
# Expected format: flat {"1100": 450, "1010": 320, ...} (MSB-first bitstrings)
# Convert bitstring keys (str) to integer configs
counts = {}
for bs, cnt in raw_counts.items():
    counts[int(bs, 2)] = int(cnt)

print(f"[qsci-assemble] Loaded {len(counts)} unique measurement outcomes")

# 1b.  Qubit Hamiltonian JSON
ham_path = os.path.join(INPUT_DIR, "qubit_hamiltonian")
with open(ham_path) as fh:
    raw_ham = json.load(fh)

n_qubits = raw_ham["n_qubits"]
n_elec_raw = raw_ham.get("n_elec")
if n_elec_raw is None:
    print("[qsci-assemble][ERR] qubit_hamiltonian JSON missing 'n_elec' field. "
          "The upstream qsci-prep node must embed the electron count.", file=sys.stderr)
    sys.exit(1)
N_ELECTRONS = int(n_elec_raw)
n_spatial = n_qubits // 2
n_alpha = N_ELECTRONS // 2
n_beta = N_ELECTRONS // 2

# Reconstruct duck-typed QubitOperator from the compact sparse JSON v2 emitted
# by qsci-prep: {"X0 Z1 Y4": coeff_real, ...} ("" key = identity term).
ham_format = raw_ham.get("format")
if ham_format != "openfermion-sparse-v2":
    print(f"[qsci-assemble][ERR] Unsupported qubit_hamiltonian format "
          f"'{ham_format}' — upstream qsci-prep must emit "
          f"'openfermion-sparse-v2'.", file=sys.stderr)
    sys.exit(1)

class _Ham:
    def __init__(self, terms_map):
        self.terms = {}
        for pauli_str, coeff in terms_map.items():
            key = tuple((int(tok[1:]), tok[0]) for tok in pauli_str.split())
            self.terms[key] = complex(coeff, 0.0)

qubit_hamiltonian = _Ham(raw_ham["terms"])

print(f"[qsci-assemble] Qubit Hamiltonian: n_qubits={n_qubits}, "
      f"n_spatial={n_spatial}, n_electrons={N_ELECTRONS}, "
      f"n_pauli_terms={len(qubit_hamiltonian.terms)}")

# 1c.  Mean-field energy (physical_quantity, Ha — value is a bare float string)
e_mf_path = os.path.join(INPUT_DIR, "e_mf")
with open(e_mf_path) as fh:
    e_mf = float(fh.read().strip())

print(f"[qsci-assemble] e_mf = {e_mf:.10f} Ha")

# ═══════════════════════════════════════════════════════════════════════════════
# 2.  QSCI subspace construction
# ═══════════════════════════════════════════════════════════════════════════════

# 2a.  Particle-number post-selection: drop noise outcomes outside the
#      (n_alpha, n_beta) sector — they cannot belong to the physical spectrum
n_shots_raw = sum(counts.values())
counts = post_select_counts(counts, n_spatial, n_alpha, n_beta)
n_shots_kept = sum(counts.values())
print(f"[qsci-assemble] Post-selection (n_alpha={n_alpha}, n_beta={n_beta}): "
      f"kept {n_shots_kept}/{n_shots_raw} shots "
      f"({len(counts)} unique configs)")

# 2b.  Select top-K measured configurations
selected = counts_to_selected_configs(counts, K)

# 2c.  Build HF configuration (interleaved alpha-beta, RHF: n_alpha = n_beta)
hf_cfg = hf_config_int(n_spatial, n_alpha, n_beta)
print(f"[qsci-assemble] HF config = {hf_cfg} (0b{hf_cfg:0{n_qubits}b})")

# 2d.  Ensure HF configuration is always in the subspace
if hf_cfg not in selected:
    selected.insert(0, hf_cfg)
    print(f"[qsci-assemble] HF config not in top-K measurements — force-added")
else:
    print(f"[qsci-assemble] HF config found in top-K measurements")

# 2e.  Build subspace Hamiltonian (sparse — no dense 2^n matrix)
H_sub = build_subspace_hamiltonian(selected, qubit_hamiltonian.terms, n_qubits)
subspace_dim = len(selected)

print(f"[qsci-assemble] Subspace dimension = {subspace_dim} "
      f"(H_sub shape = {H_sub.shape})")

# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Diagonalise subspace Hamiltonian
# ═══════════════════════════════════════════════════════════════════════════════

eigenvalues, eigenvectors = eigh(H_sub)

# Lowest eigenvalue -> cluster QSCI energy
E_qsci_cluster = float(eigenvalues[0].real)

# e_core_baseline = ⟨HF|H_qubit|HF⟩ — diagonal element at HF index
hf_index = selected.index(hf_cfg)
e_core_baseline = float(H_sub[hf_index, hf_index].real)

# Assemble total energy: E_total = e_mf + (E_qsci_cluster - e_core_baseline)
total_energy = e_mf + (E_qsci_cluster - e_core_baseline)

print(f"[qsci-assemble] E_qsci (cluster) = {E_qsci_cluster:.10f} Ha")
print(f"[qsci-assemble] e_core_baseline   = {e_core_baseline:.10f} Ha")
print(f"[qsci-assemble] total_energy       = {total_energy:.10f} Ha")
print(f"[qsci-assemble] Delta correction   = {E_qsci_cluster - e_core_baseline:+.10f} Ha")

# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Success gate
# ═══════════════════════════════════════════════════════════════════════════════

qsci_succeeded = (
    subspace_dim > 0
    and hf_cfg in selected
    and np.isfinite(E_qsci_cluster)
    and np.isfinite(total_energy)
)
print(f"[qsci-assemble] qsci_succeeded = {qsci_succeeded}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5.  Write stream outputs
# ═══════════════════════════════════════════════════════════════════════════════

# 5a.  total_energy (physical_quantity, Ha)
with open(os.path.join(OUTPUT_DIR, "total_energy"), "w") as fh:
    fh.write(f"{total_energy:.15f}")

# e_total — onboard_output mirror (panel display, same value)
with open(os.path.join(OUTPUT_DIR, "e_total"), "w") as fh:
    fh.write(f"{total_energy:.15f}")

# 5b.  qsci_state (HDF5 — qsci/qsci-state-h5)
h5_path = os.path.join(OUTPUT_DIR, "qsci_state")
with h5py.File(h5_path, "w") as f:
    ev = np.asarray(eigenvalues.real, dtype=np.float64)
    evec = np.asarray(eigenvectors.real, dtype=np.float64)
    f.create_dataset("eigenvalues", data=ev)
    f.create_dataset("eigenvectors", data=evec)
    f.create_dataset("configs", data=np.array(selected, dtype=np.int64))
    f.create_dataset("hf_index", data=np.int64(hf_index))
    f.create_dataset("metadata/n_qubits", data=np.int64(n_qubits))
    f.create_dataset("metadata/n_spatial", data=np.int64(n_spatial))
    f.create_dataset("metadata/n_electrons", data=np.int64(N_ELECTRONS))
    f.create_dataset("metadata/subspace_dim", data=np.int64(subspace_dim))
    f.create_dataset("metadata/K", data=np.int64(K))
    f.create_dataset("metadata/source", data=np.bytes_("qsci-assemble"))
    f.create_dataset("energies/E_qsci", data=np.float64(E_qsci_cluster))
    f.create_dataset("energies/e_core_baseline", data=np.float64(e_core_baseline))
    f.create_dataset("energies/total_energy", data=np.float64(total_energy))

print(f"[qsci-assemble] Wrote HDF5 to {h5_path} "
      f"({os.path.getsize(h5_path):,} bytes)")

# 5c.  qsci_report (report_object, JSON)
report = {
    "E_qsci": total_energy,
    "E_qsci_cluster": E_qsci_cluster,
    "e_mf": e_mf,
    "e_core_baseline": e_core_baseline,
    "subspace_dim": subspace_dim,
    "n_qubits": n_qubits,
    "n_spatial": n_spatial,
    "n_electrons": N_ELECTRONS,
    "K": K,
    "n_shots_raw": n_shots_raw,
    "n_shots_postselected": n_shots_kept,
    "top_configs": selected,
    "eigenvalues": [float(ev.real) for ev in eigenvalues.flatten()],
}
report_path = os.path.join(OUTPUT_DIR, "qsci_report")
with open(report_path, "w") as fh:
    json.dump(report, fh, indent=2)
print(f"[qsci-assemble] Wrote report to {report_path}")

# 5d.  qsci_succeeded (onboard output, quality_gate)
gate_path = os.path.join(OUTPUT_DIR, "qsci_succeeded")
with open(gate_path, "w") as fh:
    fh.write("true" if qsci_succeeded else "false")

print(f"[qsci-assemble] Done.")
