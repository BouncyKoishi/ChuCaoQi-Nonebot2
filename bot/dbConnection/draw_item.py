from random import randint
from .models import DrawItemList, DrawItemStorage
from . import user as user_db
from tortoise import Tortoise
from tortoise.query_utils import Prefetch
from tortoise.functions import Sum


async def getItem(itemId):
    return await DrawItemList.filter(id=itemId).first()


async def getItemByName(itemName):
    return await DrawItemList.filter(name=itemName).first()


async def getItemListByAuthorId(authorId, rareRank=None, poolName=None):
    filterQuery = getRareRankAndPoolFilter(rareRank, poolName)
    return await filterQuery.filter(authorId=authorId).order_by("-rareRank")


async def getRandomItem(rareRank, poolName=None):
    if poolName:
        rareItemList = await DrawItemList.filter(rareRank=rareRank, pool=poolName)
    else:
        rareItemList = await DrawItemList.filter(rareRank=rareRank)
    if not rareItemList:
        return None
    return rareItemList[randint(0, len(rareItemList) - 1)]


async def getLatestItems(limit):
    return await DrawItemList.all().order_by("-id").limit(limit)


async def getPoolList():
    return await DrawItemList.all().distinct().values_list('pool', flat=True)


async def searchItem(keyword, limit, offset=0):
    conn = Tortoise.get_connection('default')
    count = (await conn.execute_query_dict('''
        SELECT
            count(*) AS count
        FROM
            DrawItemList
        WHERE
            name LIKE ('%' || ? || '%')
    ''', [keyword,]))[0]['count']
    rows = await conn.execute_query_dict('''
        SELECT
            id,
            name,
            rareRank
        FROM
            DrawItemList
        WHERE
            name LIKE ('%' || ? || '%')
        ORDER BY
            rareRank DESC
            LIMIT ? OFFSET ?
    ''', [keyword, limit, offset])
    return count, rows


async def addItem(itemName, itemRare, poolName, itemDetail, authorId):
    await DrawItemList.create(name=itemName, rareRank=itemRare, pool=poolName, detail=itemDetail, authorId=authorId)


async def deleteItem(item: DrawItemList):
    await item.delete()


async def setItemDetail(item: DrawItemList, newItemDetail):
    item.detail = newItemDetail
    await item.save()


async def getItemsWithStorage(userId, rareRank=None, poolName=None):
    filterQuery = getRareRankAndPoolFilter(rareRank, poolName)
    return await filterQuery.order_by("-rareRank").prefetch_related(
            Prefetch("draw_item_storage", queryset=DrawItemStorage.filter(user_id=userId), to_attr="storage")
        )


async def getSingleItemStorage(userId, itemId):
    return await DrawItemStorage.filter(user_id=userId, item=itemId).first()


async def getItemStorageCount(itemId):
    personCount = await DrawItemStorage.filter(item=itemId).count()
    numberCount = await DrawItemStorage.filter(item=itemId).annotate(sum=Sum("amount")).first()
    return personCount, numberCount.sum


async def setItemStorage(userId, itemId):
    itemStorageData = await getSingleItemStorage(userId, itemId)
    if itemStorageData:
        itemStorageData.amount += 1
        await itemStorageData.save()
    else:
        item = await getItem(itemId)
        unifiedUser = await user_db.getUnifiedUser(userId)
        await DrawItemStorage.create(user=unifiedUser, item=item, amount=1)


async def isPoolNameExist(poolName):
    poolItemsCount = await DrawItemList.filter(pool=poolName).count()
    return poolItemsCount > 0


def getRareRankAndPoolFilter(rareRank, poolName):
    if rareRank is not None and poolName:
        return DrawItemList.filter(rareRank=rareRank, pool=poolName)
    elif rareRank is None and poolName:
        return DrawItemList.filter(pool=poolName)
    elif rareRank is not None and not poolName:
        return DrawItemList.filter(rareRank=rareRank)
    else:
        return DrawItemList.all()
