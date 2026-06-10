#!/usr/bin/env bash
# ewf-decompose/profile/run.sh — Vayesta EWF single-fragment cluster Hamiltonian
#
# Flow:
#   1. Validate onboard params (active_atoms required)
#   2. Validate stream input (meanfield_package)
#   3. Delegate the Vayesta EWF computation to profile/main.py
#
# Shell/Python separation:
#   - run.sh   : bootstrap, onboard-param validation, enum validation
#   - main.py  : Vayesta EWF + cluster Hamiltonian HDF5 (reads MF_* env vars)
set -euo pipefail
source /mf/profile/mf2_init.sh

mf_banner "ewf-decompose" "Vayesta EWF single-fragment cluster Hamiltonian extraction"

# ── Validate required onboard params ──────────────────────────────────────────
if [[ -z "${active_atoms:-}" ]]; then
    echo "[ewf-decompose][ERROR] Onboard parameter 'active_atoms' is required" >&2
    exit 1
fi

# ── Validate stream input ─────────────────────────────────────────────────────
MEANFIELD_PATH="${INPUT_DIR}/meanfield_package"
if [[ ! -f "${MEANFIELD_PATH}" ]]; then
    echo "[ewf-decompose][ERROR] Stream input 'meanfield_package' not found at ${MEANFIELD_PATH}" >&2
    exit 1
fi

BATH_THRESHOLD="${bath_threshold:-1.0e-6}"
BATH_TYPE="${bathtype:-mp2}"
FRAGMENTATION="${fragmentation:-iao}"
ORBITAL_FILTER="${orbital_filter:-}"

echo "[ewf-decompose] active_atoms=${active_atoms}"
echo "[ewf-decompose] bath_threshold=${BATH_THRESHOLD}"
echo "[ewf-decompose] bathtype=${BATH_TYPE}"
echo "[ewf-decompose] fragmentation=${FRAGMENTATION}"
echo "[ewf-decompose] orbital_filter=${ORBITAL_FILTER:-<none>}"

# ── Validate bathtype enum ────────────────────────────────────────────────────
case "${BATH_TYPE}" in
    mp2|dmet|full) ;;
    *)
        echo "[ewf-decompose][ERROR] Invalid bathtype='${BATH_TYPE}'. Must be one of: mp2, dmet, full" >&2
        exit 1
        ;;
esac

# ── Validate fragmentation enum ──────────────────────────────────────────────
case "${FRAGMENTATION}" in
    iao|iaopao|sao) ;;
    *)
        echo "[ewf-decompose][ERROR] Invalid fragmentation='${FRAGMENTATION}'. Must be one of: iao, iaopao, sao" >&2
        exit 1
        ;;
esac

# ── Run EWF decompose (Python) ────────────────────────────────────────────────
export MF_WORKDIR="${WORKDIR}"
export MF_INPUT_DIR="${INPUT_DIR}"
export MF_OUTPUT_DIR="${OUTPUT_DIR}"
export MF_MEANFIELD_PATH="${MEANFIELD_PATH}"
export MF_ACTIVE_ATOMS="${active_atoms}"
export MF_BATH_THRESHOLD="${BATH_THRESHOLD}"
export MF_BATHTYPE="${BATH_TYPE}"
export MF_FRAGMENTATION="${FRAGMENTATION}"
export MF_ORBITAL_FILTER="${ORBITAL_FILTER}"

python3 /mf/profile/main.py

echo "[ewf-decompose] Complete."
