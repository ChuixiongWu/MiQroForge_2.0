"""物理单位定义与转换。

为 Stream I/O 的 PhysicalQuantity 类型提供量纲检查和自动单位转换。
所有转换因子基于 CODATA 2018 推荐值。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalUnit:
    """一个物理单位的描述。

    Attributes:
        symbol: 单位符号（同时作为 KNOWN_UNITS 的键）。
        dimension: 物理量纲，如 ``"energy"``, ``"length"``。
            同维度的单位之间可以自动转换。
        to_si_factor: 乘以此因子即可转换为 SI 基本单位
            （能量→J, 长度→m, 压强→Pa, …）。
    """

    symbol: str
    dimension: str
    to_si_factor: float


# ---------------------------------------------------------------------------
# 已知单位表 ── 覆盖计算化学常见量纲
# ---------------------------------------------------------------------------
# 转换因子来源:
#   CODATA 2018, NIST SP 961 (2019)
#   1 Ha  = 4.3597447222071e-18 J
#   1 Ry  = 0.5 Ha
#   1 eV  = 1.602176634e-19 J
#   1 bohr = 5.29177210903e-11 m
#   N_A   = 6.02214076e23 mol^{-1}

_NA = 6.02214076e23
_EV = 1.602176634e-19          # J
_HA = 4.3597447222071e-18      # J
_BOHR = 5.29177210903e-11      # m
_ANG = 1e-10                   # m

KNOWN_UNITS: dict[str, PhysicalUnit] = {
    # ── 能量 (energy → J) ──────────────────────────────────────────────────
    "eV":        PhysicalUnit("eV",        "energy", _EV),
    "Ha":        PhysicalUnit("Ha",        "energy", _HA),
    "Ry":        PhysicalUnit("Ry",        "energy", _HA / 2),
    "kcal/mol":  PhysicalUnit("kcal/mol",  "energy", 4184.0 / _NA),
    "kJ/mol":    PhysicalUnit("kJ/mol",    "energy", 1000.0 / _NA),
    "cm-1":      PhysicalUnit("cm-1",      "energy", 1.986447e-23),

    # ── 长度 (length → m) ──────────────────────────────────────────────────
    "Ang":       PhysicalUnit("Ang",       "length", _ANG),
    "bohr":      PhysicalUnit("bohr",      "length", _BOHR),
    "nm":        PhysicalUnit("nm",        "length", 1e-9),
    "pm":        PhysicalUnit("pm",        "length", 1e-12),

    # ── 压强 (pressure → Pa) ──────────────────────────────────────────────
    "GPa":       PhysicalUnit("GPa",       "pressure", 1e9),
    "kbar":      PhysicalUnit("kbar",      "pressure", 1e8),
    "bar":       PhysicalUnit("bar",       "pressure", 1e5),
    "atm":       PhysicalUnit("atm",       "pressure", 101325.0),

    # ── 温度 (temperature → K) ────────────────────────────────────────────
    "K":         PhysicalUnit("K",         "temperature", 1.0),

    # ── 角度 (angle → rad) ────────────────────────────────────────────────
    "deg":       PhysicalUnit("deg",       "angle", 3.141592653589793 / 180.0),
    "rad":       PhysicalUnit("rad",       "angle", 1.0),

    # ── 力 (force → N) ────────────────────────────────────────────────────
    "eV/Ang":    PhysicalUnit("eV/Ang",    "force", _EV / _ANG),
    "Ha/bohr":   PhysicalUnit("Ha/bohr",   "force", _HA / _BOHR),

    # ── 时间 (time → s) ───────────────────────────────────────────────────
    "fs":        PhysicalUnit("fs",        "time", 1e-15),
    "ps":        PhysicalUnit("ps",        "time", 1e-12),
    "ns":        PhysicalUnit("ns",        "time", 1e-9),
}


# ---------------------------------------------------------------------------
# 转换函数
# ---------------------------------------------------------------------------

class UnitConversionError(Exception):
    """单位转换失败时抛出。"""


def convert_value(
    value: float,
    from_unit: str,
    to_unit: str,
) -> float:
    """将 *value* 从 *from_unit* 转换到 *to_unit*。

    两个单位必须属于同一量纲，否则抛出 :class:`UnitConversionError`。

    Parameters:
        value: 待转换的数值。
        from_unit: 源单位符号（KNOWN_UNITS 键）。
        to_unit: 目标单位符号（KNOWN_UNITS 键）。

    Returns:
        转换后的数值。

    Raises:
        UnitConversionError: 单位未知或量纲不匹配。
    """
    if from_unit == to_unit:
        return value

    src = KNOWN_UNITS.get(from_unit)
    dst = KNOWN_UNITS.get(to_unit)

    if src is None:
        raise UnitConversionError(f"Unknown unit: {from_unit!r}")
    if dst is None:
        raise UnitConversionError(f"Unknown unit: {to_unit!r}")
    if src.dimension != dst.dimension:
        raise UnitConversionError(
            f"Dimension mismatch: {from_unit!r} ({src.dimension}) "
            f"→ {to_unit!r} ({dst.dimension})"
        )

    # value_SI = value * src.to_si_factor
    # result   = value_SI / dst.to_si_factor
    return value * (src.to_si_factor / dst.to_si_factor)
