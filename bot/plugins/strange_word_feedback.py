"""怪话选句埋点。

只负责把“选句决策 + 简短反馈”追加到按日滚动的 JSONL 日志，不参与记忆、
不做分析、不进入运行时 prompt。

日志文件：data/database/strangeWord/feedback/events-YYYY-MM-DD.jsonl
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.config import DATA_DIR


FEEDBACK_DIR = os.path.join(DATA_DIR, "database", "strangeWord", "feedback")
FEEDBACK_WINDOW_SECONDS = 120
MAX_CONTEXT_CHARS = 200
MAX_SELECTED_CHARS = 120

@dataclass(frozen=True)
class Decision:
    """一次选句结果。event_id 为 None 表示没有成功写入决策日志。"""

    text: str
    event_id: Optional[str] = None


_pending: Dict[str, Dict[str, Any]] = {}
_write_lock: Optional[asyncio.Lock] = None


def _get_write_lock() -> asyncio.Lock:
    global _write_lock
    if _write_lock is None:
        _write_lock = asyncio.Lock()
    return _write_lock


def _now() -> datetime:
    return datetime.now()


def _clean_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def build_context_excerpt(messages: List[Dict[str, Any]], limit: int = MAX_CONTEXT_CHARS) -> str:
    """把最近几条群聊压成一行，供后续 LLM 分析语境。"""
    parts: List[str] = []
    for message in list(messages)[-3:]:
        name = _clean_text(message.get("name", ""), 30)
        content = _clean_text(message.get("content", ""), 80)
        if not content:
            continue
        parts.append(f"{name}: {content}" if name else content)
    return _clean_text(" | ".join(parts), limit)


def normalize_text(value: Any) -> str:
    """复读判断用：只保留字母、数字和中文，忽略空格与标点。"""
    text = str(value or "").lower()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text)


def new_event_id() -> str:
    return f"{_now().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000, 9999)}"


def extract_message_id(sent: Any) -> Optional[Any]:
    """兼容 OneBot 返回 dict / 模型对象 / None。"""
    if sent is None:
        return None
    if isinstance(sent, (int, str)):
        return sent
    if isinstance(sent, dict):
        return sent.get("message_id") or sent.get("messageId")
    for attr in ("message_id", "messageId", "id"):
        value = getattr(sent, attr, None)
        if value is not None:
            return value
    data = getattr(sent, "dict", None)
    if callable(data):
        try:
            raw = data()
        except Exception:
            raw = None
        if isinstance(raw, dict):
            return raw.get("message_id") or raw.get("messageId")
    return None


def _event_field(event: Any, name: str) -> Any:
    value = getattr(event, name, None)
    if value is not None:
        return value
    for getter_name in ("dict",):
        getter = getattr(event, getter_name, None)
        if callable(getter):
            try:
                data = getter()
            except Exception:
                data = None
            if isinstance(data, dict) and name in data:
                return data[name]
    raw = getattr(event, "__dict__", None)
    if isinstance(raw, dict):
        return raw.get(name)
    return None


def _extract_reply_id(event: Any) -> Optional[Any]:
    reply = getattr(event, "reply", None)
    if not reply:
        return None
    for attr in ("id", "message_id", "messageId"):
        value = getattr(reply, attr, None)
        if value is not None:
            return value
    if isinstance(reply, dict):
        return reply.get("id") or reply.get("message_id")
    return None


async def _append(record: Dict[str, Any], day: Optional[str] = None) -> None:
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    target_day = day or _now().strftime("%Y-%m-%d")
    path = os.path.join(FEEDBACK_DIR, f"events-{target_day}.jsonl")
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    async with _get_write_lock():
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


async def log_decision(
    group_id: int,
    source: str,
    user_id: Any,
    context: str,
    action: str,
    selected: str,
) -> Optional[str]:
    """写一条决策日志，成功时返回 event_id，失败时返回 None。"""
    event_id = new_event_id()
    now = _now()
    record = {
        "type": "d",
        "id": event_id,
        "t": now.strftime("%m-%d %H:%M"),
        "src": source,
        "uid": str(user_id or ""),
        "ctx": _clean_text(context, MAX_CONTEXT_CHARS),
        "act": action,
        "text": _clean_text(selected, MAX_SELECTED_CHARS),
    }
    try:
        await _append(record, day=now.strftime("%Y-%m-%d"))
    except Exception as exc:
        # 埋点失败不能影响怪话主流程。
        print(f"[怪话埋点] 决策日志写入失败: {exc}")
        return None
    return event_id


def _day_from_event_id(event_id: str) -> str:
    raw = str(event_id).split("-", 1)[0]
    if len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return _now().strftime("%Y-%m-%d")


def bind_event(event_id: Optional[str], text: str, group_id: int, message_id: Any) -> None:
    """把一次已写日志的选句绑定到实际发送的 bot 消息，并启动反馈窗口。"""
    if not event_id or message_id is None:
        return
    key = str(message_id)
    _pending[key] = {
        "id": event_id,
        "text": text,
        "day": _day_from_event_id(event_id),
        "group_id": int(group_id),
        "reply": 0,
        "repeat": 0,
        "emoji": 0,
        "followup": 0,
    }
    asyncio.create_task(_settle_later(key))


async def _settle_later(key: str) -> None:
    try:
        await asyncio.sleep(FEEDBACK_WINDOW_SECONDS)
        item = _pending.pop(key, None)
        if not item:
            return
        await _append(
            {
                "type": "f",
                "id": item["id"],
                "reply": int(item["reply"]),
                "repeat": int(item["repeat"]),
                "emoji": int(item["emoji"]),
                "followup": int(item["followup"]),
            },
            day=item["day"],
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"[怪话埋点] 反馈结算失败: {exc}")


def observe_message(event: Any, bot_self_id: Any = None) -> None:
    """群消息到达时更新所有未完结核的反馈计数。"""
    if not _pending:
        return
    sender_id = _event_field(event, "user_id")
    if bot_self_id is not None and str(sender_id) == str(bot_self_id):
        return

    text = ""
    getter = getattr(event, "get_plaintext", None)
    if callable(getter):
        try:
            text = getter()
        except Exception:
            text = ""
    if not text:
        text = str(_event_field(event, "raw_message") or "")
    normalized = normalize_text(text)
    reply_id = _extract_reply_id(event)
    event_group_id = _event_field(event, "group_id")

    for key, item in list(_pending.items()):
        if event_group_id is not None and str(event_group_id) != str(item.get("group_id")):
            continue
        item["followup"] = int(item["followup"]) + 1
        if reply_id is not None and str(reply_id) == key:
            item["reply"] = 1
        selected_norm = normalize_text(item.get("text", ""))
        if len(selected_norm) >= 4 and normalized:
            if selected_norm in normalized or normalized in selected_norm:
                item["repeat"] = 1


def observe_emoji_like(event: Any) -> None:
    """处理 NapCat 的 group_msg_emoji_like 通知，记录消息表情回应总数。"""
    if not _pending:
        return
    notice_type = str(_event_field(event, "notice_type") or "")
    if notice_type != "group_msg_emoji_like":
        return
    message_id = _event_field(event, "message_id")
    if message_id is None:
        return
    item = _pending.get(str(message_id))
    if not item:
        return
    event_group_id = _event_field(event, "group_id")
    if event_group_id is not None and str(event_group_id) != str(item.get("group_id")):
        return

    likes = _event_field(event, "likes") or []
    total = 0
    if isinstance(likes, list):
        for like in likes:
            if isinstance(like, dict):
                try:
                    total += int(like.get("count") or 1)
                except (TypeError, ValueError):
                    total += 1
            else:
                try:
                    total += int(getattr(like, "count", 1) or 1)
                except (TypeError, ValueError):
                    total += 1
    item["emoji"] = total
