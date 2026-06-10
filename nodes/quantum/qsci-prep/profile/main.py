#!/usr/bin/env python3
"""qsci-prep — QSCI state preparation (quantum-exec-0.1 image).

Loads a Vayesta cluster Hamiltonian HDF5, builds the Jordan-Wigner qubit
Hamiltonian via OpenFermion, constructs an LUCJ ansatz in PennyLane, decomposes
gates to primitives, and exports an OpenQASM 3.0 circuit via Braket SDK.
"""
import json, os, sys
import numpy as np
import h5py

# ═══════════════════════════════════════════════════════════════════════════════
#  0.  Paths & constants
# ═══════════════════════════════════════════════════════════════════════════════
INPUT_DIR  = os.environ.get("MF_INPUT_DIR",  "/mf/input")
OUTPUT_DIR = os.environ.get("MF_OUTPUT_DIR", "/mf/output")
H5_PATH    = f"{INPUT_DIR}/cluster_hamiltonian"

# ═══════════════════════════════════════════════════════════════════════════════
#  1.  Load cluster embedding Hamiltonian
# ═══════════════════════════════════════════════════════════════════════════════
print("[qsci-prep] Loading cluster Hamiltonian …", flush=True)
with h5py.File(H5_PATH, "r") as f:
    heff   = np.asarray(f["cluster/heff"][:],  dtype=np.float64)
    eris   = np.asarray(f["cluster/eris"][:],  dtype=np.float64)  # physicist <pq|rs>
    e_core = np.float64(f["cluster/e_core"][()])
    norb   = int(f["meta/norb"][()])
    if "cluster/C_mo" not in f:
        print("[qsci-prep][ERR] /cluster/C_mo missing in cluster_hamiltonian. "
              "Upstream ewf-decompose must write the MO coefficients.", flush=True)
        sys.exit(1)
    C_mo   = np.asarray(f["cluster/C_mo"][:], dtype=np.float64)

n_spatial = norb
n_qubits  = 2 * n_spatial

# Electron count — sourced from Vayesta fragment metadata (RHF: n_elec = 2*nocc).
# MUST be present in the cluster contract; fail loudly if missing.
with h5py.File(H5_PATH, "r") as f:
    if "meta/n_elec" not in f:
        print("[qsci-prep][ERR] /meta/n_elec missing in cluster_hamiltonian. "
              "The upstream ewf-decompose node must write this field.", flush=True)
        sys.exit(1)
    n_elec = int(f["meta/n_elec"][()])
n_alpha = n_elec // 2
n_beta = n_elec // 2              # closed-shell fragment assumption

print(f"[qsci-prep] norb={n_spatial}  nelec={n_elec}  n_alpha={n_alpha}  "
      f"n_qubits={n_qubits}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  2.  Jordan-Wigner → sparse qubit Hamiltonian
# ═══════════════════════════════════════════════════════════════════════════════
from openfermion import InteractionOperator, jordan_wigner, QubitOperator
from openfermion.chem.molecular_data import spinorb_from_spatial

# Rotate embedding-basis tensors into the cluster MO basis — the basis in which
# the HF determinant occupies the first n_occ orbitals (matching the BasisState
# circuit prep and hf_config_int downstream) and in which the t2 seed is indexed.
h_mo = C_mo.T @ heff @ C_mo
g_mo = np.einsum("pi,qj,rk,sl,pqrs->ijkl",
                 C_mo, C_mo, C_mo, C_mo, eris, optimize=True)

# Spatial → interleaved spin-orbital expansion (α on even, β on odd qubits).
# g_mo is physicist <pq|rs>; OpenFermion's convention is h2[p,q,r,s] = <pq|sr>,
# and InteractionOperator carries the explicit 1/2 prefactor.
h1_so, h2_so = spinorb_from_spatial(h_mo, g_mo.transpose(0, 1, 3, 2))
interaction_op = InteractionOperator(float(e_core), h1_so, 0.5 * h2_so)
qubit_hamiltonian: QubitOperator = jordan_wigner(interaction_op)

# Serialise as compact sparse JSON v2: {"X0 Z1 Y4": coeff_real, ...}.
# Real orbitals ⇒ all JW coefficients are real; fail loudly if not.
max_imag = max((abs(c.imag) for c in qubit_hamiltonian.terms.values()), default=0.0)
if max_imag > 1e-10:
    print(f"[qsci-prep][ERR] Non-real JW coefficient (max imag {max_imag:.3e}) — "
          "orbital tensors are expected to be real.", flush=True)
    sys.exit(1)

terms_json = {
    " ".join(f"{op}{q}" for q, op in sorted(pauli_tuple)): float(coeff.real)
    for pauli_tuple, coeff in qubit_hamiltonian.terms.items()
}

ham_json = {
    "format":  "openfermion-sparse-v2",
    "n_qubits": n_qubits,
    "n_elec":  int(n_elec),
    "constant": float(e_core),
    "terms":    terms_json,
}
with open(f"{OUTPUT_DIR}/qubit_hamiltonian", "w") as fh:
    json.dump(ham_json, fh, separators=(",", ":"))
print(f"[qsci-prep] Qubit Hamiltonian: {len(terms_json)} terms "
      f"(n_qubits={n_qubits}, MO basis, interleaved spin-orbitals)", flush=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  3.  MP2 t2 amplitudes — read precomputed seed from the cluster contract
# ═══════════════════════════════════════════════════════════════════════════════
# The classical AO→MO transform and MP2 amplitudes are computed UPSTREAM in
# ewf-decompose (classical-chem image, which has PySCF/Vayesta).  This node only
# consumes the seed, so the quantum-exec image needs no PySCF and avoids the
# previous O(norb^8) hand-rolled four-index transform that hung on real clusters.
with h5py.File(H5_PATH, "r") as f:
    if "cluster/t2_amps" not in f:
        print("[qsci-prep][ERR] /cluster/t2_amps missing in cluster_hamiltonian. "
              "Upstream ewf-decompose (>=1.2.0) must write the MP2 t2 seed.", flush=True)
        sys.exit(1)
    t2_tensor = np.asarray(f["cluster/t2_amps"][:], dtype=np.float64)

n_vir = n_spatial - n_alpha
expected_shape = (n_alpha, n_alpha, n_vir, n_vir)
if t2_tensor.shape != expected_shape:
    print(f"[qsci-prep][ERR] t2_amps shape {t2_tensor.shape} != expected "
          f"{expected_shape} (n_occ={n_alpha}, n_vir={n_vir})", flush=True)
    sys.exit(1)

# Flatten the dense t2 tensor into the (i, j, a, b, val) channel list the ansatz
# builder (section 4) expects.  Selection rule (unchanged): i ≤ j, with a ≤ b
# when i == j; keep |t2| > 1e-10; virtual indices expressed in absolute orbital
# space [n_alpha, n_spatial).
t2_list = []                                      # [(i, j, a, b, t2_val), …]
for i in range(n_alpha):
    for j in range(i, n_alpha):
        for a in range(n_vir):
            b_start = a if i == j else 0
            for b in range(b_start, n_vir):
                t2_val = float(t2_tensor[i, j, a, b])
                if abs(t2_val) > 1e-10:
                    t2_list.append((i, j, a + n_alpha, b + n_alpha, t2_val))

# Sort by descending |t2|; cap for practical circuit depth
t2_list.sort(key=lambda x: abs(x[4]), reverse=True)
MAX_DOUBLE = min(len(t2_list), 24)
t2_list = t2_list[:MAX_DOUBLE]
print(f"[qsci-prep] MP2 t2 (from contract): {len(t2_list)} channels retained", flush=True)
if t2_list:
    top = t2_list[0]
    print(f"           max |t2| = {abs(top[4]):.6f}  "
          f"({top[0]},{top[1]}) -> ({top[2]},{top[3]})", flush=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  4.  Build LUCJ ansatz in PennyLane → decompose → export via Braket
# ═══════════════════════════════════════════════════════════════════════════════
import pennylane as qml

# ── 4a. HF bitstring (interleaved α-β-α-β-… JW ordering) ────
hf_bits = []
for p in range(n_spatial):
    hf_bits.append(1 if p < n_alpha else 0)
    hf_bits.append(1 if p < n_beta else 0)

# ── 4b. Gate decomposition helpers ───────────────────────────

def _ising_zz(angles, pairs, nq):
    """Generate PennyLane IsingZZ gates."""
    for idx, (i, j) in enumerate(pairs):
        phi = float(angles[idx])
        if abs(phi) > 1e-10:
            qml.IsingZZ(phi, wires=[i, j])

def _single_exc(angles, pairs, nq):
    """Generate PennyLane SingleExcitation gates."""
    for idx, (p, q) in enumerate(pairs):
        th = float(angles[idx])
        if abs(th) > 1e-10:
            qml.SingleExcitation(th, wires=[p, q])

# ── 4c. Collect all gate pairs ────────────────────────────────

# Single-excitation pairs: (occupied_spatial, virtual_spatial) -> qubits
alpha_pairs = []   # [(qubit_p, qubit_q), …]
beta_pairs  = []
for p in range(n_alpha):
    for qq in range(n_alpha, n_spatial):
        alpha_pairs.append((2 * p, 2 * qq))
for p in range(n_beta):
    for qq in range(n_beta, n_spatial):
        beta_pairs.append((2 * p + 1, 2 * qq + 1))

all_single_pairs = alpha_pairs + beta_pairs
n_single = len(all_single_pairs)

# ZZ pairs: (spatial_p, spatial_q) -> αα, ββ, αβ
zz_pairs_aa = []
zz_pairs_bb = []
zz_pairs_ab = []
for p in range(n_spatial):
    for qq in range(p + 1, n_spatial):
        zz_pairs_aa.append((2 * p, 2 * qq))
        zz_pairs_bb.append((2 * p + 1, 2 * qq + 1))
        zz_pairs_ab.append((2 * p, 2 * qq + 1))
n_zz_aa = len(zz_pairs_aa)
n_zz_bb = len(zz_pairs_bb)
n_zz_ab = len(zz_pairs_ab)

# Double-excitation: (i, j) -> (a, b) -> [2*i, 2*j+1, 2*a, 2*b+1] sorted
double_wires = []
for (i, j, a, b, _) in t2_list:
    w = sorted([2 * i, 2 * j + 1, 2 * a, 2 * b + 1])
    if len(set(w)) == 4:
        double_wires.append(w)
    else:
        double_wires.append(None)
n_double = len(t2_list)

# ── 4d. Concrete (numeric) parameters — NO free symbols ───────

import pennylane.numpy as pnp
single_angles   = pnp.zeros(n_single,     dtype=float)   # t1 ≈ 0 (RHF)
z_angles        = pnp.zeros(n_qubits,     dtype=float)   # chemical potential
zz_angles_aa    = pnp.zeros(n_zz_aa,      dtype=float)
zz_angles_bb    = pnp.zeros(n_zz_bb,      dtype=float)
zz_angles_ab    = pnp.zeros(n_zz_ab,      dtype=float)
double_angles   = pnp.zeros(n_double,     dtype=float)

# Bind MP2 t2 -> double excitation angles:  φ = 2 × t2  (UCCSD convention)
for didx, (_, _, _, _, t2_val) in enumerate(t2_list):
    double_angles[didx] = 2.0 * float(t2_val)

# ── 4e. Build PennyLane tape ─────────────────────────────────

print("[qsci-prep] Building PennyLane tape …", flush=True)
with qml.queuing.AnnotatedQueue() as q:
    # HF reference
    qml.BasisState(pnp.array(hf_bits), wires=range(n_qubits))

    # Single excitations (Givens rotations), interleaved α then β
    _single_exc(single_angles, all_single_pairs, n_qubits)

    # Chemical potential RZ
    for i in range(n_qubits):
        z = float(z_angles[i])
        if abs(z) > 1e-10:
            qml.RZ(z, wires=i)

    # Jastrow ZZ
    _ising_zz(zz_angles_aa, zz_pairs_aa, n_qubits)
    _ising_zz(zz_angles_bb, zz_pairs_bb, n_qubits)
    _ising_zz(zz_angles_ab, zz_pairs_ab, n_qubits)

    # Double excitations
    for didx in range(n_double):
        phi = float(double_angles[didx])
        if abs(phi) < 1e-10:
            continue
        w = double_wires[didx]
        if w is None or len(set(w)) != 4:
            continue
        qml.DoubleExcitation(phi, wires=w)

tape = qml.tape.QuantumScript.from_queue(q)
print(f"[qsci-prep] Tape: {len(tape.operations)} high-level ops", flush=True)

# ── 4f. Decompose high-level gates -> primitives ───────────────
# PennyLane's default.qubit device expands SingleExcitation,
# DoubleExcitation, IsingZZ, BasisState into CNOT + RY/RZ/PauliX.

dev = qml.device("default.qubit", wires=n_qubits)

# Attempt decomposition via device expansion (most reliable path).
# Fall back to tape.expand() in case expand_fn was renamed.
try:
    expanded = dev.expand_fn(tape)
except AttributeError:
    expanded = tape.expand(depth=20, stop_at=lambda op: op.name not in {
        "SingleExcitation", "DoubleExcitation", "BasisState", "QubitUnitary"})
    # Re-expand to catch any remaining compound gates
    expanded = expanded.expand(depth=20)

# Unwrap batch if returned
if isinstance(expanded, list):
    expanded = expanded[0]

print(f"[qsci-prep] Expanded: {len(expanded.operations)} primitive ops", flush=True)

# ── 4g. Convert to Braket Circuit & export OpenQASM 3.0 ──────
# PennyLane v0.42.3 does NOT have qml.io.to_openqasm(…).
# Use Braket SDK's native IR export instead.

from braket.circuits import Circuit
from braket.circuits.serialization import IRType

circ = Circuit()

# Gate mapping table  (PennyLane op.name -> Braket method)
for op in expanded.operations:
    name   = op.name
    params = [float(p) for p in op.parameters]
    w      = [int(wi) for wi in op.wires]

    # ── Single-qubit gates ────────────────────────────────────
    if name == "PauliX":
        circ.x(w[0])
    elif name == "PauliY":
        circ.y(w[0])
    elif name == "PauliZ":
        circ.z(w[0])
    elif name == "Hadamard":
        circ.h(w[0])
    elif name == "S":
        circ.s(w[0])
    elif name == "T":
        circ.t(w[0])
    elif name == "RX":
        circ.rx(w[0], params[0])
    elif name == "RY":
        circ.ry(w[0], params[0])
    elif name == "RZ":
        circ.rz(w[0], params[0])
    elif name == "PhaseShift":
        circ.phaseshift(w[0], params[0])

    # ── Two-qubit gates ───────────────────────────────────────
    elif name == "CNOT":
        circ.cnot(w[0], w[1])
    elif name == "CZ":
        circ.cz(w[0], w[1])
    elif name == "SWAP":
        circ.swap(w[0], w[1])

    # ── Skip identity / prep / barrier ───────────────────────
    elif name == "BasisState":
        # BasisState may survive decomposition — apply X to occupied qubits
        bs = op.parameters[0]
        for qq in range(len(bs)):
            if int(bs[qq]) == 1:
                circ.x(qq)
    elif name in ("Identity", "QubitUnitary"):
        pass  # no-op or already prepared
    elif name in ("Barrier", "WireCut"):
        pass

    # ── Unexpected -> warn ─────────────────────────────────────
    else:
        print(f"[qsci-prep] WARNING: unhandled gate '{name}', skipping", flush=True)

# ── Ensure all n_qubits appear in the circuit ──
# PennyLane's BasisState expansion only generates X gates for occupied
# qubits; unoccupied qubits never appear.  This causes Braket to serialise
# a circuit with fewer qubits than the JW encoding actually requires,
# breaking the bitstring width in downstream measurement-count parsing.
# Place an identity on every qubit that has no operations.
touched_qubits = {int(w) for op in expanded.operations for w in op.wires}
for qq in range(n_qubits):
    if qq not in touched_qubits:
        circ.i(qq)

gate_count = sum(1 for _ in circ.instructions)
print(f"[qsci-prep] Braket circuit: {gate_count} instructions", flush=True)

# Safety: check that no high-level gates were skipped (indicates decomp failure)
decomposed_ok = all(
    op.name not in ("SingleExcitation", "DoubleExcitation", "IsingZZ")
    for op in expanded.operations
)
if not decomposed_ok:
    residual = [op.name for op in expanded.operations
                if op.name in ("SingleExcitation", "DoubleExcitation", "IsingZZ")]
    print(f"[qsci-prep] ERROR: gate decomposition failed! Residual gates: {residual}",
          flush=True)
    sys.exit(1)

# Verify: no free parameters
free_params = circ.parameters
if free_params:
    print(f"[qsci-prep] ERROR: {len(free_params)} free parameters found! {free_params}",
          flush=True)
    sys.exit(1)

# Export OpenQASM 3.0
oqs3_prog = circ.to_ir(ir_type=IRType.OPENQASM)
# Braket SDK returns a Program object; extract its source string.
oqs3 = oqs3_prog.source if hasattr(oqs3_prog, "source") else str(oqs3_prog)

with open(f"{OUTPUT_DIR}/ansatz_circuit", "w") as fh:
    fh.write(oqs3)
print(f"[qsci-prep] OpenQASM 3.0 exported: {len(oqs3)} bytes", flush=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  5.  Onboard output: n_qubits
# ═══════════════════════════════════════════════════════════════════════════════
with open(f"{OUTPUT_DIR}/n_qubits", "w") as fh:
    fh.write(str(n_qubits))

print(f"[qsci-prep] Done.", flush=True)
