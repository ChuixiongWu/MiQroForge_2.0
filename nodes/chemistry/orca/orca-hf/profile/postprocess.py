"""orca-hf post-processing: parse Mulliken charges from ORCA output."""
import re
import json

log_file = "/mf/workdir/output.log"
output_dir = "/mf/output"

try:
    with open(log_file) as f:
        content = f.read()

    mulliken_pattern = re.compile(
        r"MULLIKEN ATOMIC CHARGES.*?\n-+\n(.*?)\n\s*Sum",
        re.DOTALL
    )
    match = mulliken_pattern.search(content)

    charges = []
    atom_labels = []

    if match:
        for line in match.group(1).strip().split("\n"):
            parts = line.split()
            if len(parts) >= 4:
                atom_labels.append(f"{parts[1]}{parts[0]}")
                charges.append(float(parts[3]))

    spin_populations = []
    spin_pattern = re.compile(
        r"MULLIKEN ATOMIC SPIN POPULATIONS.*?\n-+\n(.*?)\n\s*Sum",
        re.DOTALL
    )
    spin_match = spin_pattern.search(content)
    if spin_match:
        for line in spin_match.group(1).strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                spin_populations.append(float(parts[2]))

    report = {
        "charges": charges,
        "spin_populations": spin_populations,
        "atom_labels": atom_labels,
    }

    with open(f"{output_dir}/mulliken_report", "w") as f:
        json.dump(report, f, indent=2)

    print(f"[orca-hf] Mulliken report: {len(charges)} atoms")

except Exception as e:
    print(f"[orca-hf][WARN] Could not parse Mulliken charges: {e}")
    with open(f"{output_dir}/mulliken_report", "w") as f:
        json.dump({"charges": [], "spin_populations": [], "atom_labels": []}, f)
