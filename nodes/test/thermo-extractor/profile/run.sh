#!/bin/sh
# =============================================================================
# thermo-extractor mock run.sh
#
# Reads thermo data, does Ha→eV conversion, writes outputs.
# Note: is_minimum is no longer a stream input — it is derived from thermo
# data (n_imaginary == 0). In this mock, we hardcode is_minimum=true.
# =============================================================================
set -e

OUTPUT_DIR="/mf/output"
INPUT_DIR="/mf/input"
mkdir -p "$OUTPUT_DIR"

echo "[thermo-extractor] Starting mock thermochemistry extraction..."

# Read stream inputs
THERMO_DATA=$(cat "$INPUT_DIR/thermo_data_in" 2>/dev/null || echo '{}')
ENERGY_UNIT=$(cat "$INPUT_DIR/energy_unit" 2>/dev/null || echo "Ha")

# is_minimum derived from thermo data (mock: hardcode true)
IS_MINIMUM="true"

echo "[thermo-extractor] is_minimum=$IS_MINIMUM energy_unit=$ENERGY_UNIT"
echo "[thermo-extractor] thermo_data=$THERMO_DATA"

# Ha → eV conversion factor (CODATA 2018)
# 1 Ha = 27.211386245988 eV
HA_TO_EV="27.211386245988"

# Extract values (simple parsing from JSON-like string)
# gibbs_ha = -76.368043, enthalpy_ha = -76.367099
GIBBS_HA="-76.368043"
ENTHALPY_HA="-76.367099"

# Use awk for floating point arithmetic (busybox compatible)
GIBBS_EV=$(echo "$GIBBS_HA $HA_TO_EV" | awk '{printf "%.6f", $1 * $2}')
ENTHALPY_EV=$(echo "$ENTHALPY_HA $HA_TO_EV" | awk '{printf "%.6f", $1 * $2}')

echo "[thermo-extractor] Gibbs = $GIBBS_EV eV, Enthalpy = $ENTHALPY_EV eV"

# Stream outputs
# gibbs_ev — PhysicalQuantity (eV)
echo "$GIBBS_EV" > "$OUTPUT_DIR/gibbs_ev"

# summary — ReportObject (JSON)
cat > "$OUTPUT_DIR/summary" << SUMMARY_EOF
{"gibbs_ev": $GIBBS_EV, "enthalpy_ev": $ENTHALPY_EV, "is_minimum": $IS_MINIMUM, "energy_unit": "$ENERGY_UNIT"}
SUMMARY_EOF

# On-board outputs
echo "$GIBBS_EV" > "$OUTPUT_DIR/gibbs_converted"
echo "$IS_MINIMUM" > "$OUTPUT_DIR/is_valid_minimum"

echo "[thermo-extractor] Done."
