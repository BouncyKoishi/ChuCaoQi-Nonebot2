"""
多平台适配模块
支持 OneBot V11 和 QQ 官方 Bot 协议
提供统一的接口供其他插件调用
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union

from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import Event as OneBotV11Event
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.adapters.qq import Event as QQEvent
from nonebot.adapters.qq import Message as QQMessage
from nonebot.adapters.qq import MessageSegment as QQMessageSegment
from nonebot.adapters.qq import Bot as QQBot


# 统一的事件类型
UnifiedEvent = Union[OneBotV11Event, QQEvent]
UnifiedMessageEvent = Union[OneBotV11MessageEvent, QQEvent]


@dataclass(frozen=True)
class ActionResult:
    """跨事件动作（禁言 / 主动推送）的执行结果

    reason 取值：no_bot / not_group / unsupported / invalid_target /
    no_permission / rate_limited / network / failed: ...
    """

    ok: bool
    reason: Optional[str] = None


def is_onebot_v11_event(event: Event) -> bool:
    """判断是否为 OneBot V11 事件（转发 platform_context）"""
    from platform_context import is_onebot_v11_event as _impl
    return _impl(event)


def is_qq_event(event: Event) -> bool:
    """判断是否为 QQ 官方 Bot 事件（转发 platform_context）"""
    from platform_context import is_qq_event as _impl
    return _impl(event)


def is_onebot_v11_bot(bot: Bot) -> bool:
    """判断是否为 OneBot V11 Bot"""
    return isinstance(bot, OneBotV11Bot)


def is_qq_bot(bot: Bot) -> bool:
    """判断是否为 QQ 官方 Bot"""
    return isinstance(bot, QQBot)


def get_platform_user_id(event: Event) -> Optional[str]:
    """获取平台用户ID（统一格式，转发 platform_context）"""
    from platform_context import get_platform_user_id as _impl
    return _impl(event)


def get_nickname_from_event(event: Event) -> str:
    """从事件中获取用户昵称（转发 platform_context）"""
    from platform_context import get_nickname_from_event as _impl
    return _impl(event)


def get_group_id(event: Event) -> Optional[str]:
    """获取群ID（统一格式，转发 platform_context）"""
    from platform_context import get_group_id as _impl
    return _impl(event)


def is_group_message(event: Event) -> bool:
    """判断是否为群聊消息（转发 platform_context）"""
    from platform_context import is_group_message as _impl
    return _impl(event)


def get_message_id(event: Event) -> Optional[str]:
    """获取消息ID（用于被动回复，转发 platform_context）"""
    from platform_context import get_message_id as _impl
    return _impl(event)


def get_message_timestamp(event: Event) -> Optional[int]:
    """获取消息时间戳（秒，转发 platform_context）"""
    from platform_context import get_message_timestamp as _impl
    return _impl(event)


async def send_reply(
    matcher,
    message: Union[str, Message]
) -> None:
    """
    使用 matcher 发送回复（自动适配平台）
    
    Args:
        matcher: NoneBot2 的 matcher 实例
        message: 要发送的消息
    """
    await matcher.send(message)


async def send_finish(
    matcher,
    message: Union[str, Message]
) -> None:
    """
    使用 matcher 发送回复并结束（自动适配平台）
    
    Args:
        matcher: NoneBot2 的 matcher 实例
        message: 要发送的消息
    """
    await matcher.finish(message)


# 导出统一的事件类型别名，用于插件导入
MessageEvent = UnifiedMessageEvent


async def build_reply_message(event: Event, message: Union[str, Message]) -> Union[Message, str]:
    """构建"回复/引用"消息（转发 platform_context）"""
    from platform_context import build_reply_message as _impl
    return await _impl(event, message)


async def build_at_message(event: Event, user_id: int, text: str) -> Union[Message, str]:
    """构建包含艾特的消息（转发 platform_context）"""
    from platform_context import build_at_message as _impl
    return await _impl(event, user_id, text)


def build_image_message(event: Event, image_data: Any, text: str = '') -> Union[Message, str]:
    """构建包含图片的消息（转发 platform_context）"""
    from platform_context import build_image_message as _impl
    return _impl(event, image_data, text)


async def get_user_id(event: Event, auto_create: bool = True) -> Optional[int]:
    """通过event获取统一用户ID（转发 platform_context）"""
    from platform_context import get_user_id as _impl
    return await _impl(event, auto_create=auto_create)


async def get_real_qq_by_event(event: Event) -> Optional[str]:
    """通过event获取真实QQ号（转发 platform_context）"""
    from platform_context import get_real_qq_by_event as _impl
    return await _impl(event)


def get_platform_type(event: Event) -> Optional[str]:
    """获取平台类型：'onebot' / 'qqbot' / None（转发 platform_context）"""
    from platform_context import get_platform_type as _impl
    return _impl(event)


# ============================================================
# NapCat (OneBot V11) Bot 实例访问
# ============================================================

from nonebot import get_bots


def get_napcat_bot() -> Optional[Bot]:
    """
    获取 NapCat (OneBot V11) Bot 实例
    
    Returns:
        NapCat Bot 实例或 None
    """
    bots = get_bots()
    for bot in bots.values():
        if is_onebot_v11_bot(bot):
            return bot
    return None


# ============================================================
# 主动推送 - 事件无关的运行时发送能力
# ============================================================

def _get_current_bot() -> Tuple[Optional[str], Optional[Bot]]:
    """当前连接端的平台与 Bot 实例（NapCat 与官机互斥，只会命中一端）"""
    bots = list(get_bots().values())
    for bot in bots:
        if is_onebot_v11_bot(bot):
            return 'onebot', bot
    for bot in bots:
        if is_qq_bot(bot):
            return 'qqbot', bot
    return None, None


def get_current_platform() -> Optional[str]:
    """当前连接端平台：'onebot' / 'qqbot' / None（事件无关）"""
    return _get_current_bot()[0]


async def _qq_at_tag(qq: str) -> Optional[str]:
    """QQ 号转官机 at 标签；缺少绑定时返回 None"""
    from core.services.identity_service import get_unified_user_by_real_qq

    try:
        user = await get_unified_user_by_real_qq(qq)
    except Exception:
        return None
    if user and user.qqbotOpenid:
        return f'<qqbot-at-user id="{user.qqbotOpenid}" /> '
    return None


async def _qq_image_segment(seg: Any) -> Optional[Any]:
    """OneBot 图片段转官机图片段，无法解析时返回 None"""
    file = str(seg.data.get('file') or '')
    url = str(seg.data.get('url') or '')
    if file.startswith('base64://'):
        import base64
        return QQMessageSegment.file_image(base64.b64decode(file[len('base64://'):]))
    if url.startswith('http'):
        return QQMessageSegment.image(url)
    if file.startswith('http'):
        return QQMessageSegment.image(file)
    if os.path.isfile(file):
        content = await asyncio.to_thread(lambda: open(file, 'rb').read())
        return QQMessageSegment.file_image(content)
    return None


async def _to_qq_message(message: Union[str, Message]) -> Optional[Union[str, Any]]:
    """把消息转成官机可发送的形态；无法表达时返回 None

    官方 Bot 消息（如官机下的命令参数）原样返回；OneBot 消息支持
    文本、@、图片与引用，其它富媒体返回 None，避免发出半截消息。
    纯文本消息中的 @ 转为 markdown 真 at；官方协议不允许 markdown
    与媒体同条，含图片时 @ 仍退化为文本。
    """
    if isinstance(message, str):
        return message

    if isinstance(message, QQMessageSegment):
        return QQMessage([message])
    if isinstance(message, QQMessage):
        return message

    if isinstance(message, OneBotV11MessageSegment):
        segments = [message]
    elif isinstance(message, OneBotV11Message):
        segments = list(message)
    else:
        return None

    has_media = any(seg.type == 'image' for seg in segments)
    has_at = any(seg.type == 'at' for seg in segments)

    built = []
    markdown_parts: List[str] = []
    for seg in segments:
        if seg.type == 'text':
            text = str(seg.data.get('text') or '')
            built.append(QQMessageSegment.text(text))
            markdown_parts.append(text)
        elif seg.type == 'at':
            qq = str(seg.data.get('qq') or '')
            if not qq:
                continue
            if qq == 'all':
                prefix = '@全体成员 '
            elif has_at and not has_media:
                prefix = await _qq_at_tag(qq) or f'@{qq} '
            else:
                prefix = f'@{qq} '
            built.append(QQMessageSegment.text(prefix))
            markdown_parts.append(prefix)
        elif seg.type == 'image':
            segment = await _qq_image_segment(seg)
            if segment is None:
                return None
            built.append(segment)
        elif seg.type == 'reply':
            # 主动推送没有可引用的消息，忽略引用段
            continue
        else:
            return None

    if has_at and not has_media:
        content = ''.join(markdown_parts)
        return QQMessage([QQMessageSegment.markdown(content)]) if content else None
    return QQMessage(built) if built else None


def _onebot_failure(exc: Exception) -> ActionResult:
    from nonebot.exception import ActionFailed, ApiNotAvailable, NetworkError

    if isinstance(exc, ActionFailed):
        info = exc.info
        retcode = info.get('retcode')
        wording = info.get('wording') or info.get('message') or ''
        detail = f'{retcode or ""} {wording}'.strip()
        return ActionResult(False, f'failed: {detail or "unknown"}')
    if isinstance(exc, NetworkError):
        return ActionResult(False, 'network')
    if isinstance(exc, ApiNotAvailable):
        return ActionResult(False, 'unsupported')
    return ActionResult(False, f'failed: {exc}')


def _qq_failure(exc: Exception) -> ActionResult:
    from nonebot.adapters.qq.exception import (
        ActionFailed as QQActionFailed,
        ApiNotAvailable as QQApiNotAvailable,
        NetworkError as QQNetworkError,
        RateLimitException,
    )

    if isinstance(exc, RateLimitException):
        return ActionResult(False, 'rate_limited')
    if isinstance(exc, QQActionFailed):
        if exc.code == 22009:
            return ActionResult(False, 'rate_limited')
        if exc.status_code == 403:
            return ActionResult(False, 'no_permission')
        detail = f'{exc.code or exc.status_code} {exc.message or ""}'.strip()
        return ActionResult(False, f'failed: {detail}')
    if isinstance(exc, QQNetworkError):
        return ActionResult(False, 'network')
    if isinstance(exc, QQApiNotAvailable):
        return ActionResult(False, 'unsupported')
    return ActionResult(False, f'failed: {exc}')


async def push_group(
    group_id: Union[int, str],
    message: Union[str, Message],
) -> ActionResult:
    """主动向群推送消息（事件无关）

    group_id 统一为 QQ 群号：OneBot 直接使用，官机经群映射换 group_openid。
    通道由当前连接端决定，两端互斥，发送失败直接返回原因，不跨端回退。
    """
    platform, bot = _get_current_bot()
    if bot is None:
        return ActionResult(False, 'no_bot')

    if platform == 'onebot':
        try:
            target = int(group_id)
        except (TypeError, ValueError):
            return ActionResult(False, 'invalid_target')
        try:
            await bot.send_group_msg(group_id=target, message=message)
        except Exception as e:
            return _onebot_failure(e)
        return ActionResult(True)

    # 官机：QQ 群号需经映射换成 group_openid
    from core.services.identity_service import get_openid_by_onebot_group_id

    openid = get_openid_by_onebot_group_id(str(group_id))
    if not openid:
        return ActionResult(False, 'invalid_target')
    payload = await _to_qq_message(message)
    if payload is None:
        return ActionResult(False, 'unsupported')
    try:
        await bot.send_to_group(group_openid=openid, message=payload)
    except Exception as e:
        return _qq_failure(e)
    return ActionResult(True)


async def push_private(
    unified_user_id: Union[int, str],
    message: Union[str, Message],
) -> ActionResult:
    """主动向用户推送单聊消息（事件无关）

    unified_user_id 为 UnifiedUser.id：OneBot 走 realQQ 私聊，官机走 C2C。
    好友关系由 kusa_base 判断；两端互斥，不跨端回退。
    """
    from core.services.identity_service import get_unified_user_by_id

    try:
        user = await get_unified_user_by_id(int(unified_user_id))
    except (TypeError, ValueError):
        return ActionResult(False, 'invalid_target')
    if user is None:
        return ActionResult(False, 'invalid_target')

    platform, bot = _get_current_bot()
    if bot is None:
        return ActionResult(False, 'no_bot')

    if platform == 'onebot':
        if not user.realQQ:
            return ActionResult(False, 'invalid_target')
        try:
            await bot.send_private_msg(user_id=int(user.realQQ), message=message)
        except Exception as e:
            return _onebot_failure(e)
        return ActionResult(True)

    # 官机：C2C 需要用户已绑定 qqbotOpenid
    openid = user.qqbotOpenid
    if not openid:
        return ActionResult(False, 'invalid_target')
    payload = await _to_qq_message(message)
    if payload is None:
        return ActionResult(False, 'unsupported')
    try:
        await bot.send_to_c2c(openid=openid, message=payload)
    except Exception as e:
        return _qq_failure(e)
    return ActionResult(True)
