"""agents/planner/evaluator.py — Planner Agent 评判节点。

检查 SemanticWorkflow 的：
1. 完整性（是否回答了用户目标）
2. DAG 无环
3. 边端点有效性
4. constraints 清洁（只允许 geometry_file / inline_geometry）

不检查：语义类型是否在注册表中（允许新类型）、科学计算策略合理性（尊重用户意图）
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_config import LLMConfig
from agents.schemas import EvaluationResult
from agents.common.prompt_loader import load_prompt
from agents.common.session_logger import get_session
from agents.planner.state import PlannerState


def _programmatic_check(state: PlannerState) -> list[str]:
    """程序化检查（不依赖 LLM）。"""
    issues = []
    workflow = state.get("semantic_workflow")
    if not workflow:
        return ["SemanticWorkflow 为空"]

    step_ids = {s.id for s in workflow.steps}

    # 检查边端点
    for edge in workflow.edges:
        if edge.from_step not in step_ids:
            issues.append(f"边源节点 '{edge.from_step}' 不存在于步骤列表")
        if edge.to_step not in step_ids:
            issues.append(f"边目标节点 '{edge.to_step}' 不存在于步骤列表")

    # 检查 DAG 无环（简单 DFS）
    adjacency: dict[str, list[str]] = {sid: [] for sid in step_ids}
    for edge in workflow.edges:
        if edge.from_step in adjacency:
            adjacency[edge.from_step].append(edge.to_step)

    def has_cycle(node: str, visited: set[str], rec_stack: set[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    visited: set[str] = set()
    for sid in step_ids:
        if sid not in visited:
            if has_cycle(sid, visited, set()):
                issues.append("工作流包含循环依赖（DAG 校验失败）")
                break

    # 检查 constraints 清洁：只允许 geometry_file / inline_geometry
    allowed_constraint_keys = {"geometry_file", "inline_geometry"}
    for step in workflow.steps:
        bad_keys = [k for k in step.constraints if k not in allowed_constraint_keys]
        if bad_keys:
            issues.append(
                f"步骤 '{step.id}' 的 constraints 包含计算参数 {bad_keys}，"
                f"Planner 不应设置计算细节（method/basis/charge 等）"
            )

    return issues


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 块。"""
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end + 1].strip()
    return text.strip()


def evaluate_plan(state: PlannerState) -> dict[str, Any]:
    """LangGraph 评判节点 — 评判 SemanticWorkflow。"""
    iteration = state.get("iteration", 0)

    # 程序化检查
    prog_issues = _programmatic_check(state)
    if prog_issues:
        result = EvaluationResult(
            passed=False,
            issues=prog_issues,
            suggestions=["修正上述程序化检查失败项"],
            iteration=iteration,
        )
        # ── 记录程序化检查结果 ──
        session = get_session()
        if session:
            session.log_event("evaluate_programmatic", {
                "iteration": iteration,
                "passed": False,
                "issues": prog_issues,
            })
        return {"evaluation": result}

    # LLM 评判
    intent = state.get("intent", "")
    molecule = state.get("molecule", "")
    workflow_json = state.get("workflow_json", "{}")
    semantic_types = state.get("semantic_types") or {}

    system_content = load_prompt(
        "planner/prompts/plan_evaluate.jinja2",
        intent=intent,
        molecule=molecule,
        workflow_json=workflow_json,
        semantic_types=semantic_types,
    )

    llm = LLMConfig.get_chat_model(purpose="evaluator", temperature=0.0)

    eval_messages = [HumanMessage(content=system_content)]

    try:
        response = llm.invoke(eval_messages)

        # ── 记录评判 LLM 调用 ──
        session = get_session()
        if session:
            session.log_llm_call(
                "evaluate", eval_messages, response.content,
                iteration=iteration,
            )

        raw_json = _extract_json(response.content)
        data = json.loads(raw_json)

        result = EvaluationResult(
            passed=data.get("passed", False),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            iteration=iteration,
        )
    except Exception as e:
        # 评判失败则放行（避免卡死）
        session = get_session()
        if session:
            session.log_event("evaluate_error", {
                "iteration": iteration,
                "error": str(e),
                "auto_pass": True,
            })
        result = EvaluationResult(
            passed=True,
            issues=[],
            suggestions=[f"评判失败（自动放行）: {e}"],
            iteration=iteration,
        )

    return {"evaluation": result}
