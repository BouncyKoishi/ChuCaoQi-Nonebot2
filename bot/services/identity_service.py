"""
身份服务模块
提供统一用户管理功能
"""

from typing import Optional
from dbConnection.models import UnifiedUser, KusaBase, KusaField
from dbConnection import user as user_db
import secrets
import string
import datetime


def get_now():
    return datetime.datetime.now().astimezone()


async def get_unified_user_by_platform(platform: str, platform_id: str) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUserByPlatform(platform, platform_id)


async def get_unified_user_by_real_qq(realQQ: str) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUserByRealQQ(realQQ)


async def get_unified_user_by_id(userId: int) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUser(userId)


async def create_unified_user_for_onebot(realQQ: str) -> UnifiedUser:
    unified_user = await user_db.createUnifiedUserForOnebot(realQQ)
    await KusaBase.create(user=unified_user, kusa=10000, lastUseTime=get_now())
    await KusaField.create(user=unified_user)
    from dbConnection.kusa_item import changeItemAmount
    await changeItemAmount(unified_user.id, "草地", 1)
    return unified_user


async def create_unified_user_for_qqbot(openid: str) -> UnifiedUser:
    unified_user = await user_db.createUnifiedUserForQQBot(openid)
    await KusaBase.create(user=unified_user, kusa=10000, lastUseTime=get_now())
    await KusaField.create(user=unified_user)
    from dbConnection.kusa_item import changeItemAmount
    await changeItemAmount(unified_user.id, "草地", 1)
    return unified_user


async def get_or_create_unified_user(platform: str, platform_id: str) -> UnifiedUser:
    unified_user = await get_unified_user_by_platform(platform, platform_id)
    if not unified_user:
        if platform == "onebot":
            unified_user = await create_unified_user_for_onebot(platform_id)
        elif platform == "qqbot":
            unified_user = await create_unified_user_for_qqbot(platform_id)
    return unified_user


async def get_real_qq(unified_user: UnifiedUser) -> Optional[str]:
    return unified_user.realQQ


async def get_user_id_by_event(event) -> Optional[int]:
    return None


async def bind_platform_identity(
    unified_user: UnifiedUser,
    platform: str,
    platform_id: str
) -> bool:
    return await user_db.bindPlatformIdentity(unified_user, platform, platform_id)


async def generate_web_token(unified_user: UnifiedUser) -> str:
    alphabet = string.ascii_letters + string.digits
    token = 'kusa_' + ''.join(secrets.choice(alphabet) for _ in range(32))
    
    await user_db.updateUnifiedUserWebToken(unified_user, token)
    
    return token


async def verify_web_token(token: str) -> Optional[UnifiedUser]:
    if not token:
        return None
    
    unified_user = await user_db.getUnifiedUserByWebToken(token)
    if not unified_user or not unified_user.webToken:
        return None
    
    return unified_user


async def reset_web_token(unified_user: UnifiedUser) -> str:
    await user_db.updateUnifiedUserWebToken(unified_user, None)
    
    return await generate_web_token(unified_user)


async def delete_user_data(userId: int):
    from dbConnection.models import (
        KusaBase, KusaField, KusaHistory, DrawItemStorage,
        KusaItemStorage, ChatUser, DonateRecord, TradeRecord
    )
    
    await KusaBase.filter(user_id=userId).delete()
    await KusaField.filter(user_id=userId).delete()
    await KusaHistory.filter(user_id=userId).delete()
    await DrawItemStorage.filter(user_id=userId).delete()
    await KusaItemStorage.filter(user_id=userId).delete()
    await ChatUser.filter(user_id=userId).delete()
    await DonateRecord.filter(user_id=userId).delete()
    await TradeRecord.filter(user_id=userId).delete()


async def merge_users(
    source_id: int,
    target_id: int,
    keep_source_data: bool = False
) -> bool:
    source_user = await get_unified_user_by_id(source_id)
    target_user = await get_unified_user_by_id(target_id)
    
    if not source_user or not target_user:
        return False
    
    if source_user.realQQ and not target_user.realQQ:
        target_user.realQQ = source_user.realQQ
    
    if source_user.qqbotOpenid and not target_user.qqbotOpenid:
        target_user.qqbotOpenid = source_user.qqbotOpenid
    
    await user_db.saveUnifiedUser(target_user)
    
    if not keep_source_data:
        await delete_user_data(source_id)
    
    await user_db.deleteUnifiedUser(source_user)
    
    return True
