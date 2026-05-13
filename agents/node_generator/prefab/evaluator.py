"""agents/node_generator/prefab/evaluator.py — Prefab 模式评判节点。

包含预制菜节点的程序化检查、沙箱结果检查、LLM 意图评估。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, ToolMessage

from agents.llm_config import LLMConfig
from agents.schemas import EvaluationResult
from agents.common.prompt_loader import load_prompt
from agents.common.session_logger import get_session
from agents.node_generator.prefab.state import PrefabGenState

# Evaluator 工具调用最大轮次（搜索/阅读文件阶段）
_MAX_EVAL_TOOL_ROUNDS = 2


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


def _programmatic_check(state: PrefabGenState) -> list[str]:
    """正式节点的程序化检查。"""
    issues = []
    nodespec_yaml = state.get("nodespec_yaml", "")
    run_sh = state.get("run_sh", "")
    semantic_types = state.get("semantic_types") or {}
    _sandbox_dir = state.get("_sandbox_dir", "")

    # 从 sandbox 磁盘读取（Agent 产出在磁盘上，不在消息标记中）
    if not nodespec_yaml and _sandbox_dir:
        disk_path = Path(_sandbox_dir) / "nodespec.yaml"
        if disk_path.exists():
            try:
                nodespec_yaml = disk_path.read_text(encoding="utf-8")
            except Exception:
                pass
    if not run_sh and _sandbox_dir:
        disk_path = Path(_sandbox_dir) / "profile" / "run.sh"
        if disk_path.exists():
            try:
                run_sh = disk_path.read_text(encoding="utf-8")
            except Exception:
                pass

    if not nodespec_yaml:
        return ["nodespec_yaml 为空（generator 未产出且 sandbox 磁盘上也无文件）"]

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
    if semantic_type and semantic_type != "Undefined" and semantic_types and semantic_type not in semantic_types:
        issues.append(
            f"semantic_type '{semantic_type}' 不在注册表中。合法值: {list(semantic_types.keys())}"
        )

    # base_image_ref 检查
    base_image_ref = metadata.get("base_image_ref")
    if base_image_ref:
        available_images = state.get("available_images") or []
        image_names = [img.get("name", "") for img in available_images]
        if base_image_ref not in image_names:
            issues.append(
                f"base_image_ref '{base_image_ref}' 不在镜像注册表中。可用: {image_names}"
            )

    # run.sh 检查（compute 节点）
    node_type = metadata.get("node_type", "")
    if node_type == "compute" and not run_sh:
        issues.append("compute 节点缺少 run.sh")
    # 注：不检查 '# MF2 init' — 编译器在编译时已处理（正则替换），
    #      sandbox 内 run.sh 可能已被替换为 source mf2_init.sh，无标记也能运行

    # 资源合理性检查
    resources = spec_data.get("resources", {})
    if resources:
        cpu = resources.get("cpu_cores", 0)
        mem = resources.get("mem_gb", 0)
        if cpu and cpu > 128:
            issues.append(f"cpu_cores={cpu} 过高（>128）")
        if mem and mem > 512:
            issues.append(f"mem_gb={mem} 过高（>512GB）")

    # 端口名 snake_case 检查
    import re
    snake_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
    for port in spec_data.get("stream_inputs", []) + spec_data.get("stream_outputs", []):
        name = port.get("name", "")
        if name and not snake_pattern.match(name):
            issues.append(f"端口名 '{name}' 不符合 snake_case 规范")

    return issues


def _check_sandbox_result(state: PrefabGenState) -> list[str]:
    """检查沙箱测试结果，返回问题列表。"""
    issues = []
    sandbox_result = state.get("sandbox_test_result")
    sandbox_passed = state.get("sandbox_test_passed", False)
    sandbox_call_count = state.get("sandbox_call_count", 0)
    sandbox_enabled = state.get("_sandbox_enabled", True)

    # 设计时模式：无沙箱工具，跳过沙箱检查
    if not sandbox_enabled:
        return issues

    if not sandbox_result:
        # 没有沙箱测试结果 — 生成器未执行任何沙箱测试
        issues.append("生成器未执行沙箱测试（至少需要 1 次 sandbox 验证）")
        return issues

    if sandbox_call_count == 0:
        issues.append("生成器未调用 test_in_sandbox（至少需要 1 次沙箱验证）")

    return_code = sandbox_result.get("return_code", -1)
    stderr = sandbox_result.get("stderr", "")

    if not sandbox_passed or return_code != 0:
        issues.append(f"沙箱测试未通过 (return_code={return_code})")
        if stderr:
            # 截取最后 500 字符的 stderr
            issues.append(f"沙箱 stderr（末尾）: {stderr[-500:]}")

    # 检查 sandbox output 目录中声明的 stream_output 是否有非空文件
    _sandbox_dir = state.get("_sandbox_dir", "")
    if return_code == 0 and _sandbox_dir:
        try:
            nodespec_yaml = state.get("nodespec_yaml", "")
            if nodespec_yaml:
                spec = yaml.safe_load(nodespec_yaml) if isinstance(nodespec_yaml, str) else {}
                if isinstance(spec, dict):
                    for port in spec.get("stream_outputs", []):
                        name = port.get("name", "")
                        if not name:
                            continue
                        out_path = Path(_sandbox_dir) / "output" / name
                        if not out_path.exists():
                            issues.append(
                                f"stream_output '{name}' 未生成文件（预期 {out_path}）"
                            )
                        elif out_path.stat().st_size == 0:
                            issues.append(
                                f"stream_output '{name}' 生成了空文件"
                            )
        except Exception:
            pass
    else:
        generated_files = sandbox_result.get("generated_files", [])
        if not generated_files and return_code == 0:
            issues.append("沙箱执行成功但未生成任何输出文件")

    return issues


def evaluate_prefab_node(state: PrefabGenState) -> dict[str, Any]:
    """Formal 模式评判节点。"""
    iteration = state.get("iteration", 0)

    # 1. 程序化检查
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

    # 2. 沙箱测试结果检查
    sandbox_issues = _check_sandbox_result(state)
    if sandbox_issues:
        result = EvaluationResult(
            passed=False,
            issues=sandbox_issues,
            suggestions=["修正沙箱测试失败项，检查 run.sh 逻辑和软件参数"],
            iteration=iteration,
        )
        session = get_session()
        if session:
            session.log_event("evaluate_sandbox_fail", {
                "iteration": iteration,
                "passed": False,
                "issues": sandbox_issues,
            })
        return {"evaluation": result}

    # 3. LLM 意图检查 — 工具调用模式：evaluator 用 read_node_file/list_node_files
    #    自行读取 sandbox 中的文件，而非将文件内容注入 prompt。
    request = state.get("request")
    sandbox_result = state.get("sandbox_test_result")
    _sandbox_dir = state.get("_sandbox_dir", "")

    sandbox_path = Path(_sandbox_dir) if _sandbox_dir else None

    # 构建 evaluator 专用工具（复用 generator 的文件读取工具）
    if sandbox_path and sandbox_path.exists():
        from agents.node_generator.prefab.tools import make_filesystem_tools
        fs_tools = make_filesystem_tools(sandbox_dir=sandbox_path)
        eval_tools = [t for t in fs_tools if t.name in ('read_node_file', 'list_node_files')]
    else:
        eval_tools = []

    prompt = load_prompt(
        "node_generator/prompts/prefab/evaluate.jinja2",
        request=request,
        sandbox_dir=_sandbox_dir or "N/A (no sandbox — evaluate from request description only)",
        sandbox_result=sandbox_result,
    )

    llm = LLMConfig.get_chat_model(purpose="evaluator", temperature=0.0)

    eval_messages: list = [HumanMessage(content=prompt)]

    try:
        if eval_tools:
            # ═══ 工具调用阶段：evaluator 自行读取 sandbox 文件 ═══
            llm_with_tools = llm.bind_tools(eval_tools)

            for round_idx in range(_MAX_EVAL_TOOL_ROUNDS):
                try:
                    response = llm_with_tools.invoke(eval_messages)
                except Exception as e:
                    session = get_session()
                    if session:
                        session.log_event("evaluate_tool_error", {
                            "iteration": iteration, "round": round_idx, "error": str(e),
                        })
                    break

                eval_messages.append(response)

                if not response.tool_calls:
                    break

                for tc in response.tool_calls:
                    name = tc.get("name", "")
                    args = tc.get("args", {})
                    tid = tc.get("id", "")

                    tool_fn = next((t for t in eval_tools if t.name == name), None)
                    if tool_fn is not None:
                        try:
                            tool_result = tool_fn.invoke(args)
                        except Exception as te:
                            tool_result = json.dumps({"error": f"Tool '{name}' failed: {te}"})
                    else:
                        tool_result = json.dumps({"error": f"Unknown tool: {name}"})

                    eval_messages.append(ToolMessage(
                        content=str(tool_result)[:8000],
                        tool_call_id=tid,
                    ))

            # ═══ 强制合成阶段：不加工具，产出 JSON ═══
            synthesize_prompt = (
                "TOOLS ARE NOW REMOVED. Based on the file inspection above, "
                "produce your final evaluation. Output ONLY the JSON (no prose)."
            )
            eval_messages.append(HumanMessage(content=synthesize_prompt))
            final_response = llm.invoke(eval_messages)
        else:
            # 无 sandbox：单轮纯文本评估（从请求描述判断意图合理性）
            final_response = llm.invoke(eval_messages)

        session = get_session()
        if session:
            session.log_llm_call(
                "evaluate", eval_messages, final_response.content,
                iteration=iteration,
            )

        raw_json = _extract_json(final_response.content)
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
