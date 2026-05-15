"""api/routers/memory.py — Memory 系统管理 API。

提供经验记忆的浏览和删除功能。
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import CurrentUser, require_user

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryDeleteRequest(BaseModel):
    software: str = Field(default="gaussian", description="软件名")
    entry_id: str | None = Field(default=None, description="按 ChromaDB ID 删除单条")
    task_prefix: str | None = Field(default=None, description="删除 task 以指定前缀开头的所有条目")
    delete_all: bool = Field(default=False, description="清空该 software 全部经验")


@router.get("/list", summary="列出所有 memory 条目")
async def list_memory(
    software: str = Query(default="gaussian", description="软件名"),
    user: CurrentUser = Depends(require_user),
):
    """列出指定 software 的所有经验条目（含 ID，供删除用）。"""
    try:
        from agents.node_generator.shared.memory import get_experience_store
        store = get_experience_store(software)
        return {"software": software, "entries": store.list_all(), "count": store.count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", summary="删除 memory 条目")
async def delete_memory(
    req: MemoryDeleteRequest,
    user: CurrentUser = Depends(require_user),
):
    """删除经验条目。支持三种模式：
    - entry_id: 按 ChromaDB ID 删除单条
    - task_prefix: 删除 task 以指定前缀开头的所有条目
    - delete_all: 清空该 software 全部经验
    """
    try:
        from agents.node_generator.shared.memory import get_experience_store
        store = get_experience_store(req.software)

        if req.delete_all:
            ok = store.delete_all()
            return {"deleted": "all" if ok else 0, "software": req.software}
        elif req.entry_id:
            ok = store.delete_by_id(req.entry_id)
            return {"deleted": 1 if ok else 0, "ids": [req.entry_id]}
        elif req.task_prefix:
            n = store.delete_by_task_prefix(req.task_prefix)
            return {"deleted": n, "prefix": req.task_prefix}
        else:
            raise HTTPException(
                status_code=400,
                detail="必须提供 entry_id、task_prefix 或 delete_all=true",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
