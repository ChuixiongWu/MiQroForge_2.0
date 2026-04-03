"""项目管理 REST API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.projects import (
    CanvasState,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationMeta,
    ProjectCreateRequest,
    ProjectDuplicateRequest,
    ProjectListResponse,
    ProjectMeta,
    ProjectUpdateRequest,
    SnapshotListResponse,
    SnapshotMeta,
)
from api.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

_svc: ProjectService | None = None


def _get_svc() -> ProjectService:
    global _svc
    if _svc is None:
        _svc = ProjectService()
    return _svc


# ── Projects CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=ProjectListResponse)
def list_projects():
    svc = _get_svc()
    projects = svc.list_projects()
    return ProjectListResponse(total=len(projects), projects=projects)


@router.post("", response_model=ProjectMeta, status_code=201)
def create_project(req: ProjectCreateRequest):
    svc = _get_svc()
    meta = svc.create_project(req.name, req.description, req.icon)
    return meta


@router.get("/{project_id}", response_model=ProjectMeta)
def get_project(project_id: str):
    svc = _get_svc()
    meta = svc.get_project(project_id)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


@router.patch("/{project_id}", response_model=ProjectMeta)
def update_project(project_id: str, req: ProjectUpdateRequest):
    svc = _get_svc()
    meta = svc.update_project(project_id, name=req.name, description=req.description, icon=req.icon)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


@router.delete("/{project_id}")
def delete_project(project_id: str):
    svc = _get_svc()
    ok = svc.delete_project(project_id)
    if not ok:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return {"deleted": project_id}


@router.post("/{project_id}/duplicate", response_model=ProjectMeta, status_code=201)
def duplicate_project(project_id: str, req: ProjectDuplicateRequest | None = None):
    svc = _get_svc()
    new_name = req.name if req else None
    meta = svc.duplicate_project(project_id, new_name)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


# ── Canvas ────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/canvas", response_model=CanvasState)
def get_canvas(project_id: str):
    svc = _get_svc()
    data = svc.load_canvas(project_id)
    if data is None:
        # Return empty canvas for existing projects without canvas yet
        if svc.get_project(project_id) is None:
            raise HTTPException(404, f"Project '{project_id}' not found")
        return CanvasState()
    return data


@router.put("/{project_id}/canvas")
def save_canvas(project_id: str, canvas: CanvasState):
    svc = _get_svc()
    ok = svc.save_canvas(project_id, canvas.model_dump())
    if not ok:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return {"saved": True}


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/{project_id}/conversations", response_model=list[ConversationMeta])
def list_conversations(project_id: str):
    svc = _get_svc()
    if svc.get_project(project_id) is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return svc.list_conversations(project_id)


@router.post("/{project_id}/conversations", response_model=ConversationMeta, status_code=201)
def create_conversation(project_id: str, req: ConversationCreateRequest):
    svc = _get_svc()
    conv = svc.create_conversation(project_id, req.title)
    if conv is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return conv


@router.get("/{project_id}/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(project_id: str, conv_id: str):
    svc = _get_svc()
    data = svc.load_conversation(project_id, conv_id)
    if data is None:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return data


@router.put("/{project_id}/conversations/{conv_id}")
def save_conversation(project_id: str, conv_id: str, body: dict):
    svc = _get_svc()
    messages = body.get("messages", [])
    ok = svc.save_conversation_messages(project_id, conv_id, messages)
    if not ok:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return {"saved": True}


@router.delete("/{project_id}/conversations/{conv_id}")
def delete_conversation(project_id: str, conv_id: str):
    svc = _get_svc()
    ok = svc.delete_conversation(project_id, conv_id)
    if not ok:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return {"deleted": conv_id}


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/snapshots", response_model=SnapshotListResponse)
def list_snapshots(project_id: str):
    svc = _get_svc()
    if svc.get_project(project_id) is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    snaps = svc.list_snapshots(project_id)
    return SnapshotListResponse(total=len(snaps), snapshots=snaps)


@router.post("/{project_id}/snapshots", response_model=SnapshotMeta, status_code=201)
def create_snapshot(project_id: str, body: dict):
    svc = _get_svc()
    name = body.get("name", "Untitled Snapshot")
    canvas = body.get("canvas", {})
    snap = svc.create_snapshot(project_id, name, canvas)
    if snap is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return snap


@router.delete("/{project_id}/snapshots/{snapshot_id}")
def delete_snapshot(project_id: str, snapshot_id: str):
    svc = _get_svc()
    ok = svc.delete_snapshot(project_id, snapshot_id)
    if not ok:
        raise HTTPException(404, f"Snapshot '{snapshot_id}' not found")
    return {"deleted": snapshot_id}
