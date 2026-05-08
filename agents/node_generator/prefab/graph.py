"""agents/node_generator/prefab/graph.py — Prefab 模式 LangGraph 图。

拓扑：START → generate → save → END

ReAct Agent 内循环在 generate 内部完成，
外循环由 API 端点管理。
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from agents.node_generator.prefab.state import PrefabGenState
from agents.node_generator.prefab.generator import generate_prefab_node
from agents.node_generator.prefab.evaluator import evaluate_prefab_node
from agents.schemas import NodeGenResult


# ─── 节点函数 ──────────────────────────────────────────────────────────────────


def _generate_with_feedback(state: PrefabGenState) -> dict[str, Any]:
    """生成节点（带反馈上下文传递）。"""
    return generate_prefab_node(state)


def _package_result(state: PrefabGenState) -> dict[str, Any]:
    """打包生成结果为 NodeGenResult（不写文件）。

    节点不自动入库。用户在前端确认后，通过 /node/accept 端点持久化。
    """
    request = state.get("request")
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "")
    input_templates = state.get("input_templates") or {}

    if not request or not nodespec_yaml:
        return {}

    # 提取节点名
    import yaml
    try:
        spec_data = yaml.safe_load(nodespec_yaml)
        node_name = spec_data.get("metadata", {}).get("name", "generated-node")
    except Exception:
        node_name = "generated-node"

    evaluation = state.get("evaluation")
    result = NodeGenResult(
        node_name=node_name,
        nodespec_yaml=nodespec_yaml,
        run_sh=run_sh,
        input_templates=input_templates,
        saved_path=None,  # 未入库，saved_path 为空
        evaluation=evaluation,
    )
    return {"result": result}


# ─── 图构建 ────────────────────────────────────────────────────────────────────


def build_prefab_graph():
    """构建并编译 Prefab Node Generator LangGraph 图。

    generate → save → END
    外循环（generate → evaluate → retry）由 API 端点管理。
    """
    graph = StateGraph(PrefabGenState)

    graph.add_node("generate", _generate_with_feedback)
    graph.add_node("save", _package_result)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "save")
    graph.add_edge("save", END)

    return graph.compile()


_prefab_graph = None


def get_prefab_graph():
    global _prefab_graph
    if _prefab_graph is None:
        _prefab_graph = build_prefab_graph()
    return _prefab_graph


def run_prefab_node_generator(request, **extra_state) -> PrefabGenState:
    """运行 Prefab Node Generator Agent。

    Parameters:
        request: NodeGenRequest 实例。
        **extra_state: 额外的状态字段（如 _input_data、resource_overrides 等）。
    """
    graph = get_prefab_graph()
    initial_state: PrefabGenState = {"request": request, "iteration": 0, **extra_state}
    return graph.invoke(initial_state)
