"""节点索引服务 — 加载并缓存 NodeIndex。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from node_index.models import NodeIndex, NodeIndexEntry
from node_index.scanner import load_index, scan_nodes, write_index
from node_index.search import search_nodes


class NodeIndexService:
    """节点索引服务 — 提供节点查询和搜索功能。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._index: NodeIndex | None = None
        self._user_settings_path: Path | None = None
        self._user_nodes_dirs: list[Path] | None = None

    def _load_include_test_setting(self) -> bool:
        """从 userdata/settings.yaml 或用户 settings.yaml 读取配置。"""
        if self._user_settings_path and self._user_settings_path.exists():
            settings_path = self._user_settings_path
        else:
            settings_path = self.project_root / "userdata" / "settings.yaml"
        if not settings_path.exists():
            return False
        try:
            with settings_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("index", {}).get("include_test_nodes", False)
        except Exception:
            return False

    def _get_index(self) -> NodeIndex:
        """懒加载索引（首次调用时从磁盘读取，失败则实时扫描）。"""
        if self._index is None:
            try:
                self._index = load_index(self.project_root)
            except FileNotFoundError:
                # 索引不存在，实时扫描
                include_test = self._load_include_test_setting()
                self._index = scan_nodes(
                    self.project_root,
                    include_test_nodes=include_test,
                    user_nodes_dirs=self._user_nodes_dirs,
                )
                write_index(self._index, self.project_root)
        return self._index

    def refresh(self) -> NodeIndex:
        """重新扫描并更新索引缓存。"""
        include_test = self._load_include_test_setting()
        self._index = scan_nodes(
            self.project_root,
            include_test_nodes=include_test,
            user_nodes_dirs=self._user_nodes_dirs,
        )
        write_index(self._index, self.project_root)
        return self._index

    def list_all(self) -> list[NodeIndexEntry]:
        return self._get_index().entries

    def get_by_name(self, name: str) -> NodeIndexEntry | None:
        for entry in self._get_index().entries:
            if entry.name == name:
                return entry
        return None

    def search(self, query: str, max_results: int = 20) -> list[NodeIndexEntry]:
        return search_nodes(self._get_index(), query, max_results=max_results)

    def get_index_info(self) -> dict:
        idx = self._get_index()
        return {
            "total_nodes": idx.total_nodes,
            "generated_at": idx.generated_at,
            "mf_version": idx.mf_version,
        }
