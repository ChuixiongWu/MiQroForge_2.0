"""认证路由 — POST /auth/login, GET /auth/me。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import (
    CurrentUser,
    authenticate_user,
    create_jwt,
    get_current_user,
    require_user,
)
from api.config import get_settings, Settings
from api.models.auth import LoginRequest, LoginResponse, UserInfo

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, settings: Settings = Depends(get_settings)):
    """用户名密码登录，返回 JWT token。"""
    user = authenticate_user(req.username, req.password, settings.auth_dir)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_jwt(user.username, user.role)
    return LoginResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


@router.get("/auth/me", response_model=UserInfo)
def me(user: CurrentUser = Depends(require_user),
       settings: Settings = Depends(get_settings)):
    """返回当前登录用户的信息。"""
    from api.auth import _load_users_yaml
    data = _load_users_yaml(settings.auth_dir)
    entry = data.get("users", {}).get(user.username, {})
    return UserInfo(
        username=user.username,
        role=user.role,
        display_name=entry.get("display_name", user.username),
        created_at=entry.get("created_at", ""),
    )
