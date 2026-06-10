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

# ── Run PySCF RHF + write HDF5 mean-field package (Python) ───────────────────
export MF_CHARGE="${CHARGE}"
export MF_BASIS="${BASIS}"
export MF_WORKDIR="${WORKDIR}"
export MF_OUTPUT_DIR="${OUTPUT_DIR}"

python3 /mf/profile/main.py

echo ""
echo "[chem-prep] Done."
