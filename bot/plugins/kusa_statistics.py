import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB
import dbConnection.kusa_field as fieldDB
from datetime import datetime
from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot
from nonebot.params import CommandArg
from nonebot.adapters import Message
from kusa_base import is_super_admin, config, parse_user_identifier
from functools import wraps
from services import WarehouseService
from multi_platform import get_user_id,  send_finish
from typing import Union


def permissionCheck(onlyAdmin=False, costCredentials=0):
    def decorator(func):
        @wraps(func)
        async def wrapper(event: Union[OneBotV11MessageEvent, QQMessageEvent], *args, **kwargs):
            userId = await get_user_id(event, auto_create=True)
            superAdmin = await is_super_admin(userId)
            if superAdmin:
                return await func(event, *args, **kwargs)
            if onlyAdmin and not superAdmin:
                return
            amount = await itemDB.getItemAmount(userId, "侦察凭证")
            if amount >= costCredentials:
                await itemDB.changeItemAmount(userId, '侦察凭证', -costCredentials)
                return await func(event, *args, **kwargs)
            else:
                await send_finish(admin_help_cmd, f'查看该信息需要消耗{costCredentials}个侦察凭证，你的侦察凭证不足^ ^')
                return
        return wrapper
    return decorator


admin_help_cmd = on_command("admin_help", priority=5, block=True)

@admin_help_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_admin_help(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    outputStr = "管理员命令列表：\n"
    outputStr += "TOTAL_KUSA 系统总草数\n"
    outputStr += "KUSA_RANK 草排行榜\n"
    outputStr += "FACTORY_RANK 工厂数排行榜\n"
    outputStr += "KUSA_ADV [userId] 总草精数统计\n"
    outputStr += "KUSA_ADV_RANK 总草精排行榜\n"
    outputStr += "TITLE_LIST 系统称号列表\n"
    outputStr += "GIVE_TITLE [userId] [称号] 给予称号\n"
    outputStr += "SET_DONATION [userId] [金额] (qq/ifd) 设置捐赠金额\n"
    outputStr += "SET_NAME [userId] (名字) 设置名称（默认从昵称取）"
    await send_finish(admin_help_cmd, outputStr)


total_kusa_cmd = on_command('TOTAL_KUSA', priority=5, block=True)

@total_kusa_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_total_kusa(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    result = await WarehouseService.get_total_stats()
    
    await send_finish(total_kusa_cmd,
        f'系统总草数: {result["totalKusa"]}\n'
        f'可用总草数: {result["availableKusa"]}\n'
        f'历史总草精数: {result["totalAdvKusa"]}\n'
        f'可用总草精数: {result["availableAdvKusa"]}'
    )


kusa_rank_cmd = on_command('KUSA_RANK', priority=5, block=True)

@kusa_rank_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_kusa_rank(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    rank_list = await WarehouseService.get_kusa_rank(limit=25)
    
    output = "草排行榜：\n"
    for item in rank_list:
        output += f"{item['rank']}. {item['name']}: {item['kusa']:,}\n"
    
    await send_finish(kusa_rank_cmd, output[:-1])


factory_rank_cmd = on_command('FACTORY_RANK', priority=5, block=True)

@factory_rank_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_factory_rank(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    factory_list = await itemDB.getStoragesOrderByAmountDesc("生草工厂")
    
    output = "工厂数排行榜：\n"
    for i, info in enumerate(factory_list[:25]):
        user = await baseDB.getKusaUser(info.user_id)
        user_name = user.name if user.name else str(user.user_id)
        output += f'{i + 1}. {user_name}: {info.amount}\n'
    
    await send_finish(factory_rank_cmd, output[:-1])


kusa_adv_cmd = on_command('KUSA_ADV', priority=5, block=True)

@kusa_adv_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_kusa_adv(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId_str = args.extract_plain_text().strip()
    self_userId = await get_user_id(event, auto_create=True)
    
    if not userId_str:
        userId = self_userId
    else:
        # 使用通用函数解析用户标识符
        userId = await parse_user_identifier(userId_str)
        if not userId:
            await send_finish(kusa_adv_cmd, "用户不存在")
            return
    
    result = await WarehouseService.get_user_stats(userId=userId)
    
    if 'error' in result:
        await send_finish(kusa_adv_cmd, "用户不存在")
        return
    
    await send_finish(kusa_adv_cmd,
        f"{result['userId']}草精情况：\n"
        f"现有 {result['nowAdvKusa']}\n"
        f"信息员等级消费 {result['titleAdvKusa']}\n"
        f"道具消费 {result['itemAdvKusa']}\n"
        f"总计 {result['totalAdvKusa']}"
    )


草精排行榜_cmd = on_command('草精排行榜', priority=5, block=True)

@草精排行榜_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=10)
async def handle_草精排行榜(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    userId = await get_user_id(event, auto_create=True)
    outputStr = '总草精排行榜：' + await getKusaAdvRank(userId=userId)
    await send_finish(草精排行榜_cmd, outputStr)


草精新星榜_cmd = on_command('草精新星榜', priority=5, block=True)

@草精新星榜_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=10)
async def handle_草精新星榜(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    userId = await get_user_id(event, auto_create=True)
    outputStr = '草精新星排行榜：' + await getKusaAdvRank(userId=userId, levelMax=6)
    await send_finish(草精新星榜_cmd, outputStr)


kusa_adv_rank_cmd = on_command('KUSA_ADV_RANK', priority=5, block=True)

@kusa_adv_rank_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_kusa_adv_rank(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    strippedArg = args.extract_plain_text().strip()
    showInactiveUsers = True if '-i' in strippedArg else False
    showSubAccount = True if '-s' in strippedArg else False
    levelMax = 10
    if '--l' in strippedArg:
        try:
            levelMax = int(strippedArg.split('--l')[1].strip().split()[0])
        except (IndexError, ValueError):
            await send_finish(kusa_adv_rank_cmd, "Invalid levelMax value. Please provide a valid integer after --l.")
            return
    outputStr = '草精排行榜（自定义）：' + await getKusaAdvRank(userId, levelMax, showInactiveUsers, showSubAccount)
    await send_finish(kusa_adv_rank_cmd, outputStr)


async def getKusaAdvRank(userId=None, levelMax: int = 10, showInactiveUsers: bool = False, showSubAccount: bool = True) -> str:
    """获取草精排行榜（优化版本）"""
    from datetime import datetime, timedelta
    from dbConnection.user import getUnifiedUsersByIds
    from dbConnection.kusa_item import getItemStorageInfo

    userList = await baseDB.getAllKusaUser()

    all_trade_records = await baseDB.getAllTradeRecordsByCostItem('草之精华')
    user_trade_amount = {}
    for record in all_trade_records:
        uid = record.user_id
        user_trade_amount[uid] = user_trade_amount.get(uid, 0) + record.costItemAmount

    users_with_blueprint = set()
    for user in userList:
        try:
            storage = await getItemStorageInfo(user.user_id, '生草工业园区蓝图')
            if storage and storage.amount > 0:
                users_with_blueprint.add(user.user_id)
        except:
            pass

    if not showInactiveUsers:
        cutoff_time = datetime.now() - timedelta(days=90)
        cutoff_timestamp = cutoff_time.timestamp()
        from dbConnection.kusa_field import getKusaHistory
        recent_kusa_records = await getKusaHistory(cutoff_timestamp)
        active_users = {record.user_id for record in recent_kusa_records}
    else:
        active_users = None

    unified_user_ids = [user.user_id for user in userList]
    unified_users = await getUnifiedUsersByIds(unified_user_ids)
    unified_user_map = {u.id: u for u in unified_users}
    
    userAdvKusaDict = {}
    for user in userList:
        if user.vipLevel > levelMax:
            continue
        unified_user = unified_user_map.get(user.user_id)
        if not showSubAccount and unified_user and unified_user.relatedUserId:
            continue
        if user.user_id not in users_with_blueprint:
            continue
        if not showInactiveUsers and active_users is not None:
            if user.user_id not in active_users:
                continue
        
        nowKusaAdv = user.advKusa or 0
        titleKusaAdv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0
        itemKusaAdv = user_trade_amount.get(user.user_id, 0)
        total = nowKusaAdv + titleKusaAdv + itemKusaAdv
        userAdvKusaDict[user] = total
    
    userAdvKusaDict = sorted(userAdvKusaDict.items(), key=lambda x: x[1], reverse=True)
    outputStr = "\n"

    for i in range(min(len(userAdvKusaDict), 25)):
        user = userAdvKusaDict[i][0]
        userName = user.name if user.name else str(user.user_id)
        outputStr += f'{i + 1}. {userName}: {userAdvKusaDict[i][1]}\n'
    if userId:
        # 获取个人排名，上一名及草精差距，下一名及草精差距
        userRank, userKusaAdv, prevInfo, nextInfo = -1, 0, None, None
        for i, (user, kusaAdv) in enumerate(userAdvKusaDict):
            if user.user_id == userId:
                userRank, userKusaAdv = i + 1, kusaAdv
                if i > 0:
                    prevInfo = (userAdvKusaDict[i - 1][0], userAdvKusaDict[i - 1][1])
                if i < len(userAdvKusaDict) - 1:
                    nextInfo = (userAdvKusaDict[i + 1][0], userAdvKusaDict[i + 1][1])
                break

        if userRank != -1:
            outputStr += f"\n您的排名：{userRank}\n"
            if prevInfo:
                prevName = prevInfo[0].name if prevInfo[0].name else str(prevInfo[0].user_id)
                outputStr += f"距上一名 {prevName} 还差 {prevInfo[1] - userKusaAdv}草精\n"
            if nextInfo:
                nextName = nextInfo[0].name if nextInfo[0].name else str(nextInfo[0].user_id)
                outputStr += f"下一名 {nextName} 距您 {userKusaAdv - nextInfo[1]}草精\n"
        else:
            outputStr += "\n您不在这个排行榜上^ ^\n"
    return outputStr[:-1]


async def getKusaAdv(user):
    nowKusaAdv = user.advKusa
    titleKusaAdv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0
    advItemTradeRecord = await baseDB.getTradeRecord(userId=user.user_id, costItemName='草之精华')
    itemKusaAdv = sum(record.costItemAmount for record in advItemTradeRecord)
    return nowKusaAdv + titleKusaAdv + itemKusaAdv, nowKusaAdv, titleKusaAdv, itemKusaAdv


生草打分榜_cmd = on_command('生草打分榜', priority=5, block=True)

@生草打分榜_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=5)
async def handle_生草打分榜(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    self_mode = '-self' in args.extract_plain_text()
    
    if self_mode:
        rank_list = await fieldDB.kusaOnceRanking(userId=userId)
        user = await baseDB.getKusaUser(userId)
        user_name = user.name if user.name else str(user.user_id)
        output = f"生草打分榜({user_name})：\n"
    else:
        rank_list = await fieldDB.kusaOnceRanking()
        output = "生草打分榜：\n"
    
    for i, rank in enumerate(rank_list):
        create_time = datetime.fromtimestamp(rank.createTimeTs)
        time_str = create_time.strftime("%Y-%m-%d %H:%M")
        if self_mode:
            output += f"{i + 1}. {rank.kusaResult}草({time_str})\n"
        else:
            rank_user = await baseDB.getKusaUser(rank.user_id)
            user_name = rank_user.name if rank_user.name else str(rank_user.user_id)
            output += f"{i + 1}. {user_name}：{rank.kusaResult}草({time_str})\n"
    
    await send_finish(生草打分榜_cmd, output[:-1])


草精打分榜_cmd = on_command('草精打分榜', priority=5, block=True)

@草精打分榜_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=5)
async def handle_草精打分榜(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event, auto_create=True)
    self_mode = '-self' in args.extract_plain_text()
    
    if self_mode:
        rank_list = await fieldDB.kusaAdvOnceRanking(userId=userId)
        user = await baseDB.getKusaUser(userId)
        user_name = user.name if user.name else str(user.user_id)
        output = f"草精打分榜({user_name})：\n"
    else:
        rank_list = await fieldDB.kusaAdvOnceRanking()
        output = "草精打分榜：\n"
    
    for i, rank in enumerate(rank_list):
        create_time = datetime.fromtimestamp(rank.createTimeTs)
        time_str = create_time.strftime("%Y-%m-%d %H:%M")
        if self_mode:
            output += f"{i + 1}. {rank.advKusaResult}草精({time_str})\n"
        else:
            rank_user = await baseDB.getKusaUser(rank.user_id)
            user_name = rank_user.name if rank_user.name else str(rank_user.user_id)
            output += f"{i + 1}. {user_name}：{rank.advKusaResult}草精({time_str})\n"
    
    await send_finish(草精打分榜_cmd, output[:-1])


title_list_cmd = on_command('TITLE_LIST', priority=5, block=True)

@title_list_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_title_list(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    item_titles = await itemDB.getItemsByType("称号")
    
    output = "系统称号列表：\n"
    output += "\n".join([item.name for item in item_titles])
    
    await send_finish(title_list_cmd, output)


give_title_cmd = on_command('GIVE_TITLE', priority=5, block=True)

@give_title_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_give_title(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    userId_str, title = stripped_arg.split(" ")
    
    # 使用通用函数解析用户标识符
    userId = await parse_user_identifier(userId_str)
    if not userId:
        await send_finish(give_title_cmd, "用户不存在")
        return
    
    user = await baseDB.getKusaUser(userId)
    if not user:
        await send_finish(give_title_cmd, "用户不存在")
        return
    
    item = await itemDB.getItem(title)
    if not item or item.type != '称号':
        await send_finish(give_title_cmd, '你想给出的称号不存在')
        return
    
    await itemDB.changeItemAmount(userId, title, 1)
    await send_finish(give_title_cmd, f'成功赠送用户{userId}称号{title}')


set_donation_cmd = on_command('SET_DONATION', priority=5, block=True)

@set_donation_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_set_donation(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    parts = stripped_arg.split(" ")
    userId_str = parts[0]
    amount = parts[1] if len(parts) > 1 else "0"
    source = parts[2] if len(parts) > 2 else "qq"
    
    # 使用通用函数解析用户标识符
    userId = await parse_user_identifier(userId_str)
    if not userId:
        await send_finish(set_donation_cmd, "用户不存在")
        return
    
    user = await baseDB.getKusaUser(userId)
    if not user:
        await send_finish(set_donation_cmd, "用户不存在")
        return
    
    await baseDB.setDonateRecord(userId, float(amount), source)
    await send_finish(set_donation_cmd, f'成功添加用户{userId}通过{source}捐赠{amount}元的记录')
    
    total_donate = await baseDB.getDonateAmount(userId)
    if total_donate >= 20:
        have_title = await itemDB.getItemAmount(userId, "投喂者")
        if not have_title:
            await itemDB.changeItemAmount(userId, "投喂者", 1)
            await send_finish(set_donation_cmd, f'为用户{userId}自动添加了称号"投喂者"')


set_name_cmd = on_command('SET_NAME', priority=5, block=True)

@set_name_cmd.handle()
@permissionCheck(onlyAdmin=True)
async def handle_set_name(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    userId_str, name = stripped_arg.split(" ") if " " in stripped_arg else (stripped_arg, None)
    
    # 使用通用函数解析用户标识符
    userId = await parse_user_identifier(userId_str)
    if not userId:
        await send_finish(set_name_cmd, "用户不存在")
        return
    
    if not name:
        user = await baseDB.getKusaUser(userId)
        if user and user.name:
            name = user.name
        else:
            await send_finish(set_name_cmd, "无法获取用户昵称")
            return
    
    user = await baseDB.getKusaUser(userId)
    if not user:
        await send_finish(set_name_cmd, "用户不存在")
        return
    
    await baseDB.changeKusaUserName(userId, name)
    await send_finish(set_name_cmd, f'成功修改用户{userId}的名字为{name}')
