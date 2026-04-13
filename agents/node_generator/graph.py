"""agents/node_generator/graph.py — Node Generator Agent LangGraph 图。

双模式拓扑：

Formal 模式（正式节点）：
  START → generate → evaluate → [pass? END : refine → generate → ...]
  + finalize: 保存生成节点到 userdata/nodes/

Ephemeral 模式（临时节点）：
  START → generate → save → END
  （生成+执行+评估的完整循环在 _generate_ephemeral_agent 内部完成，
    API 端点负责外循环。）
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from agents.node_generator.state import NodeGenState
from agents.node_generator.generator import generate_node
from agents.node_generator.evaluator import evaluate_node
from agents.schemas import NodeGenResult, EvaluationResult


MAX_ITERATIONS = 3


def _is_ephemeral(state: NodeGenState) -> bool:
    request = state.get("request")
    return getattr(request, "node_mode", "formal") == "ephemeral" if request else False


# ─── Formal 模式路由 ───────────────────────────────────────────────────────────

def _route_after_evaluate(state: NodeGenState) -> str:
    """Formal 模式：评估后的路由。"""
    evaluation: EvaluationResult | None = state.get("evaluation")
    iteration: int = state.get("iteration", 0)
    if evaluation and evaluation.passed:
        return "end"
    if iteration >= MAX_ITERATIONS:
        return "end"
    return "refine"


# ─── 节点函数 ──────────────────────────────────────────────────────────────────

def _increment_iteration(state: NodeGenState) -> dict[str, Any]:
    return {"iteration": state.get("iteration", 0) + 1}


def _generate_with_feedback(state: NodeGenState) -> dict[str, Any]:
    """生成节点（带反馈上下文传递）。"""
    return generate_node(state)


def _save_to_userdata(state: NodeGenState) -> dict[str, Any]:
    """将生成的节点保存到 userdata/nodes/。"""
    request = state.get("request")
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "") or state.get("script", "")
    input_templates = state.get("input_templates") or {}

    if not request:
        return {}

    is_ephemeral = getattr(request, "node_mode", "formal") == "ephemeral"

    # ── 临时节点模式：不保存文件，直接返回脚本内容 ──
    if is_ephemeral:
        evaluation = state.get("evaluation")
        result = NodeGenResult(
            node_name=request.semantic_type or "ephemeral",
            nodespec_yaml="",
            run_sh=run_sh,
            input_templates={},
            saved_path=None,
            evaluation=evaluation,
            script_content=run_sh,
        )
        return {"result": result}

    if not nodespec_yaml:
        return {}

    # 提取节点名
    import yaml
    try:
        spec_data = yaml.safe_load(nodespec_yaml)
        node_name = spec_data.get("metadata", {}).get("name", "generated-node")
    except Exception:
        node_name = "generated-node"

    from api.config import get_settings
    settings = get_settings()

    # 保存路径：userdata/nodes/<category>/<node-name>/
    node_dir = settings.userdata_root / "nodes" / request.category / node_name
    node_dir.mkdir(parents=True, exist_ok=True)

    # 写 nodespec.yaml
    (node_dir / "nodespec.yaml").write_text(nodespec_yaml, encoding="utf-8")

    saved_path = str(node_dir.relative_to(settings.project_root))

    # 写 run.sh
    if run_sh:
        profile_dir = node_dir / "profile"
        profile_dir.mkdir(exist_ok=True)
        (profile_dir / "run.sh").write_text(run_sh, encoding="utf-8")
        (profile_dir / "run.sh").chmod(0o755)

        # 写输入模板
        for tpl_name, tpl_content in input_templates.items():
            (profile_dir / tpl_name).write_text(tpl_content, encoding="utf-8")

    # 触发 reindex
    try:
        from node_index.scanner import scan_nodes, write_index
        index = scan_nodes(settings.project_root)
        write_index(index, settings.project_root)
    except Exception:
        pass

    # 组装最终结果
    evaluation = state.get("evaluation")
    result = NodeGenResult(
        node_name=node_name,
        nodespec_yaml=nodespec_yaml,
        run_sh=run_sh,
        input_templates=input_templates,
        saved_path=saved_path,
        evaluation=evaluation,
    )
    return {"result": result}


# ─── 图构建 ────────────────────────────────────────────────────────────────────

def build_node_generator_graph():
    """构建并编译 Node Generator Agent LangGraph 图。

    Formal 模式：generate → evaluate → refine 循环。
    Ephemeral 模式：generate → save（Agent 内循环在 generate 内部完成）。
    """
    graph = StateGraph(NodeGenState)

    graph.add_node("generate", _generate_with_feedback)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("increment", _increment_iteration)
    graph.add_node("save", _save_to_userdata)

    graph.set_entry_point("generate")

    # 根据模式分支
    def _route_after_first_generate(state: NodeGenState) -> str:
        if _is_ephemeral(state):
            # ephemeral：Agent 已在内部完成完整循环，直接 save
            return "save"
        else:
            return "evaluate"

    graph.add_conditional_edges(
        "generate",
        _route_after_first_generate,
        {
            "evaluate": "evaluate",  # formal
            "save": "save",  # ephemeral: 直接 save
        },
    )

    # Formal: evaluate → [pass? save : refine → generate]
    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "end": "save",
            "refine": "increment",
        },
    )

    graph.add_edge("increment", "generate")
    graph.add_edge("save", END)

    return graph.compile()


_node_gen_graph = None


def get_node_generator_graph():
    global _node_gen_graph
    if _node_gen_graph is None:
        _node_gen_graph = build_node_generator_graph()
    return _node_gen_graph


def run_node_generator(request, **extra_state) -> NodeGenState:
    """运行 Node Generator Agent。

    Parameters:
        request: NodeGenRequest 实例。
        **extra_state: 额外的状态字段（如 context、ports 等）。
    """
    graph = get_node_generator_graph()
    initial_state: NodeGenState = {"request": request, "iteration": 0, **extra_state}
    return graph.invoke(initial_state)
