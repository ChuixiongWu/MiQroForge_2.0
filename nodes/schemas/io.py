"""Stream I/O 与 On-Board I/O 类型定义。

实现双通道 I/O 模型：
- **Stream I/O**: 节点间连线传输的数据，分为四类（物理量 / 软件数据包 / 逻辑量 / 报告）。
- **On-Board I/O**: 用户直接在节点面板上配置的输入/输出。
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ═══════════════════════════════════════════════════════════════════════════
# Stream I/O 四分类
# ═══════════════════════════════════════════════════════════════════════════

class StreamIOCategory(str, Enum):
    """Stream I/O 的四种类型。"""

    PHYSICAL_QUANTITY = "physical_quantity"
    """物理量 — 带量纲的科学量，可自动单位转换。"""

    SOFTWARE_DATA_PACKAGE = "software_data_package"
    """软件数据包 — 计算软件内部文件，限制在同一生态系统内。"""

    LOGIC_VALUE = "logic_value"
    """逻辑量 — 布尔/枚举/整数/信号，用于工作流控制流。"""

    REPORT_OBJECT = "report_object"
    """报告 — 人类或 AI 可读的产出物。"""


# ---------------------------------------------------------------------------
# ① 物理量 (PhysicalQuantity)
# ---------------------------------------------------------------------------

class PhysicalQuantityType(BaseModel):
    """物理量的类型描述。

    连接规则：同 ``dimension``（由 ``unit`` 查 KNOWN_UNITS 得到）且同 ``shape``
    即可连接，不同单位自动转换。端口的语义含义由端口自身的 ``name`` /
    ``display_name`` / ``description`` 表达，不在类型层重复。
    """

    category: Literal[StreamIOCategory.PHYSICAL_QUANTITY]
    unit: str = Field(
        ...,
        description="KNOWN_UNITS 中的单位符号，如 'eV'、'Ang'。",
    )
    shape: str = Field(
        default="scalar",
        description="数据形状：'scalar' / 'vector3' / 'matrix3x3' / 'array'。",
    )
    constraints: Optional[dict[str, Any]] = Field(
        default=None,
        description="值域约束，如 {'min': 0}。",
    )


# ---------------------------------------------------------------------------
# ② 软件数据包 (SoftwareDataPackage)
# ---------------------------------------------------------------------------

class SoftwareDataPackageType(BaseModel):
    """软件数据包的类型描述。

    连接规则：``ecosystem`` + ``data_type`` 严格匹配才可连接。
    不同生态系统之间天然不互通。
    """

    category: Literal[StreamIOCategory.SOFTWARE_DATA_PACKAGE]
    ecosystem: str = Field(
        ...,
        description="所属软件生态系统，如 'vasp'、'gaussian'（str 而非枚举，便于扩展）。",
    )
    data_type: str = Field(
        ...,
        description="数据类型标识，如 'wavefunction'、'charge_density'。",
    )


# ---------------------------------------------------------------------------
# ③ 逻辑量 (LogicValue)
# ---------------------------------------------------------------------------

class LogicValueKind(str, Enum):
    """逻辑量的子类型。"""

    BOOLEAN = "boolean"
    ENUM = "enum"
    INTEGER = "integer"
    SIGNAL = "signal"


class LogicValueType(BaseModel):
    """逻辑量的类型描述。

    连接规则：同 ``kind`` 可连；``boolean`` ↔ ``signal`` 可隐式转换。
    """

    category: Literal[StreamIOCategory.LOGIC_VALUE]
    kind: LogicValueKind
    allowed_values: Optional[list[str]] = Field(
        default=None,
        description="枚举类型的合法值列表。",
    )
    value_range: Optional[dict[str, int]] = Field(
        default=None,
        description="整数类型的值域范围，如 {'min': 0, 'max': 100}。",
    )


# ---------------------------------------------------------------------------
# ④ 报告 (ReportObject)
# ---------------------------------------------------------------------------

class ReportFormat(str, Enum):
    """报告的输出格式。"""

    MARKDOWN = "markdown"
    JSON = "json"
    PNG = "png"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


class ReportObjectType(BaseModel):
    """报告对象的类型描述。

    连接规则：同 ``format`` 直接连通；不同格式时发出警告。
    """

    category: Literal[StreamIOCategory.REPORT_OBJECT]
    format: ReportFormat
    content_schema: Optional[str] = Field(
        default=None,
        description="JSON Schema 或内容结构的描述性说明。",
    )
    description: str = Field(
        default="",
        description="报告内容的简要描述。",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stream I/O 联合类型（按 category 辨别）
# ═══════════════════════════════════════════════════════════════════════════

StreamIOType = Annotated[
    Union[
        PhysicalQuantityType,
        SoftwareDataPackageType,
        LogicValueType,
        ReportObjectType,
    ],
    Field(discriminator="category"),
]
"""四种 Stream I/O 类型的辨别联合体。"""


# ═══════════════════════════════════════════════════════════════════════════
# Stream 端口
# ═══════════════════════════════════════════════════════════════════════════

class StreamInputPort(BaseModel):
    """Stream 输入端口 — 接收上游节点的数据。"""

    name: str = Field(
        ...,
        description="端口标识符，节点内唯一。",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="人类可读的显示名称。留空时自动从 name 生成。",
    )
    io_type: StreamIOType
    required: bool = Field(
        default=True,
        description="是否为必需连接。",
    )
    description: str = Field(
        default="",
        description="端口用途说明。",
    )

    @model_validator(mode="after")
    def _auto_display_name(self) -> "StreamInputPort":
        if self.display_name is None:
            self.display_name = self.name.replace("-", " ").replace("_", " ").title()
        return self


class StreamOutputPort(BaseModel):
    """Stream 输出端口 — 向下游节点提供数据。"""

    name: str = Field(
        ...,
        description="端口标识符，节点内唯一。",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="人类可读的显示名称。留空时自动从 name 生成。",
    )
    io_type: StreamIOType
    description: str = Field(
        default="",
        description="端口用途说明。",
    )

    @model_validator(mode="after")
    def _auto_display_name(self) -> "StreamOutputPort":
        if self.display_name is None:
            self.display_name = self.name.replace("-", " ").replace("_", " ").title()
        return self


# ═══════════════════════════════════════════════════════════════════════════
# On-Board I/O
# ═══════════════════════════════════════════════════════════════════════════

class OnBoardInputKind(str, Enum):
    """On-Board 输入参数的数据类型。

    选型指南（供节点开发者和 Agent 参考）：

    - ``string``  — 单行自由文本。用于无固定选项的标识符、路径、关键词。
                   例：ORCA method 关键词（"B3LYP"）、basis set 名（"def2-SVP"）。
                   关联字段：无。
                   切勿用于有固定候选值的参数（改用 ``enum``）。

    - ``integer`` — 整数。用于计数类参数，如核数、最大迭代次数、电荷（含负数）。
                   关联字段：``min_value``、``max_value``（可选，用于 UI 范围校验）。
                   ``resource_bindings`` 绑定的参数必须是 ``integer`` 或 ``float``。

    - ``float``   — 浮点数。用于物理量参数，如温度（298.15 K）、压力（1.0 atm）、能量阈值。
                   关联字段：``min_value``、``max_value``、``unit``（仅供 UI 显示）。

    - ``boolean`` — 布尔值（true/false）。用于开关类参数，如"是否启用溶剂模型"。
                   ``OnBoardOutput`` 中 ``quality_gate=True`` 的输出必须是 ``boolean``。

    - ``enum``    — 枚举（有限候选值）。用于有明确选项集的参数，如收敛标准、弥散修正类型。
                   **必须**同时提供 ``allowed_values``，否则 Schema 报错。
                   例：``allowed_values: [none, D3, D3BJ, D4]``。

    - ``textarea``— 多行文本。用于需要换行的内容，如 XYZ 分子坐标、内联脚本片段。
                   UI 渲染为可拉伸的 textarea 组件。
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    TEXTAREA = "textarea"


class GateDefault(str, Enum):
    """Quality Gate 的默认行为策略。"""

    MUST_PASS = "must_pass"
    """必须通过 — Gate 为 false 时阻止下游节点运行（Argo when 条件）。"""

    WARN = "warn"
    """仅警告 — Gate 为 false 时记录警告，不阻断工作流。"""

    IGNORE = "ignore"
    """忽略 — 不生成任何 Argo 条件，完全忽略此 Gate 的值。"""


class OnBoardInput(BaseModel):
    """On-Board 输入 — 用户在节点面板直接配置的参数。

    例如：泛函类型、截断能、收敛阈值等。

    必填/可选规则：
    - ``default`` 不为 None → 可选（用户不填则使用默认值）
    - ``default`` 为 None → 必填（用户必须提供值）

    kind 选型速查：
    - ``string``   自由单行文本（ORCA 方法名、文件名等）
    - ``integer``  整数（核数、电荷、迭代次数）；可被 resource_bindings 绑定
    - ``float``    浮点数（温度、压力、阈值）；可被 resource_bindings 绑定
    - ``boolean``  开关（true/false）
    - ``enum``     固定选项集，**必须**同时填 allowed_values
    - ``textarea`` 多行文本（XYZ 坐标、内联脚本）

    """

    name: str = Field(
        ...,
        description="参数标识符，节点内唯一，snake_case 命名。",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="人类可读的显示名称。留空时自动从 name 生成（下划线→空格，首字母大写）。",
    )
    kind: OnBoardInputKind = Field(
        ...,
        description=(
            "参数数据类型。"
            "string=单行文本 | integer=整数 | float=浮点 | "
            "boolean=开关 | enum=枚举（需配 allowed_values）| textarea=多行文本。"
        ),
    )
    default: Any = Field(
        default=None,
        description=(
            "默认值。为 None（即不写此字段）表示必填，用户必须提供。"
            "有默认值则为可选。类型须与 kind 匹配：integer→int，float→float，"
            "boolean→true/false，enum→allowed_values 中的某个值。"
        ),
    )
    allowed_values: Optional[list[str]] = Field(
        default=None,
        description="枚举类型的合法值列表。kind=enum 时必填，其他 kind 留空。",
    )
    min_value: Optional[float] = Field(
        default=None,
        description="数值类型（integer/float）的最小值，用于 UI 校验。其他 kind 留空。",
    )
    max_value: Optional[float] = Field(
        default=None,
        description="数值类型（integer/float）的最大值，用于 UI 校验。其他 kind 留空。",
    )
    unit: Optional[str] = Field(
        default=None,
        description=(
            "参数的物理单位，仅供 UI 标签显示，不做自动转换。"
            "仅在 kind=float 或 kind=integer 时有意义，如 'K'、'atm'、'eV'。"
        ),
    )
    description: str = Field(
        default="",
        description=(
            "参数用途说明，在 UI 中作为帮助文字显示。"
            "建议说明：取值含义、对计算的影响、与其他参数的联动关系。"
        ),
    )

    @model_validator(mode="after")
    def _auto_display_name(self) -> "OnBoardInput":
        if self.display_name is None:
            self.display_name = self.name.replace("-", " ").replace("_", " ").title()
        return self


class OnBoardOutput(BaseModel):
    """On-Board 输出 — 节点面板直接显示的运行结果。

    例如：最终能量、收敛状态等。

    当 ``quality_gate=True`` 时，此输出被标记为质量控制关切，
    需要 ``kind`` 为 ``boolean``，可配置默认策略 ``gate_default``。
    """

    name: str = Field(
        ...,
        description="输出标识符，节点内唯一。",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="人类可读的显示名称。留空时自动从 name 生成。",
    )
    kind: OnBoardInputKind
    unit: Optional[str] = Field(
        default=None,
        description="输出值的单位。",
    )
    description: str = Field(
        default="",
        description="输出用途说明。",
    )

    # ── Quality Gate 字段 ──────────────────────────────────────────────────
    quality_gate: bool = Field(
        default=False,
        description=(
            "是否为质量控制门控。True 时此输出作为收敛/质量判据，"
            "工作流编译器会生成对应的 Argo 条件逻辑。"
        ),
    )
    gate_default: GateDefault = Field(
        default=GateDefault.MUST_PASS,
        description=(
            "Gate 默认行为策略。仅当 quality_gate=True 时生效。"
            "must_pass: 阻断下游 | warn: 仅警告 | ignore: 忽略。"
        ),
    )
    gate_description: str = Field(
        default="",
        description="Gate 的质量控制描述，如 '检查几何优化是否收敛'。",
    )

    @model_validator(mode="after")
    def _auto_display_name(self) -> "OnBoardOutput":
        if self.display_name is None:
            self.display_name = self.name.replace("-", " ").replace("_", " ").title()
        return self

    @model_validator(mode="after")
    def _validate_gate_kind(self) -> "OnBoardOutput":
        """quality_gate=True 时 kind 必须为 boolean。"""
        if self.quality_gate and self.kind != OnBoardInputKind.BOOLEAN:
            raise ValueError(
                f"quality_gate=True 时 kind 必须为 boolean，当前为: {self.kind.value!r}"
            )
        return self
