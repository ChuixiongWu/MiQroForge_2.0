"""Stream I/O 端口连接校验规则测试。

覆盖：
- 跨类别连接拒绝
- 物理量：同量纲/不同量纲/不同单位/不同形状
- 软件数据包：相同/不同 ecosystem / 不同 data_type
- 逻辑量：同 kind / boolean↔signal 隐式转换 / 不兼容 kind
- 报告：同格式 / 不同格式警告
"""

from __future__ import annotations

import pytest

from nodes.schemas.connection import (
    ConnectionValidationResult,
    validate_connection,
)
from nodes.schemas.io import (
    LogicValueKind,
    LogicValueType,
    PhysicalQuantityType,
    ReportFormat,
    ReportObjectType,
    SoftwareDataPackageType,
    StreamIOCategory,
    StreamInputPort,
    StreamOutputPort,
)


# ═══════════════════════════════════════════════════════════════════════════
# 辅助工厂函数
# ═══════════════════════════════════════════════════════════════════════════

def _out(name: str, io_type) -> StreamOutputPort:
    return StreamOutputPort(name=name, display_name=name, io_type=io_type)

def _inp(name: str, io_type) -> StreamInputPort:
    return StreamInputPort(name=name, display_name=name, io_type=io_type)

# category 简写常量
_PQ  = StreamIOCategory.PHYSICAL_QUANTITY
_SDP = StreamIOCategory.SOFTWARE_DATA_PACKAGE
_LV  = StreamIOCategory.LOGIC_VALUE
_RO  = StreamIOCategory.REPORT_OBJECT


# ═══════════════════════════════════════════════════════════════════════════
# 跨类别
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossCategory:
    """跨类别连接始终无效。"""

    def test_physical_to_logic(self):
        src = _out("e", PhysicalQuantityType(category=_PQ, unit="eV"))
        tgt = _inp("f", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "类别不匹配" in result.message

    def test_sdp_to_report(self):
        src = _out("w", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="wavefunction"))
        tgt = _inp("r", ReportObjectType(category=_RO, format=ReportFormat.JSON))
        result = validate_connection(src, tgt)
        assert not result.valid


# ═══════════════════════════════════════════════════════════════════════════
# ① 物理量
# ═══════════════════════════════════════════════════════════════════════════

class TestPhysicalQuantity:
    """物理量连接校验。"""

    def test_same_unit_valid(self):
        src = _out("e1", PhysicalQuantityType(category=_PQ, unit="eV"))
        tgt = _inp("e2", PhysicalQuantityType(category=_PQ, unit="eV"))
        result = validate_connection(src, tgt)
        assert result.valid
        assert not result.warnings

    def test_same_dimension_different_unit(self):
        """同量纲不同单位 → 合法 + 自动转换警告。"""
        src = _out("e1", PhysicalQuantityType(category=_PQ, unit="eV"))
        tgt = _inp("e2", PhysicalQuantityType(category=_PQ, unit="Ha"))
        result = validate_connection(src, tgt)
        assert result.valid
        assert any("自动转换" in w for w in result.warnings)

    def test_different_dimension_invalid(self):
        """不同量纲 → 无效。"""
        src = _out("e", PhysicalQuantityType(category=_PQ, unit="eV"))
        tgt = _inp("l", PhysicalQuantityType(category=_PQ, unit="Ang"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "量纲不匹配" in result.message

    def test_unknown_source_unit(self):
        src = _out("x", PhysicalQuantityType(category=_PQ, unit="bogus"))
        tgt = _inp("y", PhysicalQuantityType(category=_PQ, unit="eV"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "未知" in result.message

    def test_unknown_target_unit(self):
        src = _out("x", PhysicalQuantityType(category=_PQ, unit="eV"))
        tgt = _inp("y", PhysicalQuantityType(category=_PQ, unit="bogus"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "未知" in result.message

    def test_shape_mismatch_invalid(self):
        """形状不匹配 → 无效。"""
        src = _out("f", PhysicalQuantityType(category=_PQ, unit="eV/Ang", shape="vector3"))
        tgt = _inp("f", PhysicalQuantityType(category=_PQ, unit="eV/Ang", shape="scalar"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "形状不匹配" in result.message

    def test_vector3_same_shape(self):
        src = _out("f1", PhysicalQuantityType(category=_PQ, unit="eV/Ang", shape="vector3"))
        tgt = _inp("f2", PhysicalQuantityType(category=_PQ, unit="Ha/bohr", shape="vector3"))
        result = validate_connection(src, tgt)
        assert result.valid


# ═══════════════════════════════════════════════════════════════════════════
# ② 软件数据包
# ═══════════════════════════════════════════════════════════════════════════

class TestSoftwareDataPackage:
    """软件数据包连接校验。"""

    def test_same_ecosystem_same_type_valid(self):
        src = _out("w1", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="wavefunction"))
        tgt = _inp("w2", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="wavefunction"))
        result = validate_connection(src, tgt)
        assert result.valid

    def test_different_ecosystem_invalid(self):
        src = _out("w1", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="wavefunction"))
        tgt = _inp("w2", SoftwareDataPackageType(category=_SDP, ecosystem="gaussian", data_type="wavefunction"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "生态系统不匹配" in result.message

    def test_same_ecosystem_different_type_invalid(self):
        src = _out("w1", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="wavefunction"))
        tgt = _inp("c1", SoftwareDataPackageType(category=_SDP, ecosystem="vasp", data_type="charge_density"))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "数据类型不匹配" in result.message


# ═══════════════════════════════════════════════════════════════════════════
# ③ 逻辑量
# ═══════════════════════════════════════════════════════════════════════════

class TestLogicValue:
    """逻辑量连接校验。"""

    def test_same_kind_valid(self):
        src = _out("b1", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        tgt = _inp("b2", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        result = validate_connection(src, tgt)
        assert result.valid
        assert not result.warnings

    def test_boolean_to_signal_implicit(self):
        """boolean → signal 可隐式转换。"""
        src = _out("b", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        tgt = _inp("s", LogicValueType(category=_LV, kind=LogicValueKind.SIGNAL))
        result = validate_connection(src, tgt)
        assert result.valid
        assert any("隐式转换" in w for w in result.warnings)

    def test_signal_to_boolean_implicit(self):
        """signal → boolean 可隐式转换。"""
        src = _out("s", LogicValueType(category=_LV, kind=LogicValueKind.SIGNAL))
        tgt = _inp("b", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        result = validate_connection(src, tgt)
        assert result.valid

    def test_integer_to_enum_invalid(self):
        src = _out("i", LogicValueType(category=_LV, kind=LogicValueKind.INTEGER))
        tgt = _inp("e", LogicValueType(category=_LV, kind=LogicValueKind.ENUM, allowed_values=["a", "b"]))
        result = validate_connection(src, tgt)
        assert not result.valid
        assert "不匹配" in result.message

    def test_boolean_to_integer_invalid(self):
        src = _out("b", LogicValueType(category=_LV, kind=LogicValueKind.BOOLEAN))
        tgt = _inp("i", LogicValueType(category=_LV, kind=LogicValueKind.INTEGER))
        result = validate_connection(src, tgt)
        assert not result.valid

    def test_enum_same_kind_valid(self):
        src = _out("e1", LogicValueType(category=_LV, kind=LogicValueKind.ENUM, allowed_values=["a", "b"]))
        tgt = _inp("e2", LogicValueType(category=_LV, kind=LogicValueKind.ENUM, allowed_values=["a", "b", "c"]))
        result = validate_connection(src, tgt)
        assert result.valid


# ═══════════════════════════════════════════════════════════════════════════
# ④ 报告
# ═══════════════════════════════════════════════════════════════════════════

class TestReportObject:
    """报告连接校验。"""

    def test_same_format_valid(self):
        src = _out("r1", ReportObjectType(category=_RO, format=ReportFormat.JSON))
        tgt = _inp("r2", ReportObjectType(category=_RO, format=ReportFormat.JSON))
        result = validate_connection(src, tgt)
        assert result.valid
        assert not result.warnings

    def test_different_format_warning(self):
        """不同格式 → 合法但有警告。"""
        src = _out("r1", ReportObjectType(category=_RO, format=ReportFormat.JSON))
        tgt = _inp("r2", ReportObjectType(category=_RO, format=ReportFormat.CSV))
        result = validate_connection(src, tgt)
        assert result.valid
        assert any("格式转换" in w for w in result.warnings)

    def test_markdown_to_html_warning(self):
        src = _out("r1", ReportObjectType(category=_RO, format=ReportFormat.MARKDOWN))
        tgt = _inp("r2", ReportObjectType(category=_RO, format=ReportFormat.HTML))
        result = validate_connection(src, tgt)
        assert result.valid
        assert len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════
# ConnectionValidationResult 模型
# ═══════════════════════════════════════════════════════════════════════════

class TestConnectionValidationResult:
    """ConnectionValidationResult 模型本身的测试。"""

    def test_default_values(self):
        r = ConnectionValidationResult(valid=True)
        assert r.valid
        assert r.message == ""
        assert r.warnings == []

    def test_serialization(self):
        r = ConnectionValidationResult(
            valid=False,
            message="test error",
            warnings=["warn1"],
        )
        d = r.model_dump()
        assert d["valid"] is False
        assert d["message"] == "test error"
        assert d["warnings"] == ["warn1"]
