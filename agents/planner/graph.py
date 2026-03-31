"""agents/planner/graph.py — 构建 Planner Agent LangGraph 图。

流程：
  START → search_nodes → generate → evaluate → [passed? END : refine → evaluate → ...]
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from agents.planner.state import PlannerState
from agents.planner.generator import generate_plan, load_semantic_types, search_nodes_for_intent
from agents.planner.evaluator import evaluate_plan
from agents.schemas import EvaluationResult


MAX_ITERATIONS = 3


def _prepare_state(state: PlannerState) -> dict[str, Any]:
    """初始化阶段：加载语义类型 + RAG 检索节点。"""
    intent = state.get("intent", "")
    molecule = state.get("molecule", "")

    semantic_types = load_semantic_types()
    node_summaries = search_nodes_for_intent(intent, molecule)

    return {
        "semantic_types": semantic_types,
        "node_summaries": node_summaries,
        "iteration": 0,
    }


def _route_after_evaluate(state: PlannerState) -> str:
    """评判后路由：通过 → end，否则继续迭代。"""
    evaluation: EvaluationResult | None = state.get("evaluation")
    iteration: int = state.get("iteration", 0)

    if evaluation and evaluation.passed:
        return "end"
    if iteration >= MAX_ITERATIONS:
        return "end"
    return "refine"


def _increment_iteration(state: PlannerState) -> dict[str, Any]:
    return {"iteration": state.get("iteration", 0) + 1}


def build_planner_graph():
    """构建并编译 Planner Agent LangGraph 图。"""
    graph = StateGraph(PlannerState)

    # 注册节点
    graph.add_node("prepare", _prepare_state)
    graph.add_node("generate", generate_plan)
    graph.add_node("evaluate", evaluate_plan)
    graph.add_node("increment", _increment_iteration)

    # 入口
    graph.set_entry_point("prepare")

    # 边
    graph.add_edge("prepare", "generate")
    graph.add_edge("generate", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "end": END,
            "refine": "increment",
        },
    )

    graph.add_edge("increment", "generate")

    return graph.compile()


# 全局单例图（延迟编译）
_planner_graph = None


def get_planner_graph():
    """获取 Planner Agent 编译图（单例）。"""
    global _planner_graph
    if _planner_graph is None:
        _planner_graph = build_planner_graph()
    return _planner_graph


def run_planner(
    intent: str,
    molecule: str = "",
    preferences: str = "",
) -> PlannerState:
    """运行 Planner Agent，返回最终状态。

    Parameters
    ----------
    intent:      用户意图（自然语言）
    molecule:    目标分子（可选）
    preferences: 用户偏好（可选）

    Returns
    -------
    PlannerState: 包含 semantic_workflow 和 evaluation 的最终状态
    """
    graph = get_planner_graph()

    initial_state: PlannerState = {
        "intent": intent,
        "molecule": molecule,
        "preferences": preferences,
    }

    result = graph.invoke(initial_state)
    return result
