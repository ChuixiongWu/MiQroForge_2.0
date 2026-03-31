#!/usr/bin/env bash
# orca-geo-opt/profile/run.sh — DFT 几何优化
set -euo pipefail
# MF2 init

mf_banner "orca-geo-opt" "DFT geometry optimization"

# 所有 onboard 参数由编译器生成的 mf_node_params.sh 自动加载，此处可直接使用：
# method  basis_set  dispersion  convergence  max_iter  charge  multiplicity  n_cores
echo "[orca-geo-opt] Method=${method}/${basis_set} Disp=${dispersion} Convergence=${convergence}"
echo "[orca-geo-opt] Charge=${charge} Mult=${multiplicity} MaxIter=${max_iter} Cores=${n_cores}"

# ── 读取 stream input: xyz_geometry ──────────────────────────────────────────
XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[orca-geo-opt][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"
echo "[orca-geo-opt] Loaded input geometry: $(wc -l < "${WORKDIR}/input.xyz") lines"

# ── 生成 ORCA 输入文件（标准库 string.Template 渲染）─────────────────────────
python3 << PYEOF
from string import Template
disp = '${dispersion}'
disp_kw = (disp + ' ') if disp != 'none' else ''
tmpl = Template(open('/mf/profile/input.orca.template').read())
result = tmpl.substitute(
    method='${method}',
    basis_set='${basis_set}',
    disp_kw=disp_kw,
    n_cores='${n_cores}',
    charge='${charge}',
    multiplicity='${multiplicity}',
    convergence='${convergence}',
    max_iter='${max_iter}',
)
with open('${WORKDIR}/input.inp', 'w') as f:
    f.write(result)
PYEOF

echo "[orca-geo-opt] Generated input.inp:"
cat "${WORKDIR}/input.inp"

# ── 运行 ORCA ─────────────────────────────────────────────────────────────────
cd "$WORKDIR"
echo "[orca-geo-opt] Running ORCA optimization..."
/opt/orca/orca input.inp > output.log 2>&1
echo "[orca-geo-opt] ORCA finished."

# ── 解析输出 ──────────────────────────────────────────────────────────────────
ENERGY=$(grep "FINAL SINGLE POINT ENERGY" output.log | tail -1 | awk '{print $NF}' || echo "")
if [[ -z "$ENERGY" ]]; then
    echo "[orca-geo-opt][ERROR] Cannot extract energy!" >&2
    cat output.log >&2
    exit 1
fi

OPT_CONVERGED="true"
if grep -q "THE OPTIMIZATION HAS CONVERGED" output.log; then
    echo "[orca-geo-opt] Optimization CONVERGED"
elif grep -q "OPTIMIZATION HAS NOT CONVERGED" output.log \
     || ! grep -q "FINAL SINGLE POINT ENERGY" output.log; then
    OPT_CONVERGED="false"
    echo "[orca-geo-opt][WARN] Optimization DID NOT CONVERGE"
fi

OPT_CYCLES=$(grep -c "GEOMETRY OPTIMIZATION CYCLE" output.log || echo "0")
echo "[orca-geo-opt] Energy=${ENERGY} Ha  Converged=${OPT_CONVERGED}  Cycles=${OPT_CYCLES}"

# ── 提取最终 XYZ 几何 ─────────────────────────────────────────────────────────
python3 /mf/profile/postprocess.py

# ── 写入输出 ──────────────────────────────────────────────────────────────────
echo "${ENERGY}"        > "${OUTPUT_DIR}/total_energy"
echo "${OPT_CONVERGED}" > "${OUTPUT_DIR}/opt_converged"
echo "${ENERGY}"        > "${OUTPUT_DIR}/final_energy"
echo "${OPT_CYCLES}"    > "${OUTPUT_DIR}/opt_cycles"

GBW_FILE="${WORKDIR}/input.gbw"
if [[ -f "$GBW_FILE" ]]; then
    cp "$GBW_FILE" "${OUTPUT_DIR}/gbw_file"
    echo "[orca-geo-opt] GBW file: $(du -sh "$GBW_FILE" | cut -f1)"
else
    echo "[orca-geo-opt][WARN] GBW file not found" >&2
    echo "NO_GBW" > "${OUTPUT_DIR}/gbw_file"
fi

echo "[orca-geo-opt] Done."
