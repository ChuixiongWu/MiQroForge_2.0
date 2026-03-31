"""Quality Policy 校验测试。

覆盖：
- MFWorkflow.quality_policy 字段
- QualityGateOverride 模型校验
- _validate_quality_policy：合法 override、非法 node_id、非法 gate_name
- 生效策略 info 消息
- 无 quality_policy 时默认空列表
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workflows.pipeline.models import (
    MFConnection,
    MFNodeInstance,
    MFWorkflow,
    QualityGateOverride,
)
from workflows.pipeline.loader import load_workflow
from workflows.pipeline.validator import validate_workflow
from nodes.schemas.io import GateDefault


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
H2O_MF_YAML = PROJECT_ROOT / "workflows" / "examples" / "h2o-thermo-mf.yaml"


# ═══════════════════════════════════════════════════════════════════════════
# QualityGateOverride 模型
# ═══════════════════════════════════════════════════════════════════════════

class TestQualityGateOverrideModel:

    def test_basic_must_pass(self):
        override = QualityGateOverride(
            node_id="geo-opt",
            gate_name="converged",
            action=GateDefault.MUST_PASS,
        )
        assert override.node_id == "geo-opt"
        assert override.gate_name == "converged"
        assert override.action == GateDefault.MUST_PASS

    def test_warn_action(self):
        override = QualityGateOverride(
            node_id="freq",
            gate_name="is_true_minimum",
            action=GateDefault.WARN,
        )
        assert override.action == GateDefault.WARN

    def test_ignore_action(self):
        override = QualityGateOverride(
            node_id="geo-opt",
            gate_name="converged",
            action=GateDefault.IGNORE,
        )
        assert override.action == GateDefault.IGNORE

    def test_action_from_string(self):
        override = QualityGateOverride(
            node_id="geo-opt",
            gate_name="converged",
            action="warn",
        )
        assert override.action == GateDefault.WARN

    def test_invalid_action_raises(self):
        with pytest.raises(Exception):
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="converged",
                action="maybe",
            )


# ═══════════════════════════════════════════════════════════════════════════
# MFWorkflow.quality_policy 字段
# ═══════════════════════════════════════════════════════════════════════════

class TestMFWorkflowQualityPolicy:

    def test_default_quality_policy_is_empty(self):
        wf = MFWorkflow(
            name="test",
            nodes=[MFNodeInstance(id="a", node="some-node")],
        )
        assert wf.quality_policy == []

    def test_quality_policy_with_overrides(self):
        wf = MFWorkflow(
            name="test",
            nodes=[MFNodeInstance(id="a", node="some-node")],
            quality_policy=[
                QualityGateOverride(
                    node_id="a",
                    gate_name="converged",
                    action=GateDefault.IGNORE,
                )
            ],
        )
        assert len(wf.quality_policy) == 1
        assert wf.quality_policy[0].node_id == "a"

    def test_multiple_overrides(self):
        wf = MFWorkflow(
            name="test",
            nodes=[MFNodeInstance(id="a", node="some-node")],
            quality_policy=[
                QualityGateOverride(node_id="a", gate_name="gate1", action=GateDefault.WARN),
                QualityGateOverride(node_id="a", gate_name="gate2", action=GateDefault.IGNORE),
            ],
        )
        assert len(wf.quality_policy) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Validator: _validate_quality_policy
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateQualityPolicy:

    def _make_h2o_wf(self, quality_policy=None) -> MFWorkflow:
        """加载 H2O 工作流并附加 quality_policy。"""
        wf = load_workflow(H2O_MF_YAML)
        if quality_policy is not None:
            # 通过 model_copy 替换 quality_policy
            wf = wf.model_copy(update={"quality_policy": quality_policy})
        return wf

    def test_h2o_with_no_policy_valid(self):
        """无 quality_policy 时 H2O 工作流仍然通过校验。"""
        wf = self._make_h2o_wf()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid

    def test_h2o_quality_gate_info_messages(self):
        """有 quality gate 的节点会产生 info 级别的生效策略消息。"""
        wf = self._make_h2o_wf()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        gate_infos = [i for i in report.infos if "quality_gate:" in i.location]
        # geo-opt has 1 gate, freq has 1 gate → 2 info messages
        assert len(gate_infos) >= 2

    def test_valid_override_geo_opt_converged(self):
        """合法覆盖 geo-opt.converged → warn。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="converged",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid
        assert not any("不存在" in i.message for i in report.errors)

    def test_valid_override_freq_is_true_minimum(self):
        """合法覆盖 freq.is_true_minimum → ignore。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="freq",
                gate_name="is_true_minimum",
                action=GateDefault.IGNORE,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid

    def test_invalid_node_id_in_policy(self):
        """quality_policy 引用不存在的 node_id → error。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="nonexistent-node",
                gate_name="converged",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert not report.valid
        assert any(
            "nonexistent-node" in i.message and "不存在" in i.message
            for i in report.errors
        )

    def test_invalid_gate_name_in_policy(self):
        """quality_policy 引用的 gate_name 在节点中不存在 → error。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="nonexistent_gate",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert not report.valid
        assert any(
            "nonexistent_gate" in i.message
            for i in report.errors
        )

    def test_invalid_gate_name_on_node_without_gates(self):
        """quality_policy 引用 thermo-extract（无 quality gate）→ error。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="thermo-extract",
                gate_name="anything",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert not report.valid

    def test_overridden_gate_shows_overridden_in_info(self):
        """被覆盖的 gate 在 info 消息中标注 [overridden]。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="converged",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        overridden_infos = [
            i for i in report.infos
            if "overridden" in i.message and "geo-opt" in i.location
        ]
        assert len(overridden_infos) >= 1

    def test_override_warn_shows_warn_in_info(self):
        """覆盖为 warn 时 info 消息显示 warn。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="converged",
                action=GateDefault.WARN,
            )
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        geo_gate_info = next(
            (i for i in report.infos if "geo-opt.converged" in i.location),
            None,
        )
        assert geo_gate_info is not None
        assert "warn" in geo_gate_info.message

    def test_default_policy_shows_must_pass_in_info(self):
        """未 override 的 gate 使用默认 must_pass，info 消息中体现。"""
        wf = self._make_h2o_wf()
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        # geo-opt.converged should show must_pass
        geo_gate_info = next(
            (i for i in report.infos if "geo-opt.converged" in i.location),
            None,
        )
        assert geo_gate_info is not None
        assert "must_pass" in geo_gate_info.message

    def test_multiple_valid_overrides(self):
        """多个合法 override 同时存在。"""
        wf = self._make_h2o_wf(quality_policy=[
            QualityGateOverride(
                node_id="geo-opt",
                gate_name="converged",
                action=GateDefault.WARN,
            ),
            QualityGateOverride(
                node_id="freq",
                gate_name="is_true_minimum",
                action=GateDefault.IGNORE,
            ),
        ])
        report = validate_workflow(wf, project_root=PROJECT_ROOT)
        assert report.valid
        assert len([i for i in report.errors]) == 0
