"""工作流服务 — 调用现有的 loader → validator → compiler 管线。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from workflows.pipeline.compiler import compile_to_argo, compile_to_yaml_str, generate_configmaps
from workflows.pipeline.loader import load_workflow
from workflows.pipeline.models import MFWorkflow
from workflows.pipeline.validator import ValidationReport, validate_workflow


class WorkflowService:
    """工作流服务 — 封装 MF 管线的校验和编译功能。"""

    def __init__(self, project_root: Path, docker_hub_mirror: str = "") -> None:
        self.project_root = project_root
        self.docker_hub_mirror = docker_hub_mirror

    def validate_yaml_str(self, yaml_content: str) -> ValidationReport:
        """从 YAML 字符串校验工作流。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="mf-validate-"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            workflow = load_workflow(tmp_path)
            return validate_workflow(workflow, project_root=self.project_root)
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def compile_yaml_str(self, yaml_content: str, project_id: str = "") -> dict:
        """从 YAML 字符串编译工作流，返回 Argo YAML + ConfigMaps + 临时节点日志。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="mf-compile-"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            workflow = load_workflow(tmp_path)
            report = validate_workflow(workflow, project_root=self.project_root)

            if not report.valid:
                raise ValueError(
                    f"Workflow validation failed: "
                    + "; ".join(i.message for i in report.errors)
                )

            ephemeral_logs: dict = {}
            argo_dict = compile_to_argo(
                workflow, report.resolved_nodes,
                project_root=self.project_root,
                docker_hub_mirror=self.docker_hub_mirror,
                ephemeral_logs=ephemeral_logs,
                project_id=project_id,
            )
            configmaps = generate_configmaps(
                workflow, report.resolved_nodes, project_root=self.project_root
            )

            return {
                "workflow": argo_dict,
                "configmaps": configmaps,
                "argo_yaml": yaml.dump(argo_dict, default_flow_style=False, allow_unicode=True),
                "ephemeral_logs": ephemeral_logs,
            }
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def validate_report_to_dict(self, report: ValidationReport) -> dict:
        """将 ValidationReport 转换为 API 响应 dict。"""
        return {
            "valid": report.valid,
            "errors": [
                {"location": i.location, "message": i.message}
                for i in report.errors
            ],
            "warnings": [
                {"location": i.location, "message": i.message}
                for i in report.warnings
            ],
            "infos": [
                {"location": i.location, "message": i.message}
                for i in report.infos
            ],
            "resolved_nodes": {
                nid: {
                    "name": spec.metadata.name,
                    "version": spec.metadata.version,
                    "node_type": spec.metadata.node_type.value,
                }
                for nid, spec in report.resolved_nodes.items()
            },
        }
