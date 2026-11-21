"""平台上下文层

分层：platform_compat（适配器补丁）→ platform_context（事件级统一视图）→ 插件
      multi_platform 仅保留跨事件的运行时能力（NapCat/QQBot 实例、双端转发）

插件通过 ``get_context(event, bot)`` 取到 PlatformContext，只面向这里暴露的
字段、发送方法与能力声明编程，不再关心 OneBot V11 / QQ 官方 Bot 的协议差异。

本模块是唯一允许出现平台 isinstance 分支的地方；multi_platform 中的同名
事件工具已降级为对本模块的转发，供尚未迁移的旧调用方使用。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, List, Optional, Union

from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import Event as OneBotV11Event
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.drivers import Request
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
    QQ 官方：msg_elements（文本 + msg_idx + attachments，附件含图片 URL）
    """

    text: str = ''
    message_id: Optional[str] = None
    sender_name: Optional[str] = None
    images: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ActionResult:
    """双端动作（目前仅禁言）的执行结果

    reason 取值：not_group / unsupported / invalid_target / no_permission /
    rate_limited / failed / network
    """

    ok: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class PlatformCapabilities:
    """协议层能力声明，供插件在入口处做功能开关

    这里只表示“该平台协议本身是否支持”，不代表当前群已获得授权：
    - 官bot 主动推送需要群主开启开关，禁言需要机器人是群管理员；
      这类运行时授权由具体调用的返回值判断，不在此静态声明。
    - 群成员信息/列表、群基本信息、踢人在官bot 侧属于平台白名单接口，
      默认拿不到，因此声明为 False，对应能力保留为 OneBot 专属实现。
    """

    can_reply: bool = True
    can_quote: bool = False
    can_send_image: bool = False
    can_receive_images: bool = False
    can_active_push: bool = False
    can_ban: bool = False
    # 支持按 QQ 号指定禁言对象（依赖 QQ 号可解析为平台成员，仅 OneBot）
    can_ban_by_qq: bool = False
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
                can_ban_by_qq=True,
                can_member_list=True,
                can_recall=True,
            )
        if platform == 'qqbot':
            # 协议支持：被动/主动消息、引用、图片、撤回、禁言；
            # 主动推送与禁言的实际可用性由群授权决定（群主开关 / 机器人管理员）
            # 群成员信息、群成员列表、群基本信息、踢人仅平台白名单可用，默认关闭
            return cls(
                can_reply=True,
                can_quote=True,
                can_send_image=True,
                can_receive_images=True,
                can_active_push=True,
                can_ban=True,
                can_member_list=False,
                can_recall=True,
            )
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
        return OneBotV11Message([OneBotV11MessageSegment.reply(int(message_id))]) + message
    if is_qq_event(event):
        return QQMessage([QQMessageSegment.reference(message_id)]) + message
    return message


async def build_at_message(event: Event, user_id: int, text: str) -> Union[Message, str]:
    """构建艾特消息，内部把统一用户 ID 换成真实 QQ 号"""
    real_qq = await get_real_qq_by_event(event)
    if is_onebot_v11_event(event) and real_qq:
        return OneBotV11Message([OneBotV11MessageSegment.at(int(real_qq)), ' ' + text])
    return f'@{real_qq or user_id} {text}'


def build_image_message(event: Event, image_data: Any, text: str = '') -> Union[Message, str]:
    """构建图片消息：url 或本地字节均可，两端协议都支持发图

    OneBot 直接构造图片段；QQ 官方用 file_image 上传本地字节、image 传 URL，
    实际上传由适配器在发送时完成。
    """
    if is_onebot_v11_event(event):
        segments = [OneBotV11MessageSegment.image(image_data)]
        if text:
            segments.append(text)
        return OneBotV11Message(segments)
    if is_qq_event(event) and QQMessageSegment is not None:
        try:
            if isinstance(image_data, (bytes, bytearray)):
                segment = QQMessageSegment.file_image(bytes(image_data))
            elif hasattr(image_data, 'read'):
                segment = QQMessageSegment.file_image(image_data)
            else:
                segment = QQMessageSegment.image(str(image_data))
        except Exception:
            return f'[图片] {text}' if text else '[图片]'
        segments = [segment]
        if text:
            segments.append(QQMessageSegment.text(' ' + text))
        return QQMessage(segments)
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
    def platform_member_id(self) -> Optional[str]:
        """平台内的成员标识：OneBot 为 QQ 号，QQ 官方为 member_openid

        官bot 的成员管理接口使用 member_openid，而不是身份标识 union_openid；
        群事件里只有当前消息发送者的 member_openid 可得。
        """
        if self.platform == 'qqbot':
            author = getattr(self.event, 'author', None)
            return getattr(author, 'member_openid', None) if author else None
        return self.platform_user_id

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
                    url = seg.data.get('url')
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
                # 部分实现只在消息里带 reply 段而不填 event.reply，至少保留消息 ID
                try:
                    for seg in self.event.get_message():
                        if seg.type == 'reply':
                            return Quote(message_id=str(seg.data.get('id') or '') or None)
                except Exception:
                    pass
                return None
            try:
                text = reply.message.extract_plain_text().strip()
            except Exception:
                text = ''
            images: List[str] = []
            try:
                images = [
                    seg.data.get('url')
                    for seg in reply.message
                    if seg.type in ('image', 'mface') and seg.data.get('url')
                ]
            except Exception:
                images = []
            sender = getattr(reply, 'sender', None)
            return Quote(
                text=text,
                message_id=str(getattr(reply, 'message_id', '') or '') or None,
                sender_name=getattr(sender, 'nickname', None),
                images=images,
            )

        def collect_images(node) -> List[str]:
            urls: List[str] = []
            if isinstance(node, dict):
                attachments = node.get('attachments') or []
                nested = node.get('msg_elements') or []
            else:
                attachments = getattr(node, 'attachments', None) or []
                nested = getattr(node, 'msg_elements', None) or []
            for attachment in attachments:
                url = attachment.get('url') if isinstance(attachment, dict) else getattr(attachment, 'url', None)
                if url:
                    urls.append(url)
            for child in nested:
                urls.extend(collect_images(child))
            return urls

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
        images: List[str] = []
        for item in elements:
            images.extend(collect_images(item))
        return Quote(text=text.strip(), message_id=message_id, images=images)

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

    def build_image(self, image_data: Any, text: str = '') -> Union[Message, str]:
        """构造图片消息，image_data 可为 URL 或本地字节"""
        return build_image_message(self.event, image_data, text)

    # ---------- 双端动作 ----------

    async def ban(self, duration: int = 60, target: Optional[str] = None) -> ActionResult:
        """禁言群成员

        target 为平台成员标识（OneBot 为 QQ 号，官bot 为 member_openid），
        缺省为当前消息发送者。官bot 没有成员信息接口，无法把 QQ 号解析成
        member_openid，只能直接传入事件中出现过的 member_openid；最长 30 天。
        """
        if not self.is_group:
            return ActionResult(False, 'not_group')
        if not self.capabilities.can_ban or self.bot is None:
            return ActionResult(False, 'unsupported')

        if self.platform == 'onebot':
            group_id = self.group_id
            target = target or self.platform_user_id
            if not group_id or not target:
                return ActionResult(False, 'invalid_target')
            try:
                await self.bot.set_group_ban(
                    group_id=int(group_id),
                    user_id=int(target),
                    duration=max(duration, 0),
                )
            except Exception as e:
                return ActionResult(False, f'failed: {e}')
            return ActionResult(True)

        if self.platform == 'qqbot':
            return await self._ban_qqbot(duration, target)

        return ActionResult(False, 'unsupported')

    async def _ban_qqbot(self, duration: int, target: Optional[str]) -> ActionResult:
        # 官bot 成员管理接口只认 member_openid；未指定时使用当前发言人
        member_openid = target or self.platform_member_id
        if not self.group_id or not member_openid:
            return ActionResult(False, 'invalid_target')

        duration = min(max(duration, 0), 30 * 24 * 3600)
        member: dict = {'op': 'add' if duration else 'del', 'member_openid': member_openid}
        if duration:
            expire_at = datetime.now(timezone.utc) + timedelta(seconds=duration)
            member['mute_expire_at'] = expire_at.astimezone().isoformat(timespec='seconds')

        request = Request(
            'POST',
            self.bot.adapter.get_api_base().joinpath(
                'v2', 'groups', self.group_id, 'restrict_chat_setting'
            ),
            json={'members': [member]},
        )
        try:
            request.headers.update(await self.bot.get_authorization_header())
            response = await self.bot.adapter.request(request)
        except Exception as e:
            return ActionResult(False, f'network: {e}')

        if 200 <= response.status_code < 300:
            return ActionResult(True)
        if response.status_code == 429:
            return ActionResult(False, 'rate_limited')
        payload: Any = {}
        try:
            payload = json.loads(response.content) if response.content else {}
        except Exception:
            pass
        code = payload.get('code') if isinstance(payload, dict) else None
        if response.status_code == 403 or code == 11253:
            return ActionResult(False, 'no_permission')
        message = payload.get('message') if isinstance(payload, dict) else None
        return ActionResult(False, f'failed: {code or response.status_code} {message or ""}'.strip())


def get_context(event: Event, bot: Optional[Bot] = None) -> PlatformContext:
    """为事件构造平台上下文（轻量对象，属性按需计算）"""
    return PlatformContext(event, bot)


def _context_dependency(bot: Bot, event: Event) -> PlatformContext:
    return get_context(event, bot)


# 依赖注入别名：async def handle(ctx: Ctx) 即可直接拿到上下文
Ctx = Annotated[PlatformContext, Depends(_context_dependency)]
