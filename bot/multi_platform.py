"""
多平台适配模块
支持 OneBot V11 和 QQ 官方 Bot 协议
提供统一的接口供其他插件调用
"""

from typing import Union, Optional, Any
from nonebot.adapters import Bot, Event, Message
from nonebot.params import Event as EventParam

try:
    from services.identity_service import (
        get_unified_user_by_platform,
        get_or_create_unified_user,
        get_real_qq
    )
    IDENTITY_SERVICE_AVAILABLE = True
except ImportError:
    IDENTITY_SERVICE_AVAILABLE = False

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
    """判断是否为 OneBot V11 事件"""
    return isinstance(event, OneBotV11Event)


def is_qq_event(event: Event) -> bool:
    """判断是否为 QQ 官方 Bot 事件"""
    if not QQ_AVAILABLE:
        return False
    return isinstance(event, QQEvent)


def is_onebot_v11_bot(bot: Bot) -> bool:
    """判断是否为 OneBot V11 Bot"""
    return isinstance(bot, OneBotV11Bot)


def is_qq_bot(bot: Bot) -> bool:
    """判断是否为 QQ 官方 Bot"""
    if not QQ_AVAILABLE:
        return False
    return isinstance(bot, QQBot)


def get_platform_user_id(event: Event) -> Optional[str]:
    """获取平台用户ID（统一格式）"""
    if is_onebot_v11_event(event):
        # OneBot V11 使用 user_id
        return str(getattr(event, 'user_id', None))
    elif is_qq_event(event):
        # QQ 官方 Bot
        if hasattr(event, 'author') and event.author:
            # GroupAtMessageCreateEvent 使用 author.member_openid
            if hasattr(event.author, 'member_openid'):
                return str(event.author.member_openid)
            # C2CMessageCreateEvent 使用 author.user_openid
            if hasattr(event.author, 'user_openid'):
                return str(event.author.user_openid)
            # 其他情况使用 author.id
            return str(event.author.id)
        if hasattr(event, 'user') and event.user:
            return str(event.user.id)
    return None


def get_nickname_from_event(event: Event) -> str:
    """从事件中获取用户昵称"""
    if is_onebot_v11_event(event):
        return event.sender.nickname if event.sender else ""
    elif is_qq_event(event):
        # QQ官方Bot部分未验证可用性
        if hasattr(event, 'author') and event.author:
            if hasattr(event.author, 'member_openid'):
                return ""
            if hasattr(event.author, 'user_openid'):
                return ""
        return ""
    return ""


def get_group_id(event: Event) -> Optional[str]:
    """获取群ID（统一格式）"""
    if is_onebot_v11_event(event):
        group_id = getattr(event, 'group_id', None)
        return str(group_id) if group_id is not None else None
    elif is_qq_event(event):
        # QQ 官方 Bot
        # GroupAtMessageCreateEvent 使用 group_openid 或 group_id
        if hasattr(event, 'group_openid') and event.group_openid:
            return str(event.group_openid)
        if hasattr(event, 'group_id') and event.group_id:
            return str(event.group_id)
        # 频道相关使用 guild_id 或 channel_id
        if hasattr(event, 'guild_id') and event.guild_id:
            return str(event.guild_id)
        if hasattr(event, 'channel_id') and event.channel_id:
            return str(event.channel_id)
    return None


def is_group_message(event: Event) -> bool:
    """判断是否为群聊消息"""
    if is_onebot_v11_event(event):
        if hasattr(event, 'message_type') and getattr(event, 'message_type') == 'private':
            return False
        return hasattr(event, 'group_id') and getattr(event, 'group_id') is not None
    elif is_qq_event(event):
        if QQ_AVAILABLE:
            if GroupAtMessageCreateEvent and isinstance(event, GroupAtMessageCreateEvent):
                return True
        return hasattr(event, 'group_openid') or hasattr(event, 'group_id') or hasattr(event, 'guild_id')
    return False


def get_message_id(event: Event) -> Optional[str]:
    """获取消息ID（用于被动回复）"""
    if is_onebot_v11_event(event):
        # OneBot V11 使用 message_id
        return str(getattr(event, 'message_id', None))
    elif is_qq_event(event):
        # QQ 官方 Bot 使用 id
        if hasattr(event, 'id') and event.id:
            return str(event.id)
    return None


def get_message_timestamp(event: Event) -> Optional[int]:
    """获取消息时间戳（秒）"""
    if is_onebot_v11_event(event):
        # OneBot V11
        import time
        return int(time.time())
    elif is_qq_event(event):
        # QQ 官方 Bot
        if hasattr(event, 'timestamp') and event.timestamp:
            # 解析 ISO 格式时间
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except:
                pass
    return None


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


def build_message(event: Event, *segments) -> Union[Message, str]:
    """
    构建兼容双平台的消息
    
    Args:
        event: 事件对象
        *segments: 消息段列表，可以是 MessageSegment 或字符串
        
    Returns:
        OneBot V11: Message 对象
        QQ Bot: 字符串
    """
    if is_onebot_v11_event(event):
        from nonebot.adapters.onebot.v11 import Message as OBMessage
        return OBMessage(list(segments))
    else:
        parts = []
        for seg in segments:
            if isinstance(seg, str):
                parts.append(seg)
            else:
                parts.append(str(seg))
        return ''.join(parts)


async def build_at_message(event: Event, user_id: int, text: str) -> Union[Message, str]:
    """
    构建包含艾特的消息，兼容双平台
    内部自动将统一用户ID转换为真实QQ号用于艾特
    
    Args:
        event: 事件对象
        user_id: 统一用户ID
        text: 附加文本
        
    Returns:
        OneBot V11: Message([at, text])
        QQ Bot: "@real_qq text"
    """
    from nonebot.adapters.onebot.v11 import MessageSegment as OBMS
    from nonebot.adapters.onebot.v11 import Message as OBMessage
    real_qq = await get_real_qq_by_event(event)
    if is_onebot_v11_event(event) and real_qq:
        return OBMessage([OBMS.at(int(real_qq)), ' ' + text])
    else:
        return f"@{real_qq or user_id} {text}"


def build_image_message(event: Event, image_data: Any, text: str = '') -> Union[Message, str]:
    """
    构建包含图片的消息，兼容双平台
    
    Args:
        event: 事件对象
        image_data: 图片数据（URL、文件路径或 bytes）
        text: 附加文本
        
    Returns:
        OneBot V11: Message([image, text])
        QQ Bot: "@user_id text"
    """
    from nonebot.adapters.onebot.v11 import MessageSegment as OBMS
    from nonebot.adapters.onebot.v11 import Message as OBMessage
    if is_onebot_v11_event(event):
        segments = [OBMS.image(image_data)]
        if text:
            segments.append(text)
        return OBMessage(segments)
    else:
        return f'[图片] {text}' if text else '[图片]'


async def get_user_id(event: Event, auto_create: bool = True) -> Optional[int]:
    """
    通过event获取user_id
    
    Args:
        event: 事件对象
        auto_create: 如果用户不存在是否自动创建
        
    Returns:
        user_id或None
    """
    if not IDENTITY_SERVICE_AVAILABLE:
        return None
    
    platform = get_platform_type(event)
    platform_id = get_platform_user_id(event)
    
    if not platform or not platform_id:
        return None
    
    try:
        if auto_create:
            unified_user = await get_or_create_unified_user(platform, platform_id)
        else:
            unified_user = await get_unified_user_by_platform(platform, platform_id)
        
        if unified_user:
            return unified_user.id
    except Exception as e:
        print(f'获取user_id失败：{e}')
    
    return None


async def get_real_qq_by_event(event: Event) -> Optional[str]:
    """
    通过event获取真实QQ号
    
    Args:
        event: 事件对象
        
    Returns:
        真实QQ号或None
    """
    # OneBot V11 的 user_id 就是真实QQ号，直接返回
    if is_onebot_v11_event(event):
        return str(getattr(event, 'user_id', None))
    
    # QQ官方Bot需要通过身份服务获取绑定的QQ号
    if not IDENTITY_SERVICE_AVAILABLE:
        return None
    
    platform = get_platform_type(event)
    platform_id = get_platform_user_id(event)
    
    if not platform or not platform_id:
        return None
    
    try:
        unified_user = await get_unified_user_by_platform(platform, platform_id)
        if unified_user:
            return await get_real_qq(unified_user)
    except Exception as e:
        print(f'获取real_qq失败：{e}')
    
    return None


def get_platform_type(event: Event) -> Optional[str]:
    """
    获取平台类型
    
    Args:
        event: 事件对象
        
    Returns:
        "onebot"、"qqbot"或None
    """
    if is_onebot_v11_event(event):
        return "onebot"
    elif is_qq_event(event):
        return "qqbot"
    return None


# ============================================================
# 双端架构支持 - 通过 NapCat 执行官方 Bot 不支持的操作
# ============================================================

from nonebot import get_bots


# async def get_real_group_id(official_group_id: str) -> Optional[int]:
#     """
#     通过 GroupMapping 获取真实群号
#     
#     Args:
#         official_group_id: 官方 Bot 的群 OpenID
#         
#     Returns:
#         真实群号或 None
#     """
#     try:
#         from dbConnection.models import GroupMapping
#         mapping = await GroupMapping.filter(qqbotGroupOpenid=official_group_id).first()
#         if mapping and mapping.onebotGroupId:
#             return int(mapping.onebotGroupId)
#     except Exception as e:
#         print(f"[NapCat] 获取真实群号失败: {e}")
#     return None


async def get_real_user_id(unified_user_id: int) -> Optional[int]:
    """
    通过 UnifiedUser 获取真实 QQ 号
    
    Args:
        unified_user_id: 统一用户 ID
        
    Returns:
        真实 QQ 号或 None
    """
    try:
        from dbConnection.models import UnifiedUser
        user = await UnifiedUser.filter(id=unified_user_id).first()
        if user and user.realQQ:
            return int(user.realQQ)
    except Exception as e:
        print(f"[NapCat] 获取真实用户ID失败: {e}")
    return None


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


def get_qqbot_instance() -> Optional[Bot]:
    """
    获取 QQ 官方 Bot 实例
    
    Returns:
        QQ 官方 Bot 实例或 None
    """
    bots = get_bots()
    for bot in bots.values():
        if is_qq_bot(bot):
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
        real_group_id = await get_real_group_id(group_id)
        real_user_id = await get_real_user_id(user_id)
        
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
