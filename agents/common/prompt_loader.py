"""agents/common/prompt_loader.py — Jinja2 模板加载器。

从 agents/<agent_name>/prompts/ 目录加载 .jinja2 模板文件，
渲染为 LangChain Message 内容字符串。

用法：
    from agents.common.prompt_loader import load_prompt

    system_msg = load_prompt("planner/prompts/plan_system.jinja2", molecule="H₂O")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

# agents/ 目录根路径
_AGENTS_ROOT = Path(__file__).parent.parent


def load_prompt(template_path: str, **kwargs: Any) -> str:
    """渲染 Jinja2 模板。

    Parameters
    ----------
    template_path:
        相对于 agents/ 目录的模板路径，如 "planner/prompts/plan_system.jinja2"。
    **kwargs:
        模板变量。

    Returns
    -------
    str
        渲染后的字符串。
    """
    full_path = _AGENTS_ROOT / template_path
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {full_path}")

    env = Environment(
        loader=FileSystemLoader(str(full_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(full_path.name)
    return template.render(**kwargs)


def load_prompt_from_path(full_path: str | Path, **kwargs: Any) -> str:
    """从完整路径渲染 Jinja2 模板。"""
    full_path = Path(full_path)
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {full_path}")

    env = Environment(
        loader=FileSystemLoader(str(full_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(full_path.name)
    return template.render(**kwargs)
