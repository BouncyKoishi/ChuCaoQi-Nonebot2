"""
多平台适配模块
支持 OneBot V11 和 QQ 官方 Bot 协议
提供统一的接口供其他插件调用
"""

from typing import Union, Optional, Any
from nonebot.adapters import Bot, Event, Message

# 尝试导入QQ适配器的事件类型
try:
    from nonebot.adapters.qq import Event as QQEvent
    from nonebot.adapters.qq import Message as QQMessage
    from nonebot.adapters.qq import MessageSegment as QQMessageSegment
    from nonebot.adapters.qq import C2CMessageCreateEvent
    from nonebot.adapters.qq import GroupAtMessageCreateEvent
    from nonebot.adapters.qq import Bot as QQBot
    QQ_AVAILABLE = True
except ImportError:
    QQEvent = None
    QQMessage = None
    QQMessageSegment = None
    C2CMessageCreateEvent = None
    GroupAtMessageCreateEvent = None
    QQBot = None
    QQ_AVAILABLE = False

# OneBot V11 事件类型
from nonebot.adapters.onebot.v11 import Event as OneBotV11Event
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot


# 统一的事件类型
UnifiedEvent = Union[OneBotV11Event, QQEvent] if QQ_AVAILABLE else OneBotV11Event
UnifiedMessageEvent = Union[OneBotV11MessageEvent, QQEvent] if QQ_AVAILABLE else OneBotV11MessageEvent


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
    if not QQ_AVAILABLE:
        return False
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
# 双端架构支持 - 通过 NapCat 执行官方 Bot 不支持的操作
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


async def execute_via_napcat(
    group_id: str,
    user_id: int,
    action: str,
    **kwargs
) -> bool:
    """
    通过 NapCat 实例执行操作
    
    Args:
        group_id: 官方 Bot 的群 OpenID
        user_id: 统一用户 ID
        action: 操作类型 ("ban", "unban", "kick", "emoji_like")
        **kwargs: 其他参数
        
    Returns:
        是否执行成功
    """
    bot = get_napcat_bot()
    if not bot:
        print("[NapCat] 未找到 NapCat 实例")
        return False
    
    try:
        from core.services.identity_service import (
            get_group_mapping_by_openid,
            get_unified_user_by_id,
        )
        mapping = await get_group_mapping_by_openid(group_id)
        real_group_id = int(mapping.onebotGroupId) if mapping and mapping.onebotGroupId else None
        unified_user = await get_unified_user_by_id(user_id)
        real_user_id = int(unified_user.realQQ) if unified_user and unified_user.realQQ else None
        
        if not real_group_id:
            print(f"[NapCat] 无法找到群 {group_id} 的真实群号")
            return False
        
        if action == "ban":
            if not real_user_id:
                print(f"[NapCat] 无法找到用户 {user_id} 的真实QQ号")
                return False
            duration = kwargs.get("duration", 60)
            await bot.set_group_ban(
                group_id=real_group_id,
                user_id=real_user_id,
                duration=duration
            )
            print(f"[NapCat] 禁言成功: 群 {real_group_id}, 用户 {real_user_id}, 时长 {duration}s")
            return True
            
        elif action == "unban":
            if not real_user_id:
                print(f"[NapCat] 无法找到用户 {user_id} 的真实QQ号")
                return False
            await bot.set_group_ban(
                group_id=real_group_id,
                user_id=real_user_id,
                duration=0
            )
            print(f"[NapCat] 解除禁言成功: 群 {real_group_id}, 用户 {real_user_id}")
            return True
            
        elif action == "kick":
            if not real_user_id:
                print(f"[NapCat] 无法找到用户 {user_id} 的真实QQ号")
                return False
            await bot.set_group_kick(
                group_id=real_group_id,
                user_id=real_user_id
            )
            print(f"[NapCat] 踢出成功: 群 {real_group_id}, 用户 {real_user_id}")
            return True
            
        elif action == "emoji_like":
            message_id = kwargs.get("message_id")
            emoji_id = kwargs.get("emoji_id", 128074)
            if not message_id:
                print("[NapCat] emoji_like 需要提供 message_id")
                return False
            await bot.set_msg_emoji_like(
                message_id=message_id,
                emoji_id=emoji_id
            )
            print(f"[NapCat] 表情点赞成功: 消息 {message_id}, 表情 {emoji_id}")
            return True
            
        elif action == "set_group_admin":
            if not real_user_id:
                print(f"[NapCat] 无法找到用户 {user_id} 的真实QQ号")
                return False
            enable = kwargs.get("enable", True)
            await bot.set_group_admin(
                group_id=real_group_id,
                user_id=real_user_id,
                enable=enable
            )
            print(f"[NapCat] 设置管理员成功: 群 {real_group_id}, 用户 {real_user_id}")
            return True
            
        elif action == "set_group_card":
            if not real_user_id:
                print(f"[NapCat] 无法找到用户 {user_id} 的真实QQ号")
                return False
            card = kwargs.get("card", "")
            await bot.set_group_card(
                group_id=real_group_id,
                user_id=real_user_id,
                card=card
            )
            print(f"[NapCat] 设置群名片成功: 群 {real_group_id}, 用户 {real_user_id}")
            return True
            
        else:
            print(f"[NapCat] 未知的操作类型: {action}")
            return False
            
    except Exception as e:
        print(f"[NapCat] 执行操作失败: {e}")
        return False
