"""LLM Provider 抽象层 — 基于 userdata/models.yaml 模型注册表。

配置文件位置：  userdata/shared/models.yaml（gitignored，API key 安全存放）
模板参考：      models.yaml.example（项目根目录）

架构：
  providers  →  API 连接配置（协议类型 + base_url + api_key）
  models     →  模型定义（model_id + provider 引用 + extra_params）
  agents     →  Agent → 模型映射

用法：
    from agents.llm_config import LLMConfig

    llm = LLMConfig.get_chat_model(purpose="planner", temperature=0.0)
    vision_content = LLMConfig.build_vision_content("evaluator_vision", text, images)
    models = LLMConfig.list_models()
"""

from __future__ import annotations

import contextvars
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

# Token 追踪回调（由 API 层注入，Agent 层零感知）
_token_tracker: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "llm_token_tracker", default=None
)

_ROOT = Path(__file__).parent.parent
_REGISTRY_PATH = _ROOT / "userdata" / "shared" / "models.yaml"

# Anthropic temperature 上限
_ANTHROPIC_TEMP_MAX = 1.0


# ─── Registry loading ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    """加载 userdata/models.yaml。文件不存在时返回空字典。"""
    if not _REGISTRY_PATH.exists():
        return {}
    with _REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ─── Resolution ───────────────────────────────────────────────────────────────

def _resolve_model_config(purpose: Optional[str]) -> dict[str, Any]:
    """三段解析：purpose → model → provider → 连接参数。

    解析链：
      agents.<purpose>  →  命名模型  →  provider 连接信息
        └─ 未设置 → default_model
              └─ 未设置 → models 中第一个

    Returns
    -------
    dict:
        provider_type  — "anthropic" | "openai" | "google"
        model_id       — API 实际 model 名称（如 claude-opus-4-7）
        model_name     — 注册表中的命名（用于日志）
        base_url       — API 端点地址
        api_key        — API 密钥
        extra_params   — 模型级额外参数（如 thinking: true），透传给 LLM 构造函数
    """
    registry = _load_registry()

    if not registry:
        raise RuntimeError(
            f"未找到模型注册表：{_REGISTRY_PATH}\n"
            "请创建该文件并配置模型，参考 models.yaml.example。"
        )

    # ── Step 1: 确定使用哪个命名模型 ──
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

    # ── Step 2: 获取模型配置 ──
    models_dict = registry.get("models") or {}
    model_cfg = models_dict.get(model_name)
    if model_cfg is None:
        hint = f"agent '{purpose}' → 模型 '{model_name}'" if purpose else f"默认模型 '{model_name}'"
        raise RuntimeError(
            f"models.yaml: {hint} 未在 models 中定义。\n"
            f"已注册的模型：{list(models_dict.keys())}"
        )

    model_id = model_cfg.get("model_id") or model_name
    provider_name = model_cfg.get("provider")
    extra_params = model_cfg.get("extra_params") or {}

    # ── Step 3: 获取 provider 连接配置 ──
    providers_dict = registry.get("providers") or {}

    if provider_name and provider_name in providers_dict:
        provider_cfg = providers_dict[provider_name]
    elif provider_name:
        raise RuntimeError(
            f"models.yaml: 模型 '{model_name}' 引用的 provider '{provider_name}' 未在 providers 中定义。\n"
            f"已注册的 provider：{list(providers_dict.keys())}"
        )
    else:
        # 兼容：未指定 provider 时使用第一个
        if providers_dict:
            provider_name = next(iter(providers_dict))
            provider_cfg = providers_dict[provider_name]
        else:
            raise RuntimeError(
                f"models.yaml: 模型 '{model_name}' 未指定 provider，且 providers 为空。\n"
                "请为每个模型添加 provider 字段，或在 providers 中注册至少一个 provider。"
            )

    return {
        "provider_type": provider_cfg.get("type", "openai"),
        "model_id": model_id,
        "model_name": model_name,
        "base_url": model_cfg.get("base_url") or provider_cfg.get("base_url", ""),
        "api_key": model_cfg.get("api_key") or provider_cfg.get("api_key", ""),
        "extra_params": extra_params,
    }


# ─── Vision Content Builder ───────────────────────────────────────────────────

def build_vision_content(
    purpose: str,
    text: str,
    images_b64: list[str],
    max_images: int = 4,
) -> list[dict[str, Any]]:
    """构建多模态消息的 content 列表，根据 provider 自动选择图片格式。

    Anthropic provider → {"type": "image", "source": {...}}
    OpenAI   provider → {"type": "image_url", "image_url": {...}}

    Parameters
    ----------
    purpose:
        Agent 用途标签（如 "evaluator_vision"），用于查找对应 provider。
    text:
        文本 prompt 内容。
    images_b64:
        Base64 编码的图片列表。
    max_images:
        最多附加多少张图片（默认 4）。

    Returns
    -------
    list[dict]:
        LangChain HumanMessage content 列表，可直接传入 HumanMessage(content=result)。
    """
    cfg = _resolve_model_config(purpose)
    provider_type = cfg["provider_type"]

    content: list[dict[str, Any]] = [{"type": "text", "text": text}]

    for b64 in images_b64[:max_images]:
        if provider_type == "anthropic":
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64,
                },
            })
        else:
            # OpenAI / Google / 默认：OpenAI 兼容格式
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}",
                    "detail": "high",
                },
            })

    return content


# ─── Chat Model Factory ───────────────────────────────────────────────────────

def get_chat_model(purpose: Optional[str] = None, temperature: float = 0.0):
    """获取 LangChain BaseChatModel 实例。

    如果有 TokenUsageTracker 在当前上下文中，自动附加到模型回调。

    Parameters
    ----------
    purpose:
        Agent 用途标签，对应 models.yaml agents 映射（如 "planner", "evaluator"）。
        None 时使用 default_model。
    temperature:
        生成温度（0 = 确定性，1 = 创意）。
        Anthropic provider 自动 clamp 到 [0, 1]。

    Returns
    -------
    BaseChatModel
        LangChain 聊天模型实例（ChatAnthropic / ChatOpenAI / ChatGoogleGenerativeAI）。
    """
    cfg = _resolve_model_config(purpose)
    provider_type = cfg["provider_type"]
    model_id = cfg["model_id"]
    base_url = cfg["base_url"]
    api_key = cfg["api_key"] or "EMPTY"
    extra_params = cfg.get("extra_params") or {}

    model = None

    if provider_type == "anthropic":
        from langchain_anthropic import ChatAnthropic

        temp = min(max(temperature, 0.0), _ANTHROPIC_TEMP_MAX)
        kwargs: dict[str, Any] = {
            "model": model_id,
            "api_key": api_key,
            "temperature": temp,
        }
        if base_url:
            kwargs["base_url"] = base_url
        kwargs.update(extra_params)
        model = ChatAnthropic(**kwargs)

    elif provider_type == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": model_id,
            "api_key": api_key,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if "claude" not in model_id.lower():
            kwargs["temperature"] = temperature
        if extra_params:
            kwargs["extra_body"] = extra_params
        model = ChatOpenAI(**kwargs)

    elif provider_type == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs = {
            "model": model_id,
            "google_api_key": api_key,
            "temperature": temperature,
        }
        if extra_params:
            kwargs.update(extra_params)
        model = ChatGoogleGenerativeAI(**kwargs)

    else:
        raise ValueError(
            f"未知 provider type '{provider_type}'。"
            "支持的类型：anthropic, openai, google"
        )

    # 自动附加 TokenUsageTracker（若当前上下文中有）
    tracker = _token_tracker.get()
    if tracker is not None and model is not None:
        if hasattr(model, 'callbacks') and model.callbacks:
            model.callbacks.append(tracker)
        elif hasattr(model, 'callbacks'):
            model.callbacks = [tracker]

    return model


# ─── Public API ───────────────────────────────────────────────────────────────

class LLMConfig:
    """LLM 配置帮助类（静态方法封装，对外统一接口）。"""

    @staticmethod
    def get_chat_model(purpose: Optional[str] = None, temperature: float = 0.0):
        """获取指定 purpose 的 LangChain 模型实例。"""
        return get_chat_model(purpose=purpose, temperature=temperature)

    @staticmethod
    def set_token_tracker(tracker) -> None:
        """在当前上下文（线程）中设置 token 追踪器。
        之后所有由此线程创建的 LLM 模型都会自动附加该 tracker。
        """
        _token_tracker.set(tracker)

    @staticmethod
    def get_token_tracker():
        """获取当前上下文（线程）中的 token 追踪器。"""
        return _token_tracker.get()

    @staticmethod
    def clear_token_tracker() -> None:
        """清除当前上下文中的 token 追踪器。"""
        _token_tracker.set(None)

    @staticmethod
    def build_vision_content(
        purpose: str,
        text: str,
        images_b64: list[str],
        max_images: int = 4,
    ) -> list[dict[str, Any]]:
        """构建 provider 感知的多模态 content 列表。"""
        return build_vision_content(purpose, text, images_b64, max_images)

    @staticmethod
    def list_models() -> list[str]:
        """返回所有已注册的命名模型列表。"""
        return list((_load_registry().get("models") or {}).keys())

    @staticmethod
    def list_providers() -> list[str]:
        """返回所有已注册的 provider 列表。"""
        return list((_load_registry().get("providers") or {}).keys())

    @staticmethod
    def get_agent_model(purpose: str) -> str:
        """返回指定 purpose 实际使用的命名模型（用于日志/调试）。"""
        return _resolve_model_config(purpose)["model_name"]

    @staticmethod
    def get_provider_type(purpose: str) -> str:
        """返回指定 purpose 对应的 provider type（用于客户端判断协议格式）。"""
        return _resolve_model_config(purpose)["provider_type"]

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
