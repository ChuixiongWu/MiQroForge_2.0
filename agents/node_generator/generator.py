"""agents/node_generator/generator.py — Node Generator Agent 生成节点。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_config import LLMConfig
from agents.common.prompt_loader import load_prompt
from agents.common.session_logger import get_session
from agents.node_generator.state import NodeGenState
from agents.node_generator.knowledge import load_available_images, load_reference_nodes


def _parse_generated_output(text: str) -> dict[str, str]:
    """解析生成内容中的各部分（nodespec_yaml, run_sh, 模板）。"""
    sections: dict[str, str] = {}

    markers = {
        "nodespec_yaml": "=== NODESPEC_YAML ===",
        "run_sh": "=== RUN_SH ===",
        "input_template": "=== INPUT_TEMPLATE ===",
    }

    current_section = None
    current_lines: list[str] = []

    for line in text.splitlines():
        found_marker = False
        for key, marker in markers.items():
            if marker in line:
                # 保存上一节
                if current_section:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = key
                current_lines = []
                found_marker = True
                break

        if not found_marker and current_section:
            current_lines.append(line)

    # 保存最后一节
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # 清除代码块标记
    for key in list(sections.keys()):
        val = sections[key]
        if val.startswith("```yaml") or val.startswith("```bash") or val.startswith("```"):
            # 找到第一行后的内容，直到最后的 ```
            lines = val.splitlines()
            if lines:
                lines = lines[1:]  # 移除第一行的 ``` 标记
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            sections[key] = "\n".join(lines).strip()

    return sections


def _load_semantic_types() -> dict[str, Any]:
    from pathlib import Path
    import yaml
    registry_path = (
        Path(__file__).parent.parent.parent / "nodes" / "schemas" / "semantic_registry.yaml"
    )
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("types", {})


def generate_node(state: NodeGenState) -> dict[str, Any]:
    """LangGraph 生成节点 — 生成或修正节点定义。"""
    request = state.get("request")
    if not request:
        return {"error": "缺少 NodeGenRequest 输入"}

    iteration = state.get("iteration", 0)
    evaluation = state.get("evaluation")
    is_ephemeral = getattr(request, "node_mode", "formal") == "ephemeral"

    # 首次加载知识
    available_images = state.get("available_images") or load_available_images()
    semantic_types = state.get("semantic_types") or _load_semantic_types()
    reference_nodes = state.get("reference_nodes") or load_reference_nodes(
        target_software=request.target_software,
        semantic_type=request.semantic_type,
    )

    if is_ephemeral:
        # ── 临时节点模式：生成纯 Python 脚本 ──
        system_content = load_prompt(
            "node_generator/prompts/nodegen_ephemeral_system.jinja2",
        )
        user_content = load_prompt(
            "node_generator/prompts/nodegen_ephemeral_generate.jinja2",
            request=request.model_dump(),
            iteration=iteration,
            prev_nodespec=state.get("run_sh", ""),
            eval_issues=(evaluation.issues if evaluation and not evaluation.passed else []),
        )
    else:
        # ── 正式节点模式：生成完整 NodeSpec ──
        needs_template = request.target_software is not None

        system_content = load_prompt(
            "node_generator/prompts/nodegen_system.jinja2",
            available_images=available_images,
            semantic_types=semantic_types,
        )

        user_content = load_prompt(
            "node_generator/prompts/nodegen_generate.jinja2",
            request=request.model_dump(),
            reference_nodes=reference_nodes,
            iteration=iteration,
            prev_nodespec=state.get("nodespec_yaml", ""),
            eval_issues=(evaluation.issues if evaluation and not evaluation.passed else []),
            needs_template=needs_template,
        )

    llm = LLMConfig.get_chat_model(purpose="node_generator", temperature=0.1)

    gen_messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    try:
        response = llm.invoke(gen_messages)

        # ── 记录 LLM 调用 ──
        session = get_session()
        if session:
            session.log_llm_call(
                "generate", gen_messages, response.content,
                iteration=iteration,
            )

        sections = _parse_generated_output(response.content)

        if is_ephemeral:
            # 临时节点：只取 run_sh 部分（实际是 Python 脚本）
            script = sections.get("run_sh", "")
            # 如果解析失败，尝试将整个响应作为脚本
            if not script:
                script = response.content.strip()
            return {
                "nodespec_yaml": "",
                "run_sh": script,
                "input_templates": {},
                "available_images": available_images,
                "semantic_types": semantic_types,
                "reference_nodes": reference_nodes,
                "error": None,
            }

        return {
            "nodespec_yaml": sections.get("nodespec_yaml", ""),
            "run_sh": sections.get("run_sh", ""),
            "input_templates": (
                {"input.inp.template": sections["input_template"]}
                if "input_template" in sections else {}
            ),
            "available_images": available_images,
            "semantic_types": semantic_types,
            "reference_nodes": reference_nodes,
            "error": None,
        }

    except Exception as e:
        session = get_session()
        if session:
            session.log_event("generate_error", {
                "iteration": iteration,
                "error": str(e),
            })
        return {
            "nodespec_yaml": "",
            "run_sh": "",
            "input_templates": {},
            "available_images": available_images,
            "semantic_types": semantic_types,
            "reference_nodes": reference_nodes,
            "error": f"Node Generator 生成失败: {e}",
        }
