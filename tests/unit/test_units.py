"""物理单位转换正确性测试。

覆盖：
- KNOWN_UNITS 完整性检查
- 同量纲内的正确转换
- 跨量纲转换拒绝
- 同单位恒等转换
- 未知单位错误处理
- 常见计算化学转换因子的数值精度
"""

from __future__ import annotations

import math

import pytest

from nodes.schemas.units import (
    KNOWN_UNITS,
    PhysicalUnit,
    UnitConversionError,
    convert_value,
)


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN_UNITS 完整性
# ═══════════════════════════════════════════════════════════════════════════

class TestKnownUnits:
    """KNOWN_UNITS 字典的结构校验。"""

    def test_all_entries_are_physical_units(self):
        for symbol, unit in KNOWN_UNITS.items():
            assert isinstance(unit, PhysicalUnit)
            assert unit.symbol == symbol

    def test_all_have_positive_si_factor(self):
        for symbol, unit in KNOWN_UNITS.items():
            assert unit.to_si_factor > 0, f"{symbol} has non-positive SI factor"

    def test_all_have_nonempty_dimension(self):
        for symbol, unit in KNOWN_UNITS.items():
            assert unit.dimension, f"{symbol} has empty dimension"

    def test_expected_dimensions_present(self):
        dims = {u.dimension for u in KNOWN_UNITS.values()}
        for expected in ("energy", "length", "pressure", "temperature",
                         "angle", "force", "time"):
            assert expected in dims, f"dimension {expected!r} missing"

    def test_expected_symbols_present(self):
        expected = [
            "eV", "Ha", "Ry", "kcal/mol", "kJ/mol", "cm-1",
            "Ang", "bohr", "nm", "pm",
            "GPa", "kbar", "bar", "atm",
            "K", "deg", "rad",
            "eV/Ang", "Ha/bohr",
            "fs", "ps", "ns",
        ]
        for sym in expected:
            assert sym in KNOWN_UNITS, f"{sym!r} not in KNOWN_UNITS"


# ═══════════════════════════════════════════════════════════════════════════
# 转换正确性
# ═══════════════════════════════════════════════════════════════════════════

class TestConvertValue:
    """convert_value() 函数的正确性。"""

    # ── 恒等转换 ──

    def test_identity_conversion(self):
        assert convert_value(42.0, "eV", "eV") == 42.0

    # ── 能量转换 ──

    def test_ev_to_ha(self):
        # 1 Ha ≈ 27.2114 eV
        result = convert_value(27.2114, "eV", "Ha")
        assert result == pytest.approx(1.0, rel=1e-4)

    def test_ha_to_ry(self):
        # 1 Ha = 2 Ry
        result = convert_value(1.0, "Ha", "Ry")
        assert result == pytest.approx(2.0, rel=1e-10)

    def test_ev_to_kcal_per_mol(self):
        # 1 eV ≈ 23.0605 kcal/mol
        result = convert_value(1.0, "eV", "kcal/mol")
        assert result == pytest.approx(23.0605, rel=1e-3)

    def test_ha_to_kj_per_mol(self):
        # 1 Ha ≈ 2625.50 kJ/mol
        result = convert_value(1.0, "Ha", "kJ/mol")
        assert result == pytest.approx(2625.50, rel=1e-3)

    def test_ev_to_cm_inv(self):
        # 1 eV ≈ 8065.54 cm⁻¹
        result = convert_value(1.0, "eV", "cm-1")
        assert result == pytest.approx(8065.54, rel=1e-3)

    # ── 长度转换 ──

    def test_ang_to_bohr(self):
        # 1 Å ≈ 1.8897 bohr
        result = convert_value(1.0, "Ang", "bohr")
        assert result == pytest.approx(1.8897, rel=1e-3)

    def test_ang_to_nm(self):
        # 1 Å = 0.1 nm
        result = convert_value(1.0, "Ang", "nm")
        assert result == pytest.approx(0.1, rel=1e-10)

    def test_nm_to_pm(self):
        # 1 nm = 1000 pm
        result = convert_value(1.0, "nm", "pm")
        assert result == pytest.approx(1000.0, rel=1e-10)

    # ── 压强转换 ──

    def test_gpa_to_kbar(self):
        # 1 GPa = 10 kbar
        result = convert_value(1.0, "GPa", "kbar")
        assert result == pytest.approx(10.0, rel=1e-10)

    def test_atm_to_bar(self):
        # 1 atm = 1.01325 bar
        result = convert_value(1.0, "atm", "bar")
        assert result == pytest.approx(1.01325, rel=1e-4)

    # ── 角度转换 ──

    def test_deg_to_rad(self):
        result = convert_value(180.0, "deg", "rad")
        assert result == pytest.approx(math.pi, rel=1e-10)

    def test_rad_to_deg(self):
        result = convert_value(math.pi, "rad", "deg")
        assert result == pytest.approx(180.0, rel=1e-10)

    # ── 力转换 ──

    def test_ev_ang_to_ha_bohr(self):
        # 1 eV/Å = ? Ha/bohr
        # eV/Å → N: eV / Å = 1.602e-19 / 1e-10 = 1.602e-9
        # Ha/bohr → N: Ha / bohr = 4.3597e-18 / 5.2918e-11 = 8.2387e-8
        # 1 eV/Å = 1.602e-9 / 8.2387e-8 ≈ 0.019447 Ha/bohr
        result = convert_value(1.0, "eV/Ang", "Ha/bohr")
        assert result == pytest.approx(0.019447, rel=1e-3)

    # ── 时间转换 ──

    def test_ps_to_fs(self):
        # 1 ps = 1000 fs
        result = convert_value(1.0, "ps", "fs")
        assert result == pytest.approx(1000.0, rel=1e-10)

    def test_ns_to_ps(self):
        # 1 ns = 1000 ps
        result = convert_value(1.0, "ns", "ps")
        assert result == pytest.approx(1000.0, rel=1e-10)

    # ── 往返转换精度 ──

    def test_roundtrip_energy(self):
        """eV → Ha → Ry → eV 往返精度。"""
        original = 13.6
        ha = convert_value(original, "eV", "Ha")
        ry = convert_value(ha, "Ha", "Ry")
        back = convert_value(ry, "Ry", "eV")
        assert back == pytest.approx(original, rel=1e-10)

    def test_roundtrip_length(self):
        """Å → bohr → nm → Å 往返精度。"""
        original = 2.5
        bohr_val = convert_value(original, "Ang", "bohr")
        nm_val = convert_value(bohr_val, "bohr", "nm")
        back = convert_value(nm_val, "nm", "Ang")
        assert back == pytest.approx(original, rel=1e-10)


# ═══════════════════════════════════════════════════════════════════════════
# 错误处理
# ═══════════════════════════════════════════════════════════════════════════

class TestConvertValueErrors:
    """convert_value() 的错误处理。"""

    def test_unknown_source_unit(self):
        with pytest.raises(UnitConversionError, match="Unknown unit.*'foo'"):
            convert_value(1.0, "foo", "eV")

    def test_unknown_target_unit(self):
        with pytest.raises(UnitConversionError, match="Unknown unit.*'baz'"):
            convert_value(1.0, "eV", "baz")

    def test_dimension_mismatch(self):
        with pytest.raises(UnitConversionError, match="Dimension mismatch"):
            convert_value(1.0, "eV", "Ang")

    def test_force_vs_energy_mismatch(self):
        with pytest.raises(UnitConversionError, match="Dimension mismatch"):
            convert_value(1.0, "eV/Ang", "eV")

    def test_pressure_vs_temperature_mismatch(self):
        with pytest.raises(UnitConversionError, match="Dimension mismatch"):
            convert_value(1.0, "GPa", "K")
