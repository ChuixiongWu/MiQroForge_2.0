"""用户路径解析 — 所有用户相关文件系统路径的单一真相来源。"""

from __future__ import annotations

from pathlib import Path


class UserPaths:
    """解析当前用户的数据目录路径。

    用法：
        paths = UserPaths(username="alice", settings=settings)
        projects = paths.projects_dir   # → userdata/users/alice/projects
        models   = paths.shared_models_file  # → userdata/shared/models.yaml
    """

    def __init__(self, username: str, settings) -> None:
        self._username = username
        self._settings = settings
        self._user_dir: Path = settings.users_root / username
        self._shared_dir: Path = settings.shared_root

    # ── 私有目录 ──────────────────────────────────────────────────────────

    @property
    def user_dir(self) -> Path:
        return self._user_dir

    @property
    def projects_dir(self) -> Path:
        return self._user_dir / "projects"

    @property
    def globalfiles_dir(self) -> Path:
        """用户上传的全局文件（不挂 PVC，仅供 UI 上传下载）。"""
        return self._user_dir / "globalfiles"

    @property
    def nodes_dir(self) -> Path:
        return self._user_dir / "nodes"

    @property
    def agent_sessions_dir(self) -> Path:
        return self._user_dir / "agent_sessions"

    @property
    def usage_dir(self) -> Path:
        return self._user_dir / "usage"

    @property
    def settings_file(self) -> Path:
        return self._user_dir / "settings.yaml"

    @property
    def preferences_file(self) -> Path:
        return self._user_dir / "node_preferences.yaml"

    @property
    def pip_history_file(self) -> Path:
        return self._user_dir / "pip_history.jsonl"

    @property
    def tmp_dir(self) -> Path:
        """项目 tmp/ 的根（用于 prefab 节点生成临时文件）。"""
        return self._user_dir / "tmp"

    # ── 共享目录 ──────────────────────────────────────────────────────────

    @property
    def shared_dir(self) -> Path:
        return self._shared_dir

    @property
    def shared_models_file(self) -> Path:
        return self._shared_dir / "models.yaml"

    @property
    def shared_node_gen_memory_dir(self) -> Path:
        return self._shared_dir / "node_gen_memory"

    @property
    def shared_chroma_dir(self) -> Path:
        return self._shared_dir / "vectorstore" / "chroma"

    # ── 便捷方法 ──────────────────────────────────────────────────────────

    def ensure_dirs(self) -> None:
        """创建用户的所有私有目录（首次访问时调用）。"""
        for d in [
            self.projects_dir,
            self.globalfiles_dir,
            self.nodes_dir,
            self.agent_sessions_dir,
            self.usage_dir,
            self.tmp_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)
