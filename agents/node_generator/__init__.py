"""agents/node_generator/__init__.py — Node Generator Agent 公共 API。

提供统一入口 run_node_generator()，根据 request.node_mode 分派到
prefab 或 ephemeral 子模块。同时导出各子模块的独立入口。
"""

from .prefab.graph import run_prefab_node_generator
from .ephemeral.graph import run_ephemeral_node_generator

__all__ = [
    "run_node_generator",
    "run_prefab_node_generator",
    "run_ephemeral_node_generator",
]


def run_node_generator(request, **extra_state):
    """统一入口：根据 request.node_mode 分派到 prefab 或 ephemeral。

    Parameters:
        request: NodeGenRequest 实例。
        **extra_state: 额外的状态字段。
    """
    if getattr(request, "node_mode", "prefab") == "ephemeral":
        return run_ephemeral_node_generator(request, **extra_state)
    return run_prefab_node_generator(request, **extra_state)
