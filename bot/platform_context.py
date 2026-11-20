"""平台上下文层

分层：platform_compat（适配器补丁）→ platform_context（事件级统一视图）→ 插件
      multi_platform 仅保留跨事件的运行时能力（NapCat/QQBot 实例、双端转发）

插件通过 ``get_context(event, bot)`` 取到 PlatformContext，只面向这里暴露的
字段、发送方法与能力声明编程，不再关心 OneBot V11 / QQ 官方 Bot 的协议差异。

本模块是唯一允许出现平台 isinstance 分支的地方；multi_platform 中的同名
事件工具已降级为对本模块的转发，供尚未迁移的旧调用方使用。
"""

from dataclasses import dataclass
from typing import Annotated, Any, List, Optional, Union

from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import Event as OneBotV11Event
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.params import Depends

try:
    from nonebot.adapters.qq import Event as QQEvent
    from nonebot.adapters.qq import GroupAtMessageCreateEvent
    from nonebot.adapters.qq import Message as QQMessage
    from nonebot.adapters.qq import MessageSegment as QQMessageSegment
    QQ_AVAILABLE = True
except ImportError:
    QQEvent = None
    GroupAtMessageCreateEvent = None
    QQMessage = None
    QQMessageSegment = None
    QQ_AVAILABLE = False

try:
    from core.services.identity_service import (
        get_or_create_unified_user,
        get_real_qq,
        get_unified_user_by_platform,
    )
    IDENTITY_SERVICE_AVAILABLE = True
except ImportError:
    IDENTITY_SERVICE_AVAILABLE = False


@dataclass(frozen=True)
class Quote:
    """被引用的消息（双端统一视图）

    OneBot：event.reply（Reply 模型，含完整被引用消息）
    QQ 官方：msg_elements[0]（适配器只给出被引用消息的文本与 msg_idx）
    """

    text: str = ''
    message_id: Optional[str] = None
    sender_name: Optional[str] = None


@dataclass(frozen=True)
class PlatformCapabilities:
    """当前平台可用的能力声明，供插件在入口处做功能开关"""

    can_reply: bool = True
    can_quote: bool = False
    can_send_image: bool = False
    can_receive_images: bool = False
    can_active_push: bool = False
    can_ban: bool = False
    can_member_list: bool = False
    can_recall: bool = False

    @classmethod
    def for_platform(cls, platform: Optional[str]) -> 'PlatformCapabilities':
        if platform == 'onebot':
            # NapCat 实现了完整的 OneBot V11 API
            return cls(
                can_reply=True,
                can_quote=True,
                can_send_image=True,
                can_receive_images=True,
                can_active_push=True,
                can_ban=True,
                can_member_list=True,
                can_recall=True,
            )
        if platform == 'qqbot':
            # 官方 Bot 只保证被动回复；主动推送需单独申请权限
            return cls(can_reply=True)
        return cls()


# ---------- 平台判定与事件派生（唯一允许 isinstance 分支的地方） ----------

def is_onebot_v11_event(event: Event) -> bool:
    return isinstance(event, OneBotV11Event)


def is_qq_event(event: Event) -> bool:
    if not QQ_AVAILABLE:
        return False
    return isinstance(event, QQEvent)


def get_platform_type(event: Event) -> Optional[str]:
    """平台类型：'onebot' / 'qqbot' / None"""
    if is_onebot_v11_event(event):
        return 'onebot'
    if is_qq_event(event):
        return 'qqbot'
    return None


def get_platform_user_id(event: Event) -> Optional[str]:
    """平台侧用户标识：OneBot 为 QQ 号，QQ 官方为 openid

    QQ 官方只允许 union_openid 作为跨场景身份；它缺失时按事件场景回退到
    场景内 ID（群聊 member_openid / 私聊 user_openid），绝不跨场景回退，
    否则同一人会在群聊和私聊中被当成两个用户。
    """
    if is_onebot_v11_event(event):
        user_id = getattr(event, 'user_id', None)
        return str(user_id) if user_id is not None else None
    if is_qq_event(event):
        author = getattr(event, 'author', None)
        if author:
            union_openid = getattr(author, 'union_openid', None)
            if union_openid:
                return str(union_openid)
            if is_group_message(event):
                scene_id = getattr(author, 'member_openid', None) or getattr(author, 'id', None)
            else:
                scene_id = getattr(author, 'user_openid', None) or getattr(author, 'id', None)
            return str(scene_id) if scene_id else None
        user = getattr(event, 'user', None)
        if user:
            return str(user.id)
    return None


def get_nickname_from_event(event: Event) -> str:
    """事件中的用户昵称（QQ 官方暂无可用昵称）"""
    if is_onebot_v11_event(event):
        sender = getattr(event, 'sender', None)
        return sender.nickname if sender else ''
    return ''


def get_group_id(event: Event) -> Optional[str]:
    """群 ID（统一字符串）"""
    if is_onebot_v11_event(event):
        group_id = getattr(event, 'group_id', None)
        return str(group_id) if group_id is not None else None
    if is_qq_event(event):
        for attr in ('group_openid', 'group_id', 'guild_id', 'channel_id'):
            value = getattr(event, attr, None)
            if value:
                return str(value)
    return None


def is_group_message(event: Event) -> bool:
    if is_onebot_v11_event(event):
        if getattr(event, 'message_type', None) == 'private':
            return False
        return getattr(event, 'group_id', None) is not None
    if is_qq_event(event):
        if QQ_AVAILABLE and GroupAtMessageCreateEvent and isinstance(event, GroupAtMessageCreateEvent):
            return True
        return any(hasattr(event, attr) for attr in ('group_openid', 'group_id', 'guild_id'))
    return False


def get_message_id(event: Event) -> Optional[str]:
    """消息 ID（用于被动回复）"""
    if is_onebot_v11_event(event):
        return str(getattr(event, 'message_id', None))
    if is_qq_event(event):
        message_id = getattr(event, 'id', None)
        if message_id:
            return str(message_id)
    return None


def get_message_timestamp(event: Event) -> Optional[int]:
    """消息时间戳（秒）"""
    if is_onebot_v11_event(event):
        import time
        return int(time.time())
    if is_qq_event(event):
        timestamp = getattr(event, 'timestamp', None)
        if timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except Exception:
                pass
    return None


# ---------- 身份 ----------

async def get_user_id(event: Event, auto_create: bool = True) -> Optional[int]:
    """统一用户 ID（不存在时按 auto_create 决定是否建号）"""
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
    """真实 QQ 号：OneBot 直接取 user_id，QQ 官方经身份绑定查询"""
    if is_onebot_v11_event(event):
        user_id = getattr(event, 'user_id', None)
        return str(user_id) if user_id is not None else None
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


# ---------- 消息构造 ----------

async def build_reply_message(event: Event, message: Union[str, Message]) -> Union[Message, str]:
    """构建引用回复：群聊引用当前消息，私聊原样返回"""
    if not is_group_message(event):
        return message
    message_id = get_message_id(event)
    if not message_id:
        return message
    if is_onebot_v11_event(event):
        return OneBotV11Message([OneBotV11MessageSegment.reply(int(message_id)), message])
    if is_qq_event(event):
        return QQMessage([QQMessageSegment.reference(message_id), message])
    return message


async def build_at_message(event: Event, user_id: int, text: str) -> Union[Message, str]:
    """构建艾特消息，内部把统一用户 ID 换成真实 QQ 号"""
    real_qq = await get_real_qq_by_event(event)
    if is_onebot_v11_event(event) and real_qq:
        return OneBotV11Message([OneBotV11MessageSegment.at(int(real_qq)), ' ' + text])
    return f'@{real_qq or user_id} {text}'


def build_image_message(event: Event, image_data: Any, text: str = '') -> Union[Message, str]:
    """构建图片消息；QQ 官方退化为文本占位"""
    if is_onebot_v11_event(event):
        segments = [OneBotV11MessageSegment.image(image_data)]
        if text:
            segments.append(text)
        return OneBotV11Message(segments)
    return f'[图片] {text}' if text else '[图片]'


class PlatformContext:
    """事件级平台上下文：统一字段 + 发送封装 + 能力声明"""

    def __init__(self, event: Event, bot: Optional[Bot] = None):
        self.event = event
        self.bot = bot
        self.platform = get_platform_type(event)
        self.capabilities = PlatformCapabilities.for_platform(self.platform)

    # ---------- 事件派生信息 ----------

    @property
    def is_group(self) -> bool:
        return is_group_message(self.event)

    @property
    def group_id(self) -> Optional[str]:
        return get_group_id(self.event)

    @property
    def platform_user_id(self) -> Optional[str]:
        return get_platform_user_id(self.event)

    @property
    def message_id(self) -> Optional[str]:
        return get_message_id(self.event)

    @property
    def timestamp(self) -> Optional[int]:
        return get_message_timestamp(self.event)

    @property
    def nickname(self) -> str:
        return get_nickname_from_event(self.event) or ''

    @property
    def text(self) -> str:
        try:
            return (self.event.get_plaintext() or '').strip()
        except Exception:
            return ''

    @property
    def images(self) -> List[str]:
        """当前消息中的图片 URL 列表"""
        if self.platform == 'onebot':
            urls = []
            try:
                segments = self.event.get_message()
            except Exception:
                return urls
            for seg in segments:
                if seg.type == 'image':
                    url = seg.data.get('url') or seg.data.get('file')
                    if url:
                        urls.append(url)
            return urls
        attachments = getattr(self.event, 'attachments', None) or []
        return [a.url for a in attachments if getattr(a, 'url', None)]

    @property
    def quote(self) -> Optional[Quote]:
        """被引用的消息；未引用时返回 None"""
        if self.platform == 'onebot':
            reply = getattr(self.event, 'reply', None)
            if not reply:
                return None
            try:
                text = reply.message.extract_plain_text().strip()
            except Exception:
                text = ''
            sender = getattr(reply, 'sender', None)
            return Quote(
                text=text,
                message_id=str(getattr(reply, 'message_id', '') or '') or None,
                sender_name=getattr(sender, 'nickname', None),
            )

        elements = getattr(self.event, 'msg_elements', None) or []
        if not elements:
            return None
        element = elements[0]
        if isinstance(element, dict):
            text = element.get('content') or ''
            message_id = element.get('msg_idx')
        else:
            text = getattr(element, 'content', '') or ''
            message_id = getattr(element, 'msg_idx', None)
        if not text and not message_id:
            return None
        return Quote(text=text.strip(), message_id=message_id)

    # ---------- 身份 ----------

    async def get_user_id(self, auto_create: bool = True) -> Optional[int]:
        return await get_user_id(self.event, auto_create=auto_create)

    async def get_real_qq(self) -> Optional[str]:
        return await get_real_qq_by_event(self.event)

    # ---------- 发送 ----------

    async def finish_quoted(self, matcher, message: Union[str, Message]) -> None:
        """群聊中引用当前消息后发送并结束（私聊退化为普通发送）"""
        await matcher.finish(await build_reply_message(self.event, message))

    async def build_quoted(self, message: Union[str, Message]) -> Union[str, Message]:
        """构造引用当前消息的回复内容，由调用方自行发送"""
        return await build_reply_message(self.event, message)

    async def at(self, user_id: int, text: str) -> Union[Message, str]:
        """构造艾特消息：OneBot 使用真实 at 段，QQ 官方退化为文本前缀"""
        return await build_at_message(self.event, user_id, text)


def get_context(event: Event, bot: Optional[Bot] = None) -> PlatformContext:
    """为事件构造平台上下文（轻量对象，属性按需计算）"""
    return PlatformContext(event, bot)


def _context_dependency(bot: Bot, event: Event) -> PlatformContext:
    return get_context(event, bot)


# 依赖注入别名：async def handle(ctx: Ctx) 即可直接拿到上下文
Ctx = Annotated[PlatformContext, Depends(_context_dependency)]
