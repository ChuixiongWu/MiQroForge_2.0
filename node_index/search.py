"""简单文本搜索 — 按名称、标签、描述匹配节点。

纯 Python 实现，零外部依赖。Phase 2 将替换为向量检索。
"""

from __future__ import annotations

from .models import NodeIndex, NodeIndexEntry


def search_nodes(
    index: NodeIndex,
    query: str,
    *,
    max_results: int = 20,
) -> list[NodeIndexEntry]:
    """在索引中搜索匹配的节点。

    搜索逻辑：将 query 拆分为关键词，在以下字段中匹配：
    - name, display_name, description
    - software, methods, domains, capabilities, keywords
    - stream 端口名 + onboard 参数名

    按匹配度排序（匹配的关键词数 × 字段权重）。

    Parameters:
        index: 已加载的 NodeIndex。
        query: 搜索查询字符串。
        max_results: 最大返回数量。

    Returns:
        按相关性排序的 NodeIndexEntry 列表。
    """
    if not query.strip():
        return list(index.entries[:max_results])

    # 拆分关键词并转小写
    keywords = [kw.lower() for kw in query.strip().split() if kw]

    scored: list[tuple[float, NodeIndexEntry]] = []

    for entry in index.entries:
        score = _score_entry(entry, keywords)
        if score > 0:
            scored.append((score, entry))

    # 按分数降序排序
    scored.sort(key=lambda x: -x[0])

    return [entry for _, entry in scored[:max_results]]


def _score_entry(entry: NodeIndexEntry, keywords: list[str]) -> float:
    """计算单个索引条目的匹配分数。"""
    score = 0.0

    # 预构建小写搜索文本
    fields = {
        "name": (entry.name.lower(), 10.0),  # 名称精确匹配权重最高
        "display_name": (entry.display_name.lower(), 5.0),
        "description": (entry.description.lower(), 3.0),
        "software": ((entry.software or "").lower(), 8.0),
        "semantic_type": ((entry.semantic_type or "").lower(), 8.0),
        "category": (entry.category.lower(), 4.0),
        "node_type": (entry.node_type.lower(), 2.0),
    }

    # 列表字段
    list_fields = {
        "methods": (entry.methods, 6.0),
        "domains": (entry.domains, 5.0),
        "capabilities": (entry.capabilities, 6.0),
        "keywords": (entry.keywords, 4.0),
    }

    for kw in keywords:
        # 字符串字段
        for field_name, (text, weight) in fields.items():
            if kw in text:
                # 精确匹配加分
                if text == kw:
                    score += weight * 2
                elif text.startswith(kw) or text.endswith(kw):
                    score += weight * 1.5
                else:
                    score += weight

        # 列表字段
        for field_name, (items, weight) in list_fields.items():
            for item in items:
                item_lower = item.lower()
                if kw in item_lower:
                    if item_lower == kw:
                        score += weight * 2
                    else:
                        score += weight

        # 端口名匹配
        for port in entry.stream_inputs + entry.stream_outputs:
            if kw in port.name.lower() or kw in port.detail.lower():
                score += 2.0

        # onboard 参数名和 display_name 匹配（低权重）
        for param in entry.onboard_inputs:
            if kw in param.name.lower() or kw in param.display_name.lower():
                score += 1.0
        for output in entry.onboard_outputs:
            if kw in output.name.lower() or kw in output.display_name.lower():
                score += 1.0

    return score
