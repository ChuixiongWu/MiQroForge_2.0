#!/bin/sh
# =============================================================================
# diverging-geo-opt mock run.sh
#
# Simulates a geometry optimization that FAILS TO CONVERGE.
# Always writes converged=false to the quality gate output.
# Downstream tasks protected by must_pass will be skipped by Argo.
# =============================================================================
set -e

OUTPUT_DIR="/mf/output"
INPUT_DIR="/mf/input"
mkdir -p "$OUTPUT_DIR"

echo "[diverging-geo-opt] Starting mock geometry optimization (will diverge)..."

# Read on-board parameters
FUNCTIONAL=$(cat "$INPUT_DIR/functional" 2>/dev/null || echo "B3LYP")
BASIS_SET=$(cat "$INPUT_DIR/basis_set" 2>/dev/null || echo "6-31G*")
CHARGE=$(cat "$INPUT_DIR/charge" 2>/dev/null || echo "0")
MULTIPLICITY=$(cat "$INPUT_DIR/multiplicity" 2>/dev/null || echo "1")

echo "[diverging-geo-opt] functional=$FUNCTIONAL basis_set=$BASIS_SET charge=$CHARGE multiplicity=$MULTIPLICITY"
echo "[diverging-geo-opt] Simulating 200 optimization steps with no convergence..."

# Stream outputs — partial / unreliable data from a non-converged run
echo "MOCK_PARTIAL_CHECKPOINT_DIVERGED_${FUNCTIONAL}_${BASIS_SET}" > "$OUTPUT_DIR/optimized_checkpoint"
echo "-75.9912345" > "$OUTPUT_DIR/total_energy"

# On-board outputs
echo "-75.9912345" > "$OUTPUT_DIR/final_energy"
echo "200" > "$OUTPUT_DIR/n_iterations"

# ── Quality gate: converged = false ──────────────────────────────────────────
# This is the key output. Argo reads _qg_converged from /mf/output/converged.
# Because gate_default=must_pass, downstream tasks will be skipped.
echo "false" > "$OUTPUT_DIR/converged"

echo "[diverging-geo-opt] DONE. converged=false — downstream tasks should be blocked."
