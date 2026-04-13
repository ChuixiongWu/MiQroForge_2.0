"""agents/node_generator/sandbox.py — 服务端执行沙箱。

为临时节点 Agent 提供安全的脚本执行环境：
- 优先使用 Docker 容器执行（ephemeral-py 镜像），与 Pod 环境一致
- Docker 不可用时 fallback 到宿主 subprocess
- 提供 LangChain Tool 工厂：sandbox_execute、pip_install
- 沙箱工作目录使用 userdata/sandbox_runs/<run_id>/ 持久化（不随 with 块清理）

路径处理策略：
1. 优先创建 /mf/input → tmpdir/input 等符号链接（Pod 内可用）
2. 降级：将脚本中的 /mf/ 绝对路径替换为临时目录路径
"""

from __future__ import annotations

import glob as _glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# 支持的图片扩展名
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".gif", ".webp"}


# ═══════════════════════════════════════════════════════════════════════════
# 执行模式选择
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_sandbox_mode() -> str:
    """解析沙箱执行模式。返回 'docker' 或 'subprocess'。"""
    mode = os.environ.get("MF_SANDBOX_MODE", "auto").lower()
    if mode == "docker":
        return "docker"
    if mode == "subprocess":
        return "subprocess"
    # auto: 优先 docker
    return "docker" if _docker_available() else "subprocess"


def _docker_available() -> bool:
    """检查 Docker daemon 是否可用。"""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 沙箱工作目录管理
# ═══════════════════════════════════════════════════════════════════════════

def _get_sandbox_base_dir() -> Path:
    """获取沙箱基础目录 userdata/sandbox_runs/。"""
    root = Path(__file__).parent.parent.parent
    base = root / "userdata" / "sandbox_runs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_sandbox_dir() -> Path:
    """创建一个持久化的沙箱工作目录。调用方负责在不再需要时清理。

    Returns:
        沙箱目录路径，含 input/、output/、workspace/ 子目录。
    """
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    sandbox_dir = _get_sandbox_base_dir() / run_id
    (sandbox_dir / "input").mkdir(parents=True)
    (sandbox_dir / "output").mkdir(parents=True)
    (sandbox_dir / "workspace").mkdir(parents=True)
    return sandbox_dir


def cleanup_sandbox_dir(sandbox_dir: Path) -> None:
    """清理沙箱工作目录。"""
    try:
        if sandbox_dir.exists() and str(sandbox_dir).startswith(str(_get_sandbox_base_dir())):
            shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# 符号链接 / 路径重写
# ═══════════════════════════════════════════════════════════════════════════

def _setup_symlinks(tmpdir_path: Path) -> bool:
    """尝试在 /mf/ 下创建符号链接到临时目录的对应子目录。

    如果权限不足（非 root 环境），返回 False，调用方需降级处理。
    """
    mapping = {
        "/mf/input": tmpdir_path / "input",
        "/mf/output": tmpdir_path / "output",
        "/mf/workspace": tmpdir_path / "workspace",
    }
    try:
        for link_path, target in mapping.items():
            p = Path(link_path)
            if p.is_symlink():
                p.unlink()
            elif p.exists():
                return False  # 已有真实目录，不覆盖
            p.parent.mkdir(parents=True, exist_ok=True)
            p.symlink_to(target, target_is_directory=True)
        return True
    except (PermissionError, OSError):
        return False


def _cleanup_symlinks() -> None:
    """清理沙箱创建的符号链接。"""
    for link_path in ("/mf/input", "/mf/output", "/mf/workspace"):
        p = Path(link_path)
        try:
            if p.is_symlink():
                p.unlink()
        except (PermissionError, OSError):
            pass


def _rewrite_script_paths(
    script: str,
    input_dir: Path,
    output_dir: Path,
    workspace_dir: Path,
) -> str:
    """将脚本中的 /mf/ 绝对路径替换为实际临时目录路径。"""
    script = script.replace("/mf/input/", str(input_dir) + "/")
    script = script.replace("/mf/output/", str(output_dir) + "/")
    script = script.replace("/mf/workspace/", str(workspace_dir) + "/")
    # 无尾斜杠的精确匹配
    script = script.replace('"/mf/input"', f'"{input_dir}"')
    script = script.replace('"/mf/output"', f'"{output_dir}"')
    script = script.replace('"/mf/workspace"', f'"{workspace_dir}"')
    return script


# ═══════════════════════════════════════════════════════════════════════════
# Docker 执行
# ═══════════════════════════════════════════════════════════════════════════

_EPHEMERAL_IMAGE = "ephemeral-py:3.11"


def _execute_in_docker(
    script: str,
    input_data: dict[str, str] | None,
    env_overrides: dict[str, str] | None,
    timeout: int,
    sandbox_dir: Path | None = None,
) -> dict[str, Any]:
    """在 Docker 容器内执行脚本。"""
    own_dir = sandbox_dir is None
    if own_dir:
        sandbox_dir = create_sandbox_dir()

    try:
        input_dir = sandbox_dir / "input"
        output_dir = sandbox_dir / "output"
        workspace_dir = sandbox_dir / "workspace"

        # 写入输入数据
        if input_data:
            for port_name, content in input_data.items():
                port_file = input_dir / port_name
                port_file.write_text(content, encoding="utf-8")

        # 写入脚本
        script_path = sandbox_dir / "_script.py"
        script_path.write_text(script, encoding="utf-8")

        # 环境变量
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{sandbox_dir}:/sandbox",
            "-e", "MF_INPUT_DIR=/sandbox/input",
            "-e", "MF_OUTPUT_DIR=/sandbox/output",
            "-e", "MF_WORKSPACE_DIR=/sandbox/workspace",
        ]
        # 传递额外环境变量
        for k, v in (env_overrides or {}).items():
            cmd.extend(["-e", f"{k}={v}"])

        cmd.extend([_EPHEMERAL_IMAGE, "python", "/sandbox/_script.py"])

        timed_out = False
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(sandbox_dir),
                env=env,
            )
            stdout = result.stdout
            stderr = result.stderr
            return_code = result.returncode
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = (
                e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            ) + "\n[TIMEOUT]"
            return_code = -1
            timed_out = True

        # 检测生成的文件
        generated_files, image_files = _scan_output_files(output_dir, workspace_dir)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "timed_out": timed_out,
            "generated_files": generated_files,
            "image_files": image_files,
            "sandbox_dir": str(sandbox_dir),
        }
    finally:
        if own_dir:
            cleanup_sandbox_dir(sandbox_dir)


def _docker_pip_install(package: str) -> dict[str, Any]:
    """在 Docker 容器内执行 pip install。"""
    cmd = [
        "docker", "run", "--rm",
        _EPHEMERAL_IMAGE,
        "pip", "install", "--no-cache-dir", package,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "return_code": result.returncode,
            "output": (result.stdout + result.stderr)[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"return_code": -1, "output": "pip install timed out"}
    except Exception as e:
        return {"return_code": -1, "output": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# Subprocess 执行（fallback）
# ═══════════════════════════════════════════════════════════════════════════

def _execute_in_subprocess(
    script: str,
    input_data: dict[str, str] | None,
    env_overrides: dict[str, str] | None,
    timeout: int,
    sandbox_dir: Path | None = None,
) -> dict[str, Any]:
    """在宿主机子进程中执行脚本（fallback）。"""
    own_dir = sandbox_dir is None
    if own_dir:
        sandbox_dir = create_sandbox_dir()

    try:
        input_dir = sandbox_dir / "input"
        output_dir = sandbox_dir / "output"
        workspace_dir = sandbox_dir / "workspace"

        # 写入输入数据
        if input_data:
            for port_name, content in input_data.items():
                port_file = input_dir / port_name
                port_file.write_text(content, encoding="utf-8")

        # 路径处理：优先 symlink，否则重写脚本路径
        symlinks_ok = _setup_symlinks(sandbox_dir)
        if not symlinks_ok:
            script = _rewrite_script_paths(script, input_dir, output_dir, workspace_dir)

        # 写入脚本
        script_path = sandbox_dir / "_script.py"
        script_path.write_text(script, encoding="utf-8")

        # 环境变量
        env = os.environ.copy()
        env["MF_INPUT_DIR"] = str(input_dir)
        env["MF_OUTPUT_DIR"] = str(output_dir)
        env["MF_WORKSPACE_DIR"] = str(workspace_dir)
        if env_overrides:
            env.update(env_overrides)

        # 执行
        timed_out = False
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(sandbox_dir),
                env=env,
            )
            stdout = result.stdout
            stderr = result.stderr
            return_code = result.returncode
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = (
                e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            ) + "\n[TIMEOUT]"
            return_code = -1
            timed_out = True

        # 清理符号链接
        if symlinks_ok:
            _cleanup_symlinks()

        # 检测生成的文件
        generated_files, image_files = _scan_output_files(output_dir, workspace_dir)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "timed_out": timed_out,
            "generated_files": generated_files,
            "image_files": image_files,
            "sandbox_dir": str(sandbox_dir),
        }
    finally:
        if own_dir:
            cleanup_sandbox_dir(sandbox_dir)


def _subprocess_pip_install(package: str) -> dict[str, Any]:
    """在宿主机执行 pip install（fallback）。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "return_code": result.returncode,
            "output": (result.stdout + result.stderr)[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"return_code": -1, "output": "pip install timed out"}
    except Exception as e:
        return {"return_code": -1, "output": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════════════════════

def _scan_output_files(output_dir: Path, workspace_dir: Path) -> tuple[list[str], list[str]]:
    """扫描输出目录，返回 (generated_files, image_files)。"""
    generated_files: list[str] = []
    image_files: list[str] = []
    for dirpath in (output_dir, workspace_dir):
        for fpath in sorted(_glob.glob(str(dirpath / "**" / "*"), recursive=True)):
            if os.path.isfile(fpath):
                generated_files.append(fpath)
                ext = os.path.splitext(fpath)[1].lower()
                if ext in _IMAGE_EXTENSIONS:
                    image_files.append(fpath)
    return generated_files, image_files


# ═══════════════════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════════════════

def execute_script_sandbox(
    script: str,
    input_data: dict[str, str] | None = None,
    env_overrides: dict[str, str] | None = None,
    timeout: int = 120,
    sandbox_dir: Path | None = None,
) -> dict[str, Any]:
    """在沙箱中执行 Python 脚本。

    优先使用 Docker 容器（与 Pod 环境一致），不可用时 fallback 到 subprocess。

    Parameters
    ----------
    script:
        要执行的 Python 脚本内容。
    input_data:
        真实的输入数据 {port_name: file_content}。
    env_overrides:
        额外的环境变量。
    timeout:
        执行超时（秒）。
    sandbox_dir:
        沙箱工作目录。None 时自动创建（调用方需在不再需要时清理）。

    Returns
    -------
    dict:
        stdout, stderr, return_code, timed_out, generated_files, image_files, sandbox_dir
    """
    mode = _resolve_sandbox_mode()
    if mode == "docker":
        return _execute_in_docker(script, input_data, env_overrides, timeout, sandbox_dir)
    return _execute_in_subprocess(script, input_data, env_overrides, timeout, sandbox_dir)


def _run_pip_install(package: str) -> dict[str, Any]:
    """统一 pip install 入口。"""
    mode = _resolve_sandbox_mode()
    if mode == "docker":
        return _docker_pip_install(package)
    return _subprocess_pip_install(package)


# ═══════════════════════════════════════════════════════════════════════════
# LangChain Tool 工厂
# ═══════════════════════════════════════════════════════════════════════════

def make_sandbox_tool(
    input_data: dict[str, str],
    env_overrides: dict[str, str] | None = None,
    sandbox_dir: Path | None = None,
):
    """创建绑定到特定 input_data 的 sandbox_execute Tool。

    Parameters
    ----------
    input_data:
        真实输入数据 {port_name: content}。
    env_overrides:
        额外环境变量。
    sandbox_dir:
        共享的沙箱目录（持久化，不会在每次调用后清理）。
    """
    from langchain_core.tools import tool

    _input_data = input_data
    _env_overrides = env_overrides or {}
    _sandbox_dir = sandbox_dir

    @tool
    def sandbox_execute(script: str) -> dict:
        """Execute a Python script in the sandbox.

        The script has access to /mf/input/I1, /mf/input/I2, ... for reading inputs
        and should write outputs to /mf/output/O1, /mf/output/O2, ...
        Images should be saved to the workspace directory.

        Returns dict with keys: stdout, stderr, return_code, image_files, image_paths.
        """
        result = execute_script_sandbox(
            script=script,
            input_data=_input_data,
            env_overrides=_env_overrides,
            timeout=60,
            sandbox_dir=_sandbox_dir,
        )
        return {
            "stdout": result["stdout"][:3000],
            "stderr": result["stderr"][:2000],
            "return_code": result["return_code"],
            "image_files": [os.path.basename(f) for f in result["image_files"]],
            "image_paths": result["image_files"],  # 完整路径，供 evaluator 读取
        }

    return sandbox_execute


def make_pip_install_tool():
    """创建 pip_install Tool 和安装历史记录器。

    Returns
    -------
    tuple:
        (pip_install_tool, install_history)
        install_history 是一个 list，在 LLM 调用 pip_install 时自动追加记录。
    """
    from langchain_core.tools import tool

    install_history: list[dict] = []

    @tool
    def pip_install(package: str) -> str:
        """Install a Python package via pip.

        Use this when your script needs a library NOT in the pre-installed list:
        numpy, matplotlib, scipy, pandas, pyyaml, jinja2, requests.
        For faster installs in China, packages are installed from PyPI directly.
        """
        result = _run_pip_install(package)
        install_history.append({
            "package": package,
            "return_code": result["return_code"],
            "output": result["output"][:500],
        })
        return result["output"][:500]

    return pip_install, install_history


def save_pip_history(
    pip_history: list[dict],
    description: str,
    userdata_root: Path | None = None,
) -> None:
    """将 pip 安装历史持久化到 userdata/pip_history.jsonl。

    Parameters
    ----------
    pip_history:
        make_pip_install_tool 返回的 install_history 列表。
    description:
        节点描述（截断到 100 字符用于分析）。
    userdata_root:
        userdata 根目录。None 时自动探测。
    """
    if not pip_history:
        return

    if userdata_root is None:
        # 自动探测：从当前文件向上找项目根
        root = Path(__file__).parent.parent.parent
        userdata_root = root / "userdata"

    history_path = userdata_root / "pip_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    desc_short = description[:100]

    with open(history_path, "a", encoding="utf-8") as f:
        for entry in pip_history:
            record = {
                "timestamp": timestamp,
                "description": desc_short,
                **entry,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
