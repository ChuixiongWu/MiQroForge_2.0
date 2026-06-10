#!/usr/bin/env bash
# =============================================================================
# qsci-assemble — QSCI Subspace Diagonalisation & Energy Assembly
#
# Reads measurement outcome counts (JSON), the qubit Hamiltonian (JSON),
# and the mean-field energy e_mf.  Runs sparse QSCI subspace diagonalisation
# using Slater-Condon rules (no dense 2^n matrix) and assembles the total
# embedded energy.
#
# Key formula:
#   E_total = e_mf + (E_qsci - e_core_baseline)
# where E_qsci is the lowest eigenvalue of the subspace Hamiltonian H_S and
# e_core_baseline is ⟨HF|H_qubit|HF⟩ (the cluster core baseline that is
# already counted in e_mf, avoiding double-counting).
# =============================================================================
set -euo pipefail

# ── MF2 runtime bootstrap ────────────────────────────────────────────────────
source /mf/profile/mf2_init.sh

mf_banner "qsci-assemble" "QSCI subspace diagonalisation & energy assembly"

# ── Read onboard parameters ──────────────────────────────────────────────────
K=$(mf_param K 100)

echo "[qsci-assemble] K                       = ${K}"

# ── Run QSCI pipeline in Python ──────────────────────────────────────────────
export MF_K="${K}"
export MF_INPUT_DIR="${INPUT_DIR}"
export MF_OUTPUT_DIR="${OUTPUT_DIR}"

python3 /mf/profile/main.py

echo ""
echo "[qsci-assemble] QSCI subspace assembly complete."
