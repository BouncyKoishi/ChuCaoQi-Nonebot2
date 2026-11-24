"""
消息预处理插件 - NoneBot2 版本
全局触发门禁：群白名单、按用户前置限流

门禁覆盖两类触发：
- 消息指令：! 业务指令、# 回复类指令。用适配器归一化后的纯文本判断，
  因此“回复时发指令”“@机器人后发指令”都能正确识别（这两个前缀段会被
  适配器从 message 中剥掉，但 raw_message 里仍保留，不能拿来判断）。
- 拍一拍：只处理“拍机器人”的 notice，该能力仅 OneBot 提供。

群白名单只约束 OneBot 群。官方 Bot 群的 group_openid 在建立群映射前无法
解析成 QQ 群号，连“登记群映射”的指令本身都会被白名单拦掉，因此官方 Bot
的群一律放行，群级管控交由 QQ 平台侧（机器人可被拉入哪些群）负责。

前置限流只针对用户消息指令，静默丢弃，不警告、不屏蔽、不发任何提示。
"""

import time

from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotMessageEvent
from nonebot.adapters.onebot.v11.event import PokeNotifyEvent
from nonebot.adapters.qq import C2CMessageCreateEvent, GroupAtMessageCreateEvent
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

from kusa_base import plugin_config
from platform_context import (
    get_group_id,
    get_platform_type,
    get_platform_user_id,
    is_group_message,
)

MESSAGE_EVENTS = (OneBotMessageEvent, GroupAtMessageCreateEvent, C2CMessageCreateEvent)

# 统一指令入口：! 为业务指令， # 为 reply_commands 的回复类指令
COMMAND_PREFIXES = ('!', '#')

# 按用户前置限流：允许 5 条瞬时突发，之后每秒恢复 1 条
USER_BURST = 5
USER_RATE = 1.0

# platform_user_id -> [tokens, last_refill_monotonic]
_user_tokens: dict[str, list] = {}

# 日志节流：刷屏时不要一条一条打日志
_dropped = 0
_last_log = 0.0


def _is_group_allowed(group_key: str) -> bool:
    if not group_key:
        return False
    allow_groups = {str(gid) for gid in plugin_config.get('group', {}).get('allow', [])}
    return group_key in allow_groups


def _take_user(user_id: str) -> bool:
    now = time.monotonic()
    tokens, last = _user_tokens.get(user_id, (float(USER_BURST), now))
    tokens = min(float(USER_BURST), tokens + (now - last) * USER_RATE)
    if tokens < 1:
        _user_tokens[user_id] = [tokens, now]
        return False
    _user_tokens[user_id] = [tokens - 1, now]
    return True


@event_preprocessor
async def preprocessor_handler(event):
    """消息预处理处理器 - 全局生效"""
    global _dropped, _last_log

    # 拍一拍：只拦“拍机器人”这一种 notice，其它 notice 不在此处理
    if isinstance(event, PokeNotifyEvent):
        if event.sub_type != 'poke' or not event.group_id:
            return
        if event.target_id != event.self_id:
            return
        if not _is_group_allowed(str(event.group_id)):
            raise IgnoredException("非可用群，跳过拍一拍响应")
        return

    if not isinstance(event, MESSAGE_EVENTS):
        return

    # 用归一化后的纯文本判断前缀：回复段、@ 段已被适配器剥掉
    text = (event.get_plaintext() or '').strip()
    if not text.startswith(COMMAND_PREFIXES):
        return

    platform_user_id = get_platform_user_id(event)
    if not platform_user_id:
        return

    # 群白名单只约束 OneBot；官方 Bot 群在全放行下才能发出登记群映射的指令
    if (
        is_group_message(event)
        and get_platform_type(event) == 'onebot'
        and not _is_group_allowed(get_group_id(event))
    ):
        raise IgnoredException("非可用群，跳过指令响应")

    if not _take_user(platform_user_id):
        _dropped += 1
        now = time.monotonic()
        if now - _last_log >= 10:
            logger.warning(
                f"指令前置限流：丢弃 {_dropped} 条指令（最近一次 user_id={platform_user_id}）"
            )
            _last_log = now
            _dropped = 0
        raise IgnoredException("指令触发频率过高，静默丢弃")
