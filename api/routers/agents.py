"""api/routers/agents.py — Phase 2 Agent API 端点。

提供三个独立可调用的 Agent 端点：
  POST /api/v1/agents/plan          — Planner Agent
  POST /api/v1/agents/yaml          — YAML Coder Agent
  POST /api/v1/agents/node          — Node Generator Agent
  POST /api/v1/agents/save-session  — 保存对话会话到 userdata/agent_sessions/
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.agents import (
    PlanRequest, PlanResponse,
    YAMLRequest, YAMLResponse,
    NodeGenAPIRequest, NodeGenAPIResponse,
    SaveSessionRequest, SaveSessionResponse,
)
from agents.schemas import NodeGenRequest
from agents.common.session_logger import (
    start_session, end_session,
    save_agent_log, save_conversation,
)

router = APIRouter(prefix="/agents", tags=["agents"])


# ─── Planner Agent ────────────────────────────────────────────────────────────

@router.post("/plan", response_model=PlanResponse, summary="运行 Planner Agent")
async def plan_workflow(
    request: PlanRequest,
    settings: Settings = Depends(get_settings),
) -> PlanResponse:
    """解析用户意图，通过 RAG 检索节点，生成语义工作流蓝图。"""
    try:
        from agents.planner.graph import run_planner

        # 前端未传 session_id 时，服务端自动生成（确保日志总能被保存）
        effective_session_id = (
            request.session_id
            or f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        def _run_with_session():
            session = start_session("planner", {
                "intent": request.intent,
                "molecule": request.molecule,
                "preferences": request.preferences,
            })
            try:
                state = run_planner(
                    intent=request.intent,
                    molecule=request.molecule,
                    preferences=request.preferences,
                )
                return state
            finally:
                log = end_session()
                if log:
                    try:
                        save_agent_log(
                            log.to_dict(),
                            session_id=effective_session_id,
                            userdata_root=settings.userdata_root,
                        )
                    except Exception:
                        pass

        state = await asyncio.to_thread(_run_with_session)

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
async def generate_yaml(
    request: YAMLRequest,
    settings: Settings = Depends(get_settings),
) -> YAMLResponse:
    """将语义工作流翻译为可执行的 MF YAML。"""
    try:
        from agents.yaml_coder.graph import run_yaml_coder

        effective_session_id = (
            request.session_id
            or f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        def _run_with_session():
            start_session("yaml_coder", {
                "workflow_name": request.semantic_workflow.name,
                "step_count": len(request.semantic_workflow.steps),
                "selected_implementations": request.selected_implementations,
            })
            try:
                state = run_yaml_coder(
                    semantic_workflow=request.semantic_workflow,
                    user_params=request.user_params,
                    selected_implementations=request.selected_implementations,
                )
                return state
            finally:
                log = end_session()
                if log:
                    try:
                        save_agent_log(
                            log.to_dict(),
                            session_id=effective_session_id,
                            userdata_root=settings.userdata_root,
                        )
                    except Exception:
                        pass

        state = await asyncio.to_thread(_run_with_session)

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
async def generate_node(
    request: NodeGenAPIRequest,
    settings: Settings = Depends(get_settings),
) -> NodeGenAPIResponse:
    """生成新的正式节点（nodespec.yaml + run.sh + 模板）。"""
    try:
        from agents.node_generator.graph import run_node_generator

        gen_request = NodeGenRequest(
            semantic_type=request.semantic_type,
            description=request.description,
            target_software=request.target_software,
            target_method=request.target_method,
            category=request.category,
        )

        effective_session_id = (
            request.session_id
            or f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        def _run_with_session():
            start_session("node_generator", {
                "semantic_type": request.semantic_type,
                "target_software": request.target_software,
                "category": request.category,
            })
            try:
                state = run_node_generator(gen_request)
                return state
            finally:
                log = end_session()
                if log:
                    try:
                        save_agent_log(
                            log.to_dict(),
                            session_id=effective_session_id,
                            userdata_root=settings.userdata_root,
                        )
                    except Exception:
                        pass

        state = await asyncio.to_thread(_run_with_session)
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


# ─── Save Session ─────────────────────────────────────────────────────────────

@router.post("/save-session", response_model=SaveSessionResponse, summary="保存对话会话")
async def save_session(
    request: SaveSessionRequest,
    settings: Settings = Depends(get_settings),
) -> SaveSessionResponse:
    """将前端对话消息保存到 userdata/agent_sessions/{date}/{session_id}/conversation.json。

    由前端在用户清空对话面板时调用，保存完整的对话历史。
    Agent 调用详情（prompt + LLM response）已在每次调用时自动保存。
    """
    try:
        saved_path = await asyncio.to_thread(
            save_conversation,
            messages=request.messages,
            session_id=request.session_id,
            userdata_root=settings.userdata_root,
        )
        return SaveSessionResponse(
            saved=True,
            session_id=request.session_id,
            path=str(saved_path.relative_to(settings.project_root)),
            message_count=len(request.messages),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存会话失败: {e}")
