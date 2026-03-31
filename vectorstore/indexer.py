"""vectorstore/indexer.py — 从 node_index.yaml 构建节点向量索引。

支持两种模式：
1. ChromaDB + ONNX 嵌入（需要网络，首次下载模型）
2. 关键词搜索降级（离线/无网络时自动切换）

用法：
    python -m vectorstore.indexer          # 重建完整索引
    from vectorstore.indexer import build_index
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _make_document(entry: dict[str, Any]) -> str:
    """将节点索引条目序列化为可搜索的文档字符串。"""
    parts = [
        f"Node: {entry.get('name', '')}",
        f"Display Name: {entry.get('display_name', '')}",
        f"Description: {entry.get('description', '')}",
        f"Category: {entry.get('category', '')}",
        f"Software: {entry.get('software') or 'N/A'}",
        f"Semantic Type: {entry.get('semantic_type') or 'N/A'}",
        f"Semantic Display: {entry.get('semantic_display_name') or 'N/A'}",
        f"Methods: {', '.join(entry.get('methods', []))}",
        f"Domains: {', '.join(entry.get('domains', []))}",
        f"Capabilities: {', '.join(entry.get('capabilities', []))}",
        f"Keywords: {', '.join(entry.get('keywords', []))}",
    ]

    inputs = entry.get("stream_inputs", [])
    outputs = entry.get("stream_outputs", [])
    if inputs:
        parts.append(f"Inputs: {', '.join(p['display_name'] for p in inputs)}")
    if outputs:
        parts.append(f"Outputs: {', '.join(p['display_name'] for p in outputs)}")

    return "\n".join(parts)


def _make_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    """提取节点条目的可检索元数据。"""
    return {
        "name": entry.get("name", ""),
        "display_name": entry.get("display_name", ""),
        "description": entry.get("description", ""),
        "category": entry.get("category", ""),
        "software": entry.get("software") or "",
        "semantic_type": entry.get("semantic_type") or "",
        "node_type": entry.get("node_type", ""),
        "nodespec_path": entry.get("nodespec_path", ""),
        "source": entry.get("source", "system"),
        # JSON-serialize complex fields for Chroma metadata compatibility
        "stream_inputs": json.dumps(entry.get("stream_inputs", [])),
        "stream_outputs": json.dumps(entry.get("stream_outputs", [])),
        "onboard_inputs": json.dumps(entry.get("onboard_inputs", [])),
    }


def _try_build_chromadb_index(
    entries_data: list[dict[str, Any]],
    persist_dir: Path,
    collection_name: str,
) -> bool:
    """尝试用 ChromaDB + ONNX 构建索引。失败时返回 False。"""
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        client = chromadb.PersistentClient(path=str(persist_dir))

        # 删除旧集合
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

        embedding_fn = DefaultEmbeddingFunction()

        # 测试嵌入是否可用（触发模型下载检查）
        embedding_fn(["test"])

        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        documents = []
        metadatas = []
        ids = []

        for entry in entries_data:
            doc = _make_document(entry)
            meta = _make_metadata(entry)
            documents.append(doc)
            metadatas.append(meta)
            ids.append(entry["name"])

        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)

        # 标记索引类型
        (persist_dir / ".index_type").write_text("chromadb")
        print(f"[vectorstore] ChromaDB 索引已构建: {len(documents)} 节点 → {persist_dir}")
        return True

    except Exception as e:
        print(f"[vectorstore] ChromaDB 索引构建失败（将使用关键词搜索）: {e}")
        return False


def _build_keyword_index(
    entries_data: list[dict[str, Any]],
    persist_dir: Path,
) -> None:
    """构建关键词搜索索引（离线降级方案）。"""
    index_file = persist_dir / "keyword_index.json"
    keyword_index = []

    for entry in entries_data:
        doc = _make_document(entry)
        meta = _make_metadata(entry)
        keyword_index.append({
            "document": doc.lower(),
            "metadata": meta,
        })

    with index_file.open("w", encoding="utf-8") as f:
        json.dump(keyword_index, f, ensure_ascii=False, indent=2)

    # 标记索引类型
    (persist_dir / ".index_type").write_text("keyword")
    print(f"[vectorstore] 关键词索引已构建: {len(keyword_index)} 节点 → {persist_dir}")


def build_index(project_root: Path | None = None) -> int:
    """从 node_index.yaml 构建（或重建）向量索引。

    优先使用 ChromaDB，离线时降级为关键词搜索。

    Returns:
        索引的节点数量。
    """
    from node_index.scanner import scan_nodes
    from vectorstore.config import get_chroma_persist_dir, COLLECTION_NAME

    if project_root is None:
        from api.config import get_settings
        project_root = get_settings().project_root

    # 扫描并生成索引（包含 userdata/nodes/）
    index = scan_nodes(project_root)

    if index.total_nodes == 0:
        print("[vectorstore] 未找到任何节点，索引为空。")
        return 0

    persist_dir = get_chroma_persist_dir()
    entries_data = [e.model_dump(mode="json") for e in index.entries]

    # 先尝试 ChromaDB，失败则降级为关键词索引
    success = _try_build_chromadb_index(entries_data, persist_dir, COLLECTION_NAME)
    if not success:
        _build_keyword_index(entries_data, persist_dir)

    return index.total_nodes


if __name__ == "__main__":
    build_index()
