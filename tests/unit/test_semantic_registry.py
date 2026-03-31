"""语义类型注册表测试。

覆盖：
- 注册表加载、校验
- NodeMetadata._validate_semantic_type 集成
- 已有节点都能通过
- reload_semantic_registry 清缓存
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nodes.schemas.semantic_registry import (
    SemanticRegistry,
    SemanticTypeEntry,
    load_semantic_registry,
    reload_semantic_registry,
)
from nodes.schemas import NodeMetadata, NodeType


# ═══════════════════════════════════════════════════════════════════════════
# 注册表加载
# ═══════════════════════════════════════════════════════════════════════════

class TestSemanticRegistryLoading:

    def test_registry_loads(self):
        registry = load_semantic_registry()
        assert isinstance(registry, SemanticRegistry)

    def test_registry_version(self):
        registry = load_semantic_registry()
        assert registry.version == "1.0"

    def test_registry_has_required_types(self):
        registry = load_semantic_registry()
        for key in [
            "geometry-optimization",
            "frequency-analysis",
            "single-point-energy",
        ]:
            assert key in registry.types, f"Missing key: {key}"
        # thermo-extraction 已从注册表移除（功能整合到 orca-freq）
        assert "thermo-extraction" not in registry.types

    def test_all_entries_have_display_name(self):
        registry = load_semantic_registry()
        for key, entry in registry.types.items():
            assert entry.display_name, f"Empty display_name for {key}"

    def test_all_entries_have_description(self):
        registry = load_semantic_registry()
        for key, entry in registry.types.items():
            assert entry.description, f"Empty description for {key}"

    def test_all_entries_have_domain(self):
        registry = load_semantic_registry()
        for key, entry in registry.types.items():
            assert entry.domain, f"Empty domain for {key}"


# ═══════════════════════════════════════════════════════════════════════════
# SemanticRegistry 方法
# ═══════════════════════════════════════════════════════════════════════════

class TestSemanticRegistryMethods:

    def test_is_valid_known_type(self):
        registry = load_semantic_registry()
        assert registry.is_valid("geometry-optimization") is True

    def test_is_valid_unknown_type(self):
        registry = load_semantic_registry()
        assert registry.is_valid("not-a-real-type") is False

    def test_get_known_type(self):
        registry = load_semantic_registry()
        entry = registry.get("geometry-optimization")
        assert entry is not None
        assert entry.display_name == "Geometry Optimization"

    def test_get_unknown_type(self):
        registry = load_semantic_registry()
        assert registry.get("nonexistent") is None

    def test_display_name_known(self):
        registry = load_semantic_registry()
        assert registry.display_name("geometry-optimization") == "Geometry Optimization"

    def test_display_name_unknown_fallback(self):
        registry = load_semantic_registry()
        dn = registry.display_name("my-custom-type")
        assert dn == "My Custom Type"

    def test_all_keys_sorted(self):
        registry = load_semantic_registry()
        keys = registry.all_keys()
        assert keys == sorted(keys)

    def test_all_keys_not_empty(self):
        registry = load_semantic_registry()
        assert len(registry.all_keys()) > 0


# ═══════════════════════════════════════════════════════════════════════════
# NodeMetadata 集成 — semantic_type 校验
# ═══════════════════════════════════════════════════════════════════════════

class TestNodeMetadataSemanticTypeIntegration:

    def _make_meta(self, semantic_type=None):
        return NodeMetadata(
            name="test-node",
            node_type=NodeType.LIGHTWEIGHT,
            semantic_type=semantic_type,
        )

    def test_none_semantic_type_allowed(self):
        meta = self._make_meta(semantic_type=None)
        assert meta.semantic_type is None

    def test_registered_type_passes(self):
        meta = self._make_meta(semantic_type="geometry-optimization")
        assert meta.semantic_type == "geometry-optimization"

    def test_unregistered_type_raises(self):
        with pytest.raises(ValueError, match="未在注册表中注册"):
            self._make_meta(semantic_type="not-in-registry")

    def test_non_kebab_case_raises(self):
        with pytest.raises(ValueError):
            self._make_meta(semantic_type="UPPERCASE_TYPE")

    def test_all_registered_types_pass(self):
        """所有注册表中的 key 都应该能通过 NodeMetadata 校验。"""
        registry = load_semantic_registry()
        for key in registry.all_keys():
            meta = self._make_meta(semantic_type=key)
            assert meta.semantic_type == key


# ═══════════════════════════════════════════════════════════════════════════
# 已有节点能正常加载（回归）
# ═══════════════════════════════════════════════════════════════════════════

class TestExistingNodesLoadWithRegistry:

    @pytest.fixture(scope="class")
    def all_nodespecs(self):
        from nodes.schemas import NodeSpec
        root = Path(__file__).parent.parent.parent
        specs = {}
        for p in (root / "nodes").rglob("nodespec.yaml"):
            if "schemas" in p.parts or "base_images" in p.parts:
                continue
            try:
                spec = NodeSpec.from_yaml(p)
                specs[spec.metadata.name] = spec
            except Exception as e:
                pytest.fail(f"Failed to load {p}: {e}")
        return specs

    def test_orca_geo_opt_loads(self, all_nodespecs):
        assert "orca-geo-opt" in all_nodespecs

    def test_orca_freq_loads(self, all_nodespecs):
        assert "orca-freq" in all_nodespecs

    def test_orca_single_point_loads(self, all_nodespecs):
        assert "orca-single-point" in all_nodespecs

    def test_orca_thermo_extractor_removed(self, all_nodespecs):
        """orca-thermo-extractor 已从 nodes/chemistry/ 移除。"""
        assert "orca-thermo-extractor" not in all_nodespecs

    def test_all_nodes_have_valid_semantic_type(self, all_nodespecs):
        """有 semantic_type 的节点，其值都在注册表中。"""
        registry = load_semantic_registry()
        for name, spec in all_nodespecs.items():
            st = spec.metadata.semantic_type
            if st is not None:
                assert registry.is_valid(st), (
                    f"Node {name!r} has unregistered semantic_type: {st!r}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# reload_semantic_registry
# ═══════════════════════════════════════════════════════════════════════════

class TestReloadSemanticRegistry:

    def test_reload_returns_same_content(self):
        r1 = load_semantic_registry()
        r2 = reload_semantic_registry()
        assert r1.version == r2.version
        assert set(r1.all_keys()) == set(r2.all_keys())

    def test_reload_clears_cache(self):
        """reload 后 load_semantic_registry 仍能工作。"""
        reload_semantic_registry()
        r = load_semantic_registry()
        assert r is not None
