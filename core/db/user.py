"""
用户数据访问模块

专门负责UnifiedUser表的所有数据库操作
"""

import datetime
from typing import Optional, List, Dict
from .models import UnifiedUser, GroupMapping, IdentityBindRequest


# ===== 查询类函数 =====

async def getUnifiedUser(userId: int) -> Optional[UnifiedUser]:
    """通过ID获取UnifiedUser"""
    return await UnifiedUser.filter(id=userId).first()


async def getUnifiedUserByRealQQ(realQQ: str) -> Optional[UnifiedUser]:
    """通过realQQ获取UnifiedUser"""
    return await UnifiedUser.filter(realQQ=realQQ).first()


async def getUnifiedUserByQQBotOpenid(openid: str) -> Optional[UnifiedUser]:
    """通过qqbotOpenid获取UnifiedUser"""
    return await UnifiedUser.filter(qqbotOpenid=openid).first()


async def getUnifiedUserByWebToken(token: str) -> Optional[UnifiedUser]:
    """通过webToken获取UnifiedUser"""
    return await UnifiedUser.filter(webToken=token).first()


async def getUnifiedUsersByIds(userIds: List[int]) -> List[UnifiedUser]:
    """批量通过ID列表获取UnifiedUser"""
    if not userIds:
        return []
    return await UnifiedUser.filter(id__in=userIds).all()


async def getRealQQByUserId(userId: int) -> Optional[str]:
    """通过用户ID获取真实QQ号"""
    unified_user = await UnifiedUser.filter(id=userId).first()
    return unified_user.realQQ if unified_user else None


async def getRealQQsByUserIds(userIds: List[int]) -> Dict[int, Optional[str]]:
    """批量通过用户ID获取真实QQ号"""
    if not userIds:
        return {}
    unified_users = await UnifiedUser.filter(id__in=userIds).all()
    return {u.id: u.realQQ for u in unified_users}


async def getAllRobotUsers() -> List[UnifiedUser]:
    """获取所有机器人用户"""
    return await UnifiedUser.filter(isRobot=True).all()


async def getUnifiedUserByPlatform(platform: str, platform_id: str) -> Optional[UnifiedUser]:
    """
    通过平台类型和平台ID获取UnifiedUser
    
    Args:
        platform: 平台类型，"onebot" 或 "qqbot"
        platform_id: 平台用户ID
    """
    if platform == "onebot":
        return await getUnifiedUserByRealQQ(platform_id)
    elif platform == "qqbot":
        return await getUnifiedUserByQQBotOpenid(platform_id)
    return None


# ===== 创建类函数 =====

async def createUnifiedUserForOnebot(realQQ: str) -> UnifiedUser:
    """为OneBot平台创建UnifiedUser（如果已存在则返回现有用户）"""
    user, _ = await UnifiedUser.get_or_create(realQQ=realQQ)
    return user


async def createUnifiedUserForQQBot(openid: str) -> UnifiedUser:
    """为QQBot平台创建UnifiedUser（如果已存在则返回现有用户）"""
    user, _ = await UnifiedUser.get_or_create(qqbotOpenid=openid)
    return user


# ===== 更新类函数 =====

async def saveUnifiedUser(user: UnifiedUser) -> None:
    """保存UnifiedUser的更改"""
    await user.save()


async def updateUnifiedUserWebToken(user: UnifiedUser, token: Optional[str]) -> None:
    """
    更新用户的webToken
    
    Args:
        user: UnifiedUser对象
        token: webToken，为None时表示清除token
    """
    user.webToken = token
    if token:
        user.webTokenCreatedAt = datetime.datetime.now()
    else:
        user.webTokenCreatedAt = None
    await user.save()


async def bindPlatformIdentity(user: UnifiedUser, platform: str, platform_id: str) -> bool:
    """
    绑定平台身份
    
    Args:
        user: UnifiedUser对象
        platform: 平台类型，"onebot" 或 "qqbot"
        platform_id: 平台用户ID
        
    Returns:
        bool: 绑定成功返回True，失败返回False
    """
    if platform == "onebot":
        if user.realQQ and user.realQQ != platform_id:
            return False
        user.realQQ = platform_id
    elif platform == "qqbot":
        if user.qqbotOpenid and user.qqbotOpenid != platform_id:
            return False
        user.qqbotOpenid = platform_id
    else:
        return False
    
    await user.save()
    return True


# ===== 删除类函数 =====

async def deleteUnifiedUser(user: UnifiedUser) -> None:
    """删除UnifiedUser"""
    await user.delete()


# ===== 身份绑定申请 =====

async def getIdentityBindRequest(requestId: int) -> Optional[IdentityBindRequest]:
    return await IdentityBindRequest.filter(id=requestId).first()


async def getPendingBindRequestByOpenid(openid: str) -> Optional[IdentityBindRequest]:
    """同一 openid 只允许一条 pending"""
    return await IdentityBindRequest.filter(
        qqbotOpenid=str(openid), status='pending'
    ).order_by('-id').first()


async def getPendingBindRequestsByTargetQQ(targetQQ: str) -> List[IdentityBindRequest]:
    return await IdentityBindRequest.filter(
        targetQQ=str(targetQQ), status='pending'
    ).all()


async def getPendingBindRequests() -> List[IdentityBindRequest]:
    return await IdentityBindRequest.filter(status='pending').order_by('-id').all()


async def createIdentityBindRequest(
    qqbotOpenid: str,
    sourceUserId: Optional[int],
    targetQQ: str,
    bindType: str,
) -> IdentityBindRequest:
    return await IdentityBindRequest.create(
        qqbotOpenid=str(qqbotOpenid),
        sourceUserId=sourceUserId,
        targetQQ=str(targetQQ),
        bindType=bindType,
    )


async def updateIdentityBindRequest(
    request: IdentityBindRequest,
    status: str,
    note: Optional[str] = None,
) -> None:
    request.status = status
    request.note = note
    request.reviewedAt = datetime.datetime.now().astimezone()
    await request.save()


# ===== 身份字段（realQQ / qqbotOpenid）=====

IDENTITY_FIELDS = ('realQQ', 'qqbotOpenid')


async def getUnifiedUserByIdentityValue(field: str, value: str, exclude_id: Optional[int] = None) -> Optional[UnifiedUser]:
    """按身份字段查重，exclude_id 用于修改场景排除自身"""
    if field not in IDENTITY_FIELDS or not value:
        return None
    query = UnifiedUser.filter(**{field: str(value)})
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return await query.first()


async def setUnifiedUserIdentityField(user: UnifiedUser, field: str, value: str) -> None:
    if field not in IDENTITY_FIELDS:
        raise ValueError(f'非法身份字段: {field}')
    setattr(user, field, str(value))
    await user.save()


async def clearUnifiedUserIdentityField(user: UnifiedUser, field: str) -> None:
    if field not in IDENTITY_FIELDS:
        raise ValueError(f'非法身份字段: {field}')
    setattr(user, field, None)
    await user.save()


# ===== GroupMapping 相关函数 =====

async def getGroupMappingByOnebotGroupId(onebotGroupId: str) -> Optional[GroupMapping]:
    """通过 OneBot 群 ID（QQ 群号）获取群映射"""
    return await GroupMapping.filter(onebotGroupId=str(onebotGroupId)).first()


async def getGroupMappingByQqbotGroupOpenid(qqbotGroupOpenid: str) -> Optional[GroupMapping]:
    """通过官方 Bot 群 OpenId 获取群映射"""
    return await GroupMapping.filter(qqbotGroupOpenid=str(qqbotGroupOpenid)).first()


async def getAllGroupMappings() -> List[GroupMapping]:
    """获取全部群映射"""
    return await GroupMapping.all()


async def upsertGroupMapping(onebotGroupId: str, qqbotGroupOpenid: str) -> GroupMapping:
    """建立或覆盖 openid -> QQ 群号 的映射

    onebotGroupId 与 qqbotGroupOpenid 都有唯一约束，写入前先解除另一条
    记录对目标 QQ 群号的占用，避免唯一约束冲突。
    """
    onebotGroupId = str(onebotGroupId)
    qqbotGroupOpenid = str(qqbotGroupOpenid)

    occupied = await GroupMapping.filter(onebotGroupId=onebotGroupId).first()
    if occupied and occupied.qqbotGroupOpenid != qqbotGroupOpenid:
        occupied.onebotGroupId = None
        await occupied.save()

    mapping = await GroupMapping.filter(qqbotGroupOpenid=qqbotGroupOpenid).first()
    if mapping:
        mapping.onebotGroupId = onebotGroupId
    else:
        mapping = GroupMapping(
            qqbotGroupOpenid=qqbotGroupOpenid,
            onebotGroupId=onebotGroupId,
        )
    await mapping.save()
    return mapping
