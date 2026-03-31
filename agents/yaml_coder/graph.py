"""agents/yaml_coder/graph.py — YAML Coder Agent LangGraph 图。

流程：
  START → generate → validate+evaluate → [passed? END : refine → evaluate → ...]
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from agents.yaml_coder.state import YAMLCoderState
from agents.yaml_coder.generator import generate_yaml
from agents.yaml_coder.evaluator import evaluate_yaml
from agents.schemas import ConcretizationResult, EvaluationResult


MAX_ITERATIONS = 3


def _route_after_evaluate(state: YAMLCoderState) -> str:
    evaluation: EvaluationResult | None = state.get("evaluation")
    iteration: int = state.get("iteration", 0)

    if evaluation and evaluation.passed:
        return "end"
    if iteration >= MAX_ITERATIONS:
        return "end"
    return "refine"


def _increment_iteration(state: YAMLCoderState) -> dict[str, Any]:
    return {"iteration": state.get("iteration", 0) + 1}


def _finalize(state: YAMLCoderState) -> dict[str, Any]:
    """汇总最终结果到 ConcretizationResult。"""
    resolutions = state.get("resolutions") or []
    mf_yaml = state.get("mf_yaml", "")
    evaluation = state.get("evaluation")
    validation_valid = state.get("validation_valid", False)
    validation_errors = state.get("validation_errors", [])

    missing = [r.step_id for r in resolutions if r.needs_new_node]

    result = ConcretizationResult(
        resolutions=resolutions,
        mf_yaml=mf_yaml,
        missing_nodes=missing,
        validation_passed=validation_valid,
        validation_errors=validation_errors,
        evaluation=evaluation,
    )
    return {"result": result}


def build_yaml_coder_graph():
    """构建并编译 YAML Coder Agent LangGraph 图。"""
    graph = StateGraph(YAMLCoderState)

    graph.add_node("generate", generate_yaml)
    graph.add_node("evaluate", evaluate_yaml)
    graph.add_node("increment", _increment_iteration)
    graph.add_node("finalize", _finalize)

    graph.set_entry_point("generate")

    graph.add_edge("generate", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "end": "finalize",
            "refine": "increment",
        },
    )

    graph.add_edge("increment", "generate")
    graph.add_edge("finalize", END)

    return graph.compile()


_yaml_coder_graph = None


def get_yaml_coder_graph():
    global _yaml_coder_graph
    if _yaml_coder_graph is None:
        _yaml_coder_graph = build_yaml_coder_graph()
    return _yaml_coder_graph


def run_yaml_coder(
    semantic_workflow,
    user_params: dict | None = None,
    selected_implementations: dict | None = None,
) -> YAMLCoderState:
    """运行 YAML Coder Agent。

    Parameters
    ----------
    semantic_workflow: SemanticWorkflow 实例
    user_params: 用户提供的额外参数
    selected_implementations: step_id → node_name 的手动选择

    Returns
    -------
    YAMLCoderState: 包含 result (ConcretizationResult) 的最终状态
    """
    graph = get_yaml_coder_graph()

    initial_state: YAMLCoderState = {
        "semantic_workflow": semantic_workflow,
        "user_params": user_params or {},
        "selected_implementations": selected_implementations or {},
        "iteration": 0,
    }

    return graph.invoke(initial_state)
