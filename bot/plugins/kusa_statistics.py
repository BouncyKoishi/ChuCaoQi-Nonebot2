import core.db.kusa_system as baseDB
import core.db.kusa_item as itemDB
import core.db.kusa_field as fieldDB
import core.db.user as userDB
from datetime import datetime
from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot
from nonebot.params import CommandArg
from nonebot.adapters import Message
from kusa_base import is_super_admin, parse_user_identifier
from functools import wraps
from core.services import WarehouseService, StatisticService, admin_service
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
    outputStr += "SET_DONATION [userId] [金额] (qq/ifd/wx/other) 设置捐赠金额\n"
    outputStr += "SET_NAME [userId] (名字) 设置名称（默认从昵称取）"
    await send_finish(admin_help_cmd, outputStr)


total_kusa_cmd = on_command('TOTAL_KUSA', priority=5, block=True)

@total_kusa_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_total_kusa(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    result = await StatisticService.get_total_stats()
    
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
    rank_list = await StatisticService.get_kusa_rank(limit=25)
    
    output = "草排行榜：\n"
    for item in rank_list:
        display = item['name'] if item['name'] else (item['qq'] or str(item['userId']))
        output += f"{item['rank']}. {display}: {item['kusa']:,}\n"
    
    await send_finish(kusa_rank_cmd, output[:-1])


factory_rank_cmd = on_command('FACTORY_RANK', priority=5, block=True)

@factory_rank_cmd.handle()
@permissionCheck(onlyAdmin=False, costCredentials=1)
async def handle_factory_rank(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    rank_list = await itemDB.getItemsByType("工厂")
    output = "工厂数排行榜：\n"
    for i, info in enumerate(rank_list):
        user = await baseDB.getKusaUser(info.user_id)
        user_qq = await userDB.getRealQQByUserId(info.user_id)
        user_display = user.name if user.name else (user_qq or str(user.user_id))
        output += f'{i + 1}. {user_display}: {info.amount}\n'
    
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
    
    result = await StatisticService.get_user_stats(userId=userId)
    
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
    """获取草精排行榜（基于 StatisticService，无蓝图过滤）

    调用 StatisticService.get_total_adv_kusa_rank(limit=None) 获取完整排行榜，
    再在调用端计算"我的排名"上下文（上一名/下一名差距）。
    """
    rank_list = await StatisticService.get_total_adv_kusa_rank(
        limit=None,
        level_max=levelMax,
        show_inactive=showInactiveUsers,
        show_subaccount=showSubAccount,
        use_cache=False
    )

    def _display(item):
        if item.get('name'):
            return item['name']
        if item.get('qq'):
            return item['qq']
        return str(item['userId'])

    outputStr = "\n"
    for item in rank_list[:25]:
        outputStr += f"{item['rank']}. {_display(item)}: {item['totalAdvKusa']}\n"

    if userId:
        user_index = -1
        for i, item in enumerate(rank_list):
            if item['userId'] == userId:
                user_index = i
                break

        if user_index != -1:
            user_item = rank_list[user_index]
            user_kusa_adv = user_item['totalAdvKusa']
            outputStr += f"\n您的排名：{user_item['rank']}\n"
            if user_index > 0:
                prev_item = rank_list[user_index - 1]
                outputStr += f"距上一名 {_display(prev_item)} 还差 {prev_item['totalAdvKusa'] - user_kusa_adv}草精\n"
            if user_index < len(rank_list) - 1:
                next_item = rank_list[user_index + 1]
                outputStr += f"下一名 {_display(next_item)} 距您 {user_kusa_adv - next_item['totalAdvKusa']}草精\n"
        else:
            outputStr += "\n您不在这个排行榜上^ ^\n"
    return outputStr[:-1]


async def getKusaAdv(user):
    nowKusaAdv = user.advKusa
    titleKusaAdv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0
    advItemTradeRecord = await baseDB.getTradeRecord(userId=user.user_id, costItemName='草之精华')
    itemKusaAdv = sum(record.costItemAmount for record in advItemTradeRecord if '升级' not in (record.tradeType or ''))
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
        user_qq = await userDB.getRealQQByUserId(userId)
        user_display = user.name if user.name else (user_qq or str(user.user_id))
        output = f"生草打分榜({user_display})：\n"
        for i, rank in enumerate(rank_list):
            create_time = datetime.fromtimestamp(rank.createTimeTs)
            time_str = create_time.strftime("%Y-%m-%d %H:%M")
            output += f"{i + 1}. {rank.kusaResult}草({time_str})\n"
    else:
        rank_list = await StatisticService.get_kusa_once_ranking(limit=25)
        output = "生草打分榜：\n"
        for rank in rank_list:
            create_time = datetime.fromtimestamp(rank['createTimeTs'])
            time_str = create_time.strftime("%Y-%m-%d %H:%M")
            user_display = rank['name'] if rank['name'] else (rank['qq'] or str(rank['userId']))
            output += f"{rank['rank']}. {user_display}：{rank['kusaResult']}草({time_str})\n"

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
        user_qq = await userDB.getRealQQByUserId(userId)
        user_display = user.name if user.name else (user_qq or str(user.user_id))
        output = f"草精打分榜({user_display})：\n"
        for i, rank in enumerate(rank_list):
            create_time = datetime.fromtimestamp(rank.createTimeTs)
            time_str = create_time.strftime("%Y-%m-%d %H:%M")
            output += f"{i + 1}. {rank.advKusaResult}草精({time_str})\n"
    else:
        rank_list = await StatisticService.get_adv_kusa_once_ranking(limit=25)
        output = "草精打分榜：\n"
        for rank in rank_list:
            create_time = datetime.fromtimestamp(rank['createTimeTs'])
            time_str = create_time.strftime("%Y-%m-%d %H:%M")
            user_display = rank['name'] if rank['name'] else (rank['qq'] or str(rank['userId']))
            output += f"{rank['rank']}. {user_display}：{rank['advKusaResult']}草精({time_str})\n"

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

    result = await admin_service.give_title(userId, title)
    if result.get('success'):
        await send_finish(give_title_cmd, result['message'])
    else:
        # 兼容原提示文案
        err = result.get('error', '操作失败')
        if err == '该称号不存在':
            err = '你想给出的称号不存在'
        await send_finish(give_title_cmd, err)


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

    result = await admin_service.set_donation(userId, float(amount), source)
    if result.get('success'):
        await send_finish(set_donation_cmd, f'成功添加用户{userId}通过{source}捐赠{amount}元的记录')
        for title_name in result.get('autoTitles', []):
            await send_finish(set_donation_cmd, f'为用户{userId}自动添加了称号"{title_name}"')
    else:
        await send_finish(set_donation_cmd, result.get('error', '操作失败'))


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

    # 未传 name 时从用户昵称取默认值（指令交互特有逻辑）
    if not name:
        user = await baseDB.getKusaUser(userId)
        if user and user.name:
            name = user.name
        else:
            await send_finish(set_name_cmd, "无法获取用户昵称")
            return

    result = await WarehouseService.change_name(userId, name)
    if result.get('success'):
        await send_finish(set_name_cmd, f'成功修改用户{userId}的名字为{name}')
    else:
        await send_finish(set_name_cmd, '修改失败')
