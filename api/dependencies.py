"""FastAPI 依赖注入 — 组合 auth + settings → UserPaths。"""

from __future__ import annotations

from fastapi import Depends

from api.auth import CurrentUser, get_current_user
from api.config import Settings, get_settings
from api.user_paths import UserPaths


async def get_user_paths(
    user: CurrentUser | None = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UserPaths | None:
    """从当前请求的用户和配置创建 UserPaths。

    未认证时返回 None，由调用方决定如何处理。
    """
    if user is None:
        return None
    paths = UserPaths(username=user.username, settings=settings)
    paths.ensure_dirs()
    return paths
