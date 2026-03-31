#!/bin/sh
# =============================================================================
# gaussian-geo-opt mock run.sh
#
# Reads on-board params from /mf/input/, writes mock outputs to /mf/output/.
# Uses busybox — no external dependencies.
# =============================================================================
set -e

OUTPUT_DIR="/mf/output"
INPUT_DIR="/mf/input"
mkdir -p "$OUTPUT_DIR"

echo "[geo-opt] Starting mock geometry optimization..."

# Read on-board parameters (passed as files by Argo)
FUNCTIONAL=$(cat "$INPUT_DIR/functional" 2>/dev/null || echo "B3LYP")
BASIS_SET=$(cat "$INPUT_DIR/basis_set" 2>/dev/null || echo "6-31G*")
CHARGE=$(cat "$INPUT_DIR/charge" 2>/dev/null || echo "0")
MULTIPLICITY=$(cat "$INPUT_DIR/multiplicity" 2>/dev/null || echo "1")

echo "[geo-opt] functional=$FUNCTIONAL basis_set=$BASIS_SET charge=$CHARGE multiplicity=$MULTIPLICITY"

# Mock outputs
# total_energy — PhysicalQuantity (Ha)
echo "-76.3908154" > "$OUTPUT_DIR/total_energy"

# converged — LogicValue (boolean)
echo "true" > "$OUTPUT_DIR/converged"

# optimized_checkpoint — SoftwareDataPackage (gaussian/checkpoint)
echo "MOCK_GAUSSIAN_CHECKPOINT_DATA_H2O_${FUNCTIONAL}_${BASIS_SET}" > "$OUTPUT_DIR/optimized_checkpoint"

# On-board outputs
echo "-76.3908154" > "$OUTPUT_DIR/final_energy"
echo "12" > "$OUTPUT_DIR/n_iterations"

echo "[geo-opt] Done. Energy = -76.3908154 Ha, converged = true"
