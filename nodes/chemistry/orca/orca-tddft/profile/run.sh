#!/usr/bin/env bash
# orca-tddft/profile/run.sh — TD-DFT 激发态计算
set -euo pipefail
# MF2 init

mf_banner "orca-tddft" "TD-DFT excited-state calculation"

# ── 映射 dispersion 关键字 ───────────────────────────────────────────────────
disp_kw=""
if [[ "${dispersion}" == "D3" ]]; then
    disp_kw="D3 "
elif [[ "${dispersion}" == "D3BJ" ]]; then
    disp_kw="D3BJ "
elif [[ "${dispersion}" == "D4" ]]; then
    disp_kw="D4 "
fi

echo "[orca-tddft] Functional=${functional}/${basis_set} Disp=${dispersion} States=${n_states} Charge=${charge} Mult=${multiplicity} Cores=${n_cores}"

# ── 读取 stream input: xyz_geometry ──────────────────────────────────────────
XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[orca-tddft][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"
echo "[orca-tddft] Loaded input geometry: $(wc -l < "${WORKDIR}/input.xyz") lines"

# ── 生成 ORCA 输入文件（标准库 string.Template 渲染）─────────────────────────
python3 << PYEOF
from string import Template
tmpl = Template(open('/mf/profile/input.orca.template').read())
result = tmpl.substitute(
    functional='${functional}',
    basis_set='${basis_set}',
    disp_kw='${disp_kw}',
    n_states='${n_states}',
    n_cores='${n_cores}',
    charge='${charge}',
    multiplicity='${multiplicity}',
)
with open('${WORKDIR}/input.inp', 'w') as f:
    f.write(result)
PYEOF

echo "[orca-tddft] Generated input.inp:"
cat "${WORKDIR}/input.inp"

# ── 运行 ORCA ─────────────────────────────────────────────────────────────────
cd "$WORKDIR"
echo "[orca-tddft] Running ORCA..."
/opt/orca/orca input.inp > output.log 2>&1
echo "[orca-tddft] ORCA finished. Parsing output..."

# ── 解析输出 ──────────────────────────────────────────────────────────────────
ENERGY=$(grep "FINAL SINGLE POINT ENERGY" output.log | tail -1 | awk '{print $NF}' || echo "")
if [[ -z "$ENERGY" ]]; then
    echo "[orca-tddft][ERROR] Could not extract energy from output!" >&2
    cat output.log >&2
    exit 1
fi

CONVERGED="true"
if grep -q "SCF NOT CONVERGED" output.log; then
    CONVERGED="false"
    echo "[orca-tddft][WARN] SCF DID NOT CONVERGE!"
fi

SCF_ITER=$(grep "SCF CONVERGED AFTER" output.log | tail -1 | awk '{print $4}' || echo "0")
echo "[orca-tddft] Energy=${ENERGY} Ha  Converged=${CONVERGED}  SCF_iter=${SCF_ITER}"

# ── 提取 Mulliken 电荷 ────────────────────────────────────────────────────────
python3 /mf/profile/postprocess.py

# ── 提取 TD-DFT 激发能 ───────────────────────────────────────────────────────
python3 /mf/profile/postprocess_tddft.py

# ── 写入输出 ──────────────────────────────────────────────────────────────────
echo "${ENERGY}"      > "${OUTPUT_DIR}/total_energy"
echo "${CONVERGED}"   > "${OUTPUT_DIR}/scf_converged"
echo "${ENERGY}"      > "${OUTPUT_DIR}/scf_energy"
echo "${SCF_ITER:-0}" > "${OUTPUT_DIR}/scf_iterations"

GBW_FILE="${WORKDIR}/input.gbw"
if [[ -f "$GBW_FILE" ]]; then
    cp "$GBW_FILE" "${OUTPUT_DIR}/gbw_file"
else
    echo "[orca-tddft][WARN] GBW file not found: ${GBW_FILE}" >&2
    echo "NO_GBW" > "${OUTPUT_DIR}/gbw_file"
fi

echo "[orca-tddft] Done."
