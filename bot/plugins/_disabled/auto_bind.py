"""
UnifiedUser 自动绑定插件

利用双端 Bot 同时在线的特性，自动绑定用户身份。
仅在用户发送 !绑定 指令时触发。
"""

import hashlib
import time
import datetime
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import GroupMessageEvent as OneBotV11GroupMessageEvent
from nonebot.adapters.qq import GroupAtMessageCreateEvent

from dbConnection.user import (
    getGroupMappingByOnebotGroupId,
    getGroupMappingByQqbotGroupOpenid,
    getUnifiedUserByRealQQ,
    getUnifiedUserByQQBotOpenid,
    bindPlatformIdentity
)
from dbConnection.models import UnifiedUser, KusaBase, KusaField
from services.identity_service import get_now, merge_users
from dbConnection.kusa_item import changeItemAmount
from kusa_base import plugin_config

# 从配置文件获取官方机器人QQ号，如果未配置则禁用插件
OFFICIAL_BOT_QQ = plugin_config.get('qq', {}).get('official_bot')
if not OFFICIAL_BOT_QQ:
    print("[AutoBind] 警告: 未配置官方机器人QQ号(qq.official_bot)，自动绑定插件已禁用")
    OFFICIAL_BOT_QQ = None
else:
    OFFICIAL_BOT_QQ = str(OFFICIAL_BOT_QQ)

CACHE_TTL = 60
BIND_COMMAND = "!绑定"

_pending_messages = {}


def get_cache_key(text: str, timestamp: int, group_mapping_id: int) -> tuple:
    """生成缓存键"""
    text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
    return (text_hash, timestamp, group_mapping_id)


def cleanup_expired_cache():
    """清理过期缓存"""
    now = int(time.time())
    expired_keys = [k for k, v in _pending_messages.items() if v["expires_at"] < now]
    for key in expired_keys:
        del _pending_messages[key]


async def is_user_fully_bound(qq: str = None, openid: str = None) -> bool:
    """检查用户是否已双端绑定"""
    if qq:
        user = await getUnifiedUserByRealQQ(qq)
        if user and user.realQQ and user.qqbotOpenid:
            return True
    if openid:
        user = await getUnifiedUserByQQBotOpenid(openid)
        if user and user.realQQ and user.qqbotOpenid:
            return True
    return False


async def perform_auto_bind(openid: str, qq: str, group_mapping_id: int):
    """执行自动绑定"""
    user_by_qq = await getUnifiedUserByRealQQ(qq)
    user_by_openid = await getUnifiedUserByQQBotOpenid(openid)
    
    if user_by_qq and user_by_openid:
        if user_by_qq.id != user_by_openid.id:
            await merge_users(user_by_openid.id, user_by_qq.id)
        await bindPlatformIdentity(user_by_qq, "qqbot", openid)
        print(f"[AutoBind] 合并绑定成功: QQ={qq} <-> OpenId={openid[:20]}..., GroupMapping={group_mapping_id}")
        
    elif user_by_qq:
        await bindPlatformIdentity(user_by_qq, "qqbot", openid)
        print(f"[AutoBind] QQ绑定OpenId成功: QQ={qq} <-> OpenId={openid[:20]}..., GroupMapping={group_mapping_id}")
        
    elif user_by_openid:
        await bindPlatformIdentity(user_by_openid, "onebot", qq)
        print(f"[AutoBind] OpenId绑定QQ成功: QQ={qq} <-> OpenId={openid[:20]}..., GroupMapping={group_mapping_id}")
        
    else:
        unified_user = await UnifiedUser.create(realQQ=qq, qqbotOpenid=openid)
        await KusaBase.create(user=unified_user, kusa=10000, lastUseTime=get_now())
        await KusaField.create(user=unified_user)
        await changeItemAmount(unified_user.id, "草地", 1)
        print(f"[AutoBind] 新建用户成功: QQ={qq} <-> OpenId={openid[:20]}..., GroupMapping={group_mapping_id}")


async def try_match_and_bind(cache_key: tuple):
    """尝试匹配并触发绑定"""
    msg = _pending_messages.get(cache_key)
    if not msg:
        return
    
    qq = msg.get("qq")
    openid = msg.get("openid")
    
    if qq and openid:
        await perform_auto_bind(openid=openid, qq=qq, group_mapping_id=msg["group_mapping_id"])
        del _pending_messages[cache_key]


@event_preprocessor
async def napcat_auto_bind(event: OneBotV11GroupMessageEvent):
    """NapCat 端自动绑定 - 仅在收到 !绑定 指令时触发"""
    # 如果未配置官方机器人QQ号，直接返回
    if not OFFICIAL_BOT_QQ:
        return
    
    if not isinstance(event, OneBotV11GroupMessageEvent):
        return
    
    group_id = str(event.group_id)
    
    mapping = await getGroupMappingByOnebotGroupId(group_id)
    if not mapping or not mapping.allowAutoBind:
        return
    
    has_at_official = any(
        seg.type == "at" and str(seg.data.get("qq")) == OFFICIAL_BOT_QQ
        for seg in event.message
    )
    if not has_at_official:
        return
    
    text = event.get_plaintext().strip()
    
    # 仅处理 !绑定 指令
    if text != BIND_COMMAND:
        return
    
    qq = str(event.user_id)
    
    if await is_user_fully_bound(qq=qq):
        return
    
    timestamp = event.time
    cache_key = get_cache_key(text, timestamp, mapping.id)
    
    if cache_key in _pending_messages:
        _pending_messages[cache_key]["qq"] = qq
        await try_match_and_bind(cache_key)
    else:
        _pending_messages[cache_key] = {
            "qq": qq,
            "openid": None,
            "text": text,
            "timestamp": timestamp,
            "group_mapping_id": mapping.id,
            "expires_at": timestamp + CACHE_TTL
        }
    
    print(f"[AutoBind] NapCat缓存: QQ={qq}, 时间戳={timestamp}, GroupMapping={mapping.id}")


@event_preprocessor
async def qqbot_auto_bind(event: GroupAtMessageCreateEvent):
    """官方 Bot 端自动绑定 - 仅在收到 !绑定 指令时触发"""
    # 如果未配置官方机器人QQ号，直接返回
    if not OFFICIAL_BOT_QQ:
        return
    
    mapping = await getGroupMappingByQqbotGroupOpenid(event.group_openid)
    if not mapping or not mapping.allowAutoBind:
        return
    
    text = ""
    if hasattr(event, 'content') and event.content:
        text = event.content.strip()
    elif hasattr(event, 'message'):
        for seg in event.message:
            if seg.type == "text":
                text += seg.data.get("text", "")
        text = text.strip()
    
    # 仅处理 !绑定 指令
    if text != BIND_COMMAND:
        return
    
    openid = event.author.member_openid
    
    if await is_user_fully_bound(openid=openid):
        return
    
    msg_time_dt = datetime.datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
    timestamp = int(msg_time_dt.timestamp())
    
    cache_key = get_cache_key(text, timestamp, mapping.id)
    
    if cache_key in _pending_messages:
        _pending_messages[cache_key]["openid"] = openid
        await try_match_and_bind(cache_key)
    else:
        _pending_messages[cache_key] = {
            "qq": None,
            "openid": openid,
            "text": text,
            "timestamp": timestamp,
            "group_mapping_id": mapping.id,
            "expires_at": timestamp + CACHE_TTL
        }
    
    print(f"[AutoBind] QQBot缓存: OpenId={openid[:20]}..., 时间戳={timestamp}, GroupMapping={mapping.id}")
