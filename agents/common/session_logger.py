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
        **extra: Any,
    ) -> None:
        """记录一次 LLM 调用的完整输入和输出。

        Parameters
        ----------
        step_name:  "generate" | "evaluate" | 自定义
        messages:   LangChain Message 列表（SystemMessage/HumanMessage）
        response_content:  LLM 返回的原始文本
        iteration:  当前迭代轮次
        **extra:    额外元数据（如 parsed_json, error 等）
        """
        serialized_messages = []
        for msg in messages:
            serialized_messages.append({
                "role": type(msg).__name__,
                "content": msg.content,
            })

        self.steps.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "messages_to_llm": serialized_messages,
            "llm_response": response_content,
            **extra,
        })

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
