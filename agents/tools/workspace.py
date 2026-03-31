"""agents/tools/workspace.py — Planner workspace 感知工具。

Planner Agent 在规划工作流时可通过这两个工具了解 workspace 目录中已有哪些
用户上传的文件，并选择性读取文件内容（如分子坐标），从而将文件名正确地填入
MF YAML 的 onboard_params 中，而无需在工作流定义中硬编码文件内容。

workspace 定位：
  - 用户/Main Agent ↔ 节点 的输入输出交换区
  - 用途1：用户上传输入文件（如 .xyz 坐标、力场文件），节点运行时从
    /mf/workspace/<filename> 读取
  - 用途2：节点将大型输出写入 workspace，供人/Agent 事后检查
  - 节点间数据传递仍使用 StreamIO，不经由 workspace
"""

from __future__ import annotations

import json
from pathlib import Path


def workspace_list_files(project_root: Path) -> str:
    """列出 workspace 目录中所有文件的基本信息。

    扫描项目根目录下的 workspace/ 子目录，返回文件名、大小和扩展名列表。
    Planner Agent 可调用此工具了解用户已上传哪些输入文件（如分子坐标 .xyz、
    力场参数 .ff 等），以便在生成 MF YAML 时正确引用文件名。

    Args:
        project_root: 项目根目录路径（通常由调用方注入，不由 LLM 提供）。

    Returns:
        JSON 字符串，格式为：
            [{"name": "h2o.xyz", "size_bytes": 128, "ext": ".xyz"}, ...]
        workspace 为空或目录不存在时返回 "[]"。
    """
    workspace_dir = project_root / "userdata" / "workspace"
    if not workspace_dir.is_dir():
        return "[]"

    entries = []
    for path in sorted(workspace_dir.iterdir()):
        if path.is_file():
            entries.append({
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "ext": path.suffix,
            })

    return json.dumps(entries, ensure_ascii=False)


def workspace_read_file(
    filename: str,
    project_root: Path,
    max_chars: int = 2000,
) -> str:
    """读取 workspace 目录中指定文件的内容（文本模式，UTF-8）。

    Planner Agent 可调用此工具查看用户上传文件的内容，以便理解分子结构、
    力场参数等信息，从而制定更准确的工作流规划。

    文件名安全校验：不允许包含路径分隔符（'/'、'\\'）或父级引用（'..'），
    以防止路径穿越攻击。内容超出 max_chars 时自动截断并附加提示。

    Args:
        filename: 文件名（仅文件名，不含路径），如 "h2o.xyz"。
        project_root: 项目根目录路径（通常由调用方注入，不由 LLM 提供）。
        max_chars: 最多返回的字符数，默认 2000，防止大文件塞满上下文。

    Returns:
        文件文本内容字符串。被截断时末尾附加
        "[...（已截断，共 N 字节）]" 提示。
        文件不存在或名称非法时返回明确错误字符串（不抛异常）。
    """
    # 安全校验：不允许路径分隔符或父级引用
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return f"[错误] 非法文件名: {filename!r}（不允许路径分隔符或 '..'）"

    workspace_dir = project_root / "userdata" / "workspace"
    target = workspace_dir / filename

    if not target.is_file():
        return f"[错误] workspace 中不存在文件: {filename!r}"

    try:
        raw_bytes = target.read_bytes()
        total_bytes = len(raw_bytes)
        text = raw_bytes.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"[错误] 无法读取文件 {filename!r}: {exc}"

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + f"\n[...（已截断，共 {total_bytes} 字节）]"
