"""运行监控 API 路由。

GET  /api/v1/runs               — 列出 Argo 运行
GET  /api/v1/runs/{name}        — 运行详情
GET  /api/v1/runs/{name}/logs   — 运行日志
POST /api/v1/runs/{name}/save-outputs — 将输出参数写入 userdata/runs/{name}/outputs.json
"""

from __future__ import annotations

import json
import shutil

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.runs import RunDetailResponse, RunListResponse, RunLogsResponse, RunSummaryResponse
from api.services.argo_service import ArgoService

router = APIRouter(prefix="/runs", tags=["runs"])


def get_argo_service(settings: Settings = Depends(get_settings)) -> ArgoService:
    return ArgoService(namespace=settings.argo_namespace)


@router.get("", response_model=RunListResponse, summary="列出所有运行")
def list_runs(argo: ArgoService = Depends(get_argo_service)) -> RunListResponse:
    try:
        runs = argo.list_workflows()
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return RunListResponse(
        total=len(runs),
        runs=[RunSummaryResponse(**r) for r in runs],
    )


@router.get("/{name}", response_model=RunDetailResponse, summary="运行详情")
def get_run(name: str, argo: ArgoService = Depends(get_argo_service)) -> RunDetailResponse:
    try:
        wf = argo.get_workflow(name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    meta = wf.get("metadata", {})
    status = wf.get("status", {})

    return RunDetailResponse(
        name=meta.get("name", name),
        namespace=meta.get("namespace", ""),
        phase=status.get("phase", "Unknown"),
        raw=wf,
    )


@router.delete("/{name}", status_code=204, summary="删除运行")
def delete_run(
    name: str,
    argo: ArgoService = Depends(get_argo_service),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        argo.delete_workflow(name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Sync: remove local userdata/runs/{name}/ directory (outputs.json etc.) if present
    run_dir = settings.userdata_root / "runs" / name
    if run_dir.exists():
        shutil.rmtree(run_dir)


@router.get("/{name}/logs", response_model=RunLogsResponse, summary="运行日志")
def get_run_logs(name: str, argo: ArgoService = Depends(get_argo_service)) -> RunLogsResponse:
    try:
        logs = argo.get_logs(name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return RunLogsResponse(name=name, logs=logs)


@router.post("/{name}/save-outputs", summary="保存运行输出到 runs/ 目录")
def save_run_outputs(
    name: str,
    argo: ArgoService = Depends(get_argo_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    从 Argo 拉取工作流状态，将输出参数写入 userdata/runs/{name}/outputs.json。
    由前端在运行到达终态时调用，补全 userdata/runs/ 目录的记录。
    """
    try:
        wf = argo.get_workflow(name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    status = wf.get("status", {})
    nodes = status.get("nodes", {})

    # 提取每个 Pod 节点的输出参数，key = "{canvasNodeId}.{paramName}"
    node_outputs: dict[str, str] = {}
    for node in nodes.values():
        if node.get("type") != "Pod":
            continue
        template_name = node.get("templateName", "")
        if not template_name.startswith("mf-"):
            continue
        canvas_id = template_name[3:]
        for param in node.get("outputs", {}).get("parameters", []):
            if param.get("name") and param.get("value") is not None:
                node_outputs[f"{canvas_id}.{param['name']}"] = str(param["value"])

    run_dir = settings.userdata_root / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = run_dir / "outputs.json"
    outputs_path.write_text(
        json.dumps(
            {"phase": status.get("phase", "Unknown"), "node_outputs": node_outputs},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {"saved": True, "run": name, "outputs_count": len(node_outputs)}
