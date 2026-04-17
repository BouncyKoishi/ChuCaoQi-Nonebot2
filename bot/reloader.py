"""
重载函数模块 - 封装 NoneBot2 的 matcher 创建函数，自动添加用户注册等规则

NoneBot2 的 Rule checker 在同一优先级内通过 anyio task group 并发执行，
导致多个 matcher 的注册 Rule 同时触发，产生重复数据。
解决方案：使用 asyncio.Lock + event ID 去重，确保同一事件的注册逻辑只执行一次。

性能说明：
- 76 个协程的创建/调度开销约 0.1-0.2ms
- 数据库 I/O 约 1-10ms
- 协程开销相比数据库操作可忽略不计
- 快速路径（event_id in cache）是 O(1) 哈希查找，极快
"""

import asyncio
from typing import Union
from nonebot import on_command as _on_command, on_message as _on_message, on_notice as _on_notice
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.qq import GroupAtMessageCreateEvent

import dbConnection.user as user_db
import dbConnection.kusa_system as kusa_db

_register_lock = asyncio.Lock()
_registered_kusa_events: set[int] = set()
_registered_db_events: set[int] = set()
_MAX_CACHE_SIZE = 10000


def _get_platform_info(event) -> tuple:
    if isinstance(event, GroupMessageEvent):
        return "onebot", str(event.user_id)
    elif isinstance(event, PrivateMessageEvent):
        return "onebot", str(event.user_id)
    elif isinstance(event, GroupAtMessageCreateEvent):
        return "qqbot", event.author.id
    return None, None


def _cleanup_cache(cache: set[int]):
    if len(cache) >= _MAX_CACHE_SIZE:
        cache.clear()


async def _register_unified_user(event: Union[GroupMessageEvent, PrivateMessageEvent, GroupAtMessageCreateEvent]) -> bool:
    event_id = id(event)

    if event_id in _registered_db_events:
        return True

    async with _register_lock:
        if event_id in _registered_db_events:
            return True
        _cleanup_cache(_registered_db_events)
        _registered_db_events.add(event_id)

        platform, platform_id = _get_platform_info(event)
        if not platform:
            return True

        unified_user = await user_db.getUnifiedUserByPlatform(platform, platform_id)
        if not unified_user:
            if platform == "onebot":
                await user_db.createUnifiedUserForOnebot(platform_id)
            elif platform == "qqbot":
                await user_db.createUnifiedUserForQQBot(platform_id)

    return True


async def _register_kusa_user(event: Union[GroupMessageEvent, PrivateMessageEvent, GroupAtMessageCreateEvent]) -> bool:
    event_id = id(event)

    if event_id in _registered_kusa_events:
        return True

    async with _register_lock:
        if event_id in _registered_kusa_events:
            return True
        _cleanup_cache(_registered_kusa_events)
        _registered_kusa_events.add(event_id)

        await _register_unified_user(event)

        platform, platform_id = _get_platform_info(event)
        if platform:
            unified_user = await user_db.getUnifiedUserByPlatform(platform, platform_id)
            if unified_user:
                await kusa_db.createKusaUser(unified_user.id)

    return True


def kusa_command(cmd, **kwargs):
    """
    生草系统插件专用 on_command
    自动注册生草用户（包含统一用户），带并发去重保护

    用法:
        from reloader import kusa_command as on_command

        my_cmd = on_command("生草")
    """
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_kusa_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_command(cmd, rule=final_rule, **kwargs)


def db_command(cmd, **kwargs):
    """
    数据库交互插件专用 on_command
    自动注册统一用户，带并发去重保护

    用法:
        from reloader import db_command as on_command

        my_cmd = on_command("绑定")
    """
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_unified_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_command(cmd, rule=final_rule, **kwargs)


def kusa_message(**kwargs):
    """生草系统插件专用 on_message"""
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_kusa_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_message(rule=final_rule, **kwargs)


def db_message(**kwargs):
    """数据库交互插件专用 on_message"""
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_unified_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_message(rule=final_rule, **kwargs)
