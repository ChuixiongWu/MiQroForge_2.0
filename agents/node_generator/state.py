"""agents/node_generator/state.py — Node Generator Agent 状态定义。"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from agents.schemas import NodeGenRequest, NodeGenResult, EvaluationResult


class NodeGenState(TypedDict, total=False):
    """Node Generator Agent 的 LangGraph 状态。"""

    # 输入
    request: NodeGenRequest

    # 中间状态
    reference_nodes: list[dict[str, Any]]   # few-shot 参考节点
    available_images: list[dict[str, Any]]  # 可用 Docker 镜像
    semantic_types: dict[str, Any]          # 语义类型注册表

    # 生成状态（formal 模式）
    nodespec_yaml: str
    run_sh: str
    input_templates: dict[str, str]         # 文件名 → 内容

    # 生成状态（ephemeral 模式）
    _input_data: dict[str, str]             # 真实输入数据 {port_name: content}
    script: str                             # 生成的 Python 脚本
    exec_stdout: str                        # 执行 stdout
    exec_stderr: str                        # 执行 stderr
    exec_return_code: int                   # 执行返回码
    generated_files: list[str]              # 沙箱生成的文件列表
    image_files: list[str]                  # 检测到的图片文件列表
    vision_feedback: list[str]              # 视觉评估反馈
    _sandbox_dir: str                       # 沙箱持久化目录（evaluator 可读取图片）

    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int

    # 输出
    result: Optional[NodeGenResult]

    # 错误
    error: Optional[str]
