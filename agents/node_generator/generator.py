"""agents/node_generator/generator.py — Node Generator Agent 生成节点。"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

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
            lines = val.splitlines()
            if lines:
                lines = lines[1:]
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


def _extract_script(text: str) -> str:
    """从 LLM 纯文本响应中提取脚本。优先使用 RUN_SH marker，否则从 markdown 提取。"""
    # 1. 尝试 marker 方式
    sections = _parse_generated_output(text)
    script = sections.get("run_sh", "")
    if script:
        return script

    # 2. 整个文本就是脚本（无 marker）
    script = text.strip()

    # 3. 从 markdown 代码块提取
    if "```python" in script:
        try:
            start = script.index("```python") + 9
            end = script.index("```", start)
            return script[start:end].strip()
        except ValueError:
            pass
    elif "```" in script:
        try:
            start = script.index("```") + 3
            end = script.index("```", start)
            return script[start:end].strip()
        except ValueError:
            pass

    return script


def _load_ephemeral_settings() -> dict[str, Any]:
    """从 userdata/settings.yaml 加载 ephemeral 运行时配置。"""
    from pathlib import Path
    import yaml
    settings_path = Path(__file__).parent.parent.parent / "userdata" / "settings.yaml"
    if not settings_path.exists():
        return {}
    try:
        with settings_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("ephemeral", {})
    except Exception:
        return {}


def generate_node(state: NodeGenState) -> dict[str, Any]:
    """LangGraph 生成节点 — 生成或修正节点定义。"""
    request = state.get("request")
    if not request:
        return {"error": "缺少 NodeGenRequest 输入"}

    iteration = state.get("iteration", 0)
    evaluation = state.get("evaluation")
    is_ephemeral = getattr(request, "node_mode", "formal") == "ephemeral"

    if is_ephemeral:
        return _generate_ephemeral_agent(state, request, iteration)

    # ── 正式节点模式：生成完整 NodeSpec ──
    available_images = state.get("available_images") or load_available_images()
    semantic_types = state.get("semantic_types") or _load_semantic_types()
    reference_nodes = state.get("reference_nodes") or load_reference_nodes(
        target_software=request.target_software,
        semantic_type=request.semantic_type,
    )

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

        session = get_session()
        if session:
            session.log_llm_call(
                "generate", gen_messages, response.content,
                iteration=iteration,
            )

        sections = _parse_generated_output(response.content)

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


def _generate_ephemeral_agent(
    state: NodeGenState,
    request: Any,
    iteration: int,
) -> dict[str, Any]:
    """临时节点模式：LLM Agent 循环，把 sandbox 当工具用。

    LLM 绑定 sandbox_execute 和 pip_install 两个工具：
    - 内循环：LLM 调工具 → 执行 → 看结果 → 自修正
    - LLM 不再调工具 = 完成 → 提取最终脚本

    Returns:
        dict 含 script, exec_stdout, exec_stderr, exec_return_code, image_files 等
    """
    from agents.node_generator.sandbox import (
        execute_script_sandbox,
        make_sandbox_tool,
        make_pip_install_tool,
        save_pip_history,
        create_sandbox_dir,
        cleanup_sandbox_dir,
    )

    # 加载配置
    ephemeral_cfg = _load_ephemeral_settings()
    max_inner_rounds = ephemeral_cfg.get("max_inner_rounds", 3)

    system_content = load_prompt("node_generator/prompts/nodegen_ephemeral_system.jinja2")

    # 收集真实输入数据预览
    input_data = state.get("_input_data") or {}
    input_data_preview: dict[str, str] = {}
    for k, v in input_data.items():
        input_data_preview[k] = v[:500] if len(v) > 500 else v

    prev_script = state.get("script", "")
    prev_stderr = state.get("exec_stderr", "")
    vision_feedback = state.get("vision_feedback", [])

    has_execution_history = bool(prev_script and (prev_stderr or vision_feedback))

    user_content = load_prompt(
        "node_generator/prompts/nodegen_ephemeral_generate.jinja2",
        request=request.model_dump(),
        iteration=iteration,
        prev_script=prev_script,
        prev_stderr=prev_stderr,
        vision_feedback=vision_feedback,
        input_data=input_data_preview,
        has_execution_history=has_execution_history,
    )

    # 构建工具（共享一个持久化沙箱目录，evaluator 可读取图片）
    context = request.context or {}
    sweep_ctx = context.get("sweep_context")
    env_overrides: dict[str, str] = {}

    # 注入 _sweep_keys 到 sandbox 环境变量
    # 优先从 context.sweep_context 读取，fallback 到 input_data 中的 _sweep_keys 文件
    if sweep_ctx:
        env_overrides["_sweep_keys"] = json.dumps(sweep_ctx.get("sweep_values", []))
    elif "_sweep_keys" in input_data:
        env_overrides["_sweep_keys"] = input_data["_sweep_keys"]
        # 同时构造 sweep_ctx 供 prompt 模板使用
        try:
            sweep_values = json.loads(input_data["_sweep_keys"])
            sweep_ctx = {"sweep_values": sweep_values}
        except (json.JSONDecodeError, KeyError):
            pass

    sandbox_dir = create_sandbox_dir()
    sandbox_tool = make_sandbox_tool(input_data, env_overrides, sandbox_dir=sandbox_dir)
    pip_tool, pip_history = make_pip_install_tool()

    # 绑定工具的 LLM
    llm = LLMConfig.get_chat_model(purpose="node_generator", temperature=0.1)
    llm_with_tools = llm.bind_tools([sandbox_tool, pip_tool])

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    script = ""
    exec_stdout = ""
    exec_stderr = ""
    exec_return_code = -1
    generated_files: list[str] = []
    image_files: list[str] = []
    sandbox_exec_count = 0
    max_tool_calls = max_inner_rounds * 2  # 安全上限（含 pip_install）
    last_tool_calls: list[str] = []  # 最后一次 LLM 调用的 tool_calls

    try:
        for _ in range(max_tool_calls):
            response = llm_with_tools.invoke(messages)

            # 记录 tool_calls 概要（不记完整 messages，最后一步才记）
            session = get_session()
            if session:
                tc_names = [tc.get("name", "") for tc in (response.tool_calls or [])]
                last_tool_calls = tc_names
                session.log_event("generate_agent_step", {
                    "iteration": iteration,
                    "tool_calls": tc_names,
                    "response_preview": response.content[:200] if response.content else "",
                })

            # LLM 不再调工具 → 完成
            if not response.tool_calls:
                messages.append(response)
                # 从对话历史中取最后调用 sandbox_execute 时的脚本
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc.get("name") == "sandbox_execute":
                                script = tc.get("args", {}).get("script", "")
                                break
                        if script:
                            break
                # fallback: 如果没有调过 sandbox，从 LLM 文本中提取
                if not script:
                    script = _extract_script(response.content)
                break

            # 追加 AI 消息（含 tool_calls）
            messages.append(response)

            # 执行每个工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                if tool_name == "sandbox_execute":
                    if sandbox_exec_count >= max_inner_rounds:
                        tool_result = json.dumps({
                            "error": f"Maximum sandbox executions ({max_inner_rounds}) reached.",
                            "return_code": -1,
                        })
                    else:
                        sandbox_exec_count += 1
                        result = sandbox_tool.invoke(tool_args)
                        tool_result = json.dumps(result)

                        # 记录最后一次成功执行的结果
                        result_dict = result if isinstance(result, dict) else json.loads(result)
                        exec_stdout = result_dict.get("stdout", "")
                        exec_stderr = result_dict.get("stderr", "")
                        exec_return_code = result_dict.get("return_code", -1)
                        image_files = result_dict.get("image_paths", result_dict.get("image_files", []))

                    # 日志：sandbox 调用的输入脚本和输出结果
                    session = get_session()
                    if session:
                        script_preview = tool_args.get("script", "")[:500]
                        result_preview = tool_result[:800]
                        session.log_event("sandbox_call", {
                            "iteration": iteration,
                            "sandbox_exec_count": sandbox_exec_count,
                            "script_preview": script_preview,
                            "result_preview": result_preview,
                            "return_code": exec_return_code,
                        })

                elif tool_name == "pip_install":
                    result = pip_tool.invoke(tool_args)
                    tool_result = str(result)

                    session = get_session()
                    if session:
                        session.log_event("pip_install_call", {
                            "iteration": iteration,
                            "package": tool_args.get("package", ""),
                            "result_preview": tool_result[:500],
                        })
                else:
                    tool_result = f"Unknown tool: {tool_name}"

                messages.append(ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_id,
                ))

        else:
            # 达到最大工具调用次数，从最后的 sandbox 调用取脚本
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get("name") == "sandbox_execute":
                            script = tc.get("args", {}).get("script", "")
                            break
                    if script:
                        break
                elif isinstance(msg, AIMessage) and msg.content:
                    script = _extract_script(msg.content)
                    break

        # 持久化 pip 历史
        save_pip_history(
            pip_history,
            description=request.description or "",
            userdata_root=None,
        )

        # 记录最终 LLM 响应（含完整对话上下文）
        session = get_session()
        if session:
            session.log_llm_call(
                "generate_agent_final", messages, script,
                iteration=iteration,
                sandbox_exec_count=sandbox_exec_count,
                exec_return_code=exec_return_code,
            )

        return {
            "nodespec_yaml": "",
            "run_sh": script,
            "script": script,
            "input_templates": {},
            "exec_stdout": exec_stdout,
            "exec_stderr": exec_stderr,
            "exec_return_code": exec_return_code,
            "generated_files": generated_files,
            "image_files": image_files,
            "_sandbox_dir": str(sandbox_dir),
            "error": None,
        }

    except Exception as e:
        session = get_session()
        if session:
            session.log_event("generate_agent_error", {
                "iteration": iteration,
                "error": str(e),
            })
        return {
            "nodespec_yaml": "",
            "run_sh": script,
            "script": script,
            "input_templates": {},
            "exec_stdout": exec_stdout,
            "exec_stderr": exec_stderr or str(e),
            "exec_return_code": exec_return_code,
            "generated_files": generated_files,
            "image_files": image_files,
            "_sandbox_dir": str(sandbox_dir),
            "error": f"Ephemeral Agent 生成失败: {e}",
        }
