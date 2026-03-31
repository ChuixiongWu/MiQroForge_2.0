#!/usr/bin/env python3
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("MF_OUTPUT_DIR", "/mf/output"))
WORKSPACE_DIR = Path(os.environ.get("MF_WORKSPACE_DIR", "/mf/workspace"))

geometry_file = os.environ.get("geometry_file", "").strip()
inline_geometry = os.environ.get("inline_geometry", "").strip()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 优先级：geometry_file（文件名或内容）> inline_geometry
if geometry_file:
    # 判断是否为文件名（无换行）
    if "\n" not in geometry_file:
        # 文件名：从 workspace 读取
        xyz_path = WORKSPACE_DIR / geometry_file
        if not xyz_path.exists():
            print(f"[ERROR] File not found: {xyz_path}", file=sys.stderr)
            sys.exit(1)
        content = xyz_path.read_text()
    else:
        # 已是内容
        content = geometry_file
elif inline_geometry:
    content = inline_geometry
else:
    print("[ERROR] No geometry provided", file=sys.stderr)
    sys.exit(1)

# 写出
out = OUTPUT_DIR / "xyz_geometry"
out.write_text(content)
print(f"[geometry-file-input] Wrote {len(content)} bytes to xyz_geometry")
