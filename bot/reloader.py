"""
重载函数模块 - 封装 NoneBot2 的 matcher 创建函数，自动添加用户注册等规则

NoneBot2 的 Rule checker 在同一优先级内通过 anyio task group 并发执行，
导致多个 matcher 的注册 Rule 同时触发，产生重复数据。
解决方案：使用 event ID 去重，避免同一事件重复执行注册逻辑。
并发安全由数据库 UNIQUE 约束 + get_or_create 保证。
"""

from nonebot import get_driver, on_command as _on_command, on_message as _on_message, on_notice as _on_notice
from nonebot.adapters import Event
from nonebot.permission import Permission
from nonebot.rule import Rule

from platform_context import get_platform_type, get_platform_user_id

import core.db.user as user_db
import core.db.kusa_system as kusa_db

_registered_kusa_events: set[int] = set()
_registered_db_events: set[int] = set()
_MAX_CACHE_SIZE = 10000


def _get_platform_info(event: Event) -> tuple:
    """平台类型与平台用户标识，取值规则与 PlatformContext 保持一致

    QQ 官方取个人 openid（群 member_openid / 私聊 user_openid），
    避免同一人在不同场景被注册成多个统一用户。
    """
    return get_platform_type(event), get_platform_user_id(event)


def _cleanup_cache(cache: set[int]):
    if len(cache) >= _MAX_CACHE_SIZE:
        cache.clear()


async def _register_unified_user(event: Event) -> bool:
    event_id = id(event)

    if event_id in _registered_db_events:
        return True

    _cleanup_cache(_registered_db_events)
    _registered_db_events.add(event_id)

    platform, platform_id = _get_platform_info(event)
    if not platform or not platform_id:
        return True

    unified_user = await user_db.getUnifiedUserByPlatform(platform, platform_id)
    if not unified_user:
        if platform == "onebot":
            await user_db.createUnifiedUserForOnebot(platform_id)
        elif platform == "qqbot":
            await user_db.createUnifiedUserForQQBot(platform_id)

    return True


async def _register_kusa_user(event: Event) -> bool:
    event_id = id(event)

    if event_id in _registered_kusa_events:
        return True

    _cleanup_cache(_registered_kusa_events)
    _registered_kusa_events.add(event_id)

    await _register_unified_user(event)

    platform, platform_id = _get_platform_info(event)
    if platform and platform_id:
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


# ===== 官机未绑定账号门禁 =====
#
# 官机账号在完成身份绑定（realQQ 非空）前不参与涉及用户权益的插件。
# 禁止清单中的插件改用 bound_kusa_command / bound_db_command 注册 matcher
# （门禁通过后由对应包装器补齐账号：kusa 层建 UnifiedUser + KusaBase，db 层建 UnifiedUser）

async def _is_bound(bot, event: Event) -> bool:
    if get_platform_type(event) != 'qqbot':
        return True

    platform_id = get_platform_user_id(event)
    if not platform_id:
        return False
    try:
        user = await user_db.getUnifiedUserByPlatform('qqbot', platform_id)
    except Exception:
        return False
    return bool(user and user.realQQ)


bound_required = Permission(_is_bound)

# 被门禁拦截的指令名（含别名），用于给出绑定提示
_blocked_commands: set = set()


def _gate(cmd, kwargs: dict) -> dict:
    _blocked_commands.add(str(cmd))
    for alias in kwargs.get('aliases') or ():
        _blocked_commands.add(str(alias))
    kwargs.setdefault('permission', bound_required)
    return kwargs


def bound_kusa_command(cmd, **kwargs):
    """禁止清单插件专用 kusa_command：官机未绑定时拦截"""
    return kusa_command(cmd, **_gate(cmd, kwargs))


def bound_db_command(cmd, **kwargs):
    """禁止清单插件专用 db_command：官机未绑定时拦截"""
    return db_command(cmd, **_gate(cmd, kwargs))


def _parse_command_name(text: str) -> str:
    starts = sorted(get_driver().config.command_start or (), key=len, reverse=True)
    for start in starts:
        if text.startswith(start):
            rest = text[len(start):].strip()
            return rest.split()[0] if rest else ''
    return ''


async def _is_unbound_blocked_command(bot, event: Event) -> bool:
    if get_platform_type(event) != 'qqbot':
        return False
    if _parse_command_name((event.get_plaintext() or '').strip()) not in _blocked_commands:
        return False
    return not await _is_bound(bot, event)


bind_hint = _on_message(rule=Rule(_is_unbound_blocked_command), priority=2, block=True)


@bind_hint.handle()
async def _send_bind_hint():
    await bind_hint.finish('该指令需要先完成身份绑定，请发送 !绑定 <你的QQ号>')
