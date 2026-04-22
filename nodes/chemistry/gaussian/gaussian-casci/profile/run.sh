#!/usr/bin/env bash
# gaussian-casci/profile/run.sh — CASCI 单点能量
set -euo pipefail
# MF2 init

mf_banner "gaussian-casci" "CASCI single-point energy calculation"

echo "[gaussian-casci] CASCI(${active_electrons},${active_orbitals})/${basis_set} Ref=${reference} Pop=${population} Cores=${n_cores}"

XYZ_INPUT="${INPUT_DIR}/xyz_geometry"
if [[ ! -f "$XYZ_INPUT" ]]; then
    echo "[gaussian-casci][ERROR] Required stream input 'xyz_geometry' not found at ${XYZ_INPUT}" >&2
    exit 1
fi
cp "$XYZ_INPUT" "${WORKDIR}/input.xyz"

python3 << PYEOF
from string import Template

basis_set = '${basis_set}'
population = '${population}'
active_electrons = '${active_electrons}'
active_orbitals = '${active_orbitals}'
reference = '${reference}'
charge = '${charge}'
multiplicity = '${multiplicity}'
n_cores = '${n_cores}'
mem_gb = '${mem_gb}'

mem_mb = str(int(float(mem_gb) * 1024))

# Reference keyword mapping
ref_kw_map = {
    'rhf': '',
    'uhf': 'UHF',
    'rohf': 'ROHF',
}
ref_kw = ref_kw_map.get(reference, '')

with open('${WORKDIR}/input.xyz') as f:
    lines = f.readlines()
geometry_lines = "".join(lines[2:])

with open('/mf/profile/input.gjf.template') as f:
    tmpl = Template(f.read())

result = tmpl.substitute(
    basis_set=basis_set,
    population=population,
    active_electrons=active_electrons,
    active_orbitals=active_orbitals,
    ref_kw=ref_kw,
    n_cores=n_cores,
    mem_mb=mem_mb,
    charge=charge,
    multiplicity=multiplicity,
    geometry_lines=geometry_lines,
)

with open('${WORKDIR}/input.gjf', 'w') as f:
    f.write(result)

print(f"[gaussian-casci] Generated input.gjf ({mem_mb}MB, {n_cores} cores)")
PYEOF

echo "[gaussian-casci] Generated input.gjf:"
cat "${WORKDIR}/input.gjf"

cd "$WORKDIR"
echo "[gaussian-casci] Running Gaussian..."
if ! g16 < input.gjf > output.log 2>&1; then
    ec=$?
    echo "[gaussian-casci][ERROR] g16 exited with ${ec}; dumping output.log tail:" >&2
    tail -n 200 output.log >&2 || true
    exit "${ec}"
fi
echo "[gaussian-casci] Gaussian finished. Parsing output..."

ENERGY=$(grep "SCF Done" output.log | tail -1 | awk '{print $5}' || echo "")
if [[ -z "$ENERGY" ]]; then
    echo "[gaussian-casci][ERROR] Could not extract energy from output!" >&2
    cat output.log >&2
    exit 1
fi

CONVERGED="true"
if grep -q "Convergence criterion not met" output.log; then
    CONVERGED="false"
    echo "[gaussian-casci][WARN] SCF DID NOT CONVERGE!"
fi

echo "[gaussian-casci] Energy=${ENERGY} Ha  Converged=${CONVERGED}"

if [[ -f input.chk ]]; then
    echo "[gaussian-casci] Converting .chk to .fchk..."
    formchk input.chk input.fchk > /dev/null 2>&1
    cp input.fchk "${OUTPUT_DIR}/fchk_file"
else
    echo "[gaussian-casci][WARN] .chk file not found!" >&2
    echo "NO_FCHK" > "${OUTPUT_DIR}/fchk_file"
fi

echo "${ENERGY}"    > "${OUTPUT_DIR}/total_energy"
echo "${CONVERGED}" > "${OUTPUT_DIR}/scf_converged"
echo "${ENERGY}"    > "${OUTPUT_DIR}/scf_energy"

echo "[gaussian-casci] Done."
