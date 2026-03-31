"""agents/yaml_coder/generator.py — YAML Coder Agent 生成节点。

负责：
1. 加载候选节点的完整 NodeSpec（Level 3）
2. 构建步骤 → 节点解析映射
3. 调用 LLM 生成 MF YAML
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_config import LLMConfig
from agents.schemas import NodeResolution
from agents.common.prompt_loader import load_prompt
from agents.yaml_coder.state import YAMLCoderState


def _load_node_details(semantic_workflow, selected_implementations: dict[str, str]) -> list[dict[str, Any]]:
    """加载所有候选节点的完整 NodeSpec（Level 3）。"""
    from vectorstore.retriever import get_retriever

    retriever = get_retriever()

    # 收集所有候选节点名称
    node_names = set()
    for step in semantic_workflow.steps:
        # 用户手动选择优先
        if step.id in selected_implementations:
            node_names.add(selected_implementations[step.id])
        # RAG 候选
        for node_name in semantic_workflow.available_implementations.get(step.id, []):
            node_names.add(node_name)

    if not node_names:
        return []

    return retriever.get_detailed(list(node_names))


def _build_resolutions(
    semantic_workflow,
    selected_implementations: dict[str, str],
    available_nodes: list[dict[str, Any]],
) -> list[NodeResolution]:
    """为每个语义步骤选择具体节点。"""
    node_by_name = {n["metadata"]["name"]: n for n in available_nodes if "metadata" in n}
    # Also try by top-level name
    for n in available_nodes:
        if isinstance(n, dict) and "name" in n and "metadata" not in n:
            node_by_name[n["name"]] = n

    resolutions = []
    for step in semantic_workflow.steps:
        # 用户指定 → RAG 候选 → 空
        selected_name = selected_implementations.get(step.id)
        if not selected_name:
            candidates = semantic_workflow.available_implementations.get(step.id, [])
            selected_name = candidates[0] if candidates else None

        resolution = NodeResolution(
            step_id=step.id,
            resolved_node=selected_name,
            onboard_params=dict(step.constraints),
            needs_new_node=(selected_name is None),
            new_node_request=step.description if selected_name is None else None,
        )
        # 设置 nodespec_path
        if selected_name and selected_name in node_by_name:
            node_data = node_by_name[selected_name]
            # NodeSpec dump 格式：metadata.name, nodespec_path 在 scanner 里是 entry.nodespec_path
            # 但 get_detailed() 返回的是 NodeSpec.model_dump()，没有 nodespec_path
            # 我们从 scanner 索引条目里找 nodespec_path
            pass

        resolutions.append(resolution)
    return resolutions


def _get_nodespec_path(node_name: str) -> str | None:
    """从节点索引获取 nodespec_path。"""
    try:
        from node_index.scanner import load_index
        from api.config import get_settings
        index = load_index(get_settings().project_root)
        for entry in index.entries:
            if entry.name == node_name:
                return entry.nodespec_path
    except Exception:
        pass
    return None


def generate_yaml(state: YAMLCoderState) -> dict[str, Any]:
    """LangGraph 生成节点 — 生成或修正 MF YAML。"""
    semantic_workflow = state.get("semantic_workflow")
    if not semantic_workflow:
        return {"error": "缺少 SemanticWorkflow 输入"}

    user_params = state.get("user_params") or {}
    selected_implementations = state.get("selected_implementations") or {}
    iteration = state.get("iteration", 0)
    evaluation = state.get("evaluation")

    # 加载完整 NodeSpec（Level 3）
    available_nodes = state.get("available_nodes")
    if not available_nodes:
        available_nodes = _load_node_details(semantic_workflow, selected_implementations)

    # 构建解析映射
    resolutions = state.get("resolutions")
    if not resolutions or iteration > 0:
        resolutions = _build_resolutions(semantic_workflow, selected_implementations, available_nodes)

    # 为 resolutions 补充 nodespec_path
    for res in resolutions:
        if res.resolved_node and not res.resolved_nodespec_path:
            path = _get_nodespec_path(res.resolved_node)
            if path:
                res.resolved_nodespec_path = path

    # 构建 Prompt 用的节点摘要（包含 nodespec_path）
    try:
        from node_index.scanner import load_index
        from api.config import get_settings
        index = load_index(get_settings().project_root)
        node_index_map = {e.name: e for e in index.entries}
    except Exception:
        node_index_map = {}

    prompt_nodes = []
    seen_names = set()
    for step in semantic_workflow.steps:
        node_name = selected_implementations.get(step.id) or (
            semantic_workflow.available_implementations.get(step.id, [None])[0]
        )
        if node_name and node_name not in seen_names:
            seen_names.add(node_name)
            entry = node_index_map.get(node_name)
            if entry:
                prompt_nodes.append({
                    "name": entry.name,
                    "nodespec_path": entry.nodespec_path,
                    "description": entry.description,
                    "semantic_type": entry.semantic_type,
                    "software": entry.software,
                    "stream_inputs": [p.model_dump() for p in entry.stream_inputs],
                    "stream_outputs": [p.model_dump() for p in entry.stream_outputs],
                    "onboard_inputs": [p.model_dump() for p in entry.onboard_inputs],
                })

    # 构建 Prompt
    system_content = load_prompt(
        "yaml_coder/prompts/yaml_system.jinja2",
        available_nodes=prompt_nodes,
    )

    user_content = load_prompt(
        "yaml_coder/prompts/yaml_generate.jinja2",
        semantic_workflow_json=json.dumps(semantic_workflow.model_dump(mode="json"), indent=2, ensure_ascii=False),
        resolutions=[r.model_dump() for r in resolutions],
        user_params=user_params,
        iteration=iteration,
        prev_yaml=state.get("mf_yaml", ""),
        validation_errors=state.get("validation_errors", []),
        evaluation_issues=evaluation.issues if evaluation and not evaluation.passed else [],
    )

    llm = LLMConfig.get_chat_model(purpose="yaml_coder", temperature=0.0)

    try:
        response = llm.invoke([
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ])
        mf_yaml = response.content.strip()

        # 去除可能的 markdown 代码块
        if mf_yaml.startswith("```yaml"):
            mf_yaml = mf_yaml[7:]
        elif mf_yaml.startswith("```"):
            mf_yaml = mf_yaml[3:]
        if mf_yaml.endswith("```"):
            mf_yaml = mf_yaml[:-3]
        mf_yaml = mf_yaml.strip()

        return {
            "mf_yaml": mf_yaml,
            "available_nodes": available_nodes,
            "resolutions": resolutions,
            "error": None,
        }

    except Exception as e:
        return {
            "mf_yaml": "",
            "available_nodes": available_nodes,
            "resolutions": resolutions,
            "error": f"YAML Coder 生成失败: {e}",
        }
