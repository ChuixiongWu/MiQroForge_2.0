"""agents/node_generator/shared/ — 共享工具模块。

提供 knowledge、manual_index、compression、memory、sandbox_base 等
在 prefab 和 ephemeral 模式中都会用到的基础设施。
"""

from .sandbox_base import (
    create_sandbox_dir,
    cleanup_sandbox_dir,
    _scan_output_files,
    save_pip_history,
    _ensure_docker,
    _docker_available,
)

__all__ = [
    "create_sandbox_dir",
    "cleanup_sandbox_dir",
    "_scan_output_files",
    "save_pip_history",
    "_ensure_docker",
    "_docker_available",
]
