"""api/routers/agents.py — Phase 2 Agent API 端点。

提供三个独立可调用的 Agent 端点：
  POST /api/v1/agents/plan          — Planner Agent
  POST /api/v1/agents/yaml          — YAML Coder Agent
  POST /api/v1/agents/node          — Node Generator Agent
  POST /api/v1/agents/save-session  — 保存对话会话到 userdata/agent_sessions/
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.agents import (
    PlanRequest, PlanResponse,
    YAMLRequest, YAMLResponse,
    NodeGenAPIRequest, NodeGenAPIResponse,
    EphemeralGenRequest, EphemeralGenResponse,
    EphemeralEvalRequest, EphemeralEvalResponse,
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


# ─── Ephemeral Node Agent (Runtime) ────────────────────────────────────────────

def _load_ephemeral_settings() -> dict[str, Any]:
    """从 userdata/settings.yaml 加载 ephemeral 运行时配置。"""
    settings_path = Path(__file__).parent.parent.parent / "userdata" / "settings.yaml"
    if not settings_path.exists():
        return {}
    try:
        import yaml
        with settings_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("ephemeral", {})
    except Exception:
        return {}


@router.post("/ephemeral", response_model=EphemeralGenResponse, summary="运行临时节点 Agent")
async def ephemeral_generate(
    request: EphemeralGenRequest,
    settings: Settings = Depends(get_settings),
) -> EphemeralGenResponse:
    """为临时节点生成 Python 脚本并在服务端沙箱执行。

    由 Argo Pod 的 wrapper 脚本在运行时调用。
    内部运行完整的外循环（generate → evaluate → retry），wrapper 只需调一次。
    """
    try:
        from agents.node_generator.graph import run_node_generator
        from agents.node_generator.evaluator import evaluate_node
        from agents.schemas import NodeGenRequest

        gen_request = NodeGenRequest(
            semantic_type="ephemeral",
            description=request.description,
            node_mode="ephemeral",
            ports=request.ports,
            context=request.context,
        )

        ephemeral_cfg = _load_ephemeral_settings()
        max_outer = ephemeral_cfg.get("max_outer_rounds", 2)

        script = ""
        exec_stdout = ""
        exec_stderr = ""
        exec_return_code = -1
        generated_files: list[str] = []
        image_files: list[str] = []
        vision_feedback: list[str] = []
        evaluation = None
        sandbox_dirs: list[str] = []

        def _run_with_session():
            nonlocal script, exec_stdout, exec_stderr, exec_return_code
            nonlocal generated_files, image_files, vision_feedback, evaluation

            try:
                for outer_round in range(max_outer):
                    # --- Generate (含内循环 agent + sandbox) ---
                    start_session("node_generator_ephemeral", {
                        "description": request.description,
                        "ports": request.ports,
                        "outer_round": outer_round,
                        "run_name": request.run_name,
                        "project_id": request.project_id,
                    })
                    try:
                        state = run_node_generator(
                            gen_request,
                            _input_data=request.input_data,
                            iteration=outer_round,
                            script=script,
                            run_sh=script,
                            exec_stderr=exec_stderr,
                            vision_feedback=vision_feedback,
                        )
                    finally:
                        log = end_session()
                        if log:
                            try:
                                log_dict = log.to_dict()
                                if request.run_name and request.project_id:
                                    run_log_dir = (
                                        settings.userdata_root / "projects" / request.project_id
                                        / "runs" / request.run_name
                                    )
                                    run_log_dir.mkdir(parents=True, exist_ok=True)
                                    time_str = datetime.now().strftime("%H-%M-%S")
                                    agent_type = log_dict.get("agent_type", "unknown")
                                    filepath = run_log_dir / f"{agent_type}_gen_r{outer_round}_{time_str}.json"
                                    filepath.write_text(json.dumps(log_dict, indent=2, ensure_ascii=False, default=str))
                                else:
                                    effective_session_id = f"ephemeral-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                    save_agent_log(log_dict, session_id=effective_session_id, userdata_root=settings.userdata_root)
                            except Exception:
                                pass

                    script = state.get("script", "") or state.get("run_sh", "")
                    exec_stdout = state.get("exec_stdout", "")
                    exec_stderr = state.get("exec_stderr", "")
                    exec_return_code = state.get("exec_return_code", -1)
                    generated_files = state.get("generated_files", [])
                    image_files = state.get("image_files", [])

                    # 记录沙箱目录（用于后续清理）
                    sb_dir = state.get("_sandbox_dir", "")
                    if sb_dir:
                        sandbox_dirs.append(sb_dir)

                    # --- 执行失败 → 带 stderr 进下一轮 ---
                    if exec_return_code != 0:
                        vision_feedback = []
                        continue

                    # --- 执行成功 → 评估 ---
                    start_session("ephemeral_evaluator", {
                        "description": request.description,
                        "ports": request.ports,
                        "outer_round": outer_round,
                        "image_count": len(image_files),
                        "run_name": request.run_name,
                        "project_id": request.project_id,
                    })
                    try:
                        eval_state = {
                            "request": gen_request,
                            "script": script,
                            "run_sh": script,
                            "exec_stdout": exec_stdout,
                            "exec_stderr": exec_stderr,
                            "exec_return_code": exec_return_code,
                            "image_files": image_files,
                            "generated_files": generated_files,
                            "iteration": outer_round,
                        }
                        eval_result = evaluate_node(eval_state)
                    finally:
                        log = end_session()
                        if log:
                            try:
                                log_dict = log.to_dict()
                                if request.run_name and request.project_id:
                                    run_log_dir = (
                                        settings.userdata_root / "projects" / request.project_id
                                        / "runs" / request.run_name
                                    )
                                    run_log_dir.mkdir(parents=True, exist_ok=True)
                                    time_str = datetime.now().strftime("%H-%M-%S")
                                    filepath = run_log_dir / f"ephemeral_eval_r{outer_round}_{time_str}.json"
                                    filepath.write_text(json.dumps(log_dict, indent=2, ensure_ascii=False, default=str))
                                else:
                                    effective_session_id = f"ephemeral-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                    save_agent_log(log_dict, session_id=effective_session_id, userdata_root=settings.userdata_root)
                            except Exception:
                                pass

                    evaluation = eval_result.get("evaluation")
                    if evaluation and evaluation.passed:
                        break

                    # 评估不通过 → 带反馈进下一轮
                    if evaluation:
                        vision_feedback = evaluation.issues + evaluation.suggestions
                    else:
                        vision_feedback = []

            finally:
                # 清理沙箱工作目录
                from agents.node_generator.sandbox import cleanup_sandbox_dir
                for sb_dir in sandbox_dirs:
                    cleanup_sandbox_dir(Path(sb_dir))

        await asyncio.to_thread(_run_with_session)

        # success 要求：脚本执行成功 且 evaluator 通过（或未评估）
        eval_passed = evaluation.passed if evaluation else True
        overall_success = (exec_return_code == 0) and eval_passed

        # 将 sandbox 中生成的图片复制到项目作用域 workspace，使前端可通过项目 files API 访问
        if image_files:
            import shutil as _shutil
            if request.project_id:
                target_dir = settings.userdata_root / "workspace" / ".files" / request.project_id
            else:
                target_dir = settings.userdata_root / "workspace"
            target_dir.mkdir(parents=True, exist_ok=True)
            for img_path in image_files:
                try:
                    src = Path(img_path)
                    if src.is_file():
                        _shutil.copy2(src, target_dir / src.name)
                except Exception:
                    pass

        return EphemeralGenResponse(
            script=script,
            stdout=exec_stdout[:5000],
            stderr=exec_stderr[:2000],
            return_code=exec_return_code,
            success=overall_success,
            generated_files=generated_files,
            image_files=image_files,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ephemeral Agent 失败: {e}")


@router.post("/ephemeral/evaluate", response_model=EphemeralEvalResponse, summary="视觉评估临时节点输出")
async def ephemeral_evaluate(
    request: EphemeralEvalRequest,
    settings: Settings = Depends(get_settings),
) -> EphemeralEvalResponse:
    """对临时节点的输出进行多模态视觉评估。

    接收脚本输出和 base64 编码的图片，返回评估结果。
    """
    try:
        from agents.node_generator.evaluator import evaluate_node_vision
        from agents.schemas import NodeGenRequest

        gen_request = NodeGenRequest(
            semantic_type="ephemeral",
            description=request.description,
            node_mode="ephemeral",
            ports=request.ports,
        )

        state: dict[str, Any] = {
            "request": gen_request,
            "script": request.script,
            "run_sh": request.script,
            "exec_stdout": request.stdout,
            "exec_stderr": request.stderr,
            "exec_return_code": 0 if not request.stderr else 1,
            "image_files": [],  # 图片通过 base64 传入
            "iteration": 0,
        }

        # 将 base64 图片写入临时文件
        import tempfile
        import base64 as b64mod
        tmp_image_paths: list[str] = []
        if request.image_base64_list:
            tmpdir = tempfile.mkdtemp(prefix="mf_eval_")
            for i, b64str in enumerate(request.image_base64_list):
                img_path = f"{tmpdir}/image_{i}.png"
                with open(img_path, "wb") as f:
                    f.write(b64mod.b64decode(b64str))
                tmp_image_paths.append(img_path)
            state["image_files"] = tmp_image_paths

        def _run_eval():
            start_session("ephemeral_evaluator", {
                "description": request.description,
                "ports": request.ports,
                "image_count": len(request.image_base64_list),
                "run_name": request.run_name,
                "project_id": request.project_id,
            })
            try:
                return evaluate_node_vision(state)
            finally:
                log = end_session()
                if log:
                    try:
                        log_dict = log.to_dict()
                        if request.run_name and request.project_id:
                            run_log_dir = (
                                settings.userdata_root / "projects" / request.project_id
                                / "runs" / request.run_name
                            )
                            run_log_dir.mkdir(parents=True, exist_ok=True)
                            time_str = datetime.now().strftime("%H-%M-%S")
                            filepath = run_log_dir / f"ephemeral_evaluator_{time_str}.json"
                            filepath.write_text(json.dumps(log_dict, indent=2, ensure_ascii=False, default=str))
                        else:
                            effective_session_id = f"ephemeral-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                            save_agent_log(log_dict, session_id=effective_session_id, userdata_root=settings.userdata_root)
                    except Exception:
                        pass

        result = await asyncio.to_thread(_run_eval)

        # 清理临时文件
        for p in tmp_image_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass

        evaluation = result.get("evaluation")
        if evaluation:
            return EphemeralEvalResponse(
                passed=evaluation.passed,
                issues=evaluation.issues,
                suggestions=evaluation.suggestions,
            )
        return EphemeralEvalResponse(passed=True, issues=[], suggestions=["评估未返回结果"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ephemeral 评估失败: {e}")


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
