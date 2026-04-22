"""节点资源估算 Schema。

每个节点必须声明运行所需的计算资源。
Compute 节点需要完整声明；Lightweight 节点使用合理默认值。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """资源配置类型标识，用作 Union 辨别器。"""

    COMPUTE = "compute"
    LIGHTWEIGHT = "lightweight"


class ComputeResources(BaseModel):
    """重量级计算节点的资源估算。

    所有字段均为必填（``gpu_count`` 除外），以确保
    Argo 模板能生成准确的 ``resources.requests``。
    """

    type: Literal[ResourceType.COMPUTE] = ResourceType.COMPUTE

    cpu_cores: int = Field(
        ..., ge=1,
        description="所需 CPU 核数。",
    )
    mem_gb: float = Field(
        ..., gt=0,
        description="应用层内存（GiB），传递给计算软件（如 Gaussian %mem、Psi4 set_memory）。"
                    "Pod 内存 = mem_gb + mem_overhead。",
    )
    mem_overhead: float = Field(
        default=0.0, ge=0,
        description="Pod 内存超出应用层内存的部分（GiB）。用于软件 overhead（如 Psi4 需要额外 4GB）。"
                    "大多数节点不需要，省略即默认为 0。",
    )
    estimated_walltime_hours: float = Field(
        ..., gt=0,
        description="预估运行时长（小时）。",
    )
    gpu_count: int = Field(
        default=0, ge=0,
        description="所需 GPU 数量。",
    )
    gpu_type: Optional[str] = Field(
        default=None,
        description="GPU 型号要求，如 'nvidia-a100'。",
    )
    scratch_disk_gb: float = Field(
        default=0, ge=0,
        description="临时磁盘空间（GiB），用于计算中间文件。",
    )
    parallel_tasks: int = Field(
        default=1, ge=1,
        description="MPI 并行任务数。",
    )
    parametrize: Optional[list[str]] = Field(
        default=None,
        description=(
            "需要参数化的资源字段列表，用户可在前端覆盖。"
            "如 ['cpu_cores', 'mem_gb']。"
            "每个字段的 onboard input 名称与默认属性由 resource_defaults.yaml 统一定义。"
            "编译器会从 onboard_params 读取实际值并覆盖静态资源声明。"
        ),
    )


class LightweightResources(BaseModel):
    """轻量节点的资源估算。

    提供合理的默认值，大多数场景无需修改。
    """

    type: Literal[ResourceType.LIGHTWEIGHT] = ResourceType.LIGHTWEIGHT

    cpu_cores: int = Field(
        default=1, ge=1,
        description="所需 CPU 核数。",
    )
    memory_gb: float = Field(
        default=1.0, gt=0,
        description="所需内存（GiB）。",
    )
    estimated_walltime_hours: float = Field(
        default=0.083, gt=0,
        description="预估运行时长（小时），默认约 5 分钟。",
    )
    timeout_seconds: int = Field(
        default=300, gt=0,
        description="硬超时（秒），超过后强制终止。",
    )
