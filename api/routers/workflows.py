"""工作流 API 路由。

POST /api/v1/workflows/validate — 校验 MF YAML
POST /api/v1/workflows/compile  — 校验 + 编译
POST /api/v1/workflows/submit   — 校验 + 编译 + 提交到 Argo
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.workflows import (
    WorkflowCompileRequest,
    WorkflowCompileResponse,
    WorkflowSubmitRequest,
    WorkflowSubmitResponse,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    ValidationIssueResponse,
    ResolvedNodeResponse,
)
from api.services.argo_service import ArgoService
from api.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_service(settings: Settings = Depends(get_settings)) -> WorkflowService:
    return WorkflowService(settings.project_root, docker_hub_mirror=settings.docker_hub_mirror)


def get_argo_service(settings: Settings = Depends(get_settings)) -> ArgoService:
    return ArgoService(namespace=settings.argo_namespace)


@router.post("/validate", response_model=WorkflowValidateResponse, summary="校验 MF 工作流")
def validate_workflow(
    req: WorkflowValidateRequest,
    svc: WorkflowService = Depends(get_workflow_service),
) -> WorkflowValidateResponse:
    """
    校验 MF 格式工作流 YAML。

    - 解析节点 NodeSpec
    - 验证 Stream I/O 连接类型兼容性
    - 检查必填参数
    - DAG 无环检查

    校验失败返回 422（validation errors 在响应体中）。
    """
    try:
        report = svc.validate_yaml_str(req.yaml_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse workflow: {str(e)}")

    report_dict = svc.validate_report_to_dict(report)

    return WorkflowValidateResponse(
        valid=report_dict["valid"],
        errors=[ValidationIssueResponse(**i) for i in report_dict["errors"]],
        warnings=[ValidationIssueResponse(**i) for i in report_dict["warnings"]],
        infos=[ValidationIssueResponse(**i) for i in report_dict["infos"]],
        resolved_nodes={
            k: ResolvedNodeResponse(**v)
            for k, v in report_dict["resolved_nodes"].items()
        },
    )


@router.post("/compile", response_model=WorkflowCompileResponse, summary="编译 MF 工作流")
def compile_workflow(
    req: WorkflowCompileRequest,
    svc: WorkflowService = Depends(get_workflow_service),
) -> WorkflowCompileResponse:
    """
    校验并编译 MF YAML 为 Argo Workflow YAML + ConfigMaps。

    校验失败返回 400。
    """
    try:
        result = svc.compile_yaml_str(req.yaml_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

    return WorkflowCompileResponse(
        valid=True,
        argo_yaml=result["argo_yaml"],
        configmaps_count=len(result["configmaps"]),
        workflow=result["workflow"],
        configmaps=result["configmaps"],
    )


@router.post("/submit", response_model=WorkflowSubmitResponse, summary="提交工作流到 Argo")
def submit_workflow(
    req: WorkflowSubmitRequest,
    svc: WorkflowService = Depends(get_workflow_service),
    argo: ArgoService = Depends(get_argo_service),
    settings: Settings = Depends(get_settings),
) -> WorkflowSubmitResponse:
    """
    校验 + 编译 + 提交 MF 工作流到 Argo。

    校验失败返回 400。提交失败返回 502。
    提交成功后自动将 MF YAML 和 Argo YAML 保存到 runs/{name}/。
    """
    # 1. 编译
    try:
        result = svc.compile_yaml_str(req.yaml_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

    # 2. 提交
    try:
        submit_result = argo.submit(result["workflow"], result["configmaps"])
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Argo submission failed: {str(e)}")

    # 3. 保存 MF YAML + Argo YAML 到 runs/{name}/
    run_name = submit_result["workflow_name"]
    run_dir = settings.project_root / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "mf-workflow.yaml").write_text(req.yaml_content, encoding="utf-8")
    (run_dir / "argo-workflow.yaml").write_text(result["argo_yaml"], encoding="utf-8")

    return WorkflowSubmitResponse(**submit_result)
