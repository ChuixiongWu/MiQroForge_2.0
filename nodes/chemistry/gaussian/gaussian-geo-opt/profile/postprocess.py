"""gaussian-geo-opt post-processing: extract optimized geometry from Gaussian output."""
import re
import os

log_file = "/mf/workdir/output.log"
output_dir = os.environ.get("OUTPUT_DIR", "/mf/output")

try:
    with open(log_file) as f:
        content = f.read()

    # Gaussian 输出中的标准取向几何（Standard orientation）有多帧
    # 取最后一帧
    pattern = re.compile(
        r"Standard orientation:.*?"
        r"-+\s*\n"
        r"\s*Center\s+Atomic\s+Atomic\s+Coordinates.*?\n"
        r"\s*Number\s+Number\s+Type\s+X\s+Y\s+Z\s*\n"
        r"\s*-+\s*\n"
        r"((?:\s+\d+\s+\d+\s+\d+\s+[+-]?\d+\.\d+\s+[+-]?\d+\.\d+\s+[+-]?\d+\.\d+\s*\n)+)"
        r"\s*-+",
        re.DOTALL
    )
    matches = pattern.findall(content)

    if matches:
        last_geom = matches[-1].strip()
        # 转换为 XYZ 格式
        atomic_symbols = {
            1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N",
            8: "O", 9: "F", 10: "Ne", 11: "Na", 12: "Mg", 13: "Al",
            14: "Si", 15: "P", 16: "S", 17: "Cl", 18: "Ar", 19: "K",
            20: "Ca", 26: "Fe", 29: "Cu", 30: "Zn", 79: "Au",
        }

        xyz_lines = []
        for line in last_geom.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 6:
                atomic_num = int(parts[1])
                symbol = atomic_symbols.get(atomic_num, f"X{atomic_num}")
                x, y, z = float(parts[3]), float(parts[4]), float(parts[5])
                xyz_lines.append(f"{symbol}  {x:.6f}  {y:.6f}  {z:.6f}")

        xyz_content = f"{len(xyz_lines)}\nOptimized geometry from Gaussian\n"
        xyz_content += "\n".join(xyz_lines) + "\n"

        with open(f"{output_dir}/optimized_xyz", "w") as f:
            f.write(xyz_content)

        print(f"[gaussian-geo-opt] Extracted {len(xyz_lines)} atoms")
    else:
        print("[gaussian-geo-opt][WARN] Could not find Standard orientation in output")

except Exception as e:
    print(f"[gaussian-geo-opt][WARN] Post-processing failed: {e}")
