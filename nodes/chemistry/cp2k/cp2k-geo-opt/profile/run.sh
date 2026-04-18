#!/usr/bin/env bash
# cp2k-geo-opt/profile/run.sh — 几何优化（固定晶胞）
set -euo pipefail
# MF2 init

mf_banner "cp2k-geo-opt" "Geometry optimization (fixed cell)"

echo "[cp2k-geo-opt] XC=${xc_functional} Basis=${basis_set} Cutoff=${cutoff} Ry Opt=${opt_algorithm}"

# ── 读取 stream input: xyz_geometry ──────────────────────────────────────────
XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[cp2k-geo-opt][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"
echo "[cp2k-geo-opt] Loaded input geometry"

# ── 生成 CP2K 输入文件 ───────────────────────────────────────────────────────
python3 << PYEOF
import os
import sys
from string import Template

cell_abc = '${cell_abc}'
smearing = '${smearing}'
electronic_temperature = '${electronic_temperature}'
xc_functional = '${xc_functional}'
basis_set = '${basis_set}'
cutoff = '${cutoff}'
rel_cutoff = '${rel_cutoff}'
max_scf = '${max_scf}'
eps_scf = '${eps_scf}'
charge = '${charge}'
multiplicity = '${multiplicity}'
opt_algorithm = '${opt_algorithm}'
max_opt_iter = '${max_opt_iter}'
opt_max_force = '${opt_max_force}'
workdir = '${WORKDIR}'

parts = cell_abc.split()
if len(parts) >= 3:
    cell_block = f"      ABC  {parts[0]}  {parts[1]}  {parts[2]}"
else:
    cell_block = f"      ABC  {parts[0]}  {parts[0]}  {parts[0]}"

smear_block = ""
added_mos_block = ""
if smearing != "none":
    smear_block = f"""      &SMEAR  ON
        METHOD  {smearing.upper()}
        ELECTRONIC_TEMPERATURE  {electronic_temperature}
      &END SMEAR"""
    added_mos_block = "      ADDED_MOS  10"

xyz_file = os.path.join(workdir, "input.xyz")
elements = set()
try:
    with open(xyz_file) as f:
        natoms = int(f.readline().strip())
        f.readline()
        for _ in range(natoms):
            elements.add(f.readline().split()[0])
except Exception:
    elements = {"X"}

valence = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 3, "C": 4, "N": 5,
    "O": 6, "F": 7, "Ne": 8, "Na": 9, "Mg": 2, "Al": 3, "Si": 4,
    "P": 5, "S": 6, "Cl": 7, "Ar": 8, "K": 9, "Ca": 2, "Sc": 3,
    "Ti": 4, "V": 5, "Cr": 6, "Mn": 7, "Fe": 8, "Co": 9, "Ni": 10,
    "Cu": 11, "Zn": 12, "Ga": 3, "Ge": 4, "As": 5, "Se": 6, "Br": 7,
    "Kr": 8, "Rb": 9, "Sr": 2, "Y": 3, "Zr": 4, "Nb": 5, "Mo": 6,
    "Tc": 7, "Ru": 8, "Rh": 9, "Pd": 10, "Ag": 11, "Cd": 12,
    "In": 3, "Sn": 4, "Sb": 5, "Te": 6, "I": 7, "Cs": 9, "Ba": 2,
    "La": 3, "Hf": 4, "Ta": 5, "W": 6, "Re": 7, "Os": 8, "Ir": 9,
    "Pt": 10, "Au": 11, "Hg": 12, "Tl": 3, "Pb": 4, "Bi": 5,
}

kind_blocks = ""
for elem in sorted(elements):
    if elem not in valence:
        print(f"[cp2k-geo-opt][ERROR] Element '{elem}' not in valence table. "
              f"Please add it to the lookup dict in run.sh.", file=sys.stderr)
        sys.exit(1)
    q = valence[elem]
    kind_blocks += f"""    &KIND {elem}
      BASIS_SET  {basis_set}
      POTENTIAL  GTH-{xc_functional}-q{q}
    &END KIND
"""

with open("/mf/profile/input.cp2k.template") as f:
    tmpl = Template(f.read())

result = tmpl.substitute(
    charge=charge, multiplicity=multiplicity,
    cutoff=cutoff, rel_cutoff=rel_cutoff,
    max_scf=max_scf, eps_scf=eps_scf,
    xc_functional=xc_functional,
    cell_block=cell_block, smear_block=smear_block,
    added_mos_block=added_mos_block,
    kind_blocks=kind_blocks,
    opt_algorithm=opt_algorithm, max_opt_iter=max_opt_iter,
    opt_max_force=opt_max_force,
)

with open(os.path.join(workdir, "input.inp"), "w") as f:
    f.write(result)

print(f"[cp2k-geo-opt] Generated input.inp ({len(elements)} elements)")
PYEOF

# ── 运行 CP2K ─────────────────────────────────────────────────────────────────
cd "$WORKDIR"
echo "[cp2k-geo-opt] Running CP2K geometry optimization..."
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
mpirun -oversubscribe -np ${n_cores} cp2k.psmp -i input.inp -o output.out 2>&1
echo "[cp2k-geo-opt] CP2K finished."

# ── 解析输出 ──────────────────────────────────────────────────────────────────
ENERGY=""
for f in cp2k_calc-1.ener cp2k_calc.ener; do
    if [[ -f "$f" ]]; then
        ENERGY=$(grep -v "^#" "$f" | tail -1 | awk '{print $4}' || echo "")
        [[ -n "$ENERGY" ]] && break
    fi
done
if [[ -z "$ENERGY" ]]; then
    ENERGY=$(grep "ENERGY| Total FORCE_EVAL" output.out | tail -1 | awk '{print $NF}' || echo "")
fi
if [[ -z "$ENERGY" ]]; then
    ENERGY=$(grep "Total energy:" output.out | tail -1 | awk '{print $NF}' || echo "")
fi
if [[ -z "$ENERGY" ]]; then
    echo "[cp2k-geo-opt][ERROR] Could not extract energy!" >&2
    exit 1
fi

CONVERGED="true"
if grep -q "GEOMETRY OPTIMIZATION COMPLETED" output.out; then
    CONVERGED="true"
elif grep -q "Maximum number of optimization steps reached" output.out; then
    CONVERGED="false"
fi

OPT_CYCLES=$(grep -c "OPTIMIZATION STEP" output.out || echo "0")

echo "[cp2k-geo-opt] Energy=${ENERGY} Ha  Converged=${CONVERGED}  Cycles=${OPT_CYCLES}"

# ── 提取优化后几何 ───────────────────────────────────────────────────────────
POS_FILE="cp2k_calc-pos-1.xyz"
if [[ -f "$POS_FILE" ]]; then
    cp "$POS_FILE" "${OUTPUT_DIR}/optimized_xyz"
else
    cp "${WORKDIR}/input.xyz" "${OUTPUT_DIR}/optimized_xyz"
fi

echo "${ENERGY}"        > "${OUTPUT_DIR}/total_energy"
echo "${ENERGY}"        > "${OUTPUT_DIR}/final_energy"
echo "${CONVERGED}"     > "${OUTPUT_DIR}/opt_converged"
echo "${OPT_CYCLES:-0}" > "${OUTPUT_DIR}/opt_cycles"
echo "${cell_abc}"      > "${OUTPUT_DIR}/cell_parameters"

echo "[cp2k-geo-opt] Done."
