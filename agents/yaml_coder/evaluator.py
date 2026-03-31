"""agents/yaml_coder/evaluator.py — YAML Coder Agent 评判节点。

检查生成的 MF YAML：
1. 程序化校验（Phase 1 validator）
2. LLM 意图忠实度检查
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from agents.llm_config import LLMConfig
from agents.schemas import EvaluationResult
from agents.common.prompt_loader import load_prompt
from agents.yaml_coder.state import YAMLCoderState


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


def _run_programmatic_validation(yaml_content: str) -> dict[str, Any]:
    """运行 Phase 1 validator 做程序化校验。"""
    from workflows.pipeline.loader import load_workflow
    from workflows.pipeline.validator import validate_workflow
    from api.config import get_settings

    settings = get_settings()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        workflow = load_workflow(tmp_path)
        result = validate_workflow(workflow, project_root=settings.project_root)

        return {
            "valid": result.valid,
            "errors": [e.message for e in result.errors],
            "warnings": [w.message for w in result.warnings],
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"校验异常: {e}"],
            "warnings": [],
        }
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def evaluate_yaml(state: YAMLCoderState) -> dict[str, Any]:
    """LangGraph 评判节点 — 评判生成的 MF YAML。"""
    iteration = state.get("iteration", 0)
    mf_yaml = state.get("mf_yaml", "")

    if not mf_yaml:
        result = EvaluationResult(
            passed=False,
            issues=["生成的 YAML 为空"],
            suggestions=["重新生成完整的 MF YAML"],
            iteration=iteration,
        )
        return {
            "evaluation": result,
            "validation_valid": False,
            "validation_errors": ["YAML 为空"],
            "validation_warnings": [],
        }

    # 程序化校验
    val = _run_programmatic_validation(mf_yaml)
    validation_valid = val["valid"]
    validation_errors = val["errors"]
    validation_warnings = val["warnings"]

    # LLM 意图评判
    semantic_workflow = state.get("semantic_workflow")
    semantic_workflow_json = (
        json.dumps(semantic_workflow.model_dump(mode="json"), indent=2, ensure_ascii=False)
        if semantic_workflow else "{}"
    )

    prompt = load_prompt(
        "yaml_coder/prompts/yaml_evaluate.jinja2",
        semantic_workflow_json=semantic_workflow_json,
        mf_yaml=mf_yaml,
        validation_valid=validation_valid,
        validation_errors=validation_errors,
    )

    llm = LLMConfig.get_chat_model(purpose="evaluator", temperature=0.0)

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw_json = _extract_json(response.content)
        data = json.loads(raw_json)

        passed = data.get("passed", False) and validation_valid
        issues = data.get("issues", [])
        if not validation_valid:
            issues = validation_errors + issues

        result = EvaluationResult(
            passed=passed,
            issues=issues,
            suggestions=data.get("suggestions", []),
            iteration=iteration,
        )
    except Exception as e:
        # 评判失败，仅依赖程序化结果
        result = EvaluationResult(
            passed=validation_valid,
            issues=validation_errors if not validation_valid else [],
            suggestions=[f"LLM 评判失败（仅程序化校验）: {e}"],
            iteration=iteration,
        )

    return {
        "evaluation": result,
        "validation_valid": validation_valid,
        "validation_errors": validation_errors,
        "validation_warnings": validation_warnings,
    }
