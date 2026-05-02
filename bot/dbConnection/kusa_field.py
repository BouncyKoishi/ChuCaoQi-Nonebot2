import datetime
from tortoise import Tortoise
from .models import KusaField, KusaHistory
from .kusa_system import get_now
from . import user as user_db


async def getKusaField(userId) -> KusaField:
    return await KusaField.filter(user_id=userId).first()


async def batchGetKusaField(userIdList):
    """
    批量获取多个用户的田地信息
    返回: {userId: KusaField}
    """
    fields = await KusaField.filter(user_id__in=userIdList).all()
    return {field.user_id: field for field in fields}


async def batchKusaSoilUseUp(userIdList):
    """
    批量消耗所有用户的承载力
    返回: {userId: usedCapacity}
    """
    fields = await KusaField.filter(user_id__in=userIdList).all()
    result = {}
    for field in fields:
        result[field.user_id] = field.soilCapacity
        field.soilCapacity = 0
    if fields:
        await KusaField.bulk_update(fields, ['soilCapacity'])
    return result


async def getAllKusaField(onlyFinished=False, onlySoilNotBest=False):
    if onlyFinished:
        nowTimestamp = datetime.datetime.now().timestamp()
        return await KusaField.filter(kusaFinishTs__lt=nowTimestamp).all()
    if onlySoilNotBest:
        return await KusaField.filter(soilCapacity__lt=25).all()
    return await KusaField.all()


async def kusaStartGrowing(userId, kusaFinishTs, usingKela, biogasEffect, kusaType, plantCosting, weedCosting,
                           isPrescient, overloadOnHarvest, isMirroring):
    kusaField = await getKusaField(userId)
    if kusaField:
        kusaField.kusaFinishTs = kusaFinishTs
        kusaField.isUsingKela = usingKela
        kusaField.isPrescient = isPrescient
        kusaField.isMirroring = isMirroring
        kusaField.biogasEffect = biogasEffect
        kusaField.kusaType = kusaType
        kusaField.weedCosting = weedCosting
        kusaField.soilCapacity -= plantCosting
        kusaField.overloadOnHarvest = overloadOnHarvest
        kusaField.lastUseTime = get_now()
        await kusaField.save()


async def updateKusaResult(userId, kusaResult, advKusaResult):
    kusaField = await getKusaField(userId)
    if kusaField:
        kusaField.kusaResult = kusaResult
        kusaField.advKusaResult = advKusaResult
        await kusaField.save()


async def updateDefaultKusaType(userId, kusaType):
    kusaField = await getKusaField(userId)
    if kusaField:
        kusaField.defaultKusaType = kusaType
        await kusaField.save()


async def kusaStopGrowing(field: KusaField, force=False):
    if force:
        field.soilCapacity -= field.weedCosting
    field.weedCosting = 0
    field.kusaFinishTs = None
    field.isUsingKela = False
    field.isPrescient = False
    field.isMirroring = False
    field.overloadOnHarvest = False
    field.biogasEffect = 1.0
    field.kusaResult = 0
    field.advKusaResult = 0
    field.kusaType = None
    field.lastUseTime = get_now()
    await field.save()


async def kusaSoilRecover(userId, recoveryAmount=1):
    kusaField = await getKusaField(userId)
    if kusaField:
        kusaField.soilCapacity += recoveryAmount
        kusaField.soilCapacity = min(kusaField.soilCapacity, 25)
        await kusaField.save()
        if kusaField.soilCapacity == 25:
            return True
    return False


async def kusaSoilUseUp(userId):
    kusaField = await getKusaField(userId)
    if kusaField:
        usedCapacity = kusaField.soilCapacity
        kusaField.soilCapacity = 0
        await kusaField.save()
        return usedCapacity
    return 0


async def kusaHistoryAdd(field: KusaField):
    createTimeTs = datetime.datetime.now().timestamp()
    unifiedUser = await user_db.getUnifiedUser(field.user_id)
    await KusaHistory.create(user=unifiedUser, kusaType=field.kusaType, createTimeTs=createTimeTs,
                             kusaResult=field.kusaResult, advKusaResult=field.advKusaResult)


async def kusaHistoryReport(userId, endTime: datetime.datetime, interval):
    startTime = endTime - datetime.timedelta(seconds=interval)
    conn = Tortoise.get_connection('default')
    rows = await conn.execute_query_dict(f'''
            SELECT
                count(*) AS count,
                sum(kusaResult) AS sumKusa,
                avg(kusaResult) AS avgKusa,
                sum(advKusaResult) AS sumAdvKusa,
                avg(advKusaResult) AS avgAdvKusa
            FROM
                KusaHistory
            WHERE
                userId = ? AND createTimeTs < ? AND createTimeTs > ?
        ''', [userId, endTime.timestamp(), startTime.timestamp()])
    return rows[0] if rows else {"count": 0, "sumKusa": 0, "sumAdvKusa": 0, "avgKusa": 0, "avgAdvKusa": 0}


async def getKusaHistory(startTimeTs: float):
    """获取指定时间戳之后的生草历史记录"""
    return await KusaHistory.filter(createTimeTs__gte=startTimeTs).all()


async def getRecentKusaHistory(userId, limit: int):
    rows = await KusaHistory.filter(user_id=userId).order_by('-createTimeTs').limit(limit)
    return rows


async def kusaHistoryTotalReport(interval, endTime: datetime.datetime = None):
    if endTime is None:
        endTime = datetime.datetime.now()
    startTime = endTime - datetime.timedelta(seconds=interval)
    conn = Tortoise.get_connection('default')
    rows = await conn.execute_query_dict(f'''
        SELECT
            count(*) AS count,
            sum(kusaResult) AS sumKusa,
            sum(advKusaResult) AS sumAdvKusa
        FROM
            KusaHistory
        WHERE
            createTimeTs < ? AND createTimeTs > ?
    ''', [endTime.timestamp(), startTime.timestamp()])
    return rows[0] if rows else {"count": 0, "sumKusa": 0, "sumAdvKusa": 0}


async def kusaFarmChampion(endTime: datetime.datetime = None, interval: int = 86400):
    if endTime is None:
        endTime = datetime.datetime.now()
    startTime = endTime - datetime.timedelta(seconds=interval)

    async def executeChampionQuery(conn, select: str, orderBy: str):
        rows = await conn.execute_query_dict(f'''
                SELECT
                    userId,
                    {select}
                FROM
                    KusaHistory
                WHERE
                    createTimeTs < ? AND createTimeTs > ?
                GROUP BY
                    userId
                ORDER BY
                    {orderBy} DESC
            ''', [endTime.timestamp(), startTime.timestamp()])
        return rows[0] if rows else None

    conn = Tortoise.get_connection('default')
    maxTimes = await executeChampionQuery(conn, "count(*) AS count", "count")
    maxKusa = await executeChampionQuery(conn, "sum(kusaResult) AS sumKusa", "sumKusa")
    maxAdvKusa = await executeChampionQuery(conn, "sum(advKusaResult) AS sumAdvKusa", "sumAdvKusa")
    maxAvgAdvKusa = await executeChampionQuery(conn, "avg(advKusaResult) AS avgAdvKusa", "avgAdvKusa")
    maxOnceAdvKusa = await executeChampionQuery(conn, "max(advKusaResult) AS maxAdvKusa", "maxAdvKusa")
    return maxTimes, maxKusa, maxAdvKusa, maxAvgAdvKusa, maxOnceAdvKusa


async def kusaOnceRanking(userId=None, limit=25):
    if userId:
        return await KusaHistory.filter(user_id=userId).order_by('-kusaResult').limit(limit)
    return await KusaHistory.all().order_by('-kusaResult').limit(limit)


async def kusaAdvOnceRanking(userId=None, limit=25):
    if userId:
        return await KusaHistory.filter(user_id=userId).order_by('-advKusaResult').limit(limit)
    return await KusaHistory.all().order_by('-advKusaResult').limit(limit)
