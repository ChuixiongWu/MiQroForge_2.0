"""Workspace 文件 API 路由。

GET    /api/v1/files               — 列出 workspace/ 下所有文件
GET    /api/v1/files/{filename}    — 下载文件
POST   /api/v1/files/upload        — 上传文件（存入 workspace/）
DELETE /api/v1/files/{filename}    — 删除文件
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.config import Settings, get_settings

router = APIRouter(prefix="/files", tags=["files"])

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


# ── Pydantic 响应模型 ─────────────────────────────────────────────────────────

class FileEntry(BaseModel):
    name: str
    size_bytes: int
    modified_at: str  # ISO-8601


class FileListResponse(BaseModel):
    files: list[FileEntry]


# ── 辅助 ─────────────────────────────────────────────────────────────────────

def _get_workspace(settings: Settings) -> Path:
    """返回 workspace 目录（userdata/workspace/，自动创建）。"""
    ws = settings.userdata_root / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _safe_filename(filename: str) -> str:
    """校验文件名安全性，返回通过校验的文件名；不安全则抛 400。"""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    # 不允许隐藏文件（以 . 开头），但 .gitkeep 除外 — 直接拒绝即可
    return filename


def _file_entry(path: Path) -> FileEntry:
    import datetime
    stat = path.stat()
    return FileEntry(
        name=path.name,
        size_bytes=stat.st_size,
        modified_at=datetime.datetime.fromtimestamp(
            stat.st_mtime, tz=datetime.timezone.utc
        ).isoformat(),
    )


# ── 端点 ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=FileListResponse, summary="列出 workspace 文件")
def list_files(
    settings: Settings = Depends(get_settings),
) -> FileListResponse:
    ws = _get_workspace(settings)
    entries = sorted(
        [
            _file_entry(p)
            for p in ws.iterdir()
            if p.is_file() and p.name != ".gitkeep"
        ],
        key=lambda e: e.name,
    )
    return FileListResponse(files=entries)


@router.get("/upload", include_in_schema=False)
def upload_method_hint() -> dict:
    """防止 GET /files/upload 被路由器误匹配为 /{filename}。"""
    return {"detail": "Use POST /files/upload to upload a file."}


@router.post("/upload", summary="上传文件到 workspace")
async def upload_file(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> FileEntry:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    safe_name = _safe_filename(file.filename)
    ws = _get_workspace(settings)
    dest = ws / safe_name

    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 50 MB 限制")

    dest.write_bytes(content)
    return _file_entry(dest)


@router.get("/{filename}", summary="下载 workspace 文件")
def download_file(
    filename: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    safe_name = _safe_filename(filename)
    ws = _get_workspace(settings)
    path = ws / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件 '{safe_name}' 不存在")
    return FileResponse(str(path), filename=safe_name)


@router.delete("/{filename}", summary="删除 workspace 文件")
def delete_file(
    filename: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    safe_name = _safe_filename(filename)
    ws = _get_workspace(settings)
    path = ws / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件 '{safe_name}' 不存在")
    os.remove(path)
    return {"deleted": safe_name}
