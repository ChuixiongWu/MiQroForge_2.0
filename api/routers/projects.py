"""项目管理 REST API。"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.auth import CurrentUser, require_user
from api.config import get_settings, Settings
from api.dependencies import get_user_paths
from api.user_paths import UserPaths
from api.models.projects import (
    CanvasState,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationMeta,
    ProjectBatchDeleteRequest,
    ProjectCreateRequest,
    ProjectDuplicateRequest,
    ProjectListResponse,
    ProjectMeta,
    ProjectReorderRequest,
    ProjectUpdateRequest,
    SnapshotListResponse,
    SnapshotMeta,
)
from api.services.project_service import ProjectService
from api.routers.files import FileEntry, FileListResponse, _safe_filename, _file_entry

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_svc(paths: UserPaths) -> ProjectService:
    return ProjectService(paths)


# ── Projects CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=ProjectListResponse)
def list_projects(
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    projects = svc.list_projects()
    return ProjectListResponse(total=len(projects), projects=projects)


@router.post("", response_model=ProjectMeta, status_code=201)
def create_project(
    req: ProjectCreateRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    meta = svc.create_project(req.name, req.description, req.icon)
    return meta


@router.get("/{project_id}", response_model=ProjectMeta)
def get_project(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    meta = svc.get_project(project_id)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


@router.patch("/{project_id}", response_model=ProjectMeta)
def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    meta = svc.update_project(project_id, name=req.name, description=req.description, icon=req.icon, order=req.order)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    ok = svc.delete_project(project_id)
    if not ok:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return {"deleted": project_id}


@router.post("/{project_id}/duplicate", response_model=ProjectMeta, status_code=201)
def duplicate_project(
    project_id: str,
    req: ProjectDuplicateRequest | None = None,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    new_name = req.name if req else None
    meta = svc.duplicate_project(project_id, new_name)
    if meta is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return meta


@router.put("/reorder")
def reorder_projects(
    req: ProjectReorderRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    svc.reorder_projects(req.ids)
    return {"reordered": len(req.ids)}


@router.post("/batch-delete")
def batch_delete_projects(
    req: ProjectBatchDeleteRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    deleted = svc.batch_delete_projects(req.ids)
    return {"deleted": deleted}


# ── Canvas ────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/canvas", response_model=CanvasState)
def get_canvas(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    data = svc.load_canvas(project_id)
    if data is None:
        if svc.get_project(project_id) is None:
            raise HTTPException(404, f"Project '{project_id}' not found")
        return CanvasState()
    return data


@router.put("/{project_id}/canvas")
def save_canvas(
    project_id: str,
    canvas: CanvasState,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    ok = svc.save_canvas(project_id, canvas.model_dump())
    if not ok:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return {"saved": True}


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/{project_id}/conversations", response_model=list[ConversationMeta])
def list_conversations(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    if svc.get_project(project_id) is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return svc.list_conversations(project_id)


@router.post("/{project_id}/conversations", response_model=ConversationMeta, status_code=201)
def create_conversation(
    project_id: str,
    req: ConversationCreateRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    conv = svc.create_conversation(project_id, req.title)
    if conv is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return conv


@router.get("/{project_id}/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(
    project_id: str,
    conv_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    data = svc.load_conversation(project_id, conv_id)
    if data is None:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return data


@router.put("/{project_id}/conversations/{conv_id}")
def save_conversation(
    project_id: str,
    conv_id: str,
    body: dict,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    messages = body.get("messages", [])
    ok = svc.save_conversation_messages(project_id, conv_id, messages)
    if not ok:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return {"saved": True}


@router.delete("/{project_id}/conversations/{conv_id}")
def delete_conversation(
    project_id: str,
    conv_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    ok = svc.delete_conversation(project_id, conv_id)
    if not ok:
        raise HTTPException(404, f"Conversation '{conv_id}' not found")
    return {"deleted": conv_id}


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/snapshots", response_model=SnapshotListResponse)
def list_snapshots(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    if svc.get_project(project_id) is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    snaps = svc.list_snapshots(project_id)
    return SnapshotListResponse(total=len(snaps), snapshots=snaps)


@router.post("/{project_id}/snapshots", response_model=SnapshotMeta, status_code=201)
def create_snapshot(
    project_id: str,
    body: dict,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    name = body.get("name", "Untitled Snapshot")
    canvas = body.get("canvas", {})
    snap = svc.create_snapshot(project_id, name, canvas)
    if snap is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    return snap


@router.delete("/{project_id}/snapshots/{snapshot_id}")
def delete_snapshot(
    project_id: str,
    snapshot_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
):
    svc = _get_svc(paths)
    ok = svc.delete_snapshot(project_id, snapshot_id)
    if not ok:
        raise HTTPException(404, f"Snapshot '{snapshot_id}' not found")
    return {"deleted": snapshot_id}


# ── Project Files ────────────────────────────────────────────────────────────

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _get_project_files_dir(project_id: str, paths: UserPaths) -> Path:
    """返回项目文件目录 userdata/workspace/proj_{pid}/（PVC 挂载，真实目录）。"""
    svc = _get_svc(paths)
    if svc.get_project(project_id) is None:
        raise HTTPException(404, f"Project '{project_id}' not found")
    from api.services.project_service import _project_files_dir
    return _project_files_dir(project_id)


class CopyFromWorkspaceRequest(BaseModel):
    filename: str


@router.get("/{project_id}/files", response_model=FileListResponse, summary="列出项目文件")
def list_project_files(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> FileListResponse:
    d = _get_project_files_dir(project_id, paths)
    entries = sorted(
        [_file_entry(p) for p in d.iterdir() if p.is_file() and p.name != ".gitkeep"],
        key=lambda e: e.name,
    )
    return FileListResponse(files=entries)


@router.post("/{project_id}/files/upload", summary="上传文件到项目")
async def upload_project_file(
    project_id: str,
    file: UploadFile,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> FileEntry:
    if not file.filename:
        raise HTTPException(400, detail="缺少文件名")
    safe_name = _safe_filename(file.filename)
    d = _get_project_files_dir(project_id, paths)
    dest = d / safe_name

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(413, detail="文件超过 50 MB 限制")

    dest.write_bytes(content)
    return _file_entry(dest)


@router.get("/{project_id}/files/{filename}", summary="下载项目文件")
def download_project_file(
    project_id: str,
    filename: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> FileResponse:
    safe_name = _safe_filename(filename)
    d = _get_project_files_dir(project_id, paths)
    file_path = d / safe_name
    if not file_path.is_file():
        raise HTTPException(404, detail=f"文件 '{safe_name}' 不存在")
    return FileResponse(str(file_path), filename=safe_name)


@router.delete("/{project_id}/files/{filename}", summary="删除项目文件")
def delete_project_file(
    project_id: str,
    filename: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> dict:
    safe_name = _safe_filename(filename)
    d = _get_project_files_dir(project_id, paths)
    file_path = d / safe_name
    if not file_path.is_file():
        raise HTTPException(404, detail=f"文件 '{safe_name}' 不存在")
    os.remove(file_path)
    return {"deleted": safe_name}


@router.post("/{project_id}/files/copy-from-workspace", summary="从用户 workspace 复制文件到项目")
def copy_from_workspace(
    project_id: str,
    req: CopyFromWorkspaceRequest,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> FileEntry:
    safe_name = _safe_filename(req.filename)
    src = paths.globalfiles_dir / safe_name
    if not src.is_file():
        raise HTTPException(404, detail=f"全局文件中不存在 '{safe_name}'")

    d = _get_project_files_dir(project_id, paths)
    dest = d / safe_name
    shutil.copy2(src, dest)
    return _file_entry(dest)


# ── 项目目录浏览 ───────────────────────────────────────────────────────────────

class DirectoryEntry(BaseModel):
    name: str
    path: str          # relative path from project root
    size_bytes: int
    is_dir: bool
    modified_at: str   # ISO-8601


class DirectoryListResponse(BaseModel):
    entries: list[DirectoryEntry]


def _safe_project_path(path: str) -> str:
    """校验项目目录内文件路径（允许子目录，拒绝路径遍历）。"""
    if not path or ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="非法文件路径")
    return path


def _get_project_dir(project_id: str, paths: UserPaths) -> Path:
    d = paths.projects_dir / project_id
    if not d.is_dir():
        raise HTTPException(404, detail=f"项目 '{project_id}' 不存在")
    return d


def _scan_directory(root: Path, base: Path) -> list[DirectoryEntry]:
    """递归扫描目录，返回所有文件和子目录的 DirectoryEntry 列表。"""
    entries: list[DirectoryEntry] = []
    for child in sorted(root.iterdir()):
        rel = str(child.relative_to(base))
        stat = child.stat()
        entries.append(DirectoryEntry(
            name=child.name,
            path=rel,
            size_bytes=stat.st_size if child.is_file() else 0,
            is_dir=child.is_dir(),
            modified_at=datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        ))
        if child.is_dir() and not child.is_symlink():
            entries.extend(_scan_directory(child, base))
    return entries


@router.get("/{project_id}/directory", response_model=DirectoryListResponse, summary="列出项目目录下所有文件")
def list_project_directory(
    project_id: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> DirectoryListResponse:
    d = _get_project_dir(project_id, paths)
    entries = _scan_directory(d, d)
    return DirectoryListResponse(entries=entries)


@router.get("/{project_id}/directory/download", summary="下载项目目录中的文件")
def download_from_project_directory(
    project_id: str,
    path: str,
    user: CurrentUser = Depends(require_user),
    paths: UserPaths = Depends(get_user_paths),
) -> FileResponse:
    safe_path = _safe_project_path(path)
    d = _get_project_dir(project_id, paths)
    file_path = d / safe_path
    if not file_path.is_file():
        raise HTTPException(404, detail=f"文件 '{safe_path}' 不存在")
    # 安全检查：确保文件在项目目录内
    try:
        file_path.resolve().relative_to(d.resolve())
    except ValueError:
        raise HTTPException(403, detail="禁止访问项目目录外的文件")
    return FileResponse(str(file_path), filename=file_path.name)
