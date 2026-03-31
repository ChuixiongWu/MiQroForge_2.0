"""api/routers/agents.py — Phase 2 Agent API 端点。

提供三个独立可调用的 Agent 端点：
  POST /api/v1/agents/plan   — Planner Agent
  POST /api/v1/agents/yaml   — YAML Coder Agent
  POST /api/v1/agents/node   — Node Generator Agent
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.models.agents import (
    PlanRequest, PlanResponse,
    YAMLRequest, YAMLResponse,
    NodeGenAPIRequest, NodeGenAPIResponse,
)
from agents.schemas import NodeGenRequest

router = APIRouter(prefix="/agents", tags=["agents"])


# ─── Planner Agent ────────────────────────────────────────────────────────────

@router.post("/plan", response_model=PlanResponse, summary="运行 Planner Agent")
async def plan_workflow(request: PlanRequest) -> PlanResponse:
    """解析用户意图，通过 RAG 检索节点，生成语义工作流蓝图。

    输出 SemanticWorkflow（抽象语义步骤 + 候选实现），
    前端将其显示为 ❓ PendingNodes + 语义边。
    """
    try:
        from agents.planner.graph import run_planner

        state = await asyncio.to_thread(
            run_planner,
            intent=request.intent,
            molecule=request.molecule,
            preferences=request.preferences,
        )

        workflow = state.get("semantic_workflow")
        if not workflow:
            error_msg = state.get("error") or "Planner 未能生成工作流"
            raise HTTPException(status_code=500, detail=error_msg)

        return PlanResponse(
            semantic_workflow=workflow,
            evaluation=state.get("evaluation"),
            available_nodes=workflow.available_implementations,
            error=state.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planner Agent 失败: {e}")


# ─── YAML Coder Agent ─────────────────────────────────────────────────────────

@router.post("/yaml", response_model=YAMLResponse, summary="运行 YAML Coder Agent")
async def generate_yaml(request: YAMLRequest) -> YAMLResponse:
    """将语义工作流翻译为可执行的 MF YAML。

    复用 Phase 1 validator 做程序化校验。
    通过 Generator-Evaluator 循环（最多 3 次）修正错误。
    """
    try:
        from agents.yaml_coder.graph import run_yaml_coder

        state = await asyncio.to_thread(
            run_yaml_coder,
            semantic_workflow=request.semantic_workflow,
            user_params=request.user_params,
            selected_implementations=request.selected_implementations,
        )

        result = state.get("result")
        mf_yaml = state.get("mf_yaml", "")

        if not mf_yaml:
            error_msg = state.get("error") or "YAML Coder 未能生成 YAML"
            raise HTTPException(status_code=500, detail=error_msg)

        validation_report = {
            "valid": state.get("validation_valid", False),
            "errors": state.get("validation_errors", []),
            "warnings": state.get("validation_warnings", []),
        }

        return YAMLResponse(
            mf_yaml=mf_yaml,
            validation_report=validation_report,
            result=result,
            error=state.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YAML Coder Agent 失败: {e}")


# ─── Node Generator Agent ─────────────────────────────────────────────────────

@router.post("/node", response_model=NodeGenAPIResponse, summary="运行 Node Generator Agent")
async def generate_node(request: NodeGenAPIRequest) -> NodeGenAPIResponse:
    """生成新的正式节点（nodespec.yaml + run.sh + 模板）。

    生成结果保存到 userdata/nodes/<category>/<node-name>/，
    并自动触发节点索引重建（reindex）。
    """
    try:
        from agents.node_generator.graph import run_node_generator

        gen_request = NodeGenRequest(
            semantic_type=request.semantic_type,
            description=request.description,
            target_software=request.target_software,
            target_method=request.target_method,
            category=request.category,
        )

        state = await asyncio.to_thread(run_node_generator, gen_request)
        result = state.get("result")

        if not result:
            error_msg = state.get("error") or "Node Generator 未能生成节点"
            raise HTTPException(status_code=500, detail=error_msg)

        return NodeGenAPIResponse(
            node_name=result.node_name,
            nodespec_yaml=result.nodespec_yaml,
            run_sh=result.run_sh,
            input_templates=result.input_templates,
            saved_path=result.saved_path,
            evaluation=result.evaluation,
            error=state.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Node Generator Agent 失败: {e}")
