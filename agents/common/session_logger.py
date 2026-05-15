"""agents/common/session_logger.py — Agent 会话日志记录器。

使用 Python contextvars 实现线程安全的会话追踪。
每次 Agent 调用自动记录：
  - 渲染后的完整 Prompt（System + User）
  - LLM 原始返回
  - 评判结果与迭代过程
  - 时间戳

保存路径：
  userdata/agent_sessions/{YYYY-MM-DD}/{session_id}/
    planner_{HH-MM-SS}.json
    yaml_coder_{HH-MM-SS}.json
    conversation.json（由前端 clear 时触发保存）

用法：
    from agents.common.session_logger import start_session, get_session, end_session

    session = start_session("planner", {"intent": "..."})
    # ... 在 generator/evaluator 中 ...
    session = get_session()
    if session:
        session.log_llm_call("generate", messages, response.content)
    # ... 结束 ...
    log_data = end_session()
"""

from __future__ import annotations

import contextvars
import json
from datetime import datetime
from pathlib import Path
from typing import Any


# ─── 线程安全的上下文变量 ─────────────────────────────────────────────────────

_current_session: contextvars.ContextVar[AgentSessionLog | None] = (
    contextvars.ContextVar("agent_session", default=None)
)


# ─── Session Log 类 ──────────────────────────────────────────────────────────

class AgentSessionLog:
    """单次 Agent 调用的完整日志。"""

    def __init__(self, agent_type: str, request_data: dict[str, Any]):
        self.agent_type = agent_type
        self.request_data = request_data
        self.started_at = datetime.now().isoformat()
        self.steps: list[dict[str, Any]] = []

    def log_llm_call(
        self,
        step_name: str,
        messages: list,
        response_content: str,
        iteration: int = 0,
        max_content_len: int = 50000,
        token_usage: dict | None = None,
        **extra: Any,
    ) -> None:
        """记录一次 LLM 调用的完整输入和输出。

        Parameters
        ----------
        step_name:  "generate" | "evaluate" | 自定义
        messages:   LangChain Message 列表（SystemMessage/HumanMessage）
        response_content:  LLM 返回的原始文本
        iteration:  当前迭代轮次
        max_content_len: 单条消息内容的最大字符数（超长则截断）。默认 50000，
            保证 SystemMessage/HumanMessage 完整显示。
        token_usage: 可选 token 用量信息 {'input_tokens': N, 'output_tokens': N, 'total_tokens': N}
        **extra:    额外元数据（如 parsed_json, error 等）
        """
        serialized_messages = []
        for msg in messages:
            content = msg.content
            msg_type = type(msg).__name__
            # ToolMessage 通常较长且重复，使用较小截断值
            limit = 5000 if msg_type == "ToolMessage" else max_content_len
            if isinstance(content, str) and len(content) > limit:
                content = content[:limit] + f"\n... [truncated at {limit} chars]"
            serialized_messages.append({
                "role": type(msg).__name__,
                "content": content,
            })

        entry = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "messages_to_llm": serialized_messages,
            "llm_response": response_content,
            **extra,
        }
        if token_usage:
            entry["token_usage"] = token_usage
        self.steps.append(entry)

    def log_event(
        self,
        step_name: str,
        data: dict[str, Any],
    ) -> None:
        """记录非 LLM 事件（如程序化检查结果、RAG 检索等）。"""
        self.steps.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            **data,
        })

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        return {
            "agent_type": self.agent_type,
            "started_at": self.started_at,
            "finished_at": datetime.now().isoformat(),
            "request": self.request_data,
            "steps": self.steps,
            "total_llm_calls": sum(
                1 for s in self.steps if "llm_response" in s
            ),
        }


# ─── Context API ─────────────────────────────────────────────────────────────

def start_session(
    agent_type: str,
    request_data: dict[str, Any],
) -> AgentSessionLog:
    """创建并注册一个新的会话日志。在 to_thread 内调用。"""
    session = AgentSessionLog(agent_type, request_data)
    _current_session.set(session)
    return session


def get_session() -> AgentSessionLog | None:
    """获取当前线程/上下文的活跃会话。"""
    return _current_session.get()


def end_session() -> AgentSessionLog | None:
    """结束当前会话并返回日志。清除上下文。"""
    session = _current_session.get()
    _current_session.set(None)
    return session


# ─── 持久化 ──────────────────────────────────────────────────────────────────

def save_agent_log(
    log_data: dict[str, Any],
    session_id: str,
    userdata_root: Path,
) -> Path:
    """将单个 Agent 调用日志保存到磁盘。

    保存路径：
        userdata/agent_sessions/{YYYY-MM-DD}/{session_id}/{agent_type}_{HH-MM-SS}.json

    Returns
    -------
    Path: 保存的文件路径
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    agent_type = log_data.get("agent_type", "unknown")

    session_dir = userdata_root / "agent_sessions" / date_str / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{agent_type}_{time_str}.json"
    filepath = session_dir / filename

    # 避免重名
    counter = 1
    while filepath.exists():
        filename = f"{agent_type}_{time_str}_{counter}.json"
        filepath = session_dir / filename
        counter += 1

    filepath.write_text(
        json.dumps(log_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return filepath


def save_conversation(
    messages: list[dict[str, Any]],
    session_id: str,
    userdata_root: Path,
) -> Path:
    """保存前端对话消息到 conversation.json。

    Parameters
    ----------
    messages:  前端 ChatMessage 列表
    session_id:  会话 ID
    userdata_root:  userdata 根目录

    Returns
    -------
    Path: 保存的文件路径
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    session_dir = userdata_root / "agent_sessions" / date_str / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    filepath = session_dir / "conversation.json"

    payload = {
        "session_id": session_id,
        "saved_at": now.isoformat(),
        "message_count": len(messages),
        "messages": messages,
    }

    filepath.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return filepath


# ─── 人类可读格式导出 ──────────────────────────────────────────────────────

def format_log_as_text(log_data: dict[str, Any]) -> str:
    """将会话日志格式化为人类可读的纯文本，保留所有换行符。

    输出结构：
      - 会话元数据头部
      - 每个 step：LLM 调用（完整 prompt + response）或事件
    """
    lines: list[str] = []

    # ═══ 头部 ═══
    lines.append("=" * 70)
    lines.append("MiQroForge Agent Session Log")
    lines.append("=" * 70)
    lines.append(f"Agent:    {log_data.get('agent_type', 'unknown')}")
    lines.append(f"Started:  {log_data.get('started_at', '?')}")
    lines.append(f"Finished: {log_data.get('finished_at', '?')}")
    lines.append(f"LLM Calls: {log_data.get('total_llm_calls', 0)}")

    request = log_data.get("request", {})
    if request:
        lines.append("")
        lines.append("--- Request ---")
        for k, v in request.items():
            v_str = str(v)
            if len(v_str) > 120:
                v_str = v_str[:120] + "..."
            lines.append(f"  {k}: {v_str}")

    # ═══ Steps ═══
    steps = log_data.get("steps", [])
    for i, step in enumerate(steps):
        lines.append("")
        lines.append("-" * 70)
        step_name = step.get("step", f"Step {i}")
        iteration = step.get("iteration")
        header = f"  Step {i}: {step_name}"
        if iteration is not None:
            header += f" (iteration {iteration})"
        lines.append(header)
        lines.append("-" * 70)

        # LLM 调用 → 展示完整 messages 和 response
        if "llm_response" in step:
            messages = step.get("messages_to_llm", [])
            for msg in messages:
                role = msg.get("role", "?")
                content = msg.get("content", "")
                lines.append(f"\n  [{role}]")
                # 保留 content 中的所有换行符
                for cline in content.split("\n"):
                    lines.append(f"    | {cline}")

            lines.append(f"\n  [LLM Response]")
            response = step.get("llm_response", "")
            for rline in response.split("\n"):
                lines.append(f"    | {rline}")

            # 额外元数据
            extras = {k: v for k, v in step.items()
                      if k not in ("step", "timestamp", "iteration",
                                   "messages_to_llm", "llm_response")}
            if extras:
                lines.append("")
                for ek, ev in extras.items():
                    lines.append(f"  [{ek}]: {ev}")

        # 事件 → 展示 data
        else:
            for k, v in step.items():
                if k in ("step", "timestamp", "iteration"):
                    continue
                v_str = str(v)
                lines.append(f"\n  [{k}]")
                for vline in v_str.split("\n"):
                    lines.append(f"    {vline}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("End of Session Log")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_agent_log_text(
    log_data: dict[str, Any],
    session_id: str,
    userdata_root: Path,
) -> Path:
    """将会话日志保存为人类可读的纯文本文件。

    保存路径：
        userdata/.../{session_id}/{agent_type}_{HH-MM-SS}.txt

    Returns:
        Path: 保存的文件路径
    """
    now = datetime.now()
    time_str = now.strftime("%H-%M-%S")
    agent_type = log_data.get("agent_type", "unknown")

    session_dir = userdata_root / session_id if session_id else userdata_root
    session_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{agent_type}_{time_str}.txt"
    filepath = session_dir / filename

    counter = 1
    while filepath.exists():
        filename = f"{agent_type}_{time_str}_{counter}.txt"
        filepath = session_dir / filename
        counter += 1

    text = format_log_as_text(log_data)
    filepath.write_text(text, encoding="utf-8")
    return filepath
