#!/bin/sh
# =============================================================================
# gaussian-freq mock run.sh
#
# Reads checkpoint + on-board params, writes mock frequency/thermo outputs.
# Note: opt_converged is no longer a stream input — convergence is a quality
# gate on the upstream geo-opt node (onboard output).
# =============================================================================
set -e

OUTPUT_DIR="/mf/output"
INPUT_DIR="/mf/input"
mkdir -p "$OUTPUT_DIR"

echo "[freq] Starting mock frequency analysis..."

# Read stream inputs
CHECKPOINT=$(cat "$INPUT_DIR/checkpoint_in" 2>/dev/null || echo "NO_CHECKPOINT")
TEMPERATURE=$(cat "$INPUT_DIR/temperature" 2>/dev/null || echo "298.15")

echo "[freq] checkpoint=$CHECKPOINT temperature=$TEMPERATURE"

# Mock outputs
# thermo_data — SoftwareDataPackage (gaussian/thermo-data)
cat > "$OUTPUT_DIR/thermo_data" << 'THERMO_EOF'
{"zpe_ha": 0.020772, "gibbs_ha": -76.368043, "enthalpy_ha": -76.367099, "n_imaginary": 0}
THERMO_EOF

# zpe — PhysicalQuantity (Ha)
echo "0.020772" > "$OUTPUT_DIR/zpe"

# On-board outputs
echo "0" > "$OUTPUT_DIR/n_imaginary"
echo "-76.368043" > "$OUTPUT_DIR/gibbs_energy"
echo "-76.367099" > "$OUTPUT_DIR/enthalpy"

# is_true_minimum — quality gate (onboard output, written to /mf/output/)
echo "true" > "$OUTPUT_DIR/is_true_minimum"

echo "[freq] Done. ZPE=0.020772 Ha, Gibbs=-76.368043 Ha, 0 imaginary freq"
