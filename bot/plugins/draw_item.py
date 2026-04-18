import random
from typing import Dict, Any, Optional, Union
from reloader import kusa_command as on_command
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, GroupMessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot
from nonebot.params import CommandArg
from nonebot.adapters import Message, Bot
from kusa_base import plugin_config, send_private_msg
from utils import nameDetailSplit
from itertools import groupby
import dbConnection.kusa_system as baseDB
import dbConnection.draw_item as drawItemDB
import dbConnection.kusa_item as usefulItemDB
import dbConnection.user as userDB
from services import LotteryService
from .pagination_helper import register_pagination_handler, set_pagination_state
from multi_platform import (
    get_user_id,
    get_real_qq_by_event,
    is_onebot_v11_event,
    get_group_id,
    send_finish,
)


itemRareDescribe = ['Easy', 'Normal', 'Hard', 'Lunatic']
drawConfig = plugin_config.get('drawItem', {})
sensitiveWords = plugin_config.get('sensitiveWords', [])


抽奖_cmd = on_command('抽奖', priority=5, block=True)

@抽奖_cmd.handle()
async def handle_抽奖(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    groupId = get_group_id(event)
    userId = await get_user_id(event, auto_create=True)
    realQQ = await get_real_qq_by_event(event)
    
    if not groupId:
        await send_finish(抽奖_cmd, '暂不支持私聊抽奖^ ^')
        return
    groupIdInt = int(groupId) if groupId else None
    if groupIdInt not in drawConfig['groupAllowDraw']:
        await send_finish(抽奖_cmd, '本群暂不支持抽奖^ ^')
        return
    if groupIdInt not in drawConfig['groupAllowItem']:
        await send_finish(抽奖_cmd, '本群暂不支持抽奖物品^ ^')
        return

    banRisk = drawConfig['banRisk']
    strippedArg = args.extract_plain_text().strip()
    await _getItem(groupId, userId, strippedArg, banRisk, realQQ)


十连抽_cmd = on_command('十连抽', priority=5, block=True)

@十连抽_cmd.handle()
async def handle_十连抽(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    groupId = get_group_id(event)
    userId = await get_user_id(event, auto_create=True)

    if not groupId:
        await send_finish(十连抽_cmd, '暂不支持私聊抽奖^ ^')
        return
    groupIdInt = int(groupId) if groupId else None
    if groupIdInt not in drawConfig['groupAllowItem']:
        await send_finish(十连抽_cmd, '本群暂不支持十连抽^ ^')
        return

    strippedArg = args.extract_plain_text().strip()
    baseLevel, poolName = await _getLevelAndPoolName(strippedArg)
    baseLevel = baseLevel if baseLevel is not None else 0

    # 使用 Service 层进行完整的十连抽流程（包含券检查扣减）
    result = await LotteryService.draw_ten_full(userId=userId, base_level=baseLevel, pool_name=poolName)

    if not result['success']:
        if result.get('error') == 'NO_TICKET':
            ticketName = ['十连券', '高级十连券', '特级十连券', '天琴十连券'][baseLevel]
            await send_finish(十连抽_cmd, f'你缺少{ticketName}，无法十连抽^ ^')
        else:
            await send_finish(十连抽_cmd, result.get('message', '十连抽失败！'))
        return

    draw_result = result['data']
    output = '十连抽结果：\n'
    for item in draw_result['items']:
        output += f'[{item["rare"]}]{item["name"]}'
        if item['isNew']:
            output += '(New!)'
        output += '\n'

    await send_finish(十连抽_cmd, output[:-1])


async def _getItem(groupNum, userId, strippedArg, banRisk=0, realQQ=None):
    """获取抽奖物品（内部辅助函数）"""
    _, poolName = await _getLevelAndPoolName(strippedArg)

    result = await LotteryService.draw_with_redraw(userId, pool_name=poolName, ban_risk=banRisk)
    
    if result.get('banned', False):
        bot = get_bot()
        msg = f'获得了：口球({result["disabledSeconds"]}s)！'
        try:
            await bot.send_group_msg(group_id=groupNum, message=msg)
            if realQQ:
                await bot.set_group_ban(group_id=groupNum, user_id=int(realQQ), duration=result['disabledSeconds'])
        except Exception as e:
            print(f'发送群消息失败: {e}')
        return
    
    msg = ''
    if result['redrawCount'] > 0:
        msg += f'消耗了骰子碎片*{result["redrawCount"]}，'

    item = result['item']
    msg += f'获得了：[{itemRareDescribe[item.rareRank]}]{item.name}'
    if result['isNew']:
        msg += '(New!)'
    if item.detail:
        msg += f'\n物品说明：{item.detail}'
    
    bot = get_bot()
    try:
        await bot.send_group_msg(group_id=groupNum, message=msg)
    except Exception as e:
        print(f'发送群消息失败: {e}')


添加_easy_cmd = on_command('添加-Easy', aliases={'物品添加-Easy'}, priority=5, block=True)

@添加_easy_cmd.handle()
async def handle_add_easy(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    await _addItem(event, args, 0, 添加_easy_cmd)


添加_normal_cmd = on_command('添加-Normal', aliases={'物品添加-Normal'}, priority=5, block=True)

@添加_normal_cmd.handle()
async def handle_add_normal(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    await _addItem(event, args, 1, 添加_normal_cmd)


添加_hard_cmd = on_command('添加-Hard', aliases={'物品添加-Hard'}, priority=5, block=True)

@添加_hard_cmd.handle()
async def handle_add_hard(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    await _addItem(event, args, 2, 添加_hard_cmd)


添加_lunatic_cmd = on_command('添加-Lunatic', aliases={'物品添加-Lunatic'}, priority=5, block=True)

@添加_lunatic_cmd.handle()
async def handle_add_lunatic(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    await _addItem(event, args, 3, 添加_lunatic_cmd)


async def _addItem(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message, rare, matcher):
    """添加物品（内部辅助函数）"""
    stripped_arg = args.extract_plain_text().strip()
    userId = await get_user_id(event, auto_create=True)
    itemName, itemDetail = nameDetailSplit(stripped_arg)
    if not itemName:
        await send_finish(matcher, '需要物品名!')
        return
    if '祝福' in itemName:
        return

    itemName = itemName.strip()
    itemName = itemName.replace('\n', '')
    if len(itemName) > 32:
        await send_finish(matcher, '物品名太长啦!最多32字')
        return
    if itemDetail and len(itemDetail) > 1024:
        await send_finish(matcher, '物品简介太长啦!最多1024字')
        return
    for word in sensitiveWords:
        if word in itemName or (itemDetail and word in itemDetail):
            await send_finish(matcher, '物品名或简介中包含敏感词汇^_^')
            return
    
    realQQ = await get_real_qq_by_event(event)
    userPool = drawConfig['userPool']
    poolName = userPool.get(str(realQQ), '默认')
    
    result = await LotteryService.add_custom_item(
        userId=userId,
        item_name=itemName,
        rare_rank=rare,
        pool_name=poolName,
        detail=itemDetail
    )
    
    if result['success']:
        output = "添加成功！"
        output += "注意：你添加的物品没有简介。" if not itemDetail else ""
        await send_finish(matcher, output)
    else:
        if result['error'] == 'EXIST':
            await send_finish(matcher, '此物品名已经存在!')
        elif result['error'] == 'INSUFFICIENT_KUSA':
            await send_finish(matcher, '你不够草^_^')
        elif result['error'] == 'MODERATION_FAILED':
            await send_finish(matcher, '内容审核未通过，请修改后重试')
        elif result['error'] == 'MODERATION_API_ERROR':
            await send_finish(matcher, '内容审核功能异常，暂时无法新增物品')
        else:
            await send_finish(matcher, f'添加失败：{result.get("message", "未知错误")}')


物品仓库_cmd = on_command('物品仓库', priority=5, block=True)

@物品仓库_cmd.handle()
async def handle_物品仓库(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    arg = args.extract_plain_text().strip()
    level, poolName = await _getLevelAndPoolName(arg)
    itemStorageList = await drawItemDB.getItemsWithStorage(userId, rareRank=level, poolName=poolName)
    if not itemStorageList:
        poolInfo = f'{poolName}奖池' if poolName else ''
        levelInfo = f'{itemRareDescribe[level]}等级' if level is not None else ''
        await send_finish(物品仓库_cmd, f'{poolInfo}{levelInfo}暂无可抽取物品^ ^')
        return

    outputStr, replied = '', False
    if level is None:
        groupedData = groupby(itemStorageList, key=lambda x: x.rareRank)
        for nowLevel, levelItemIterator in groupedData:
            levelItems = list(levelItemIterator)
            levelOwnItems = [item for item in levelItems if item.storage]
            if levelOwnItems:
                outputStr += f'{itemRareDescribe[nowLevel]}({len(levelOwnItems)}/{len(levelItems)}):'
                if len(levelOwnItems) > drawConfig['itemHideAmount']:
                    outputStr += ' ---隐藏了过长的物品列表--- \n'
                    continue
                outputStr += ','.join([f' {item.name}*{item.storage[0].amount}' for item in levelOwnItems]) + '\n'
        outputStr = outputStr[:-1]
    else:
        ownItem = [item for item in itemStorageList if item.storage]
        if ownItem:
            pageSize = 100
            totalPages = (len(ownItem) + pageSize - 1) // pageSize
            
            if len(ownItem) > pageSize:
                set_pagination_state(str(userId), 'warehouse', {
                    'level': level,
                    'poolName': poolName,
                    'items': [{'name': item.name, 'amount': item.storage[0].amount} for item in ownItem],
                    'current_page': 1,
                    'total_pages': totalPages,
                    'page_size': pageSize
                })
            
            displayItems = ownItem[:pageSize]
            outputStr += f'{itemRareDescribe[level]}({len(ownItem)}/{len(itemStorageList)}):'
            outputStr += ','.join([f' {item.name}*{item.storage[0].amount}' for item in displayItems])
            
            if len(ownItem) > pageSize:
                outputStr += f'\n(第1/{totalPages}页，输入!下一页查看下一页)'

    if not outputStr and not replied:
        argExistInfo = '在' if level is not None or poolName else ''
        poolInfo = f'{poolName}奖池' if poolName else ''
        levelInfo = f'{itemRareDescribe[level]}等级' if level is not None else ''
        outputStr = f'{argExistInfo}{poolInfo}{levelInfo}暂未抽到任何物品^ ^'
    await send_finish(物品仓库_cmd, outputStr)


物品详情_cmd = on_command('物品详情', priority=5, block=True)

@物品详情_cmd.handle()
async def handle_物品详情(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()
    if '祝福' in stripped_arg:
        return
    item = await drawItemDB.getItemByName(stripped_arg)
    if not item:
        await _itemSearch(event, args, 物品详情_cmd)
        return
    itemStorage = await drawItemDB.getSingleItemStorage(userId, item.id)

    outputStr = f'[{itemRareDescribe[item.rareRank]}]{item.name}'
    outputStr += f'\n持有数：{itemStorage.amount}' if itemStorage else ''
    outputStr += f'\n物品说明：{item.detail}' if item.detail else '\n暂无物品说明。'
    if item.authorId:
        author = await userDB.getUnifiedUser(item.authorId)
        author_qq = author.realQQ if author else "未知"
        outputStr += f'\n创作者：{author_qq}'
    outputStr += f'\n所属奖池：{item.pool}'
    personCount, numberCount = await drawItemDB.getItemStorageCount(item.id)
    outputStr += f'\n已被{personCount}人抽中{numberCount}次！' if personCount else '\n还没有人抽到这个物品= ='
    await send_finish(物品详情_cmd, outputStr)


物品搜索_cmd = on_command('物品搜索', priority=5, block=True)

@物品搜索_cmd.handle()
async def handle_物品搜索(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    await _itemSearch(event, args, 物品搜索_cmd)


async def _itemSearch(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message, matcher):
    """搜索物品（内部辅助函数）"""
    userId = await get_user_id(event, auto_create=True)
    strippedArg = args.extract_plain_text().strip()
    if not strippedArg:
        await send_finish(matcher, '没有搜索关键词呢^ ^')
        return
    
    pageSize = 12
    result = await LotteryService.search_item(keyword=strippedArg, page_size=pageSize)
    
    if result['count'] == 0:
        await send_finish(matcher, '没有找到该物品^ ^（如果需要查看生草系统道具信息，请使用!查询）')
        return
    
    totalPages = (result['count'] + pageSize - 1) // pageSize
    
    if result['count'] > pageSize:
        set_pagination_state(str(userId), 'search', {
            'keyword': strippedArg,
            'current_page': 1,
            'total_pages': totalPages,
            'page_size': pageSize
        })
    
    output = '你要找的是不是：\n'
    output += '\n'.join(f'[{item["rare"]}]{item["name"]}' for item in result['items'])
    
    if result['count'] > pageSize:
        output += f'\n(第1/{totalPages}页，共{result["count"]}件物品，输入!下一页查看下一页)'
    else:
        output += f'\n(共{result["count"]}件物品)'
    
    await send_finish(matcher, output)


# 注册物品仓库翻页处理器
async def handle_warehouse_next_page(user_id: str, state: dict, next_page: int) -> str:
    """处理物品仓库翻页"""
    items = state['items']
    page_size = state['page_size']
    total_pages = state['total_pages']
    
    start_idx = (next_page - 1) * page_size
    end_idx = min(start_idx + page_size, len(items))
    page_items = items[start_idx:end_idx]
    
    level = state['level']
    output = f'{itemRareDescribe[level]}({len(items)}件):'
    output += ','.join([f' {item["name"]}*{item["amount"]}' for item in page_items])
    
    if next_page < total_pages:
        output += f'\n(第{next_page}/{total_pages}页，输入!下一页查看下一页)'
    else:
        output += f'\n(第{next_page}/{total_pages}页，最后一页)'
    
    return output


# 注册物品搜索翻页处理器
async def handle_search_next_page(user_id: str, state: dict, next_page: int) -> str:
    """处理物品搜索翻页"""
    keyword = state['keyword']
    page_size = state['page_size']
    total_pages = state['total_pages']
    
    # 重新搜索获取下一页
    result = await LotteryService.search_item(keyword=keyword, page=next_page, page_size=page_size)
    
    if not result['items']:
        return '没有更多结果了'
    
    output = '你要找的是不是：\n'
    output += '\n'.join(f'[{item["rare"]}]{item["name"]}' for item in result['items'])
    
    if next_page < total_pages:
        output += f'\n(第{next_page}/{total_pages}页，共{result["count"]}件物品，输入!下一页查看下一页)'
    else:
        output += f'\n(第{next_page}/{total_pages}页，共{result["count"]}件物品，最后一页)'
    
    return output


# 注册自制物品列表翻页处理器
async def handle_self_made_items_next_page(user_id: str, state: dict, next_page: int) -> str:
    """处理自制物品列表翻页"""
    items = state['items']
    page_size = state['page_size']
    total_pages = state['total_pages']
    level = state['level']
    
    start_idx = (next_page - 1) * page_size
    end_idx = min(start_idx + page_size, len(items))
    page_items = items[start_idx:end_idx]
    
    output = f'{itemRareDescribe[level]}({len(items)}件):'
    output += ','.join([f' {item["name"]}' for item in page_items])
    
    if next_page < total_pages:
        output += f'\n(第{next_page}/{total_pages}页，输入!下一页或!上一页翻页)'
    else:
        output += f'\n(第{next_page}/{total_pages}页，最后一页)'
    
    return output


# 注册处理器
register_pagination_handler('warehouse', handle_warehouse_next_page)
register_pagination_handler('search', handle_search_next_page)
register_pagination_handler('self_made_items', handle_self_made_items_next_page)


物品修改_cmd = on_command('物品修改', priority=5, block=True)

@物品修改_cmd.handle()
async def handle_物品修改(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()
    itemName, itemDetail = nameDetailSplit(stripped_arg)
    
    result = await LotteryService.update_item_detail(
        userId=userId,
        item_name=itemName,
        detail=itemDetail
    )
    
    if result['success']:
        await send_finish(物品修改_cmd, '修改成功！')
    else:
        if result['error'] == 'ITEM_NOT_FOUND':
            await send_finish(物品修改_cmd, '没有找到该物品^ ^')
        elif result['error'] == 'NOT_AUTHOR':
            await send_finish(物品修改_cmd, '你不是该物品的作者，无法修改物品说明^ ^')
        elif result['error'] == 'MODERATION_FAILED':
            await send_finish(物品修改_cmd, '内容审核未通过，请修改后重试')
        elif result['error'] == 'MODERATION_API_ERROR':
            await send_finish(物品修改_cmd, '内容审核功能异常，暂时无法修改物品')
        else:
            await send_finish(物品修改_cmd, f'修改失败：{result.get("message", "未知错误")}')


物品删除_cmd = on_command('物品删除', priority=5, block=True)

@物品删除_cmd.handle()
async def handle_物品删除(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    itemName = args.extract_plain_text().strip()
    item = await drawItemDB.getItemByName(itemName)
    if not item:
        await send_finish(物品删除_cmd, '没有找到该物品^ ^')
        return
    if item.authorId != userId:
        await send_finish(物品删除_cmd, '你不是该物品的作者，无法删除物品^ ^')
        return

    await drawItemDB.deleteItem(item)
    await send_finish(物品删除_cmd, '删除成功！')


自制物品列表_cmd = on_command('自制物品列表', priority=5, block=True)

@自制物品列表_cmd.handle()
async def handle_自制物品列表(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    strippedArg = args.extract_plain_text().strip()
    level, poolName = await _getLevelAndPoolName(strippedArg)
    itemList = await drawItemDB.getItemListByAuthorId(userId, level, poolName)
    if not itemList:
        argExistInfo = '在' if level is not None or poolName else ''
        poolInfo = f'{poolName}奖池' if poolName else ''
        levelInfo = f'{itemRareDescribe[level]}等级' if level is not None else ''
        await send_finish(自制物品列表_cmd, f'{argExistInfo}{poolInfo}{levelInfo}暂未添加任何物品^ ^')
        return

    outputStr = ""
    if level is None:
        groupedData = groupby(itemList, key=lambda x: x.rareRank)
        for nowLevel, levelItemIterator in groupedData:
            levelItems = list(levelItemIterator)
            if levelItems:
                outputStr += f'{itemRareDescribe[nowLevel]}:'
                if len(levelItems) > drawConfig['itemHideAmount'] * 2:
                    outputStr += ' ---隐藏了过长的自制物品列表--- \n'
                    continue
                outputStr += ','.join([f' {item.name}' for item in levelItems]) + '\n'
        outputStr = outputStr[:-1]
    else:
        userId_str = str(userId)
        pageSize = 150
        totalPages = (len(itemList) + pageSize - 1) // pageSize
        
        if len(itemList) > pageSize:
            set_pagination_state(userId_str, 'self_made_items', {
                'user_id': userId_str,
                'level': level,
                'pool_name': poolName,
                'items': [{'name': item.name} for item in itemList],
                'current_page': 1,
                'total_pages': totalPages,
                'page_size': pageSize
            })
        
        outputStr += f'{itemRareDescribe[level]}:'
        displayItems = itemList[:pageSize]
        outputStr += ','.join([f' {item.name}' for item in displayItems])
        
        if len(itemList) > pageSize:
            outputStr += f'\n(第1/{totalPages}页，输入!下一页或!上一页翻页)'

    await send_finish(自制物品列表_cmd, outputStr)


奖池列表_cmd = on_command('奖池列表', aliases={'物品池列表'}, priority=5, block=True)

@奖池列表_cmd.handle()
async def handle_奖池列表(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    pools = await LotteryService.get_pool_list()
    
    if not pools:
        await send_finish(奖池列表_cmd, '暂无任何奖池^ ^')
        return
    
    output = '当前奖池列表：'
    output += '，'.join(pools)
    
    await send_finish(奖池列表_cmd, output)


最新物品_cmd = on_command('最新物品', priority=5, block=True)

@最新物品_cmd.handle()
async def handle_最新物品(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    userId = await get_user_id(event, auto_create=True)
    prescientAmount = await usefulItemDB.getItemAmount(userId, '侦察凭证')
    if not prescientAmount:
        await send_finish(最新物品_cmd, '你没有侦察凭证，无法查看最新物品^ ^')
        return
    await usefulItemDB.changeItemAmount(userId, '侦察凭证', -1)

    latestItems = await LotteryService.get_latest_items(limit=5)
    
    output = '当前抽奖系统的最新物品（倒序）：\n'
    for item in latestItems:
        output += f'[{item["rare"]}]{item["name"]}\n'
    
    await send_finish(最新物品_cmd, output[:-1])


async def _getLevelAndPoolName(strippedArg):
    """解析等级和奖池名称（内部辅助函数）"""
    if not strippedArg:
        return None, None

    argList = strippedArg.split()
    itemRareList = [rare.lower() for rare in itemRareDescribe]
    if len(argList) == 1:
        if argList[0].lower() in itemRareList:
            levelStr, poolName = argList[0], None
        else:
            poolName, levelStr = argList[0], None
    else:
        if argList[0].lower() in itemRareList:
            levelStr, poolName = argList
        elif argList[1].lower() in itemRareList:
            poolName, levelStr = argList
        else:
            return None, None
    level = itemRareList.index(levelStr.lower()) if levelStr else None
    poolName = poolName if await drawItemDB.isPoolNameExist(poolName) else None
    return level, poolName
