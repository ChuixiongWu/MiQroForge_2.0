"""节点目录 API 路由。

GET /api/v1/nodes                   — 列出所有节点
GET /api/v1/nodes/search            — 搜索节点
GET /api/v1/nodes/semantic-registry — 返回完整语义类型注册表
GET /api/v1/nodes/semantic-types    — 按语义类型分组列出节点
GET /api/v1/nodes/units             — 返回 KNOWN_UNITS 物理单位注册表
GET /api/v1/nodes/{name}            — 节点详情
POST /api/v1/nodes/reindex          — 重新生成索引
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import Settings, get_settings
from api.models.nodes import (
    NodeDetailResponse,
    NodeIndexInfoResponse,
    NodeListResponse,
    NodeSummaryResponse,
    OnBoardOutputResponse,
    OnBoardParamResponse,
    PortSummaryResponse,
    SemanticRegistryResponse,
    SemanticTypeEntry,
    SemanticTypeGroup,
    SemanticTypesResponse,
)
from api.services.node_index_service import NodeIndexService
from node_index.models import NodeIndexEntry
from nodes.schemas.semantic_registry import load_semantic_registry

router = APIRouter(prefix="/nodes", tags=["nodes"])


def get_node_service(settings: Settings = Depends(get_settings)) -> NodeIndexService:
    return NodeIndexService(settings.project_root)


def _entry_to_summary(entry: NodeIndexEntry) -> NodeSummaryResponse:
    return NodeSummaryResponse(
        name=entry.name,
        version=entry.version,
        display_name=entry.display_name,
        description=entry.description,
        node_type=entry.node_type,
        category=entry.category,
        semantic_type=entry.semantic_type,
        semantic_display_name=entry.semantic_display_name,
        base_image_ref=entry.base_image_ref,
        nodespec_path=entry.nodespec_path,
        software=entry.software,
        methods=entry.methods,
        domains=entry.domains,
        capabilities=entry.capabilities,
        keywords=entry.keywords,
        resources_cpu=entry.resources_cpu,
        resources_memory_gb=entry.resources_memory_gb,
        stream_inputs=[
            PortSummaryResponse(**p.model_dump()) for p in entry.stream_inputs
        ],
        stream_outputs=[
            PortSummaryResponse(**p.model_dump()) for p in entry.stream_outputs
        ],
        onboard_inputs_count=len(entry.onboard_inputs),
        onboard_outputs_count=len(entry.onboard_outputs),
    )


@router.get("", response_model=NodeListResponse, summary="列出所有节点")
def list_nodes(
    category: str | None = Query(None, description="按 category 过滤"),
    node_type: str | None = Query(None, description="按 node_type 过滤 (compute/lightweight)"),
    semantic_type: str | None = Query(None, description="按 semantic_type 过滤，如 'geometry-optimization'"),
    svc: NodeIndexService = Depends(get_node_service),
) -> NodeListResponse:
    entries = svc.list_all()

    if category:
        entries = [e for e in entries if e.category == category]
    if node_type:
        entries = [e for e in entries if e.node_type == node_type]
    if semantic_type:
        entries = [e for e in entries if e.semantic_type == semantic_type]

    return NodeListResponse(
        total=len(entries),
        nodes=[_entry_to_summary(e) for e in entries],
    )


@router.get("/search", response_model=NodeListResponse, summary="搜索节点")
def search_nodes(
    q: str = Query(..., description="搜索查询"),
    limit: int = Query(20, ge=1, le=100, description="最大返回数量"),
    svc: NodeIndexService = Depends(get_node_service),
) -> NodeListResponse:
    results = svc.search(q, max_results=limit)
    return NodeListResponse(
        total=len(results),
        nodes=[_entry_to_summary(e) for e in results],
    )


@router.get("/index-info", response_model=NodeIndexInfoResponse, summary="索引元信息")
def get_index_info(svc: NodeIndexService = Depends(get_node_service)) -> NodeIndexInfoResponse:
    info = svc.get_index_info()
    return NodeIndexInfoResponse(**info)


@router.post("/reindex", response_model=NodeIndexInfoResponse, summary="重新生成索引")
def reindex(svc: NodeIndexService = Depends(get_node_service)) -> NodeIndexInfoResponse:
    idx = svc.refresh()
    return NodeIndexInfoResponse(
        total_nodes=idx.total_nodes,
        generated_at=idx.generated_at,
        mf_version=idx.mf_version,
    )


# 注意：此端点必须定义在 /{name} 之前，否则 "semantic-registry" 会被当作 name 参数
@router.get("/semantic-registry", response_model=SemanticRegistryResponse, summary="返回完整语义类型注册表")
def get_semantic_registry() -> SemanticRegistryResponse:
    """返回完整的语义类型注册表，供前端在启动时加载。"""
    registry = load_semantic_registry()
    return SemanticRegistryResponse(
        version=registry.version,
        types={
            key: SemanticTypeEntry(
                display_name=entry.display_name,
                description=entry.description,
                domain=entry.domain,
            )
            for key, entry in registry.types.items()
        },
    )


@router.get("/semantic-types", response_model=SemanticTypesResponse, summary="按语义操作类型分组列出节点")
def list_semantic_types(
    svc: NodeIndexService = Depends(get_node_service),
) -> SemanticTypesResponse:
    """返回所有已知的 semantic_type 及其下的节点列表，供 Palette 两段式分组使用。"""
    entries = svc.list_all()
    registry = load_semantic_registry()

    # 按 semantic_type 分组（无 semantic_type 的节点跳过）
    groups_map: dict[str, list[NodeSummaryResponse]] = {}
    for entry in entries:
        st = entry.semantic_type
        if st is None:
            continue
        if st not in groups_map:
            groups_map[st] = []
        groups_map[st].append(_entry_to_summary(entry))

    groups = [
        SemanticTypeGroup(
            semantic_type=st,
            display_name=registry.display_name(st),
            nodes=nodes,
        )
        for st, nodes in sorted(groups_map.items())
    ]

    return SemanticTypesResponse(total=len(groups), groups=groups)


@router.get("/units", summary="返回 KNOWN_UNITS 物理单位注册表")
def get_units() -> dict:
    """返回所有已注册的物理单位，按量纲分组。

    供前端 Units Reference 面板显示，帮助用户理解 PQ 连接规则。
    连接校验逻辑：同 dimension + 同 shape → 合法（不同 unit 自动转换）。
    """
    from nodes.schemas.units import KNOWN_UNITS

    # 按 dimension 分组
    by_dimension: dict[str, list[dict]] = {}
    for symbol, unit in sorted(KNOWN_UNITS.items()):
        dim = unit.dimension
        if dim not in by_dimension:
            by_dimension[dim] = []
        by_dimension[dim].append({
            "symbol": symbol,
            "dimension": dim,
            "to_si_factor": unit.to_si_factor,
        })

    return {
        "total_units": len(KNOWN_UNITS),
        "total_dimensions": len(by_dimension),
        "dimensions": by_dimension,
    }


@router.get("/{name}", response_model=NodeDetailResponse, summary="节点详情")
def get_node(
    name: str,
    svc: NodeIndexService = Depends(get_node_service),
) -> NodeDetailResponse:
    entry = svc.get_by_name(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Node '{name}' not found")

    summary = _entry_to_summary(entry)

    # On-Board 参数完整定义直接从索引读取，无需二次解析 nodespec.yaml
    onboard_inputs = [
        OnBoardParamResponse(
            name=p.name,
            display_name=p.display_name,
            kind=p.kind,
            default=p.default,
            description=p.description,
            allowed_values=p.allowed_values,
            min_value=p.min_value,
            max_value=p.max_value,
            unit=p.unit,
            multiple_input=p.multiple_input,
        )
        for p in entry.onboard_inputs
    ]
    onboard_outputs = [
        OnBoardOutputResponse(
            name=o.name,
            display_name=o.display_name,
            kind=o.kind,
            unit=o.unit,
            description=o.description,
            quality_gate=o.quality_gate,
            gate_default=o.gate_default,
            gate_description=o.gate_description,
        )
        for o in entry.onboard_outputs
    ]

    return NodeDetailResponse(
        **summary.model_dump(),
        onboard_inputs=onboard_inputs,
        onboard_outputs=onboard_outputs,
    )
