"""Argo 服务 — 封装 argo CLI 调用。"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import yaml


class ArgoService:
    """Argo 工作流提交和查询服务。"""

    def __init__(self, namespace: str = "miqroforge-v2") -> None:
        self.namespace = namespace

    def submit(self, argo_dict: dict, configmaps: list[dict]) -> dict:
        """提交 Argo 工作流。

        Returns:
            {"workflow_name": str, "namespace": str, "uid": str}
        """
        # 先提交 ConfigMaps
        for cm in configmaps:
            self._apply_configmap(cm)

        # 提交工作流
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="mf-argo-"
        ) as f:
            yaml.dump(argo_dict, f, default_flow_style=False, allow_unicode=True)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["argo", "submit", tmp_path, "--namespace", self.namespace, "-o", "json"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"argo submit failed: {result.stderr}")

            output = json.loads(result.stdout)
            return {
                "workflow_name": output["metadata"]["name"],
                "namespace": output["metadata"]["namespace"],
                "uid": output["metadata"].get("uid", ""),
            }
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def list_workflows(self) -> list[dict]:
        """列出 namespace 中的所有工作流。"""
        result = subprocess.run(
            ["argo", "list", "--namespace", self.namespace, "-o", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"argo list failed: {result.stderr}")

        data = json.loads(result.stdout or "[]")
        if isinstance(data, dict):
            items = data.get("items") or []
        else:
            items = data

        return [self._workflow_summary(wf) for wf in (items or [])]

    def get_workflow(self, name: str) -> dict:
        """获取单个工作流的详细状态。"""
        result = subprocess.run(
            ["argo", "get", name, "--namespace", self.namespace, "-o", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"argo get failed: {result.stderr}")

        return json.loads(result.stdout)

    def delete_workflow(self, name: str) -> None:
        """删除单个工作流。"""
        result = subprocess.run(
            ["argo", "delete", name, "--namespace", self.namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"argo delete failed: {result.stderr}")

    def get_logs(self, name: str) -> str:
        """获取工作流日志。"""
        result = subprocess.run(
            ["argo", "logs", name, "--namespace", self.namespace],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr or "(no logs)"

    def _apply_configmap(self, cm: dict) -> None:
        """通过 kubectl apply 创建/更新 ConfigMap。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="mf-cm-"
        ) as f:
            yaml.dump(cm, f, default_flow_style=False, allow_unicode=True)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", tmp_path, "--namespace", self.namespace],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"kubectl apply ConfigMap failed: {result.stderr}")
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _workflow_summary(wf: dict) -> dict:
        """提取工作流摘要信息。"""
        meta = wf.get("metadata", {})
        status = wf.get("status", {})
        return {
            "name": meta.get("name", ""),
            "namespace": meta.get("namespace", ""),
            "uid": meta.get("uid", ""),
            "phase": status.get("phase", "Unknown"),
            "started_at": status.get("startedAt"),
            "finished_at": status.get("finishedAt"),
            "labels": meta.get("labels", {}),
        }
