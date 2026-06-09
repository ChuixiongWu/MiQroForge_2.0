#!/usr/bin/env bash
# =============================================================================
# chem-prep — RHF Mean-Field Preparation for Quantum Embedding
#
# Reads an optimized XYZ geometry (stream input), validates multiplicity=1,
# runs PySCF RHF, and writes the converged mean-field data as HDF5.
# =============================================================================
set -euo pipefail

# ── MF2 runtime bootstrap ────────────────────────────────────────────────────
# compiler injects: source /mf/profile/mf2_init.sh
source /mf/profile/mf2_init.sh

mf_banner "chem-prep" "RHF mean-field preparation for quantum embedding"

# ── Read onboard parameters ──────────────────────────────────────────────────
CHARGE=$(mf_param charge 0)
MULTIPLICITY=$(mf_param multiplicity 1)
BASIS=$(mf_param basis_set sto-3g)

echo "[chem-prep] charge       = ${CHARGE}"
echo "[chem-prep] multiplicity = ${MULTIPLICITY}"
echo "[chem-prep] basis        = ${BASIS}"

# ── Validate multiplicity (RHF only) ────────────────────────────────────────
if [[ "${MULTIPLICITY}" -ne 1 ]]; then
    echo "[chem-prep][ERR] multiplicity=${MULTIPLICITY} is not supported." >&2
    echo "[chem-prep][ERR] This node only supports RHF (multiplicity=1)." >&2
    exit 1
fi

# ── Read XYZ geometry from stream input ──────────────────────────────────────
XYZ_CONTENT=$(cat "${INPUT_DIR}/xyz_geometry")
mf_write_xyz "${XYZ_CONTENT}" "chem-prep"

# ── Run PySCF RHF + write HDF5 mean-field package ────────────────────────────
python3 << PYEOF
import os
import sys

import numpy as np
import h5py
from pyscf import gto, scf

workdir = "${WORKDIR}"
output_dir = "${OUTPUT_DIR}"
basis = "${BASIS}"
charge = ${CHARGE}

# ── Parse XYZ → PySCF atom string ────────────────────────────────────────
with open(os.path.join(workdir, "input.xyz")) as fh:
    lines = fh.readlines()

# Skip header lines 1 (natoms) and 2 (comment); keep coordinate lines
atom_lines = [ln.strip() for ln in lines[2:] if ln.strip()]
atom_str = "; ".join(atom_lines)
atom_label = atom_str[:200]

print(f"[chem-prep] Building molecule: {len(atom_lines)} atoms, "
      f"basis={basis}, charge={charge}")

# ── Build molecule ────────────────────────────────────────────────────────
mol = gto.M(
    atom=atom_str,
    basis=basis,
    charge=charge,
    spin=0,          # singlet → RHF
    verbose=4,
)

# ── Run RHF ───────────────────────────────────────────────────────────────
mf = scf.RHF(mol)
e_tot = mf.kernel()
converged = bool(mf.converged)

# ── Extract mean-field tensors ────────────────────────────────────────────
mo_coeff = np.asarray(mf.mo_coeff, dtype=np.float64)
mo_energy = np.asarray(mf.mo_energy, dtype=np.float64)
mo_occ = np.asarray(mf.mo_occ, dtype=np.float64)

nao, nmo = mo_coeff.shape

# ── Write native PySCF chkfile (meanfield_package) ───────────────────────
# Uses PySCF canonical API so downstream (ewf-decompose) can load with
# pyscf.lib.chkfile.load / pyscf.scf.chkfile.load_scf.
import pyscf.scf.chkfile as chkfile_mod
output_path = os.path.join(output_dir, "meanfield_package")
chkfile_mod.dump_scf(mol, output_path, e_tot, mo_energy, mo_coeff, mo_occ)
# Also stash metadata inside the chkfile for human inspection (does not
# interfere with the canonical mol/scf groups).
with h5py.File(output_path, "a") as f:
    f.create_dataset("meta/source", data=np.bytes_("pyscf-rhf"))
    f.create_dataset("meta/basis", data=np.bytes_(basis))
    f.create_dataset("meta/molecule", data=np.bytes_(atom_label))
    f.create_dataset("meta/nao", data=np.int64(nao))
    f.create_dataset("meta/nmo", data=np.int64(nmo))

print(f"[chem-prep] Native PySCF chkfile written to {output_path}")

# ── Quality gate output ───────────────────────────────────────────────────
gate_path = os.path.join(output_dir, "scf_converged")
with open(gate_path, "w") as fh:
    fh.write("true" if converged else "false")

print(f"[chem-prep] RHF e_tot = {e_tot:.10f} Ha")
print(f"[chem-prep] SCF converged: {converged}  (gate → {gate_path})")
print(f"[chem-prep] Basis dimensions: nao={nao}, nmo={nmo}")
print(f"[chem-prep] HDF5 size: {os.path.getsize(output_path):,} bytes")
PYEOF

echo ""
echo "[chem-prep] Done."
