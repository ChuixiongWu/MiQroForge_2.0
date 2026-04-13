"""agents/node_generator/evaluator.py — Node Generator Agent 评判节点。"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

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


def _programmatic_check_ephemeral(state: NodeGenState) -> list[str]:
    """临时节点的程序化检查。"""
    issues = []
    run_sh = state.get("run_sh", "") or state.get("script", "")

    if not run_sh:
        return ["生成的脚本内容为空"]

    # Python 语法检查
    try:
        compile(run_sh, "<ephemeral>", "exec")
    except SyntaxError as e:
        issues.append(f"Python 语法错误: {e}")

    # I/O 路径约定检查
    request = state.get("request")
    if request and request.ports:
        num_inputs = request.ports.get("inputs", 0)
        num_outputs = request.ports.get("outputs", 0)
        for i in range(1, num_inputs + 1):
            port_name = f"I{i}"
            expected = f"/mf/input/{port_name}"
            if expected not in run_sh:
                issues.append(f"脚本未读取输入端口 {port_name}（预期路径: {expected}）")
        for i in range(1, num_outputs + 1):
            port_name = f"O{i}"
            expected = f"/mf/output/{port_name}"
            if expected not in run_sh:
                issues.append(f"脚本未写入输出端口 {port_name}（预期路径: {expected}）")

    # Sweep 类型转换检查
    has_sweep_context = request and request.context and request.context.get("sweep_context")
    if has_sweep_context and run_sh:
        has_json_loads = "json.loads" in run_sh
        has_float_cast = "float(" in run_sh
        has_plot = any(kw in run_sh for kw in ("plt.", "plot", "matplotlib"))
        has_math = any(op in run_sh for op in (" + ", " - ", " * ", " / ", "math.", "np."))
        if has_json_loads and not has_float_cast and (has_plot or has_math):
            issues.append(
                "Sweep 上下文中的输入数据来自 Argo output 参数（字符串），"
                "但脚本未使用 float() 转换就在做数学运算或绘图。"
                "必须在使用前转换：energies = [float(v) for v in json.loads(...)]"
            )

    return issues


def _programmatic_check(state: NodeGenState) -> list[str]:
    """程序化检查。"""
    issues = []
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "")
    semantic_types = state.get("semantic_types") or {}
    request = state.get("request")
    is_ephemeral = getattr(request, "node_mode", "formal") == "ephemeral" if request else False

    if is_ephemeral:
        return _programmatic_check_ephemeral(state)

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
    request = state.get("request")
    is_ephemeral = getattr(request, "node_mode", "formal") == "ephemeral" if request else False

    if is_ephemeral:
        # ephemeral 模式：程序化检查 + 执行结果检查
        return _evaluate_ephemeral(state)

    # ── 正式节点模式 ──
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


def _evaluate_ephemeral(state: NodeGenState) -> dict[str, Any]:
    """临时节点模式的评估：程序化检查 + 执行结果检查。"""
    iteration = state.get("iteration", 0)
    return_code = state.get("exec_return_code", -1)
    exec_stderr = state.get("exec_stderr", "")
    image_files = state.get("image_files", [])

    # 1. 程序化检查
    prog_issues = _programmatic_check_ephemeral(state)

    # 2. 执行结果检查
    if return_code != 0:
        exec_issues = [f"脚本执行失败 (return_code={return_code})"]
        if exec_stderr:
            exec_issues.append(f"stderr: {exec_stderr[:1000]}")
        all_issues = prog_issues + exec_issues
        result = EvaluationResult(
            passed=False,
            issues=all_issues,
            suggestions=["修正执行错误"],
            iteration=iteration,
        )
        session = get_session()
        if session:
            session.log_event("evaluate_ephemeral_exec_fail", {
                "iteration": iteration,
                "return_code": return_code,
                "issues": all_issues,
            })
        return {"evaluation": result}

    # 3. 如果有程序化问题，返回失败
    if prog_issues:
        result = EvaluationResult(
            passed=False,
            issues=prog_issues,
            suggestions=["修正上述程序化检查失败项"],
            iteration=iteration,
        )
        session = get_session()
        if session:
            session.log_event("evaluate_ephemeral_prog_fail", {
                "iteration": iteration,
                "issues": prog_issues,
            })
        return {"evaluation": result}

    # 4. 无图片：检查有无输出文件即通过
    if not image_files:
        generated_files = state.get("generated_files", [])
        if generated_files:
            result = EvaluationResult(
                passed=True,
                issues=[],
                suggestions=["脚本执行成功，无图片输出"],
                iteration=iteration,
            )
            session = get_session()
            if session:
                session.log_event("evaluate_ephemeral_pass_no_images", {
                    "iteration": iteration,
                    "generated_files": generated_files,
                })
        else:
            result = EvaluationResult(
                passed=False,
                issues=["脚本未生成任何输出文件"],
                suggestions=["确保脚本写入了 /mf/output/ 或 /mf/workspace/"],
                iteration=iteration,
            )
            session = get_session()
            if session:
                session.log_event("evaluate_ephemeral_no_output", {
                    "iteration": iteration,
                })
        return {"evaluation": result}

    # 5. 有图片：调用视觉评估器
    # sandbox_dir 是持久化的，图片路径在评估时仍然有效
    return evaluate_node_vision(state)


def evaluate_node_vision(state: NodeGenState) -> dict[str, Any]:
    """多模态视觉评估：将图片发送给 GPT-4o 进行视觉检查。"""
    iteration = state.get("iteration", 0)
    request = state.get("request")
    script = state.get("script", "") or state.get("run_sh", "")
    exec_stdout = state.get("exec_stdout", "")
    exec_stderr = state.get("exec_stderr", "")
    image_files = state.get("image_files", [])

    # 加载图片为 base64
    images_b64: list[str] = []
    for img_path in image_files:
        try:
            img_bytes = Path(img_path).read_bytes()
            images_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
        except Exception:
            continue

    if not images_b64:
        # 无图片可评估，放行
        result = EvaluationResult(
            passed=True,
            issues=[],
            suggestions=["无图片需要评估"],
            iteration=iteration,
        )
        return {"evaluation": result}

    # 构建多模态消息
    prompt_text = load_prompt(
        "node_generator/prompts/nodegen_ephemeral_evaluate_vision.jinja2",
        description=request.description if request else "",
        ports=request.ports if request else {},
        script=script,
        stdout=exec_stdout,
        stderr=exec_stderr,
        images=images_b64,
    )

    # 构建多模态 content：text + images
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    for b64 in images_b64[:4]:  # 最多 4 张图
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high",
            },
        })

    llm = LLMConfig.get_chat_model(purpose="evaluator_vision", temperature=0.0)

    eval_messages = [
        SystemMessage(
            content="You are a visual evaluator for computational chemistry outputs. "
                    "Analyze the provided images and script output carefully."
        ),
        HumanMessage(content=content),
    ]

    try:
        response = llm.invoke(eval_messages)

        session = get_session()
        if session:
            session.log_llm_call(
                "evaluate_vision", eval_messages, response.content,
                iteration=iteration,
                image_count=len(images_b64),
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
            session.log_event("evaluate_vision_error", {
                "iteration": iteration,
                "error": str(e),
                "auto_pass": True,
            })
        result = EvaluationResult(
            passed=True,  # 评判失败则放行
            issues=[],
            suggestions=[f"视觉评判失败（自动放行）: {e}"],
            iteration=iteration,
        )

    return {"evaluation": result}
