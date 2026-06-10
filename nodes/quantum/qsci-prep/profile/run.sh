#!/usr/bin/env bash
# qsci-prep/profile/run.sh — QSCI state preparation
#   Load cluster Hamiltonian → JW qubit Hamiltonian → LUCJ ansatz → OpenQASM 3.0
#
# Dependencies: quantum-exec-0.1 image
#   (openfermion, pennylane==0.42.3, amazon-braket-sdk==1.110.1,
#    amazon-braket-pennylane-plugin==1.33.7, numpy, scipy, h5py)
set -euo pipefail
source /mf/profile/mf2_init.sh

mf_banner "qsci-prep" "QSCI state preparation"

export MF_INPUT_DIR="${INPUT_DIR}"
export MF_OUTPUT_DIR="${OUTPUT_DIR}"

python3 /mf/profile/main.py

echo "[qsci-prep] run.sh finished."
