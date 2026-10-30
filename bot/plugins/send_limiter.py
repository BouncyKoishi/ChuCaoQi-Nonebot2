"""
出站消息限流 - 防止瞬时大量发送触发 QQ 账号风控

用途：无论消息来自哪里（用户刷指令、机器人互相触发、插件循环、定时任务），
只要 bot 在一瞬间要发出大量消息，就把它压回一个安全的速率。

实现：利用 NoneBot 的 Bot.on_calling_api 钩子，在每次 API 调用前对发送类 API
做令牌桶限流；超限时抛 MockApiException 拦截本次调用并返回空结果，消息静默丢弃。
两级桶：全局（所有发送） + 单群（防止一个群刷屏、拖垮其它群）。

阈值定位：正常并发回复不受影响，只拦病态突发；调参改下面的常量即可。
"""

import time

from nonebot import logger
from nonebot.adapters import Bot
from nonebot.exception import MockApiException

# 需要计数的发送类 API（send_msg 是 bot.send 的底层调用，群/私聊方法各有独立 API）
SEND_APIS = {
    "send_msg",
    "send_group_msg",
    "send_private_msg",
    "send_group_forward_msg",
    "send_private_forward_msg",
}

# 全局令牌桶：允许 12 条瞬时突发，之后每秒恢复 3 条
BURST = 12
RATE = 3.0

# 单群令牌桶：允许 6 条瞬时突发，之后每秒恢复 2 条
GROUP_BURST = 6
GROUP_RATE = 2.0

_global_tokens = float(BURST)
_global_last = time.monotonic()

# group_id -> [tokens, last_refill_monotonic]
_group_tokens: dict[int, list] = {}

# 日志节流：循环刷屏时不要一条一条打日志
_dropped = 0
_last_log = 0.0


def _take_group(group_id: int) -> bool:
    now = time.monotonic()
    tokens, last = _group_tokens.get(group_id, (float(GROUP_BURST), now))
    tokens = min(float(GROUP_BURST), tokens + (now - last) * GROUP_RATE)
    if tokens < 1:
        _group_tokens[group_id] = [tokens, now]
        return False
    _group_tokens[group_id] = [tokens - 1, now]
    return True


def _take_global() -> bool:
    global _global_tokens, _global_last
    now = time.monotonic()
    _global_tokens = min(float(BURST), _global_tokens + (now - _global_last) * RATE)
    _global_last = now
    if _global_tokens < 1:
        return False
    _global_tokens -= 1
    return True


@Bot.on_calling_api
async def limit_outbound_messages(bot: Bot, api: str, data: dict) -> None:
    """发送类 API 的令牌桶限流，超限则静默丢弃本次消息"""
    if api not in SEND_APIS:
        return

    group_id = data.get("group_id")
    if group_id is not None:
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            group_id = None

    allowed = True
    if group_id is not None:
        allowed = _take_group(group_id)
    if allowed:
        allowed = _take_global()

    if allowed:
        return

    global _dropped, _last_log
    _dropped += 1
    now = time.monotonic()
    if now - _last_log >= 10:
        logger.warning(
            f"出站消息限流：丢弃 {_dropped} 条消息（最近一次 api={api}, "
            f"group_id={group_id}），已触发账号保护"
        )
        _last_log = now
        _dropped = 0

    # 拦截本次 API 调用，调用方拿到空结果；不会真正发到 QQ
    raise MockApiException(result={})
