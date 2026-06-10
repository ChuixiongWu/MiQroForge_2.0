#!/usr/bin/env bash
# hardware-execute/profile/run.sh — AWS Braket circuit execution
#
# Shell/Python separation:
#   - run.sh   : bootstrap, stream-input validation
#   - main.py  : Braket backend selection + execution (reads MF_* env vars)
set -euo pipefail
source /mf/profile/mf2_init.sh

mf_banner "hardware-execute" "AWS Braket circuit execution"

# ── Read OQ3 circuit from stream input ────────────────────────────────────────
OQ3_FILE="${INPUT_DIR}/ansatz_circuit"
if [[ ! -f "$OQ3_FILE" ]]; then
    echo "[hardware-execute][ERROR] Stream input 'ansatz_circuit' not found at ${OQ3_FILE}" >&2
    exit 1
fi
echo "[hardware-execute] Loaded OQ3 circuit: $(wc -c < "$OQ3_FILE") bytes"

# ── Run Braket execution (Python) ─────────────────────────────────────────────
export MF_BACKEND="$backend"
export MF_N_SHOTS="$n_shots"
export MF_OQ3_FILE="$OQ3_FILE"
export MF_OUTPUT_DIR="$OUTPUT_DIR"

echo "[hardware-execute] Backend=${backend}  Shots=${n_shots}"

python3 /mf/profile/main.py

echo "[hardware-execute] Complete."
