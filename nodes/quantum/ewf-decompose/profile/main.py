#!/usr/bin/env python3
"""ewf-decompose — Vayesta EWF single-fragment cluster Hamiltonian extraction.

Reads the PySCF RHF mean-field chkfile (MF_MEANFIELD_PATH) and the onboard
parameters (MF_ACTIVE_ATOMS / MF_BATH_THRESHOLD / MF_BATHTYPE /
MF_FRAGMENTATION / MF_ORBITAL_FILTER) from the environment, runs Vayesta EWF
with a single fragment, and writes the T6 cluster Hamiltonian HDF5
(vayesta/cluster-hamiltonian-h5) plus e_mf and n_active_orbitals.
"""
import os, sys
import numpy as np
import h5py

from pyscf import gto, scf
import pyscf.scf.chkfile as chkfile_mod
import vayesta.ewf

workdir = os.environ.get("MF_WORKDIR", "/mf/workdir")
input_dir = os.environ.get("MF_INPUT_DIR", "/mf/input")
output_dir = os.environ.get("MF_OUTPUT_DIR", "/mf/output")
meanfield_path = os.environ["MF_MEANFIELD_PATH"]

# ── Parse onboard params ──────────────────────────────────────────────────────
# active_atoms is comma-separated (e.g. "0,4"); tolerate surrounding whitespace.
active_atoms_str = os.environ.get("MF_ACTIVE_ATOMS", "")
active_atoms = [int(x.strip()) for x in active_atoms_str.replace(' ', ',').split(',') if x.strip()]
bath_threshold = float(os.environ["MF_BATH_THRESHOLD"])
bathtype = os.environ["MF_BATHTYPE"]
fragmentation = os.environ["MF_FRAGMENTATION"]
orbital_filter_raw = os.environ.get("MF_ORBITAL_FILTER", "").strip()
# Comma-separated IAO orbital-type tokens (e.g. "2p", "2s,2p", "N 2p,C 2p").
# Each token is regex-matched by Vayesta against IAO labels "<atom> <sym> <nl> <ml>".
if orbital_filter_raw:
    orbital_filter = [tok.strip() for tok in orbital_filter_raw.split(',') if tok.strip()]
else:
    orbital_filter = None

if not active_atoms:
    print("[ewf-decompose][ERROR] active_atoms is empty after parsing", file=sys.stderr)
    sys.exit(1)

# Deduplicate active_atoms while preserving order
seen = set()
deduped = []
for idx in active_atoms:
    if idx not in seen:
        seen.add(idx)
        deduped.append(idx)
active_atoms = deduped

# ── Load mean-field from native PySCF chkfile ─────────────────────────────────
print(f"[ewf-decompose] Loading mean-field from {meanfield_path}", file=sys.stderr)

try:
    mol_rec, scf_rec = chkfile_mod.load_scf(meanfield_path)
except Exception:
    print("[ewf-decompose][ERROR] Failed to load mean-field chkfile "
          "(does the file have native PySCF mol/scf groups?)", file=sys.stderr)
    sys.exit(1)

# load_scf returns (Mole instance, scf dict).  The Mole may need a fresh
# build round-trip depending on serialisation fidelity; call mol.build()
# again so that integral grids are freshly generated.
mol = mol_rec
mol.build()

natm = mol.natm
formula_str = "".join(mol.atom_pure_symbol(i) for i in range(natm))
print(f"[ewf-decompose] Molecule: {formula_str}, basis={mol.basis}, natm={natm}, "
      f"nelec={mol.nelectron}", file=sys.stderr)

# ── Validate active_atoms against molecule ────────────────────────────────────
for i, idx in enumerate(active_atoms):
    if idx < 0 or idx >= natm:
        print(f"[ewf-decompose][ERROR] active_atoms[{i}]={idx} is out of range "
              f"[0, {natm - 1}] for molecule with {natm} atoms", file=sys.stderr)
        sys.exit(1)

# ── Rebuild RHF mean-field ────────────────────────────────────────────────────
mf = scf.RHF(mol)
mf.__dict__.update(scf_rec)
mf.converged = True

e_mf = float(mf.e_tot)
print(f"[ewf-decompose] E(MF) = {e_mf:.10f} Ha", file=sys.stderr)

# ── Build bath_options from bathtype enum ─────────────────────────────────────
# mp2:  MP2 bath natural orbitals (default Vayesta behaviour)
# dmet: DMET bath only (no MP2 expansion)
# full: No bath truncation (all environment orbitals included)
if bathtype == 'mp2':
    bath_opts = dict(threshold=bath_threshold)
elif bathtype == 'dmet':
    bath_opts = dict(bathtype='dmet')
else:  # full
    bath_opts = dict(bathtype=None)

# ── Run Vayesta EWF with single fragment ──────────────────────────────────────
print(f"[ewf-decompose] Setting up Vayesta EWF "
      f"(fragmentation={fragmentation}, bathtype={bathtype}, "
      f"eta={bath_threshold})...", file=sys.stderr)

emb = vayesta.ewf.EWF(
    mf,
    solver='DUMP',
    bath_options=bath_opts,
)

# Select fragmentation method based on onboard param
frag_methods = {
    'iao': emb.iao_fragmentation,
    'iaopao': emb.iaopao_fragmentation,
    'sao': emb.sao_fragmentation,
}
frag_fn = frag_methods[fragmentation]

with frag_fn() as f:
    # Single fragment containing ALL active_atoms (not one per atom)
    f.add_atomic_fragment(active_atoms, orbital_filter=orbital_filter)

emb.kernel()
print("[ewf-decompose] Vayesta EWF embedding complete", file=sys.stderr)

# ── Read dumped cluster Hamiltonian ───────────────────────────────────────────
dump_file = os.path.join(workdir, 'clusters.h5')
if not os.path.exists(dump_file):
    print(f"[ewf-decompose][ERROR] Dump file not found: {dump_file}", file=sys.stderr)
    sys.exit(1)

with h5py.File(dump_file, 'r') as f:
    frag_keys = list(f.keys())
    if not frag_keys:
        print("[ewf-decompose][ERROR] No fragment groups in dump file", file=sys.stderr)
        sys.exit(1)

    # Exactly one fragment expected — fail loudly if not
    if len(frag_keys) != 1:
        print(f"[ewf-decompose][ERROR] Expected exactly 1 fragment, "
              f"found {len(frag_keys)}: {frag_keys}. "
              f"active_atoms={active_atoms} should produce a single fragment.", file=sys.stderr)
        sys.exit(1)

    frag = f[frag_keys[0]]
    heff_cluster = frag['heff'][:]    # (norb, norb) — 1-body effective Hamiltonian
    eris_chem = frag['eris'][:]       # (norb,norb,norb,norb) — chemist (ij|kl)
    norb = heff_cluster.shape[0]

    # ── Read electron count from Vayesta fragment metadata ──
    nocc = int(frag.attrs.get("nocc", 0))
    if nocc <= 0:
        print("[ewf-decompose][ERROR] Fragment attrs missing nocc "
              "(occupied cluster orbitals)", file=sys.stderr)
        sys.exit(1)
    n_elec = 2 * nocc   # RHF: closed-shell fragment
    print(f"[ewf-decompose] Fragment nocc={nocc} → n_elec={n_elec} "
          f"(RHF, closed-shell)", file=sys.stderr)

print(f"[ewf-decompose] Cluster norb={norb}, heff shape={heff_cluster.shape}, "
      f"eris shape={eris_chem.shape}", file=sys.stderr)

# ── Convert eris: chemist (ij|kl) → physicist <pq|rs> ─────────────────────────
# Physicist:  <pq|rs> = ∫ φ_p*(r1)φ_q(r1) (1/r12) φ_r*(r2)φ_s(r2) dr1 dr2
# Chemist:    (pq|rs) = ∫ φ_p*(r1)φ_q(r1) (1/r12) φ_r*(r2)φ_s(r2) dr1 dr2
# Mapping:    <pq|rs> = (pr|qs)  →  eris_phys[p,q,r,s] = eris_chem[p,r,q,s]
eris_phys = eris_chem.transpose(0, 2, 1, 3).copy()

# ── Core energy ───────────────────────────────────────────────────────────────
e_core = np.float64(mol.energy_nuc())

# ── Canonical cluster MOs + MP2 t2 seed (consumed by qsci-prep) ───────────────
# The cluster heff/eris are in the Vayesta embedding basis (heff non-diagonal).
# Build the cluster Fock operator, diagonalize to canonical cluster MOs, transform
# the 2e integrals with a BLAS-backed numpy einsum (O(norb^5)), and form
# closed-shell MP2 t2 amplitudes.  Precomputing the seed here (classical-chem
# image) lets the quantum-exec qsci-prep node skip PySCF and the old O(norb^8)
# hand-rolled transform.
n_occ = nocc
# Fock: F_pq = heff_pq + Σ_k [2<pk|qk> − <pk|kq>], k ∈ occ   (eris is physicist <pq|rs>)
fock = heff_cluster.copy()
for k in range(n_occ):
    fock += 2.0 * eris_phys[:, k, :, k] - eris_phys[:, k, k, :]
eps_full, C = np.linalg.eigh(fock)
order = np.argsort(eps_full)
eps_mo = eps_full[order]
C_mo = C[:, order]                       # cluster-basis → canonical-MO transform

# Cluster→canonical 4-index transform of the physicist integrals, O(norb^5) via
# numpy's BLAS-backed einsum (optimize=True stages the contraction).  Every index
# p,q,r,s is rotated by C_mo, so physicist <pq|rs> maps directly to <ij|kl>.
eris_mo_phys = np.einsum('pi,qj,rk,sl,pqrs->ijkl',
                         C_mo, C_mo, C_mo, C_mo, eris_phys, optimize=True)

# Closed-shell MP2: t2[i,j,a,b] = −<ij||ab> / (ε_a+ε_b−ε_i−ε_j), i,j∈occ, a,b∈virt
o = slice(0, n_occ)
v = slice(n_occ, norb)
g_oovv = eris_mo_phys[o, o, v, v]                       # <ij|ab>
g_as = g_oovv - g_oovv.transpose(0, 1, 3, 2)           # <ij||ab>
eps_o = eps_mo[:n_occ]
eps_v = eps_mo[n_occ:]
denom = (eps_v[None, None, :, None] + eps_v[None, None, None, :]
         - eps_o[:, None, None, None] - eps_o[None, :, None, None])
denom_safe = np.where(np.abs(denom) < 1e-12, np.inf, denom)   # near-degenerate → 0
t2_amps = (-g_as / denom_safe).astype(np.float64)
print(f"[ewf-decompose] MP2 t2 seed: shape={t2_amps.shape}, "
      f"max|t2|={(np.abs(t2_amps).max() if t2_amps.size else 0.0):.6f}", file=sys.stderr)

# ── Write T6 cluster Hamiltonian HDF5 ─────────────────────────────────────────
# Following the vayesta/cluster-hamiltonian-h5 contract (cluster_contract.py)
mol_id = f"{formula_str}_{mol.basis}"
output_path = os.path.join(output_dir, 'cluster_hamiltonian')

with h5py.File(output_path, 'w') as f:
    f.create_dataset('cluster/heff',   data=heff_cluster)
    f.create_dataset('cluster/eris',   data=eris_phys)
    f.create_dataset('cluster/e_core', data=e_core)
    f.create_dataset('meta/norb',      data=np.int64(norb))
    f.create_dataset('meta/n_elec',    data=np.int64(n_elec))
    f.create_dataset('cluster/t2_amps', data=t2_amps)
    f.create_dataset('cluster/eps_mo',  data=eps_mo.astype(np.float64))
    f.create_dataset('cluster/C_mo',    data=C_mo.astype(np.float64))
    f.create_dataset('meta/source',    data=np.bytes_('vayesta'))
    f.create_dataset('meta/molecule',  data=np.bytes_(mol_id))

print(f"[ewf-decompose] Cluster Hamiltonian written to {output_path}", file=sys.stderr)

# ── Write stream output: e_mf ─────────────────────────────────────────────────
with open(os.path.join(output_dir, 'e_mf'), 'w') as f:
    f.write(str(e_mf))

# ── Write onboard output: n_active_orbitals ───────────────────────────────────
with open(os.path.join(output_dir, 'n_active_orbitals'), 'w') as f:
    f.write(str(norb))

print(f"[ewf-decompose] Done. e_mf={e_mf:.10f} Ha, n_active_orbitals={norb}",
      file=sys.stderr)
