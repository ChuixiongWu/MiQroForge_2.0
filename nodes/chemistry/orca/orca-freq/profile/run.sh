#!/usr/bin/env bash
# orca-freq/profile/run.sh — 频率分析与热力学计算
set -euo pipefail
# MF2 init

mf_banner "orca-freq" "Harmonic frequency analysis & thermochemistry"

# 所有 onboard 参数由编译器生成的 mf_node_params.sh 自动加载，此处可直接使用：
# method  basis_set  dispersion  temperature  pressure  charge  multiplicity  n_cores
echo "[orca-freq] Method=${method}/${basis_set} T=${temperature}K P=${pressure}atm Cores=${n_cores}"
echo "[orca-freq] Charge=${charge} Multiplicity=${multiplicity}"

# ── 读取 stream input: xyz_geometry → workdir/input.xyz ──────────────────────
XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[orca-freq][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"
echo "[orca-freq] Loaded input geometry: $(wc -l < "${WORKDIR}/input.xyz") lines"

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
    temperature='${temperature}',
    pressure='${pressure}',
)
with open('${WORKDIR}/input.inp', 'w') as f:
    f.write(result)
PYEOF

echo "[orca-freq] Running ORCA frequency calculation..."
cd "$WORKDIR"
/opt/orca/orca input.inp > output.log 2>&1
echo "[orca-freq] ORCA finished."

# ── 解析热力学输出 ────────────────────────────────────────────────────────────
TEMPERATURE_VAL="${temperature}" python3 /mf/profile/postprocess.py

echo "[orca-freq] Done."
