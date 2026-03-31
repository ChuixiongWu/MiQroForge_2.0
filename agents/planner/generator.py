"""agents/planner/generator.py — Planner Agent 生成节点。

负责：
1. 从语义注册表加载语义类型
2. 通过 RAG 检索候选节点
3. 调用 LLM 生成 SemanticWorkflow
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_config import LLMConfig
from agents.schemas import SemanticWorkflow, SemanticStep, SemanticEdge
from agents.common.prompt_loader import load_prompt
from agents.planner.state import PlannerState


def load_semantic_types() -> dict[str, Any]:
    """从 semantic_registry.yaml 加载所有语义类型。"""
    registry_path = (
        Path(__file__).parent.parent.parent / "nodes" / "schemas" / "semantic_registry.yaml"
    )
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("types", {})


def search_nodes_for_intent(intent: str, molecule: str = "") -> list[dict[str, Any]]:
    """RAG 检索与意图相关的节点摘要。"""
    query = f"{intent} {molecule}".strip()
    try:
        from vectorstore.retriever import get_retriever
        retriever = get_retriever()
        return retriever.search_summary(query, n=10)
    except Exception:
        return []


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 块。"""
    # 去除 markdown 代码块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    # 找最外层的 { }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end + 1].strip()
    return text.strip()


def _build_implementations(
    steps: list[SemanticStep],
    node_summaries: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """为每个步骤找到候选实现节点。"""
    implementations: dict[str, list[str]] = {}
    for step in steps:
        candidates = [
            n["name"]
            for n in node_summaries
            if n.get("semantic_type") == step.semantic_type
        ]
        implementations[step.id] = candidates
    return implementations


def generate_plan(state: PlannerState) -> dict[str, Any]:
    """LangGraph 生成节点 — 生成或修正语义工作流。"""
    intent = state.get("intent", "")
    molecule = state.get("molecule", "")
    preferences = state.get("preferences", "")
    iteration = state.get("iteration", 0)
    evaluation = state.get("evaluation")

    # 加载语义类型
    semantic_types = state.get("semantic_types") or load_semantic_types()

    # RAG 检索节点（首次或每次迭代）
    node_summaries = state.get("node_summaries") or search_nodes_for_intent(intent, molecule)

    # ── 获取 workspace 文件列表 ───────────────────────────────────────────────
    from api.config import get_settings
    workspace_dir = get_settings().userdata_root / "workspace"
    workspace_files: list[dict[str, Any]] = []
    if workspace_dir.exists():
        for f in sorted(workspace_dir.iterdir()):
            if f.is_file() and f.name != ".gitkeep":
                workspace_files.append({"name": f.name, "size_bytes": f.stat().st_size})

    # 构建 Prompt
    system_content = load_prompt(
        "planner/prompts/plan_system.jinja2",
        semantic_types=semantic_types,
    )

    # 用户消息包含意图 + workspace 文件 + 节点摘要
    user_content = load_prompt(
        "planner/prompts/plan_generate.jinja2",
        intent=intent,
        molecule=molecule,
        preferences=preferences,
        node_summaries=node_summaries,
        workspace_files=workspace_files,
    )

    # 修正轮次：附加评判反馈
    if iteration > 0 and evaluation and not evaluation.passed:
        prev_workflow = state.get("workflow_json", "")
        feedback = "\n\n## Previous Attempt (failed evaluation):\n"
        feedback += f"```json\n{prev_workflow}\n```\n"
        feedback += "\n## Issues to Fix:\n"
        for issue in evaluation.issues:
            feedback += f"- {issue}\n"
        if evaluation.suggestions:
            feedback += "\n## Suggestions:\n"
            for sug in evaluation.suggestions:
                feedback += f"- {sug}\n"
        feedback += "\n\nPlease output a corrected SemanticWorkflow JSON."
        user_content += feedback

    llm = LLMConfig.get_chat_model(purpose="planner", temperature=0.0)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    try:
        response = llm.invoke(messages)
        raw_json = _extract_json(response.content)
        data = json.loads(raw_json)

        # 解析为 SemanticWorkflow
        workflow = SemanticWorkflow.model_validate(data)

        # 补充候选实现（RAG 结果映射）
        implementations = _build_implementations(workflow.steps, node_summaries)
        workflow.available_implementations = implementations

        workflow_json = workflow.model_dump_json(indent=2)

        return {
            "semantic_workflow": workflow,
            "workflow_json": workflow_json,
            "node_summaries": node_summaries,
            "semantic_types": semantic_types,
            "error": None,
        }

    except Exception as e:
        return {
            "semantic_workflow": None,
            "workflow_json": "",
            "error": f"Planner 生成失败: {e}",
            "node_summaries": node_summaries,
            "semantic_types": semantic_types,
        }
