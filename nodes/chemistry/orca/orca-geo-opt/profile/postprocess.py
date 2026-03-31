"""orca-geo-opt post-processing: extract optimized geometry from ORCA output."""
import os
import re

workdir = "/mf/workdir"
output_dir = "/mf/output"

# 优先读取 input.xyz（最终优化结构）
xyz_path = os.path.join(workdir, "input.xyz")
xyz_content = ""

if os.path.exists(xyz_path):
    with open(xyz_path) as f:
        xyz_content = f.read()
    print(f"[orca-geo-opt] Read optimized geometry from input.xyz ({len(xyz_content)} chars)")
else:
    # 从 output.log 提取最后一个 CARTESIAN COORDINATES (ANGSTROEM) 块
    log_path = os.path.join(workdir, "output.log")
    with open(log_path) as f:
        content = f.read()

    pattern = re.compile(
        r"CARTESIAN COORDINATES \(ANGSTROEM\)\s*\n-+\n(.*?)\n\s*\n",
        re.DOTALL
    )
    matches = list(pattern.finditer(content))
    if matches:
        coord_block = matches[-1].group(1).strip()
        lines = coord_block.split("\n")
        n_atoms = len(lines)
        xyz_content = f"{n_atoms}\nOptimized geometry (MiQroForge)\n" + "\n".join(
            "  ".join(line.split()) for line in lines
        )
        print(f"[orca-geo-opt] Extracted geometry from output.log ({n_atoms} atoms)")
    else:
        xyz_content = "0\nNo geometry extracted\n"
        print("[orca-geo-opt][WARN] Could not extract optimized geometry")

with open(os.path.join(output_dir, "optimized_xyz"), "w") as f:
    f.write(xyz_content)
