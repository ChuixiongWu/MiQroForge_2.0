"""vectorstore/retriever.py — 节点 RAG 检索接口。

支持两种后端：
1. ChromaDB（网络可用时，语义向量搜索）
2. 关键词搜索（离线降级，基于文本匹配）

用法：
    from vectorstore.retriever import get_retriever
    r = get_retriever()
    results = r.search_summary("geometry optimization", n=5)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class KeywordRetriever:
    """关键词搜索实现（离线降级方案）。"""

    def __init__(self, persist_dir: Path) -> None:
        self._index: list[dict[str, Any]] = []
        index_file = persist_dir / "keyword_index.json"
        if index_file.exists():
            with index_file.open("r", encoding="utf-8") as f:
                self._index = json.load(f)

    def _score(self, document: str, query: str) -> float:
        """简单关键词评分（词频）。"""
        query_words = query.lower().split()
        if not query_words:
            return 1.0
        score = sum(document.count(w) for w in query_words)
        return score / len(query_words)

    def search(self, query: str, n: int = 8) -> list[dict[str, Any]]:
        query_lower = query.lower()
        scored = [
            (self._score(item["document"], query_lower), item["metadata"])
            for item in self._index
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [meta for _, meta in scored[:n] if scored]

    def get_by_semantic_type(self, semantic_type: str) -> list[dict[str, Any]]:
        return [
            item["metadata"]
            for item in self._index
            if item["metadata"].get("semantic_type") == semantic_type
        ]

    def get_all(self) -> list[dict[str, Any]]:
        return [item["metadata"] for item in self._index]


class ChromaRetriever:
    """ChromaDB 向量搜索实现。"""

    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        client = chromadb.PersistentClient(path=str(persist_dir))
        embedding_fn = DefaultEmbeddingFunction()
        self._collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn,
        )

    def search(self, query: str, n: int = 8) -> list[dict[str, Any]]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n, count),
            include=["metadatas"],
        )
        return list((results["metadatas"] or [[]])[0])

    def get_by_semantic_type(self, semantic_type: str) -> list[dict[str, Any]]:
        results = self._collection.get(
            where={"semantic_type": semantic_type},
            include=["metadatas"],
        )
        return list(results.get("metadatas") or [])

    def get_all(self) -> list[dict[str, Any]]:
        results = self._collection.get(include=["metadatas"])
        return list(results.get("metadatas") or [])


class NodeRetriever:
    """节点检索器 — 统一 API，自动选择后端。"""

    def __init__(self) -> None:
        self._backend = None

    def _ensure_connected(self) -> None:
        if self._backend is not None:
            return

        from vectorstore.config import get_chroma_persist_dir, COLLECTION_NAME
        persist_dir = get_chroma_persist_dir()
        index_type_file = persist_dir / ".index_type"

        if not index_type_file.exists():
            # 尝试构建索引
            print("[vectorstore] 索引不存在，尝试自动构建...")
            from vectorstore.indexer import build_index
            build_index()

        index_type = index_type_file.read_text().strip() if index_type_file.exists() else "keyword"

        if index_type == "chromadb":
            try:
                self._backend = ChromaRetriever(persist_dir, COLLECTION_NAME)
                return
            except Exception:
                pass

        # 降级到关键词搜索
        self._backend = KeywordRetriever(persist_dir)

    def _meta_to_summary(self, meta: dict[str, Any]) -> dict[str, Any]:
        """将元数据还原为节点摘要字典。"""
        result = {
            "name": meta.get("name", ""),
            "display_name": meta.get("display_name", ""),
            "description": meta.get("description", ""),
            "category": meta.get("category", ""),
            "software": meta.get("software", "") or None,
            "semantic_type": meta.get("semantic_type", "") or None,
            "node_type": meta.get("node_type", ""),
            "nodespec_path": meta.get("nodespec_path", ""),
            "source": meta.get("source", "system"),
        }

        for field in ("stream_inputs", "stream_outputs", "onboard_inputs"):
            raw = meta.get(field, "[]")
            try:
                result[field] = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                result[field] = []

        return result

    def search_summary(self, query: str, n: int = 8) -> list[dict[str, Any]]:
        """Level 1 检索：返回节点摘要列表。"""
        self._ensure_connected()
        metas = self._backend.search(query, n=n)
        return [self._meta_to_summary(m) for m in metas]

    def search_by_semantic_type(self, semantic_type: str) -> list[dict[str, Any]]:
        """按语义类型精确匹配检索。"""
        self._ensure_connected()
        metas = self._backend.get_by_semantic_type(semantic_type)
        return [self._meta_to_summary(m) for m in metas]

    def get_detailed(self, node_names: list[str], project_root=None) -> list[dict[str, Any]]:
        """Level 3 检索：加载完整 NodeSpec JSON。"""
        if project_root is None:
            from api.config import get_settings
            settings = get_settings()
            project_root = settings.project_root
            userdata_root = settings.userdata_root
        else:
            from pathlib import Path
            userdata_root = Path(project_root) / "userdata"

        from pathlib import Path
        from nodes.schemas import NodeSpec

        results = []
        for name in node_names:
            found = False
            for search_dir in [Path(project_root) / "nodes", userdata_root / "nodes"]:
                if not search_dir.exists():
                    continue
                for spec_path in search_dir.rglob("nodespec.yaml"):
                    if "schemas" in spec_path.parts or "base_images" in spec_path.parts:
                        continue
                    try:
                        spec = NodeSpec.from_yaml(spec_path)
                        if spec.metadata.name == name:
                            results.append(spec.model_dump(mode="json"))
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break
            if not found:
                results.append({"error": f"未找到节点: {name}"})

        return results

    def list_all(self) -> list[dict[str, Any]]:
        """返回所有已索引节点的摘要。"""
        self._ensure_connected()
        metas = self._backend.get_all()
        return [self._meta_to_summary(m) for m in metas]


@lru_cache(maxsize=1)
def get_retriever() -> NodeRetriever:
    """获取全局 NodeRetriever 单例（延迟初始化）。"""
    return NodeRetriever()
