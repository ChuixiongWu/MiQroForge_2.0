"""节点索引服务 — 加载并缓存 NodeIndex。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from node_index.models import NodeIndex, NodeIndexEntry
from node_index.scanner import load_index, scan_nodes, write_index
from node_index.search import search_nodes


class NodeIndexService:
    """节点索引服务 — 提供节点查询和搜索功能。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._index: NodeIndex | None = None

    def _get_index(self) -> NodeIndex:
        """懒加载索引（首次调用时从磁盘读取，失败则实时扫描）。"""
        if self._index is None:
            try:
                self._index = load_index(self.project_root)
            except FileNotFoundError:
                # 索引不存在，实时扫描
                self._index = scan_nodes(self.project_root)
                write_index(self._index, self.project_root)
        return self._index

    def refresh(self) -> NodeIndex:
        """重新扫描并更新索引缓存。"""
        self._index = scan_nodes(self.project_root)
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
