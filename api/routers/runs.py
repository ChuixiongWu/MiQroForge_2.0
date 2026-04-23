"""运行监控 API 路由。

GET  /api/v1/runs               — 列出 Argo 运行
GET  /api/v1/runs/{name}        — 运行详情
GET  /api/v1/runs/{name}/logs   — 运行日志
POST /api/v1/runs/{name}/save-outputs — 将输出参数写入 userdata/runs/{name}/outputs.json
"""

from __future__ import annotations

import json
import shutil
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.runs import RunDetailResponse, RunListResponse, RunLogsResponse, RunSummaryResponse
from api.services.argo_service import ArgoService
from api.services.project_service import ProjectService

router = APIRouter(prefix="/runs", tags=["runs"])


def get_argo_service(settings: Settings = Depends(get_settings)) -> ArgoService:
    return ArgoService(namespace=settings.argo_namespace)


@router.get("", response_model=RunListResponse, summary="列出所有运行")
def list_runs(
    project_id: str | None = None,
    settings: Settings = Depends(get_settings),
) -> RunListResponse:
    """纯本地 runs 列表，不依赖 Argo。"""
    import datetime

    runs: list[dict] = []
    if not project_id:
        return RunListResponse(total=0, runs=[])

    project_runs_dir = settings.userdata_root / "projects" / project_id / "runs"
    if not project_runs_dir.exists():
        return RunListResponse(total=0, runs=[])

    for d in sorted(project_runs_dir.iterdir(), key=lambda p: p.name, reverse=True):
        if not d.is_dir():
            continue
        name = d.name
        phase = "Local"
        started_at = None
        finished_at = None
        duration_seconds = None
        outputs_path = d / "outputs.json"
        if outputs_path.exists():
            try:
                data = json.loads(outputs_path.read_text())
                phase = data.get("phase", "Local")
                started_at = data.get("started_at") or None
                finished_at = data.get("finished_at") or None
            except (json.JSONDecodeError, OSError):
                pass
        # Fallback: use directory mtime if no timing in outputs.json
        if not finished_at:
            try:
                mtime = d.stat().st_mtime
                finished_at = datetime.datetime.fromtimestamp(
                    mtime, tz=datetime.timezone.utc
                ).isoformat()
            except OSError:
                pass
        # Compute duration from ISO timestamps
        if started_at and finished_at:
            try:
                t0 = datetime.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                t1 = datetime.datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                duration_seconds = (t1 - t0).total_seconds()
            except (ValueError, TypeError):
                pass
        runs.append({
            "name": name,
            "namespace": "",
            "uid": "",
            "phase": phase,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration_seconds,
            "labels": {},
        })

    return RunListResponse(
        total=len(runs),
        runs=[RunSummaryResponse(**r) for r in runs],
    )


@router.get("/{name}", response_model=RunDetailResponse, summary="运行详情")
def get_run(
    name: str,
    project_id: str | None = None,
    argo: ArgoService = Depends(get_argo_service),
    settings: Settings = Depends(get_settings),
) -> RunDetailResponse:
    # Try Argo first
    try:
        wf = argo.get_workflow(name)
        meta = wf.get("metadata", {})
        status = wf.get("status", {})
        return RunDetailResponse(
            name=meta.get("name", name),
            namespace=meta.get("namespace", ""),
            phase=status.get("phase", "Unknown"),
            raw=wf,
        )
    except RuntimeError:
        pass  # Fall through to local data

    # Fallback: local-only run
    if not project_id:
        raise HTTPException(status_code=404, detail=f"Run '{name}' not found in Argo or locally")

    run_dir = settings.userdata_root / "projects" / project_id / "runs" / name
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{name}' not found")

    phase = "Local"
    outputs_path = run_dir / "outputs.json"
    node_outputs: dict[str, str] = {}
    if outputs_path.exists():
        try:
            data = json.loads(outputs_path.read_text())
            phase = data.get("phase", "Local")
            node_outputs = data.get("node_outputs", {})
        except (json.JSONDecodeError, OSError):
            pass

    # Build a synthetic Argo-like raw response for the frontend
    raw: dict[str, Any] = {
        "metadata": {"name": name, "namespace": ""},
        "status": {"phase": phase, "nodes": {}},
    }

    return RunDetailResponse(
        name=name,
        namespace="",
        phase=phase,
        raw=raw,
    )


@router.delete("/{name}", status_code=204, summary="删除运行本地数据")
def delete_run(
    name: str,
    project_id: str | None = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """只删除本地 run 数据。Argo 数据由 TTL 策略自动清理。"""
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    run_dir = settings.userdata_root / "projects" / project_id / "runs" / name
    if run_dir.exists():
        shutil.rmtree(run_dir)


@router.get("/{name}/logs", response_model=RunLogsResponse, summary="运行日志")
def get_run_logs(name: str, argo: ArgoService = Depends(get_argo_service)) -> RunLogsResponse:
    try:
        logs = argo.get_logs(name)
    except RuntimeError:
        logs = "Argo workflow 已删除或不可达，日志不可用。"
    return RunLogsResponse(name=name, logs=logs)


@router.post("/{name}/save-outputs", summary="保存运行输出到 runs/ 目录")
def save_run_outputs(
    name: str,
    project_id: str | None = None,
    canvas: dict[str, Any] | None = Body(None),
    argo: ArgoService = Depends(get_argo_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    从 Argo 拉取工作流状态，将输出参数写入 userdata/runs/{name}/outputs.json。
    可选附带 canvas 状态（body），保存为 afterrun_canvas.json。
    由前端在运行到达终态时调用。
    """
    try:
        wf = argo.get_workflow(name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    status = wf.get("status", {})
    nodes = status.get("nodes", {})

    # 提取每个 Pod 节点的输出参数，key = "{canvasNodeId}.{paramName}"
    # 对 Failed/Error 节点，抓取 pod 日志存入 _error 字段
    node_outputs: dict[str, str] = {}
    node_errors: dict[str, dict[str, str]] = {}
    node_details: dict[str, dict[str, str]] = {}
    for node in nodes.values():
        if node.get("type") != "Pod":
            continue
        template_name = node.get("templateName", "")
        if not template_name.startswith("mf-"):
            continue
        canvas_id = template_name[3:]
        phase = node.get("phase", "")

        # Collect per-node timing
        node_details[canvas_id] = {
            "phase": phase,
            "started_at": node.get("startedAt", ""),
            "finished_at": node.get("finishedAt", ""),
        }

        # Collect output parameters
        for param in node.get("outputs", {}).get("parameters", []):
            if param.get("name") and param.get("value") is not None:
                node_outputs[f"{canvas_id}.{param['name']}"] = str(param["value"])

        # For failed nodes, grab pod logs
        if phase in ("Failed", "Error"):
            argo_node_id = node.get("id", "")  # This IS the pod name in Argo
            argo_message = node.get("message", "")
            try:
                logs = argo.get_pod_logs(argo_node_id, tail=500)
                if logs is None:
                    error_msg = f"Pod 已被清理或命名空间不可达\nArgo message: {argo_message}" if argo_message else "Pod 已被清理或命名空间不可达"
                else:
                    error_msg = logs
            except Exception:
                error_msg = f"Pod 已被清理或命名空间不可达\nArgo message: {argo_message}" if argo_message else "Pod 已被清理或命名空间不可达"
            node_outputs[f"{canvas_id}._error"] = error_msg
            node_errors[canvas_id] = {
                "pod_name": argo_node_id,
                "phase": phase,
                "message": argo_message,
            }

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    run_dir = settings.userdata_root / "projects" / project_id / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = run_dir / "outputs.json"
    # Workflow-level timing from Argo
    meta = wf.get("metadata", {})
    outputs_path.write_text(
        json.dumps(
            {
                "phase": status.get("phase", "Unknown"),
                "started_at": status.get("startedAt", ""),
                "finished_at": status.get("finishedAt", ""),
                "node_outputs": node_outputs,
                "node_errors": node_errors,
                "node_details": node_details,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Save afterrun_canvas if provided
    if canvas:
        svc = ProjectService()
        svc.save_afterrun_canvas(project_id, name, canvas)

    # Collect _error texts for failed nodes (so frontend can update nodeStatuses)
    error_texts: dict[str, str] = {}
    for key, val in node_outputs.items():
        if key.endswith("._error"):
            canvas_id = key.rsplit("._error", 1)[0]
            error_texts[canvas_id] = val

    return {
        "saved": True,
        "run": name,
        "outputs_count": len(node_outputs),
        "error_texts": error_texts,
    }


@router.get("/{name}/afterrun-canvas", summary="获取 run 后画布状态")
def get_afterrun_canvas(
    name: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """返回 run 完成后保存的画布状态（含节点输出值）。"""
    svc = ProjectService()
    canvas = svc.load_afterrun_canvas(project_id, name)
    if canvas is None:
        raise HTTPException(status_code=404, detail="afterrun_canvas.json not found")
    return canvas


@router.get("/{name}/node-logs/{node_id}", summary="获取失败节点的完整 Pod 日志")
def get_node_pod_logs(
    name: str,
    node_id: str,
    argo: ArgoService = Depends(get_argo_service),
) -> dict:
    """返回指定节点的完整 pod 日志。Pod 已删除时返回 404。"""
    try:
        logs = argo.get_pod_logs(node_id)
    except Exception:
        logs = None
    if logs is None:
        raise HTTPException(
            status_code=404,
            detail="Pod 已被清理或命名空间不可达",
        )
    return {"node_id": node_id, "logs": logs}
