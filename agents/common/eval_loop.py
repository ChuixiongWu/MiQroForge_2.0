"""agents/common/eval_loop.py — Generator-Evaluator LangGraph 子图工厂。

提供通用的 Generator-Evaluator 循环构建器。
所有生成型 Agent（YAML Coder、Node Generator）复用此框架。

模式：
    generate → evaluate → [passed? → END : iteration < max? → refine → evaluate → ...]

EvaluationResult 结构：
    {"passed": bool, "issues": [...], "suggestions": [...]}

最大迭代 3 次（可配置），未通过则返回最后版本 + 评判报告。
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from langgraph.graph import StateGraph, END

from agents.schemas import EvaluationResult


# 泛型状态类型（TypedDict 子类）
S = TypeVar("S", bound=dict)


def build_eval_loop(
    *,
    state_type: type,
    generate_fn: Callable,
    evaluate_fn: Callable,
    state_key: str,
    evaluation_key: str = "evaluation",
    iteration_key: str = "iteration",
    max_iterations: int = 3,
) -> Any:
    """构建一个 Generator-Evaluator LangGraph 子图。

    Parameters
    ----------
    state_type:
        LangGraph 状态 TypedDict 类型。
    generate_fn:
        生成节点函数 (state) -> state_updates。
        负责填充 state[state_key]（生成的内容）。
    evaluate_fn:
        评判节点函数 (state) -> state_updates。
        负责填充 state[evaluation_key]（EvaluationResult）。
    state_key:
        状态中存储生成内容的键名。
    evaluation_key:
        状态中存储 EvaluationResult 的键名。
    iteration_key:
        状态中存储迭代次数的键名。
    max_iterations:
        最大迭代次数（默认 3）。

    Returns
    -------
    CompiledGraph
        可调用的 LangGraph 子图。
    """

    def _route(state: dict) -> str:
        """路由决策：通过 → END，否则继续迭代。"""
        evaluation: EvaluationResult | None = state.get(evaluation_key)
        iteration: int = state.get(iteration_key, 0)

        if evaluation and evaluation.passed:
            return "end"
        if iteration >= max_iterations:
            # 达到最大迭代，强制结束
            return "end"
        return "refine"

    def _increment_iteration(state: dict) -> dict:
        """迭代计数器递增。"""
        return {iteration_key: state.get(iteration_key, 0) + 1}

    graph = StateGraph(state_type)

    # 节点注册
    graph.add_node("generate", generate_fn)
    graph.add_node("evaluate", evaluate_fn)
    graph.add_node("increment", _increment_iteration)

    # 入口
    graph.set_entry_point("generate")

    # 生成 → 评判
    graph.add_edge("generate", "evaluate")

    # 评判 → 路由
    graph.add_conditional_edges(
        "evaluate",
        _route,
        {
            "end": END,
            "refine": "increment",
        },
    )

    # 递增后回到生成（refine 阶段，generate_fn 会读取 evaluation 的 issues 做修正）
    graph.add_edge("increment", "generate")

    return graph.compile()
