"""Stream I/O 端口连接校验。

在工作流编排阶段，验证两个端口之间是否可以合法连接。
校验规则按 :class:`~nodes.schemas.io.StreamIOCategory` 分派：

1. **跨类别** → 始终无效
2. **物理量** → 同量纲（dimension）可连，不同单位自动转换
3. **软件数据包** → 同 ``(ecosystem, data_type)`` 严格匹配
4. **逻辑量** → 同 ``kind`` 可连；``boolean ↔ signal`` 可隐式转换
5. **报告** → 同 ``format`` 可连；不同格式发出警告
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .io import (
    LogicValueKind,
    LogicValueType,
    PhysicalQuantityType,
    ReportObjectType,
    SoftwareDataPackageType,
    StreamIOCategory,
    StreamInputPort,
    StreamOutputPort,
)
from .units import KNOWN_UNITS


class ConnectionValidationResult(BaseModel):
    """连接校验结果。"""

    valid: bool
    message: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)


def validate_connection(
    source: StreamOutputPort,
    target: StreamInputPort,
) -> ConnectionValidationResult:
    """验证从 *source* 输出端口到 *target* 输入端口的连接是否合法。

    Parameters:
        source: 上游节点的输出端口。
        target: 下游节点的输入端口。

    Returns:
        校验结果，包含合法性、消息和警告列表。
    """
    src_cat = source.io_type.category
    tgt_cat = target.io_type.category

    # ── 跨类别检查 ──
    if src_cat != tgt_cat:
        return ConnectionValidationResult(
            valid=False,
            message=(
                f"类别不匹配: source={src_cat.value}, target={tgt_cat.value}。"
                "跨类别连接始终无效。"
            ),
        )

    # ── 按类别分派 ──
    dispatch = {
        StreamIOCategory.PHYSICAL_QUANTITY: _validate_physical_quantity,
        StreamIOCategory.SOFTWARE_DATA_PACKAGE: _validate_software_data_package,
        StreamIOCategory.LOGIC_VALUE: _validate_logic_value,
        StreamIOCategory.REPORT_OBJECT: _validate_report_object,
    }
    return dispatch[src_cat](source.io_type, target.io_type)


# ---------------------------------------------------------------------------
# 分类校验函数
# ---------------------------------------------------------------------------

def _validate_physical_quantity(
    src: PhysicalQuantityType,
    tgt: PhysicalQuantityType,
) -> ConnectionValidationResult:
    """物理量连接校验：同量纲可连，不同单位自动转换。"""
    src_unit = KNOWN_UNITS.get(src.unit)
    tgt_unit = KNOWN_UNITS.get(tgt.unit)

    if src_unit is None:
        return ConnectionValidationResult(
            valid=False,
            message=f"源端口单位未知: {src.unit!r}",
        )
    if tgt_unit is None:
        return ConnectionValidationResult(
            valid=False,
            message=f"目标端口单位未知: {tgt.unit!r}",
        )

    if src_unit.dimension != tgt_unit.dimension:
        return ConnectionValidationResult(
            valid=False,
            message=(
                f"量纲不匹配: {src.unit} ({src_unit.dimension}) "
                f"→ {tgt.unit} ({tgt_unit.dimension})"
            ),
        )

    warnings: list[str] = []
    if src.unit != tgt.unit:
        warnings.append(
            f"单位不同 ({src.unit} → {tgt.unit})，将自动转换。"
        )

    if src.shape != tgt.shape:
        return ConnectionValidationResult(
            valid=False,
            message=(
                f"形状不匹配: {src.shape} → {tgt.shape}"
            ),
        )

    return ConnectionValidationResult(valid=True, warnings=warnings)


def _validate_software_data_package(
    src: SoftwareDataPackageType,
    tgt: SoftwareDataPackageType,
) -> ConnectionValidationResult:
    """软件数据包连接校验：ecosystem + data_type 严格匹配。"""
    if src.ecosystem != tgt.ecosystem:
        return ConnectionValidationResult(
            valid=False,
            message=(
                f"生态系统不匹配: {src.ecosystem!r} → {tgt.ecosystem!r}。"
                "跨生态系统数据不互通，需插入显式转换节点。"
            ),
        )

    if src.data_type != tgt.data_type:
        return ConnectionValidationResult(
            valid=False,
            message=(
                f"数据类型不匹配: {src.data_type!r} → {tgt.data_type!r}"
            ),
        )

    return ConnectionValidationResult(valid=True)


def _validate_logic_value(
    src: LogicValueType,
    tgt: LogicValueType,
) -> ConnectionValidationResult:
    """逻辑量连接校验：同 kind 可连；boolean ↔ signal 可隐式转换。"""
    if src.kind == tgt.kind:
        return ConnectionValidationResult(valid=True)

    # boolean ↔ signal 隐式转换
    implicit_pair = {LogicValueKind.BOOLEAN, LogicValueKind.SIGNAL}
    if {src.kind, tgt.kind} == implicit_pair:
        return ConnectionValidationResult(
            valid=True,
            warnings=[
                f"{src.kind.value} → {tgt.kind.value} 将进行隐式转换。"
            ],
        )

    return ConnectionValidationResult(
        valid=False,
        message=(
            f"逻辑量类型不匹配: {src.kind.value} → {tgt.kind.value}"
        ),
    )


def _validate_report_object(
    src: ReportObjectType,
    tgt: ReportObjectType,
) -> ConnectionValidationResult:
    """报告连接校验：同格式直通；不同格式发出警告。"""
    warnings: list[str] = []
    if src.format != tgt.format:
        warnings.append(
            f"报告格式不同 ({src.format.value} → {tgt.format.value})，"
            "可能需要格式转换。"
        )

    return ConnectionValidationResult(valid=True, warnings=warnings)
