"""API 环境配置。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# 启动时自动加载项目根目录的 .env 文件（若存在）
# override=False：已有系统环境变量优先，.env 只作补充
_root = Path(__file__).parent.parent
load_dotenv(_root / ".env", override=False)


class Settings:
    """从环境变量读取 API 配置（.env 文件已在模块加载时写入 os.environ）。"""

    def __init__(self) -> None:
        # Argo 内部 API 地址（FastAPI 代理用，服务端到服务端）
        self.argo_server_url: str = os.environ.get(
            "ARGO_SERVER_URL", "https://localhost:2746"
        )
        self.argo_namespace: str = os.environ.get(
            "ARGO_NAMESPACE", "miqroforge-v2"
        )
        self.argo_token: str = os.environ.get("ARGO_TOKEN", "")

        # Argo UI 浏览器访问地址（返回给前端的链接）
        # 默认指向内置代理路径 /argo/，无需额外端口转发
        self.argo_ui_url: str = os.environ.get(
            "ARGO_UI_URL", "/argo/"
        )

        # 项目根目录（自动探测）
        self.project_root: Path = self._detect_project_root()

        # userdata/ 根目录（用户数据隔离：AI 生成节点、工作流、向量库等）
        self.userdata_root: Path = self.project_root / "userdata"

        # Docker Hub 国内镜像加速（可选）
        # 格式：镜像站域名，如 docker.m.daocloud.io 或 docker.mirrors.ustc.edu.cn
        # 未设置时留空，编译器回退到 registry.yaml 或直连 Docker Hub
        self.docker_hub_mirror: str = os.environ.get("DOCKER_HUB_MIRROR", "")

        # ── LLM 配置（Phase 2）────────────────────────────────────────────────
        self.llm_provider: str = os.environ.get("MF_LLM_PROVIDER", "openai")
        self.llm_model: str = os.environ.get("MF_LLM_MODEL", "gpt-4o")

        # 确保 userdata/ 子目录存在
        self._ensure_userdata_dirs()

    @staticmethod
    def _detect_project_root() -> Path:
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            if (parent / "CLAUDE.md").exists() or (parent / "nodes" / "schemas").exists():
                return parent
        return cwd

    def _ensure_userdata_dirs(self) -> None:
        """启动时自动创建 userdata/ 子目录（若不存在）。"""
        for sub in ["nodes", "workflows", "workspace", "runs", "vectorstore"]:
            (self.userdata_root / sub).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
