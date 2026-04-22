#!/usr/bin/env bash
# orca-casci/profile/run.sh — CASCI 单点能量计算
set -euo pipefail
# MF2 init

mf_banner "orca-casci" "CASCI single-point energy calculation"

echo "[orca-casci] CASCI/${basis_set} ActiveSpace(${active_electrons}e,${active_orbitals}o) Charge=${charge} Mult=${multiplicity} Cores=${n_cores}"

# ── 读取 stream input: xyz_geometry ──────────────────────────────────────────
XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[orca-casci][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"
echo "[orca-casci] Loaded input geometry: $(wc -l < "${WORKDIR}/input.xyz") lines"

# ── 生成 ORCA 输入文件（标准库 string.Template 渲染）─────────────────────────
python3 << PYEOF
from string import Template
tmpl = Template(open('/mf/profile/input.orca.template').read())
result = tmpl.substitute(
    basis_set='${basis_set}',
    active_electrons='${active_electrons}',
    active_orbitals='${active_orbitals}',
    n_cores='${n_cores}',
    charge='${charge}',
    multiplicity='${multiplicity}',
)
with open('${WORKDIR}/input.inp', 'w') as f:
    f.write(result)
PYEOF

echo "[orca-casci] Generated input.inp:"
cat "${WORKDIR}/input.inp"

# ── 运行 ORCA ─────────────────────────────────────────────────────────────────
cd "$WORKDIR"
echo "[orca-casci] Running ORCA..."
/opt/orca/orca input.inp > output.log 2>&1
echo "[orca-casci] ORCA finished. Parsing output..."

# ── 解析输出 ──────────────────────────────────────────────────────────────────
ENERGY=$(grep "FINAL SINGLE POINT ENERGY" output.log | tail -1 | awk '{print $NF}' || echo "")
if [[ -z "$ENERGY" ]]; then
    echo "[orca-casci][ERROR] Could not extract energy from output!" >&2
    cat output.log >&2
    exit 1
fi

CONVERGED="true"
if grep -q "SCF NOT CONVERGED" output.log; then
    CONVERGED="false"
    echo "[orca-casci][WARN] SCF DID NOT CONVERGE!"
fi

SCF_ITER=$(grep "SCF CONVERGED AFTER" output.log | tail -1 | awk '{print $4}' || echo "0")
echo "[orca-casci] Energy=${ENERGY} Ha  Converged=${CONVERGED}  SCF_iter=${SCF_ITER}"

# ── 提取 Mulliken 电荷 ────────────────────────────────────────────────────────
python3 /mf/profile/postprocess.py

# ── 写入输出 ──────────────────────────────────────────────────────────────────
echo "${ENERGY}"      > "${OUTPUT_DIR}/total_energy"
echo "${CONVERGED}"   > "${OUTPUT_DIR}/scf_converged"
echo "${ENERGY}"      > "${OUTPUT_DIR}/scf_energy"
echo "${SCF_ITER:-0}" > "${OUTPUT_DIR}/scf_iterations"

GBW_FILE="${WORKDIR}/input.gbw"
if [[ -f "$GBW_FILE" ]]; then
    cp "$GBW_FILE" "${OUTPUT_DIR}/gbw_file"
else
    echo "[orca-casci][WARN] GBW file not found: ${GBW_FILE}" >&2
    echo "NO_GBW" > "${OUTPUT_DIR}/gbw_file"
fi

echo "[orca-casci] Done."
