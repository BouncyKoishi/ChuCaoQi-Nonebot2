"""
用户数据访问模块

专门负责UnifiedUser表的所有数据库操作
"""

import datetime
from typing import Optional, List
from .models import UnifiedUser  # GroupMapping 已禁用


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
    """为OneBot平台创建UnifiedUser"""
    return await UnifiedUser.create(realQQ=realQQ)


async def createUnifiedUserForQQBot(openid: str) -> UnifiedUser:
    """为QQBot平台创建UnifiedUser"""
    return await UnifiedUser.create(qqbotOpenid=openid)


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


# ===== GroupMapping 相关函数 - 已禁用 =====
# 官方 QQ Bot 功能已禁用，GroupMapping 表暂时不需要
#
# async def getGroupMappingByOnebotGroupId(onebotGroupId: str) -> Optional[GroupMapping]:
#     """通过 OneBot 群 ID 获取群映射"""
#     return await GroupMapping.filter(onebotGroupId=onebotGroupId).first()
#
#
# async def getGroupMappingByQqbotGroupOpenid(qqbotGroupOpenid: str) -> Optional[GroupMapping]:
#     """通过 QQ Bot 群 OpenId 获取群映射"""
#     return await GroupMapping.filter(qqbotGroupOpenid=qqbotGroupOpenid).first()
#
#
# async def getAutoBindGroups() -> List[GroupMapping]:
#     """获取所有启用自动绑定的群"""
#     return await GroupMapping.filter(allowAutoBind=True).all()
#
#
# async def isGroupAllowAutoBind(onebotGroupId: str) -> bool:
#     """检查群是否启用自动绑定"""
#     mapping = await getGroupMappingByOnebotGroupId(onebotGroupId)
#     return mapping.allowAutoBind if mapping else False
#
#
# async def setGroupAutoBind(onebotGroupId: str, allowAutoBind: bool) -> bool:
#     """设置群的自动绑定状态"""
#     mapping = await getGroupMappingByOnebotGroupId(onebotGroupId)
#     if not mapping:
#         return False
#     mapping.allowAutoBind = allowAutoBind
#     await mapping.save()
#     return True
#
#
# async def createGroupMapping(
#     onebotGroupId: str,
#     qqbotGroupOpenid: str = None,
#     groupName: str = None,
#     allowAutoBind: bool = False
# ) -> GroupMapping:
#     """创建群映射"""
#     return await GroupMapping.create(
#         onebotGroupId=onebotGroupId,
#         qqbotGroupOpenid=qqbotGroupOpenid,
#         groupName=groupName,
#         allowAutoBind=allowAutoBind
#     )
