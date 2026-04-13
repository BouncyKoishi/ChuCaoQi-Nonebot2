import pytz
import datetime
from .models import KusaItemList, KusaItemStorage
from . import user as user_db
from utils import romanNumToInt


async def getItem(itemName) -> KusaItemList:
    return await KusaItemList.filter(name=itemName).first()


async def getItemsByType(itemType):
    return await KusaItemList.filter(type=itemType).all()


async def getItemAmount(userId, itemName) -> int:
    item = await getItem(itemName)
    if item:
        itemStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
        if itemStorage:
            return itemStorage.amount
    return 0


async def getItemStorageInfo(userId, itemName) -> KusaItemStorage:
    item = await getItem(itemName)
    if item:
        return await KusaItemStorage.filter(user_id=userId, item=item).first()
    else:
        raise ValueError("Item not found")


async def getItemStorageListByItem(itemName):
    item = await getItem(itemName)
    if not item:
        return []
    return await KusaItemStorage.filter(item=item, allowUse=True, amount__gt=0).all()


async def getUserIdListByItem(itemName):
    item = await getItem(itemName)
    if not item:
        return []
    storageList = await KusaItemStorage.filter(item=item, allowUse=True, amount__gt=0).all()
    return [storage.user_id for storage in storageList]


async def getTechLevel(userId, techNamePrefix) -> int:
    techList = await KusaItemStorage.filter(user_id=userId, item__name__contains=techNamePrefix).all()
    if not techList:
        return 0
    techItemList = [await tech.item.all() for tech in techList]
    techLevelList = [romanNumToInt(techItem.name[len(techNamePrefix):]) for techItem in techItemList]
    return max(techLevelList) if techLevelList else 0


async def changeItemAmount(userId, itemName, increaseAmount):
    if increaseAmount == 0:
        return True

    item = await getItem(itemName)
    if not item:
        return False

    itemStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
    if itemStorage:
        if itemStorage.amount + increaseAmount < 0:
            raise ValueError("Item amount cannot be negative")
        itemStorage.amount += increaseAmount
        await itemStorage.save()
        if itemStorage.amount == 0:
            await itemStorage.delete()
    else:
        if increaseAmount < 0:
            raise ValueError("Item amount cannot be negative")
        unifiedUser = await user_db.getUnifiedUser(userId)
        await KusaItemStorage.create(user=unifiedUser, item=item, amount=increaseAmount)

    return True


async def changeItemAllowUse(userId, itemName, allowUse):
    item = await getItem(itemName)
    if not item:
        return False

    itemStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
    if itemStorage:
        itemStorage.allowUse = allowUse
        await itemStorage.save()
        return True


async def updateTimeLimitedItem(userId, itemName, duration, amount=1):
    item = await getItem(itemName)
    if not item:
        return False
    if amount <= 0:
        await removeTimeLimitedItem(userId, itemName)

    itemStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
    if itemStorage:
        itemStorage.amount = amount
        itemStorage.timeLimitTs += duration
        await itemStorage.save()
    else:
        now = datetime.datetime.now().timestamp()
        timeLimitTs = now + duration
        unifiedUser = await user_db.getUnifiedUser(userId)
        await KusaItemStorage.create(user=unifiedUser, item=item, amount=amount, timeLimitTs=timeLimitTs)

    return True


async def removeTimeLimitedItem(userId, itemName):
    item = await getItem(itemName)
    if not item:
        return False

    itemStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
    if itemStorage:
        await itemStorage.delete()
        return True
    return False


async def cleanTimeLimitedItems():
    now = datetime.datetime.now().timestamp()
    return await KusaItemStorage.filter(timeLimitTs__lt=now).delete()


async def getShopItemList(priceType):
    return await KusaItemList.filter(shopPrice__not_isnull=True, priceType=priceType).order_by('shopPrice').all()


async def getStoragesOrderByAmountDesc(itemName):
    item = await getItem(itemName)
    if item:
        return await KusaItemStorage.filter(item=item).order_by('-amount').all()
    return []


async def cleanAllG(userId):
    items = await getItemsByType('G')
    for item in items:
        gStorage = await KusaItemStorage.filter(user_id=userId, item=item).first()
        if gStorage:
            await gStorage.delete()


async def batchGetItemStorage(userIdList, itemNames):
    """
    批量获取多个用户的多个物品存储信息
    返回: {userId: {itemName: KusaItemStorage或None}}
    """
    items = await KusaItemList.filter(name__in=itemNames).all()
    itemNameToItem = {item.name: item for item in items}
    
    storages = await KusaItemStorage.filter(user_id__in=userIdList, item_id__in=itemNames).prefetch_related('item').all()
    
    result = {userId: {name: None for name in itemNames} for userId in userIdList}
    for storage in storages:
        userId = storage.user_id
        itemName = storage.item.name
        if userId in result and itemName in result[userId]:
            result[userId][itemName] = storage
    
    return result


async def batchGetItemAmounts(userIdList, itemNames):
    """
    批量获取多个用户的多个物品数量
    返回: {userId: {itemName: amount}}
    """
    storageData = await batchGetItemStorage(userIdList, itemNames)
    return {
        userId: {itemName: (storage.amount if storage else 0) for itemName, storage in items.items()}
        for userId, items in storageData.items()
    }


async def batchGetTechLevels(userIdList, techNamePrefixes):
    """
    批量获取多个用户的多个科技等级
    返回: {userId: {techNamePrefix: level}}
    """
    result = {userId: {prefix: 0 for prefix in techNamePrefixes} for userId in userIdList}
    
    techItemNames = []
    for prefix in techNamePrefixes:
        items = await KusaItemList.filter(name__startswith=prefix).values_list('name', flat=True)
        techItemNames.extend(items)
    
    if not techItemNames:
        return result
    
    allTechStorages = await KusaItemStorage.filter(user_id__in=userIdList, item_id__in=techItemNames).prefetch_related('item').all()
    
    for storage in allTechStorages:
        userId = storage.user_id
        if userId not in result:
            continue
        itemName = storage.item.name
        for prefix in techNamePrefixes:
            if itemName.startswith(prefix):
                try:
                    levelStr = itemName[len(prefix):]
                    level = romanNumToInt(levelStr)
                    if level > result[userId][prefix]:
                        result[userId][prefix] = level
                except:
                    pass
    
    return result


async def batchChangeItemAmounts(updates):
    """
    批量更新物品数量
    updates: [(userId, itemName, changeAmount), ...]
    """
    if not updates:
        return
    
    itemNames = set(update[1] for update in updates)
    userIdList = set(update[0] for update in updates)
    
    items = await KusaItemList.filter(name__in=itemNames).all()
    itemNameToItem = {item.name: item for item in items}
    
    storages = await KusaItemStorage.filter(user_id__in=userIdList, item_id__in=itemNames).prefetch_related('item').all()
    storageMap = {}
    for storage in storages:
        key = (storage.user_id, storage.item.name)
        storageMap[key] = storage
    
    toCreate = []
    toDelete = []
    
    for userId, itemName, changeAmount in updates:
        if changeAmount == 0:
            continue
        if itemName not in itemNameToItem:
            continue
        
        item = itemNameToItem[itemName]
        key = (userId, itemName)
        
        if key in storageMap:
            storage = storageMap[key]
            newAmount = storage.amount + changeAmount
            if newAmount < 0:
                continue
            storage.amount = newAmount
            if newAmount == 0:
                toDelete.append(storage)
            else:
                await storage.save()
        else:
            if changeAmount > 0:
                unifiedUser = await user_db.getUnifiedUser(userId)
                toCreate.append(KusaItemStorage(user=unifiedUser, item=item, amount=changeAmount))
    
    if toCreate:
        await KusaItemStorage.bulk_create(toCreate)
    if toDelete:
        for storage in toDelete:
            await storage.delete()
