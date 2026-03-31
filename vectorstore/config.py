"""vectorstore/config.py — ChromaDB 向量库配置。"""

from __future__ import annotations

from pathlib import Path


def get_chroma_persist_dir() -> Path:
    """返回 ChromaDB 持久化目录（userdata/vectorstore/chroma）。"""
    from api.config import get_settings
    settings = get_settings()
    chroma_dir = settings.userdata_root / "vectorstore" / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


COLLECTION_NAME = "miqroforge_nodes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # ChromaDB 默认内置，零 API 开销
