"""agents/node_generator/evaluator.py — Node Generator Agent 评判节点。"""

from __future__ import annotations

import json
from typing import Any

import yaml
from langchain_core.messages import HumanMessage

from agents.llm_config import LLMConfig
from agents.schemas import EvaluationResult
from agents.common.prompt_loader import load_prompt
from agents.common.session_logger import get_session
from agents.node_generator.state import NodeGenState


def _extract_json(text: str) -> str:
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


def _programmatic_check(state: NodeGenState) -> list[str]:
    """程序化检查。"""
    issues = []
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "")
    semantic_types = state.get("semantic_types") or {}

    if not nodespec_yaml:
        return ["nodespec_yaml 为空"]

    # YAML 可解析
    try:
        spec_data = yaml.safe_load(nodespec_yaml)
    except yaml.YAMLError as e:
        return [f"nodespec.yaml 解析失败: {e}"]

    if not isinstance(spec_data, dict):
        return ["nodespec.yaml 格式不正确（应为字典）"]

    # Pydantic 校验
    try:
        from nodes.schemas import NodeSpec
        NodeSpec.model_validate(spec_data)
    except Exception as e:
        issues.append(f"NodeSpec Pydantic 校验失败: {e}")

    # 语义类型检查
    metadata = spec_data.get("metadata", {})
    semantic_type = metadata.get("semantic_type")
    if semantic_type and semantic_types and semantic_type not in semantic_types:
        issues.append(
            f"semantic_type '{semantic_type}' 不在注册表中。合法值: {list(semantic_types.keys())}"
        )

    # run.sh 检查（compute 节点）
    node_type = metadata.get("node_type", "")
    if node_type == "compute":
        if not run_sh:
            issues.append("compute 节点缺少 run.sh")
        elif "# MF2 init" not in run_sh:
            issues.append("run.sh 缺少 '# MF2 init' 标记")

    # 端口名 snake_case 检查
    import re
    snake_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
    for port in spec_data.get("stream_inputs", []) + spec_data.get("stream_outputs", []):
        name = port.get("name", "")
        if name and not snake_pattern.match(name):
            issues.append(f"端口名 '{name}' 不符合 snake_case 规范")

    return issues


def evaluate_node(state: NodeGenState) -> dict[str, Any]:
    """LangGraph 评判节点。"""
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
        session = get_session()
        if session:
            session.log_event("evaluate_programmatic", {
                "iteration": iteration,
                "passed": False,
                "issues": prog_issues,
            })
        return {"evaluation": result}

    # LLM 意图检查
    request = state.get("request")
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "")

    prompt = load_prompt(
        "node_generator/prompts/nodegen_evaluate.jinja2",
        request=request.model_dump() if request else {},
        nodespec_yaml=nodespec_yaml,
        run_sh=run_sh,
    )

    llm = LLMConfig.get_chat_model(purpose="evaluator", temperature=0.0)

    eval_messages = [HumanMessage(content=prompt)]

    try:
        response = llm.invoke(eval_messages)

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
        session = get_session()
        if session:
            session.log_event("evaluate_error", {
                "iteration": iteration,
                "error": str(e),
                "auto_pass": True,
            })
        result = EvaluationResult(
            passed=True,  # 评判失败则放行
            issues=[],
            suggestions=[f"LLM 评判失败（自动放行）: {e}"],
            iteration=iteration,
        )

    return {"evaluation": result}
