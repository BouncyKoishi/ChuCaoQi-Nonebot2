"""
生草系统数据库访问模块

负责KusaBase表（生草系统用户数据）及相关表的数据库操作
"""

import datetime
from typing import Dict, List, Optional
from .models import KusaBase, KusaField, Flag, DonateRecord, TradeRecord
from . import user as user_db


def get_now():
    """获取当前时间（带时区）"""
    return datetime.datetime.now().astimezone()


# ===== KusaUser 相关操作 =====

async def createKusaUser(userId):
    """创建生草系统用户"""
    existUser = await getKusaUser(userId)
    if not existUser:
        from .kusa_item import changeItemAmount
        unifiedUser = await user_db.getUnifiedUser(userId)
        await KusaBase.create(user=unifiedUser, kusa=10000, lastUseTime=get_now())
        await KusaField.create(user=unifiedUser)
        await changeItemAmount(userId, "草地", 1)
    else:
        existUser.lastUseTime = get_now()
        await existUser.save()


async def getNameListByKusaUserId(userIdList):
    """批量获取用户名称列表"""
    users = await KusaBase.filter(user_id__in=userIdList).values('user_id', 'name')
    return {user['user_id']: (user['name'] if user['name'] else str(user['user_id'])) for user in users}


async def getKusaUser(userId) -> KusaBase:
    """获取生草系统用户"""
    return await KusaBase.filter(user_id=userId).first()


async def getAllKusaUser():
    """获取所有生草系统用户"""
    return await KusaBase.all()


async def changeKusaUserName(userId, newName):
    """修改用户名称"""
    user = await getKusaUser(userId)
    if user:
        user.name = newName
        await user.save()
        return True
    else:
        return False


async def changeKusaUserTitle(userId, newTitle):
    """修改用户称号"""
    user = await getKusaUser(userId)
    if user:
        user.title = newTitle
        await user.save()
        return True
    else:
        return False


async def changeKusa(userId, changeAmount):
    """修改用户草数量"""
    user = await getKusaUser(userId)
    if user:
        user.kusa += changeAmount
        await user.save()
        return True
    else:
        return False


async def changeAdvKusa(userId, changeAmount):
    """修改用户草之精华数量"""
    user = await getKusaUser(userId)
    if user:
        user.advKusa += changeAmount
        await user.save()
        return True
    else:
        return False


async def batchChangeKusa(updates):
    """
    批量更新用户的草数量
    updates: {userId: changeAmount, ...}
    """
    if not updates:
        return

    userIdList = list(updates.keys())
    users = await KusaBase.filter(user_id__in=userIdList).all()
    userMap = {user.user_id: user for user in users}

    for userId, changeAmount in updates.items():
        if userId in userMap:
            userMap[userId].kusa += changeAmount

    if users:
        await KusaBase.bulk_update(users, ['kusa'])


async def batchChangeAdvKusa(updates):
    """
    批量更新用户的草之精华数量
    updates: {userId: changeAmount, ...}
    """
    if not updates:
        return

    userIdList = list(updates.keys())
    users = await KusaBase.filter(user_id__in=userIdList).all()
    userMap = {user.user_id: user for user in users}

    for userId, changeAmount in updates.items():
        if userId in userMap:
            userMap[userId].advKusa += changeAmount

    if users:
        await KusaBase.bulk_update(users, ['advKusa'])


async def batchGetKusaUserVipLevels(userIdList):
    """
    批量获取用户的VIP等级
    返回: {userId: vipLevel}
    """
    users = await KusaBase.filter(user_id__in=userIdList).values('user_id', 'vipLevel')
    return {user['user_id']: user['vipLevel'] for user in users}


# ===== Flag 相关操作 =====

async def getFlagValue(userId, flagName):
    """获取标志值"""
    flag = await Flag.filter(name=flagName, ownerId=userId).first()
    if not flag:
        flag = await Flag.filter(name=flagName, forAll=True).first()
    if not flag:
        raise Exception("Config Error: 读取时错误，无该参数信息")
    return flag.value


async def setFlag(userId, flagName, value):
    """设置标志值"""
    existFlag = await Flag.filter(name=flagName, ownerId=userId).first()
    if existFlag:
        existFlag.value = value
        await existFlag.save()
    else:
        publicFlag = await Flag.filter(name=flagName, forAll=True).first()
        if not publicFlag:
            raise Exception("Config Error: 新增时错误，无此公共参数")
        await Flag.create(name=flagName, ownerId=userId, value=value, forAll=False)


async def getFlagList():
    """获取所有公共标志列表"""
    return await Flag.filter(forAll=True).all()


# ===== DonateRecord 相关操作 =====

async def getDonateRecords(userId=None, year=None):
    """获取捐赠记录"""
    if userId:
        if year:
            return await DonateRecord.filter(user_id=userId).filter(donateDate__contains=year).order_by('donateDate')
        return await DonateRecord.filter(user_id=userId).order_by('donateDate')
    if year:
        return await DonateRecord.filter(donateDate__contains=year).order_by('donateDate')
    return await DonateRecord.all()


async def getDonateAmount(userId=None, year=None):
    """获取捐赠金额"""
    records = await getDonateRecords(userId, year)
    return sum([record.amount for record in records])


async def getDonateRank(userId=None, year=None):
    """获取捐赠排行"""
    records = await getDonateRecords(userId, year)
    groupedRecords = {}
    for record in records:
        groupedRecords.setdefault(record.user_id, []).append(record.amount)
    donates = {userId: sum(amounts) for userId, amounts in groupedRecords.items()}
    donateRank = dict(sorted(donates.items(), key=lambda item: item[1], reverse=True))
    return donateRank


async def setDonateRecord(userId, amount, source):
    """设置捐赠记录"""
    now = datetime.datetime.now()
    donateDate = now.strftime('%Y-%m-%d')
    unifiedUser = await user_db.getUnifiedUser(userId)
    await DonateRecord.create(user=unifiedUser, amount=amount, donateDate=donateDate, source=source)


# ===== TradeRecord 相关操作 =====

async def getTradeRecord(userId=None, tradeType=None, gainItemName=None, costItemName=None, startTime=None, endTime=None):
    """获取交易记录"""
    query = TradeRecord.all()
    if userId:
        query = query.filter(user_id=userId)
    if tradeType:
        query = query.filter(tradeType=tradeType)
    if gainItemName:
        query = query.filter(gainItemName=gainItemName)
    if costItemName:
        query = query.filter(costItemName=costItemName)
    if startTime:
        query = query.filter(timestamp__gt=startTime)
    if endTime:
        query = query.filter(timestamp__lt=endTime)
    return await query.order_by('timestamp').all()


async def getAllTradeRecordsByCostItem(costItemName: str):
    """获取所有指定消耗物品的交易记录"""
    return await TradeRecord.filter(costItemName=costItemName).all()


async def setTradeRecord(userId, tradeType, gainItemAmount, gainItemName, costItemAmount, costItemName, detail=None):
    """设置交易记录"""
    if gainItemAmount == 0 or costItemAmount == 0:
        return
    timestamp = datetime.datetime.now().timestamp()
    unifiedUser = await user_db.getUnifiedUser(userId)
    await TradeRecord.create(user=unifiedUser, tradeType=tradeType, detail=detail, timestamp=timestamp,
                             gainItemAmount=gainItemAmount, gainItemName=gainItemName,
                             costItemAmount=costItemAmount, costItemName=costItemName)
