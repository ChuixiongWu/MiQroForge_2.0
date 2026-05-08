"""agents/node_generator/ephemeral/graph.py — 临时节点 LangGraph 图。

拓扑：START → generate → save → END

生成+执行+评估的完整循环在 generate_ephemeral_node 内部完成，
API 端点负责外循环（generate → evaluate → retry）。
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from agents.node_generator.ephemeral.state import EphemeralGenState
from agents.node_generator.ephemeral.generator import generate_ephemeral_node
from agents.schemas import NodeGenResult


# ─── 节点函数 ──────────────────────────────────────────────────────────────────

def _generate(state: EphemeralGenState) -> dict[str, Any]:
    """生成临时节点脚本。"""
    return generate_ephemeral_node(state)


def _save(state: EphemeralGenState) -> dict[str, Any]:
    """将生成的脚本包装为 NodeGenResult（不保存文件，直接返回脚本内容）。"""
    request = state.get("request")
    script = state.get("script", "")

    if not request:
        return {}

    evaluation = state.get("evaluation")
    result = NodeGenResult(
        node_name=request.semantic_type or "ephemeral",
        nodespec_yaml="",
        run_sh=script,
        input_templates={},
        saved_path=None,
        evaluation=evaluation,
        script_content=script,
    )
    return {"result": result}


# ─── 图构建 ────────────────────────────────────────────────────────────────────

def build_ephemeral_graph():
    """构建并编译临时节点生成 LangGraph 图。"""
    graph = StateGraph(EphemeralGenState)

    graph.add_node("generate", _generate)
    graph.add_node("save", _save)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "save")
    graph.add_edge("save", END)

    return graph.compile()


_ephemeral_graph = None


def get_ephemeral_graph():
    """获取编译后的临时节点图（单例）。"""
    global _ephemeral_graph
    if _ephemeral_graph is None:
        _ephemeral_graph = build_ephemeral_graph()
    return _ephemeral_graph


def run_ephemeral_node_generator(request, **extra_state) -> EphemeralGenState:
    """运行临时节点生成 Agent。

    Parameters:
        request: NodeGenRequest 实例。
        **extra_state: 额外的状态字段（如 _input_data 等）。
    """
    graph = get_ephemeral_graph()
    initial_state: EphemeralGenState = {
        "request": request,
        "iteration": 0,
        **extra_state,
    }
    return graph.invoke(initial_state)
