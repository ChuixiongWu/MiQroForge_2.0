"""基础镜像注册表 Schema。

Level 1 实体 — 包含计算软件的容器镜像定义。
registry.yaml 通过 :class:`BaseImageRegistry` 加载并校验。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BaseImageSpec(BaseModel):
    """单个基础镜像的规格描述。

    每个条目代表一个 "软件 + 版本" 的容器环境。
    """

    name: str = Field(
        ...,
        description="唯一键，如 'vasp-6.4.1'。",
    )
    display_name: str = Field(
        ...,
        description="人类可读的显示名称。",
    )
    description: str = Field(
        default="",
        description="镜像用途说明。",
    )
    image: str = Field(
        ...,
        description="镜像仓库/名称，如 'docker.io/library/vasp'。",
    )
    tag: str = Field(
        ...,
        description="镜像标签，如 '6.4.1'。",
    )
    source_type: str = Field(
        default="dockerhub",
        description="镜像来源类型：'dockerhub' / 'custom' / 'ghcr'。",
    )
    software_name: str = Field(
        ...,
        description="底层计算软件名称，如 'vasp'。",
    )
    software_version: str = Field(
        ...,
        description="计算软件版本号，如 '6.4.1'。",
    )
    additional_software: dict[str, str] = Field(
        default_factory=dict,
        description="镜像中预装的其他软件及版本，如 {'openmpi': '4.1.6'}。",
    )
    workdir: str = Field(
        default="/mf/workdir",
        description="容器内的工作目录。",
    )
    entrypoint_convention: str = Field(
        default="/mf/profile/run.sh",
        description="入口脚本的约定路径。",
    )
    license_type: Optional[str] = Field(
        default=None,
        description="软件许可证类型，如 'proprietary' / 'GPL-3.0'。",
    )

    def full_image_ref(self) -> str:
        """返回完整镜像引用，格式 ``image:tag``。"""
        return f"{self.image}:{self.tag}"


class BaseImageRegistry(BaseModel):
    """基础镜像注册表 — 所有可用基础镜像的集合。

    对应 ``nodes/base_images/registry.yaml``。
    """

    images: list[BaseImageSpec] = Field(default_factory=list)

    def get(self, name: str) -> BaseImageSpec | None:
        """按 ``name`` 查找基础镜像，未找到返回 ``None``。"""
        for img in self.images:
            if img.name == name:
                return img
        return None

    def list_by_software(self, software_name: str) -> list[BaseImageSpec]:
        """列出指定软件的所有基础镜像版本。"""
        return [
            img for img in self.images
            if img.software_name == software_name
        ]
