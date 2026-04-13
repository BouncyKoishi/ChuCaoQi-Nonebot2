"""
物品系统插件 - NoneBot2 版本
包含商店、购买、出售、转让、启用/禁用物品等功能
"""

import re
import codecs
from typing import Union
from utils import convertNumStrToInt
from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot
from nonebot.params import CommandArg
from nonebot.adapters import Message, Bot

from kusa_base import send_private_msg
import dbConnection.kusa_system as base_db
import dbConnection.kusa_item as item_db
from services import ItemService
from . import scheduler
from multi_platform import (
    get_user_id,
    get_real_qq_by_event,
    is_onebot_v11_event,
    is_qq_event,
    send_finish,
)


# ==================== 商店命令 ====================

shop_cmd = on_command("商店", priority=5, block=True)

@shop_cmd.handle()
async def handle_shop(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理商店命令"""
    await handle_shop_internal(event, args, '草')


adv_shop_cmd = on_command("进阶商店", priority=5, block=True)

@adv_shop_cmd.handle()
async def handle_adv_shop(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理进阶商店命令"""
    await handle_shop_internal(event, args, '草之精华')


building_shop_cmd = on_command("建筑商店", aliases={"核心商店"}, priority=5, block=True)

@building_shop_cmd.handle()
async def handle_building_shop(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理建筑商店命令"""
    await handle_shop_internal(event, args, '自动化核心')


async def handle_shop_internal(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message, price_type: str):
    """商店内部处理逻辑"""
    user_id = await get_user_id(event, auto_create=True)
    arg_text = args.extract_plain_text().strip()
    show_all = '全部' in arg_text or 'all' in arg_text
    
    shop_items = await ItemService.get_shop_list(userId=user_id, shop_type=price_type)
    
    item_price_dict = {}
    for item in shop_items:
        if not show_all:
            if item.get('shopPreItems'):
                pre_items = item['shopPreItems'].split(',')
                pre_met = True
                for pre_item in pre_items:
                    if pre_item.startswith('Lv'):
                        user = await base_db.getKusaUser(int(user_id))
                        if user.vipLevel < int(pre_item[2:]):
                            pre_met = False
                            break
                    else:
                        if not await item_db.getItemAmount(user_id, pre_item):
                            pre_met = False
                            break
                if not pre_met:
                    continue
            if item.get('amountLimit'):
                item_count = await item_db.getItemAmount(user_id, item['name'])
                if item_count >= item['amountLimit']:
                    continue
        item_price_dict[item['name']] = item['actualPrice']
    
    sorted_price_dict = sorted(item_price_dict.items(), key=lambda x: x[1])
    
    if not sorted_price_dict:
        await send_finish(shop_cmd, '当前商店暂无你可以购买的物品！')
        return
    
    output = '全部物品列表：\n' if show_all else '您可以购买的物品：\n'
    output += '\n'.join([f'{name}：{price}{price_type}' for name, price in sorted_price_dict])
    output += '\n可输入"!商店帮助"来查看商店和道具的相关说明'
    await send_finish(shop_cmd, output)


# 商店帮助命令
shop_help_cmd = on_command("商店帮助", priority=5, block=True)

@shop_help_cmd.handle()
async def handle_shop_help(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理商店帮助命令"""
    try:
        with codecs.open('text/生草系统-商店帮助.txt', 'r', 'utf-8') as f:
            await send_finish(shop_help_cmd, f.read().strip())
    except FileNotFoundError:
        await send_finish(shop_help_cmd, '帮助文件未找到')


# 查询命令
query_cmd = on_command("查询", aliases={"道具详情"}, priority=5, block=True)

@query_cmd.handle()
async def handle_query(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理查询命令"""
    user_id = await get_user_id(event, auto_create=True)
    item_name = args.extract_plain_text().strip()
    
    item = await item_db.getItem(item_name)
    if not item:
        await send_finish(query_cmd, '此物品不存在!（如果需要查看抽奖物品信息，请使用!物品详情）')
        return
    
    own_item_info = await item_db.getItemStorageInfo(user_id, item_name)
    own_item_amount = own_item_info.amount if own_item_info else 0
    
    output = f'{item.name}\n'
    if item.amountLimit:
        output += f'拥有数量：{own_item_amount} / {item.amountLimit}\n'
    else:
        output += f'拥有数量：{own_item_amount}\n'
    
    if item.shopPreItems:
        output += f'前置购买条件：{get_pre_item_str(item)}\n'
    
    output += f'基础价格：{item.shopPrice}{item.priceType}\n' if item.shopPrice else '不可从商店购买\n'
    if item.priceRate:
        output += f'当前价格：{get_item_price(item, own_item_amount)}{item.priceType}\n'
        output += f'价格倍率：{item.priceRate}\n'
    if item.sellingPrice:
        output += f'商店售价：{item.sellingPrice}{item.priceType}\n'
    
    output += '可转让 ' if item.isTransferable else '不可转让 '
    output += '可禁用' if item.isControllable else '不可禁用'
    
    if item.isControllable and own_item_info:
        output += f'（当前已{"启用" if own_item_info.allowUse else "禁用"}）'
    output += '\n'
    
    if item.detail:
        output += f'物品说明：{item.detail}\n'
    else:
        output += '暂无物品说明= =\n'
    
    output = output[:-1] if output[-1] == '\n' else output
    await send_finish(query_cmd, output)


# 购买命令
buy_cmd = on_command("购买", priority=5, block=True)

@buy_cmd.handle()
async def handle_buy(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理购买命令"""
    user_id = await get_user_id(event, auto_create=True)
    arg_text = args.extract_plain_text().strip()
    
    get_name_success, item_name, buying_amount = get_item_name_and_amount(arg_text)
    if not get_name_success:
        await send_finish(buy_cmd, '需要物品名！')
        return
    
    item = await item_db.getItem(item_name)
    if not item:
        await send_finish(buy_cmd, '此物品不存在!')
        return
    
    result = await ItemService.buy_item(userId=user_id, item_name=item_name, amount=buying_amount)
    
    if result['success']:
        await send_finish(buy_cmd, result['message'])
    else:
        error_code = result.get('error', 'UNKNOWN')
        if error_code == 'PREREQ_NOT_MET':
            await send_finish(buy_cmd, '你不满足购买此物品的前置条件！')
        elif error_code == 'MAX_AMOUNT':
            await send_finish(buy_cmd, '你已达到此物品的最大数量限制!')
        elif error_code == 'INSUFFICIENT_KUSA':
            await send_finish(buy_cmd, f'你不够{result.get("totalPrice", item.shopPrice)}草^ ^')
        elif error_code == 'INSUFFICIENT_ADV_KUSA':
            await send_finish(buy_cmd, '你的草之精华不足^ ^')
        else:
            await send_finish(buy_cmd, f'购买失败：{result.get("message", "未知错误")}')


# 出售命令
sell_cmd = on_command("出售", priority=5, block=True)

@sell_cmd.handle()
async def handle_sell(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理出售命令"""
    user_id = await get_user_id(event, auto_create=True)
    arg_text = args.extract_plain_text().strip()
    
    get_name_success, item_name, selling_amount = get_item_name_and_amount(arg_text)
    if not get_name_success:
        await send_finish(sell_cmd, '需要物品名！')
        return
    
    item = await item_db.getItem(item_name)
    if not item:
        await send_finish(sell_cmd, '此物品不存在!')
        return
    
    result = await ItemService.sell_item(userId=user_id, item_name=item_name, amount=selling_amount)
    
    if result['success']:
        await send_finish(sell_cmd, result['message'])
    else:
        error_code = result.get('error', 'UNKNOWN')
        if error_code == 'NOT_FOR_SALE':
            await send_finish(sell_cmd, '此物品不能通过商店出售!')
        elif error_code == 'FLOATING_PRICE':
            await send_finish(sell_cmd, '此物品的价格不固定，不能通过商店出售!')
        elif error_code == 'INSUFFICIENT_ITEM':
            await send_finish(sell_cmd, f'你不够{item_name}^ ^')
        else:
            await send_finish(sell_cmd, f'出售失败：{result.get("message", "未知错误")}')


# 转让命令
transfer_cmd = on_command("转让", aliases={"道具转让"}, priority=5, block=True)

@transfer_cmd.handle()
async def handle_transfer(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理转让命令
    
    支持格式：
    - 转让 [物品名] [数量] qq=123456
    - 转让 [物品名] [数量] id=227
    - 当qq和id同时传入时，以id为准
    """
    user_id = await get_user_id(event, auto_create=True)
    real_qq = await get_real_qq_by_event(event)
    arg_text = args.extract_plain_text().strip()
    
    get_name_success, item_name, transfer_amount = get_item_name_and_amount(arg_text)
    
    # 解析qq参数
    qq_number_match = re.search(r'(?<=(QQ|qq)=)\d+', arg_text)
    # 解析id参数
    id_match = re.search(r'(?<=(ID|id)=)\d+', arg_text)
    
    receiver_qq = qq_number_match.group(0) if qq_number_match else None
    receiver_id = int(id_match.group(0)) if id_match else None
    
    if not get_name_success:
        await send_finish(transfer_cmd, '需要物品名！')
        return
    
    # 检查目标用户
    from services.item_service import ItemService
    receiver_user = None
    if receiver_id:
        # 优先使用id
        receiver_user = await ItemService.get_transfer_target_by_id(receiver_id)
    elif receiver_qq:
        # 使用qq
        receiver_user = await ItemService.get_transfer_target_by_qq(receiver_qq)
    else:
        await send_finish(transfer_cmd, '需要被转让人的QQ号(qq=xxx)或用户ID(id=xxx)！')
        return
    
    if not receiver_user:
        await send_finish(transfer_cmd, '你想转让的对象并没有生草账户！')
        return
    
    # 调用ItemService执行转让
    result = await ItemService.transfer_item(
        from_user_id=user_id,
        to_user_id=receiver_user.id,
        item_name=item_name,
        amount=transfer_amount
    )
    
    if not result['success']:
        if result['error'] == 'TARGET_NOT_FOUND':
            await send_finish(transfer_cmd, '你想转让的对象并没有生草账户！')
        elif result['error'] == 'ITEM_NOT_FOUND':
            await send_finish(transfer_cmd, '此物品不存在!')
        elif result['error'] == 'NOT_TRANSFERABLE':
            await send_finish(transfer_cmd, '此物品不能转让!')
        elif result['error'] == 'INSUFFICIENT_ITEM':
            await send_finish(transfer_cmd, f'你不够{item_name}^ ^')
        else:
            await send_finish(transfer_cmd, f'转让失败：{result.get("message", "未知错误")}')
        return
    
    # 显示转让对象（优先显示QQ，如果没有则显示ID）
    target_display = receiver_qq if receiver_qq else str(receiver_id)
    await send_finish(transfer_cmd, f'转让成功！转让了{transfer_amount}个{item_name}给{target_display}。')
    
    # 私聊通知
    if await base_db.getFlagValue(receiver_user.id, '物品转让提示'):
        nickname = ""
        if is_onebot_v11_event(event) and hasattr(event, 'sender') and event.sender:
            nickname = event.sender.nickname or ""
        await send_private_msg(receiver_user.id, f'{nickname}({real_qq})转让了{transfer_amount}个{item_name}给你！')


# 启用命令
enable_cmd = on_command("启用", aliases={"道具启用"}, priority=5, block=True)

@enable_cmd.handle()
async def handle_enable(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理启用命令"""
    await handle_enable_or_disable(event, args, True)


# 禁用命令
disable_cmd = on_command("禁用", aliases={"道具禁用"}, priority=5, block=True)

@disable_cmd.handle()
async def handle_disable(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理禁用命令"""
    await handle_enable_or_disable(event, args, False)


async def handle_enable_or_disable(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message, enable: bool):
    """启用/禁用物品内部处理逻辑"""
    user_id = await get_user_id(event, auto_create=True)
    arg_text = args.extract_plain_text().strip()
    
    get_name_success, item_name, _ = get_item_name_and_amount(arg_text)
    if not get_name_success:
        await send_finish(enable_cmd, '需要道具名！')
        return
    
    item = await item_db.getItem(item_name)
    item_storage_info = await item_db.getItemStorageInfo(user_id, item_name)
    
    if not item:
        await send_finish(enable_cmd, '此道具不存在!')
        return
    if not item.isControllable:
        await send_finish(enable_cmd, '此道具不能手动启用或禁用!')
        return
    if not item_storage_info:
        await send_finish(enable_cmd, '你没有此道具!')
        return
    
    await item_db.changeItemAllowUse(user_id, item_name, enable)
    await send_finish(enable_cmd, f'已{"启用" if enable else "禁用"}你的 {item_name}')


# 合成命令
compose_cmd = on_command("合成", priority=5, block=True)

@compose_cmd.handle()
async def handle_compose(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理合成命令"""
    user_id = await get_user_id(event, auto_create=True)

    arg_text = args.extract_plain_text().strip()
    get_name_success, item_name, amount = get_item_name_and_amount(arg_text)
    if not get_name_success:
        await send_finish(compose_cmd, '需要待合成物品名！')
        return

    # 使用 Service 层进行奖券合成
    result = await ItemService.compose_ticket(userId=user_id, target=item_name, amount=amount)

    if not result['success']:
        if result.get('error') == 'NO_MACHINE':
            await send_finish(compose_cmd, '你没有奖券合成机，无法进行奖券合成^ ^')
        elif result.get('error') == 'INVALID_TARGET':
            await send_finish(compose_cmd, '此物品无法进行合成！')
        elif result.get('error') == 'INSUFFICIENT':
            await send_finish(compose_cmd, f'你不够{result.get("source")}^ ^')
        else:
            await send_finish(compose_cmd, result.get('message', '合成失败！'))
        return

    await send_finish(compose_cmd, result['message'])


# ==================== 辅助函数 ====================

def get_item_name_and_amount(arg_text: str):
    """从参数中提取物品名和数量
    
    支持格式：
    - [物品名] [数量] - 如：抽奖券 10
    - [物品名] - 默认为1个
    - 数量支持 k/m/b 后缀，如：10k
    """
    # 名字匹配中文字符
    item_name_result = re.search(r'[\u4e00-\u9fa5G]+[IVX]*', arg_text)
    
    if not item_name_result:
        return False, None, None
    
    item_name = item_name_result.group(0)
    
    # 提取数量 - 排除 qq= 和 id= 后面的数字
    # 先移除所有 qq=xxx 和 id=xxx 的部分，避免误识别
    temp_text = re.sub(r'(?i)(qq|id)=\d+', '', arg_text)
    item_amount_result = re.search(r'\b\d+[kmbKMB]?\b', temp_text)
    
    item_amount = convertNumStrToInt(item_amount_result.group(0)) if item_amount_result else 1
    return True, item_name, item_amount


async def pre_item_check(item, user_id):
    """检查前置条件"""
    if not item.shopPreItems:
        return True
    
    pre_item_names = item.shopPreItems.split(',')
    for pre_item_name in pre_item_names:
        # 信息员等级限制
        if pre_item_name.startswith('Lv'):
            need_level = int(pre_item_name[2:])
            user = await base_db.getKusaUser(user_id)
            if user.vipLevel < need_level:
                return False
            continue
        
        # 前置物品限制
        pre_item = await item_db.getItem(pre_item_name)
        if not pre_item:
            return False
        if not await item_db.getItemAmount(user_id, pre_item_name):
            return False
    return True


def get_pre_item_str(item):
    """获取前置条件字符串"""
    if not item.shopPreItems:
        return ''
    
    pre_item_names = item.shopPreItems.split(',')
    pre_item_str = ''
    for pre_item_name in pre_item_names:
        if pre_item_name.startswith('Lv'):
            pre_item_str += f'信息员Lv{pre_item_name[2:]}，'
            continue
        pre_item_str += f'{pre_item_name}，'
    return pre_item_str[:-1]


def get_multi_item_price(item, own_item_amount, new_item_amount):
    """计算多个物品的总价"""
    if not item.priceRate:
        return new_item_amount * item.shopPrice
    return sum(get_item_price(item, own_item_amount + i) for i in range(new_item_amount))


def get_item_price(item, item_amount):
    """获取物品价格"""
    if not item.priceRate:
        return item.shopPrice
    return int(item.shopPrice * (item.priceRate ** item_amount))


# ==================== 定时任务 ====================

if scheduler:
    @scheduler.scheduled_job('interval', seconds=50, max_instances=10, misfire_grace_time=500)
    async def clean_time_limited_item_runner():
        """清理限时物品"""
        await item_db.cleanTimeLimitedItems()
