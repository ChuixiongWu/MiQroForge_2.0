"""MiQroForge 2.0 — FastAPI 网关。

路由版本前缀：/api/v1/

启动方式（开发）：
    uvicorn api.main:app --reload --port 8000

启动方式（生产，同时服务前端静态文件）：
    cd /path/to/MiQroForge_2.0/frontend && npm run build
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config import get_settings
from api.routers import nodes, runs, workflows
from api.routers import argo_proxy
from api.routers import files
from api.routers import agents
from api.routers import projects

# 构建好的前端目录（npm run build 输出）
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
_serve_static = FRONTEND_DIST.exists()

# ── 应用实例 ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MiQroForge 2.0 API",
    description=(
        "MiQroForge 2.0 科学计算平台 API。\n\n"
        "提供节点目录查询、工作流校验/编译/提交、运行监控、Agent 智能编排等功能。\n\n"
        "Phase 2 Agent 端点：\n"
        "- `POST /api/v1/agents/plan` — Planner Agent（意图 → 语义工作流）\n"
        "- `POST /api/v1/agents/yaml` — YAML Coder Agent（语义 → MF YAML）\n"
        "- `POST /api/v1/agents/node` — Node Generator Agent（生成新节点）"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API 路由注册 ──────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(nodes.router, prefix=API_PREFIX)
app.include_router(workflows.router, prefix=API_PREFIX)
app.include_router(runs.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(argo_proxy.router)   # /argo/* → Argo server


# ── 系统端点 ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "miqroforge-api",
        "version": "0.1.0",
        "serving_frontend": _serve_static,
    }


@app.get("/api/v1/config", tags=["system"])
def get_config() -> dict:
    """返回前端所需的运行时配置（如 Argo UI 地址）。"""
    s = get_settings()
    return {
        "argo_ui_url": s.argo_ui_url,
        "argo_namespace": s.argo_namespace,
    }


# 仅在没有静态文件服务时注册 JSON 根路由，
# 避免覆盖 SPA 的 index.html
if not _serve_static:
    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "service": "MiQroForge 2.0 API",
            "docs": "/docs",
            "health": "/health",
            "api_prefix": API_PREFIX,
        }


# ── 前端静态文件（prod 模式）─────────────────────────────────────────────────
# 必须在所有 API 路由之后挂载，API 路由优先匹配。
# html=True 确保 SPA 的任意路径都返回 index.html（客户端路由）。
if _serve_static:
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIST), html=True),
        name="frontend",
    )
