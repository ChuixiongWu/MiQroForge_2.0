"""agents/tools/node_search.py — 节点 RAG 检索工具。

通过 vectorstore.retriever 提供节点摘要检索和语义类型检索。
Agent 通过此工具查找候选节点，不直接 import nodes/ 内部实现。
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def search_nodes_summary(query: str, n_results: int = 8) -> list[dict[str, Any]]:
    """搜索节点库，返回节点摘要列表（名称 + 描述 + 端口列表）。

    Args:
        query: 自然语言搜索查询（如 "geometry optimization for molecules"）
        n_results: 返回结果数量（默认 8）

    Returns:
        节点摘要字典列表，每项包含 name, display_name, description, semantic_type, software, stream_inputs, stream_outputs
    """
    from vectorstore.retriever import get_retriever
    retriever = get_retriever()
    return retriever.search_summary(query, n=n_results)


@tool
def search_nodes_by_semantic_type(semantic_type: str) -> list[dict[str, Any]]:
    """按语义类型检索节点（精确匹配）。

    Args:
        semantic_type: 语义类型键（如 "geometry-optimization", "frequency-analysis"）

    Returns:
        匹配的节点摘要列表
    """
    from vectorstore.retriever import get_retriever
    retriever = get_retriever()
    return retriever.search_by_semantic_type(semantic_type)


@tool
def get_node_details(node_names: list[str]) -> list[dict[str, Any]]:
    """加载指定节点的完整 NodeSpec（Level 3 详细信息）。

    Args:
        node_names: 节点名称列表（如 ["orca-geo-opt", "orca-freq"]）

    Returns:
        完整 NodeSpec 字典列表
    """
    from vectorstore.retriever import get_retriever
    retriever = get_retriever()
    return retriever.get_detailed(node_names)
