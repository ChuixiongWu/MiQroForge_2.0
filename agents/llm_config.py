"""LLM Provider 抽象层 — 基于 userdata/models.yaml 模型注册表。

配置文件位置：  userdata/models.yaml（gitignored，API key 安全存放）
模板参考：      models.yaml.example（项目根目录）

用法：
    from agents.llm_config import LLMConfig

    llm = LLMConfig.get_chat_model(purpose="planner", temperature=0.0)
    models = LLMConfig.list_models()
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

_ROOT = Path(__file__).parent.parent
_REGISTRY_PATH = _ROOT / "userdata" / "models.yaml"


# ─── Registry loading ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    """加载 userdata/models.yaml。文件不存在时返回空字典。"""
    if not _REGISTRY_PATH.exists():
        return {}
    with _REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_model_config(purpose: Optional[str]) -> dict[str, Any]:
    """将 purpose → 命名模型 → 完整连接配置。

    解析优先级：
      agents.<purpose>  →  命名模型  →  models.<name>  →  base_url/api_key
        └─ 未设置 → default_model
              └─ 未设置 → models 中第一个

    每个模型的 base_url / api_key 未设置时继承全局 proxy。

    Returns
    -------
    dict:
        model_name  — 注册表中的命名（用于日志）
        model_id    — API 实际 model 名称（如 gpt-4o）
        base_url    — OpenAI 兼容接口地址
        api_key     — API 密钥
    """
    registry = _load_registry()

    if not registry:
        raise RuntimeError(
            f"未找到模型注册表：{_REGISTRY_PATH}\n"
            "请创建该文件并配置模型，参考 models.yaml.example。"
        )

    # 全局 proxy
    proxy = registry.get("proxy") or {}
    global_base_url: str = proxy.get("base_url", "")
    global_api_key: str = proxy.get("api_key", "")

    # 确定使用哪个命名模型
    model_name: Optional[str] = None
    if purpose:
        model_name = (registry.get("agents") or {}).get(purpose)
    if not model_name:
        model_name = registry.get("default_model")
    if not model_name:
        models_dict = registry.get("models") or {}
        if models_dict:
            model_name = next(iter(models_dict))

    if not model_name:
        raise RuntimeError("models.yaml 中没有定义任何模型。")

    models_dict = registry.get("models") or {}
    model_cfg = models_dict.get(model_name)
    if model_cfg is None:
        hint = f"agent '{purpose}' → 模型 '{model_name}'" if purpose else f"默认模型 '{model_name}'"
        raise RuntimeError(
            f"models.yaml: {hint} 未在 models 中定义。\n"
            f"已注册的模型：{list(models_dict.keys())}"
        )

    # 模型级别的配置覆盖全局
    return {
        "model_name": model_name,
        "model_id": model_cfg.get("model_id") or model_name,
        "base_url": model_cfg.get("base_url") or global_base_url,
        "api_key": model_cfg.get("api_key") or global_api_key,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def get_chat_model(purpose: Optional[str] = None, temperature: float = 0.0):
    """获取 LangChain BaseChatModel 实例。

    Parameters
    ----------
    purpose:
        Agent 用途标签，对应 models.yaml agents 映射（如 "planner", "evaluator"）。
        None 时使用 default_model。
    temperature:
        生成温度（0 = 确定性，1 = 创意）。

    Returns
    -------
    BaseChatModel
        LangChain 聊天模型实例（ChatOpenAI，兼容所有 OpenAI 格式接口）。
    """
    cfg = _resolve_model_config(purpose)

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": cfg["model_id"],
        "api_key": cfg["api_key"] or "EMPTY",
    }
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    if "claude" not in cfg["model_id"].lower():
        kwargs["temperature"] = temperature

    return ChatOpenAI(**kwargs)


class LLMConfig:
    """LLM 配置帮助类（静态方法封装，对外统一接口）。"""

    @staticmethod
    def get_chat_model(purpose: Optional[str] = None, temperature: float = 0.0):
        """获取指定 purpose 的 LangChain 模型实例。"""
        return get_chat_model(purpose=purpose, temperature=temperature)

    @staticmethod
    def list_models() -> list[str]:
        """返回所有已注册的命名模型列表。"""
        return list((_load_registry().get("models") or {}).keys())

    @staticmethod
    def get_agent_model(purpose: str) -> str:
        """返回指定 purpose 实际使用的命名模型（用于日志/调试）。"""
        return _resolve_model_config(purpose)["model_name"]

    @staticmethod
    def reload() -> None:
        """清除缓存，热重载 models.yaml（修改配置后无需重启服务）。"""
        _load_registry.cache_clear()

    @staticmethod
    def is_configured() -> bool:
        """检查 models.yaml 是否存在且包含至少一个模型。"""
        try:
            _resolve_model_config(None)
            return True
        except RuntimeError:
            return False
