"""agents/tools/validate_workflow.py — MF YAML 校验工具。

复用 Phase 1 的 workflow pipeline validator，
让 Agent 可以在生成后立即做程序化校验。
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def validate_mf_yaml(yaml_content: str) -> dict[str, Any]:
    """校验 MF YAML 工作流定义。

    复用 Phase 1 validator，检查端口类型兼容性、DAG 无环、参数完整性等。

    Args:
        yaml_content: MF YAML 字符串内容

    Returns:
        校验结果字典，包含：
          - valid (bool): 是否通过
          - errors (list): 错误列表（阻断提交）
          - warnings (list): 警告列表（不阻断）
          - infos (list): 信息列表
    """
    import tempfile
    from pathlib import Path
    from workflows.pipeline.loader import load_workflow
    from workflows.pipeline.validator import validate_workflow
    from api.config import get_settings

    settings = get_settings()

    try:
        # 写临时文件
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
            "errors": [{"message": e.message, "node_id": e.node_id} for e in result.errors],
            "warnings": [{"message": w.message, "node_id": w.node_id} for w in result.warnings],
            "infos": [{"message": i.message, "node_id": i.node_id} for i in result.infos],
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [{"message": f"校验失败: {e}", "node_id": None}],
            "warnings": [],
            "infos": [],
        }
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
