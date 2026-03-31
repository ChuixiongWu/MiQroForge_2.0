"""Quality Gate 字段校验测试。

覆盖：
- OnBoardOutput quality_gate 字段校验
- quality_gate=True 时 kind 必须为 boolean
- GateDefault 枚举值
- NodeSpec.quality_gates 属性
- 已有 ORCA / test 节点的 quality gate 回归
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nodes.schemas.io import GateDefault, OnBoardInputKind, OnBoardOutput
from nodes.schemas import NodeSpec


# ═══════════════════════════════════════════════════════════════════════════
# OnBoardOutput — quality gate 字段校验
# ═══════════════════════════════════════════════════════════════════════════

class TestOnBoardOutputQualityGateFields:

    def test_default_quality_gate_is_false(self):
        out = OnBoardOutput(name="energy", display_name="Energy", kind=OnBoardInputKind.FLOAT)
        assert out.quality_gate is False

    def test_default_gate_default_is_must_pass(self):
        out = OnBoardOutput(name="energy", display_name="Energy", kind=OnBoardInputKind.FLOAT)
        assert out.gate_default == GateDefault.MUST_PASS

    def test_default_gate_description_empty(self):
        out = OnBoardOutput(name="energy", display_name="Energy", kind=OnBoardInputKind.FLOAT)
        assert out.gate_description == ""

    def test_valid_quality_gate_boolean(self):
        out = OnBoardOutput(
            name="converged",
            display_name="Converged",
            kind=OnBoardInputKind.BOOLEAN,
            quality_gate=True,
            gate_default=GateDefault.MUST_PASS,
            gate_description="Must converge.",
        )
        assert out.quality_gate is True
        assert out.gate_default == GateDefault.MUST_PASS
        assert out.gate_description == "Must converge."

    def test_quality_gate_warn_policy(self):
        out = OnBoardOutput(
            name="scf_ok",
            display_name="SCF Converged",
            kind=OnBoardInputKind.BOOLEAN,
            quality_gate=True,
            gate_default=GateDefault.WARN,
        )
        assert out.gate_default == GateDefault.WARN

    def test_quality_gate_ignore_policy(self):
        out = OnBoardOutput(
            name="scf_ok",
            display_name="SCF Converged",
            kind=OnBoardInputKind.BOOLEAN,
            quality_gate=True,
            gate_default=GateDefault.IGNORE,
        )
        assert out.gate_default == GateDefault.IGNORE

    def test_quality_gate_true_with_non_boolean_raises(self):
        """quality_gate=True 时 kind 不为 boolean → ValueError。"""
        with pytest.raises(ValueError, match="boolean"):
            OnBoardOutput(
                name="energy",
                display_name="Energy",
                kind=OnBoardInputKind.FLOAT,
                quality_gate=True,
            )

    def test_quality_gate_true_integer_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            OnBoardOutput(
                name="n_steps",
                display_name="N Steps",
                kind=OnBoardInputKind.INTEGER,
                quality_gate=True,
            )

    def test_quality_gate_true_string_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            OnBoardOutput(
                name="label",
                display_name="Label",
                kind=OnBoardInputKind.STRING,
                quality_gate=True,
            )

    def test_quality_gate_true_enum_raises(self):
        with pytest.raises(ValueError, match="boolean"):
            OnBoardOutput(
                name="status",
                display_name="Status",
                kind=OnBoardInputKind.ENUM,
                quality_gate=True,
            )

    def test_quality_gate_false_any_kind_allowed(self):
        """quality_gate=False 时，任何 kind 都允许。"""
        for kind in OnBoardInputKind:
            out = OnBoardOutput(
                name="x",
                display_name="X",
                kind=kind,
                quality_gate=False,
            )
            assert out.quality_gate is False


# ═══════════════════════════════════════════════════════════════════════════
# GateDefault 枚举
# ═══════════════════════════════════════════════════════════════════════════

class TestGateDefaultEnum:

    def test_must_pass_value(self):
        assert GateDefault.MUST_PASS.value == "must_pass"

    def test_warn_value(self):
        assert GateDefault.WARN.value == "warn"

    def test_ignore_value(self):
        assert GateDefault.IGNORE.value == "ignore"

    def test_all_three_values(self):
        values = {g.value for g in GateDefault}
        assert values == {"must_pass", "warn", "ignore"}

    def test_from_string_must_pass(self):
        g = GateDefault("must_pass")
        assert g == GateDefault.MUST_PASS

    def test_from_string_warn(self):
        g = GateDefault("warn")
        assert g == GateDefault.WARN

    def test_from_string_ignore(self):
        g = GateDefault("ignore")
        assert g == GateDefault.IGNORE


# ═══════════════════════════════════════════════════════════════════════════
# NodeSpec.quality_gates 属性
# ═══════════════════════════════════════════════════════════════════════════

ORCA_DIR = Path("nodes/chemistry/orca")
TEST_DIR = Path("nodes/test")


@pytest.fixture(scope="module")
def orca_geo_opt() -> NodeSpec:
    return NodeSpec.from_yaml(ORCA_DIR / "orca-geo-opt" / "nodespec.yaml")


@pytest.fixture(scope="module")
def orca_freq() -> NodeSpec:
    return NodeSpec.from_yaml(ORCA_DIR / "orca-freq" / "nodespec.yaml")


@pytest.fixture(scope="module")
def orca_single_point() -> NodeSpec:
    return NodeSpec.from_yaml(ORCA_DIR / "orca-single-point" / "nodespec.yaml")


@pytest.fixture(scope="module")
def orca_thermo() -> NodeSpec:
    """orca-thermo-extractor 已移除；使用 test-thermo-extractor mock 节点代替。"""
    return NodeSpec.from_yaml(TEST_DIR / "thermo-extractor" / "nodespec.yaml")


@pytest.fixture(scope="module")
def test_geo_opt() -> NodeSpec:
    return NodeSpec.from_yaml(TEST_DIR / "gaussian-geo-opt" / "nodespec.yaml")


@pytest.fixture(scope="module")
def test_freq() -> NodeSpec:
    return NodeSpec.from_yaml(TEST_DIR / "gaussian-freq" / "nodespec.yaml")


@pytest.fixture(scope="module")
def test_thermo() -> NodeSpec:
    return NodeSpec.from_yaml(TEST_DIR / "thermo-extractor" / "nodespec.yaml")


class TestNodeSpecQualityGatesProperty:

    def test_quality_gates_returns_list(self, orca_geo_opt):
        assert isinstance(orca_geo_opt.quality_gates, list)

    def test_geo_opt_has_one_quality_gate(self, orca_geo_opt):
        assert len(orca_geo_opt.quality_gates) == 1

    def test_geo_opt_gate_name(self, orca_geo_opt):
        gate = orca_geo_opt.quality_gates[0]
        assert gate.name == "opt_converged"

    def test_geo_opt_gate_is_must_pass(self, orca_geo_opt):
        gate = orca_geo_opt.quality_gates[0]
        assert gate.gate_default == GateDefault.MUST_PASS

    def test_geo_opt_gate_kind_is_boolean(self, orca_geo_opt):
        gate = orca_geo_opt.quality_gates[0]
        assert gate.kind == OnBoardInputKind.BOOLEAN

    def test_freq_has_one_quality_gate(self, orca_freq):
        assert len(orca_freq.quality_gates) == 1

    def test_freq_gate_name(self, orca_freq):
        gate = orca_freq.quality_gates[0]
        assert gate.name == "is_true_minimum"

    def test_freq_gate_is_must_pass(self, orca_freq):
        gate = orca_freq.quality_gates[0]
        assert gate.gate_default == GateDefault.MUST_PASS

    def test_single_point_has_one_quality_gate(self, orca_single_point):
        assert len(orca_single_point.quality_gates) == 1

    def test_single_point_gate_name(self, orca_single_point):
        gate = orca_single_point.quality_gates[0]
        assert gate.name == "scf_converged"

    def test_thermo_extractor_has_no_quality_gates(self, orca_thermo):
        """thermo-extractor 没有 quality gate。"""
        assert len(orca_thermo.quality_gates) == 0

    def test_quality_gates_are_subset_of_onboard_outputs(self, orca_geo_opt):
        """quality_gates 中的每个元素都在 onboard_outputs 中。"""
        onboard_names = {o.name for o in orca_geo_opt.onboard_outputs}
        for gate in orca_geo_opt.quality_gates:
            assert gate.name in onboard_names


# ═══════════════════════════════════════════════════════════════════════════
# test 节点的 quality gate 回归
# ═══════════════════════════════════════════════════════════════════════════

class TestTestNodeQualityGates:

    def test_test_geo_opt_has_quality_gate(self, test_geo_opt):
        assert len(test_geo_opt.quality_gates) == 1

    def test_test_geo_opt_gate_name(self, test_geo_opt):
        assert test_geo_opt.quality_gates[0].name == "converged"

    def test_test_geo_opt_gate_is_must_pass(self, test_geo_opt):
        assert test_geo_opt.quality_gates[0].gate_default == GateDefault.MUST_PASS

    def test_test_freq_has_quality_gate(self, test_freq):
        assert len(test_freq.quality_gates) == 1

    def test_test_freq_gate_name(self, test_freq):
        assert test_freq.quality_gates[0].name == "is_true_minimum"

    def test_test_freq_gate_is_must_pass(self, test_freq):
        assert test_freq.quality_gates[0].gate_default == GateDefault.MUST_PASS

    def test_test_thermo_has_no_quality_gates(self, test_thermo):
        assert len(test_thermo.quality_gates) == 0


# ═══════════════════════════════════════════════════════════════════════════
# quality gate 不在 stream_outputs（回归：确保迁移完成）
# ═══════════════════════════════════════════════════════════════════════════

class TestQualityGateMigratedFromStreamIO:

    def test_geo_opt_opt_converged_not_in_stream_outputs(self, orca_geo_opt):
        names = [p.name for p in orca_geo_opt.stream_outputs]
        assert "opt_converged" not in names

    def test_freq_opt_converged_not_in_stream_inputs(self, orca_freq):
        names = [p.name for p in orca_freq.stream_inputs]
        assert "opt_converged" not in names

    def test_freq_is_true_minimum_not_in_stream_outputs(self, orca_freq):
        names = [p.name for p in orca_freq.stream_outputs]
        assert "is_true_minimum" not in names

    def test_single_point_converged_not_in_stream_outputs(self, orca_single_point):
        names = [p.name for p in orca_single_point.stream_outputs]
        assert "converged" not in names

    def test_test_geo_opt_converged_not_in_stream_outputs(self, test_geo_opt):
        names = [p.name for p in test_geo_opt.stream_outputs]
        assert "converged" not in names

    def test_test_freq_opt_converged_not_in_stream_inputs(self, test_freq):
        names = [p.name for p in test_freq.stream_inputs]
        assert "opt_converged" not in names

    def test_test_freq_is_true_minimum_not_in_stream_outputs(self, test_freq):
        names = [p.name for p in test_freq.stream_outputs]
        assert "is_true_minimum" not in names
