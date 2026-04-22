"""orca-tddft post-processing: parse TD-DFT excitation energies from ORCA output."""
import re
import json

log_file = "/mf/workdir/output.log"
output_dir = "/mf/output"

try:
    with open(log_file) as f:
        content = f.read()

    states = []

    # Parse TD-DFT absorption spectrum block
    # Example lines:
    #   STATE   1:  E=   3.4567 eV    27890.12 cm**-1   f= 0.012345
    tddft_pattern = re.compile(
        r"STATE\s+(\d+):\s+E=\s+([\d.]+)\s+eV\s+[\d.e+\-]+\s+cm\*\*[-]1\s+f=\s*([\d.e+\-]+)",
        re.DOTALL
    )

    for match in tddft_pattern.finditer(content):
        state_idx = int(match.group(1))
        energy_ev = float(match.group(2))
        osc_strength = float(match.group(3))
        # Convert eV to Ha: 1 eV = 0.0367493 Ha
        energy_ha = energy_ev * 0.0367493
        states.append({
            "state": state_idx,
            "energy_eV": energy_ev,
            "energy_Ha": energy_ha,
            "oscillator_strength": osc_strength,
        })

    report = {"states": states}

    with open(f"{output_dir}/excitation_energies", "w") as f:
        json.dump(report, f, indent=2)

    print(f"[orca-tddft] Excitation energies: {len(states)} states parsed")

except Exception as e:
    print(f"[orca-tddft][WARN] Could not parse excitation energies: {e}")
    with open(f"{output_dir}/excitation_energies", "w") as f:
        json.dump({"states": []}, f)
