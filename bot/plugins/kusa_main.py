"""
生草系统核心插件 - NoneBot2 版本
包含仓库、能力、称号、改名、草转让等核心功能
支持 OneBot V11 和 QQ 官方 Bot 双平台
"""

import dataclasses
import re
import string
import random
import asyncio
from typing import Dict, Union
from datetime import datetime

from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.qq import MessageEvent as QQMessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotMS
from nonebot.params import CommandArg
from nonebot.adapters import Message

import dbConnection.kusa_system as base_db
import dbConnection.kusa_item as item_db
import dbConnection.kusa_field as field_db
from utils import convertNumStrToInt
from kusa_base import (
    plugin_config, send_private_msg, send_group_msg, get_bot_qq
)
from services import WarehouseService
from multi_platform import (
    get_user_id,
    is_onebot_v11_event,
    send_finish,
    build_at_message,
)
from . import scheduler


from .kusa_statistics import getKusaAdvRank


@dataclasses.dataclass
class KusaEnvelopeInfo:
    """草包信息"""
    userId: int
    participantIds: set
    kusaLimit: int
    userLimit: int
    startTime: datetime
    maxGot: int
    maxUserId: int


vip_title_names = [
    '用户', '信息员', '高级信息员', '特级信息员', '后浪信息员',
    '天琴信息员', '天琴信息节点', '天琴信息矩阵', '天琴信息网络',
    '???', '???', '???', '???'
]

kusa_envelope_dict: Dict[str, KusaEnvelopeInfo] = {}


def get_user_id_from_event(event: Union[OneBotV11MessageEvent, QQMessageEvent]) -> int:
    """从事件中获取用户 ID（返回 userId）"""
    if is_onebot_v11_event(event):
        return int(event.user_id)
    else:
        if hasattr(event, 'author') and event.author:
            if hasattr(event.author, 'member_openid'):
                return int(event.author.member_openid)
            if hasattr(event.author, 'user_openid'):
                return int(event.author.user_openid)
        return int(getattr(event, 'user_id', 0))


def get_group_id_from_event(event: Union[OneBotV11MessageEvent, QQMessageEvent]) -> Union[int, None]:
    """从事件中获取群 ID"""
    if is_onebot_v11_event(event):
        return event.group_id
    return None


def get_nickname_from_event(event: Union[OneBotV11MessageEvent, QQMessageEvent]) -> str:
    """从事件中获取用户昵称"""
    if is_onebot_v11_event(event):
        return event.sender.nickname if event.sender else ""
    return ""


async def get_warehouse_info_str(warehouse_data: dict) -> str:
    """格式化仓库信息字符串"""
    user = warehouse_data['user']
    items = warehouse_data['items']

    output = f"当前拥有草: {user['kusa']:,}\n"
    if user.get('advKusa'):
        output += f"当前拥有草之精华: {user['advKusa']:,}\n"

    output += '\n当前财产：\n'

    wealth_items = [item for item in items if item['item']['type'] == '财产']
    g_items = [item for item in items if item['item']['type'] == 'G']

    for item in wealth_items:
        output += f"{item['item']['name']} * {item['amount']}, "
    for item in g_items:
        output += f"{item['item']['name']} * {item['amount']}, "

    if output.endswith('当前财产：\n'):
        return ''

    output = output[:-2]

    prop_items = [item for item in items if item['item']['type'] == '道具']
    if prop_items:
        output += '\n\n当前道具：\n'
        for item in prop_items:
            amount_str = f" * {item['amount']}" if item['amount'] != 1 else ""
            output += f"{item['item']['name']}{amount_str}, "
        output = output[:-2]

    return output


async def stop_envelope(envelope_id: str):
    """结束草包"""
    global kusa_envelope_dict
    if envelope_id not in kusa_envelope_dict:
        return

    envelope_info = kusa_envelope_dict.pop(envelope_id)
    user = await base_db.getKusaUser(envelope_info.userId)
    user_name = user.name if user and user.name else str(envelope_info.userId)

    if envelope_info.userLimit == 0:
        max_user = await base_db.getKusaUser(envelope_info.maxUserId)
        max_user_name = max_user.name if max_user and max_user.name else str(envelope_info.maxUserId)
        d_time = datetime.now() - envelope_info.startTime
        s_total = int(d_time.total_seconds())
        await send_group_msg(
            plugin_config.get('group', {}).get('main'),
            f'玩家 {user_name} 发的草包已被抢完，耗时{s_total // 60}min{s_total % 60}s\n'
            f'玩家 {max_user_name} 是手气王，抢到了{envelope_info.maxGot}草'
        )
    else:
        await base_db.changeKusa(envelope_info.userId, envelope_info.kusaLimit)
        await send_group_msg(
            plugin_config.get('group', {}).get('main'),
            f'玩家 {user_name} 发的草包超时未抢完，剩余{envelope_info.kusaLimit}草已退回'
        )


async def stop_envelope_timer(duration: int, envelope_id: str):
    """草包定时器"""
    await asyncio.sleep(duration)
    await stop_envelope(envelope_id)


warehouse_cmd = on_command("仓库", priority=5, block=True)

@warehouse_cmd.handle()
async def handle_warehouse(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理仓库命令
    
    支持格式：
    - /仓库 - 查看自己的仓库
    - /仓库 qq=123456 - 通过QQ号查看他人仓库
    - /仓库 id=227 - 通过用户ID查看他人仓库
    - 当qq和id同时传入时，以id为准
    """
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()
    
    # 解析qq参数
    target_qq_match = re.search(r'(?<=(QQ|qq)=)\d+', stripped_arg)
    # 解析id参数
    target_id_match = re.search(r'(?<=(ID|id)=)\d+', stripped_arg)
    
    target_qq = int(target_qq_match.group(0)) if target_qq_match else None
    target_id = int(target_id_match.group(0)) if target_id_match else None

    if target_qq or target_id:
        watcher_id = user_id
        recce_item_amount = await item_db.getItemAmount(watcher_id, '侦察凭证')
        if not recce_item_amount:
            await send_finish(warehouse_cmd, '你当前不能查看别人的仓库！请到商店购买侦察凭证。')
            return

        # 优先使用id
        if target_id:
            target_user = await WarehouseService.get_transfer_target_by_id(target_id)
        else:
            target_user = await WarehouseService.get_transfer_target_by_qq(str(target_qq))
            
        if not target_user:
            await send_finish(warehouse_cmd, '你想查看的对象并没有生草账户！')
            return

        result = await WarehouseService.get_warehouse_info(userId=target_user.id)
        user = result['user']

        output = '[侦察卫星使用中]\n'
        if user['name']:
            output += f"{user['name']}({user['qq']})的仓库状况如下：\n"
        else:
            output += f"{user['qq']}的仓库状况如下：\n"
        output += await get_warehouse_info_str(result)
        await send_finish(warehouse_cmd, output)
        await item_db.changeItemAmount(watcher_id, '侦察凭证', -1)
    else:
        result = await WarehouseService.get_warehouse_info(userId=user_id)
        user = result['user']

        donate_amount = await base_db.getDonateAmount(user_id)
        output = f'感谢您，生草系统的捐助者!\n' if donate_amount else ''
        output += f"Lv{user['vipLevel']} " if user['vipLevel'] else ''
        output += f"{user['title']} " if user['title'] else f"{vip_title_names[user['vipLevel']]} "
        user_name = user['name'] if user['name'] else get_nickname_from_event(event)
        output += f"{user_name}({user_id})\n"
        output += await get_warehouse_info_str(result)
        await send_finish(warehouse_cmd, output)


ability_cmd = on_command("能力", priority=5, block=True)

@ability_cmd.handle()
async def handle_ability(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理能力命令"""
    user_id = await get_user_id(event, auto_create=True)
    items_skill = await item_db.getItemsByType("能力")
    items_drawing = await item_db.getItemsByType("图纸")

    if not items_skill and not items_drawing:
        await send_finish(ability_cmd, '当前没有任何能力或图纸！')
        return

    output = ''
    if items_skill:
        output += f'你当前所拥有的能力：\n'
        skill_list = []
        for item in items_skill:
            item_amount = await item_db.getItemAmount(user_id, item.name)
            if item_amount != 0:
                skill_list.append(item.name)
        if skill_list:
            output += ', '.join(skill_list)

    if items_drawing:
        output += '\n\n' if output else ''
        output += f'你当前所拥有的图纸：\n'
        drawing_list = []
        for item in items_drawing:
            item_amount = await item_db.getItemAmount(user_id, item.name)
            if item_amount != 0:
                drawing_list.append(item.name)
        if drawing_list:
            output += ', '.join(drawing_list)

    if not output:
        output = '当前没有任何能力或图纸！'

    await send_finish(ability_cmd, output)


change_name_cmd = on_command("改名", priority=5, block=True)

@change_name_cmd.handle()
async def handle_change_name(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理改名命令"""
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()

    if stripped_arg:
        if len(stripped_arg) <= 25:
            result = await WarehouseService.change_name(userId=user_id, name=stripped_arg)
            if result['success']:
                await send_finish(change_name_cmd, result['message'])
            else:
                await send_finish(change_name_cmd, '改名失败')
        else:
            await send_finish(change_name_cmd, '名字太长了^ ^')


title_cmd = on_command("称号", priority=5, block=True)

@title_cmd.handle()
async def handle_title(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理称号命令"""
    user_id = await get_user_id(event, auto_create=True)
    item_title = await item_db.getItemsByType("称号")

    if not item_title:
        await send_finish(title_cmd, '当前没有任何称号！')
        return

    own_title = []
    for item in item_title:
        item_amount = await item_db.getItemAmount(user_id, item.name)
        if item_amount != 0:
            own_title.append(item.name)

    if not own_title:
        await send_finish(title_cmd, '当前没有任何可用称号！')
        return

    output = f'你当前可用的称号：{", ".join(own_title)}'
    output += f'\n可使用"!修改称号"指令来更改当前展示的称号。'
    await send_finish(title_cmd, output)


change_title_cmd = on_command("修改称号", priority=5, block=True)

@change_title_cmd.handle()
async def handle_change_title(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理修改称号命令"""
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()

    if not stripped_arg:
        result = await WarehouseService.change_title(userId=user_id, title=None)
        await send_finish(change_title_cmd, result['message'] if result['success'] else '修改失败')
        return

    item = await item_db.getItem(stripped_arg)
    if not item or item.type != '称号':
        await send_finish(change_title_cmd, '你想使用的称号不存在^ ^')
        return

    item_amount = await item_db.getItemAmount(user_id, stripped_arg)
    if not item_amount:
        await send_finish(change_title_cmd, '你没有这个称号^ ^')
        return

    result = await WarehouseService.change_title(userId=user_id, title=stripped_arg)
    if result['success']:
        await send_finish(change_title_cmd, result['message'])
    else:
        await send_finish(change_title_cmd, '修改失败')


flag_list_cmd = on_command("配置列表", priority=5, block=True)

@flag_list_cmd.handle()
async def handle_flag_list(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理配置列表命令"""
    user_id = await get_user_id(event, auto_create=True)
    flag_list = await base_db.getFlagList()
    output = ""
    for flag in flag_list:
        flag_value = await base_db.getFlagValue(user_id, flag.name)
        flag_type = 'on' if flag_value else 'off'
        output += f'{flag.name}: {flag_type}\n'
    await send_finish(flag_list_cmd, output[:-1])


flag_set_cmd = on_command("配置", priority=5, block=True)

@flag_set_cmd.handle()
async def handle_flag_set(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理配置命令"""
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()

    if not stripped_arg:
        help_str = '使用方法：\n!配置 [配置名] [on/off]\n使用 !配置列表 查看当前配置情况'
        await send_finish(flag_set_cmd, help_str)
        return

    try:
        flag_name, flag_type = stripped_arg.split()
        if flag_type.lower() not in ['on', 'off']:
            await send_finish(flag_set_cmd, '参数错误，请使用 on 或 off')
            return
        flag_value = 1 if flag_type.lower() == 'on' else 0
        await base_db.setFlag(user_id, flag_name, flag_value)
        await send_finish(flag_set_cmd, '设置成功！')
    except ValueError:
        await send_finish(flag_set_cmd, '参数格式错误，请使用：!配置 [配置名] [on/off]')


kusa_ban_cmd = on_command("口球", priority=5, block=True)

@kusa_ban_cmd.handle()
async def handle_kusa_ban(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理口球命令"""
    if not is_onebot_v11_event(event):
        await send_finish(kusa_ban_cmd, '该功能暂不支持 QQ 官方 Bot')
        return

    group_id = event.group_id
    user_id = event.user_id

    status_msg = '已经送出^ ^'
    stripped_arg = args.extract_plain_text().strip()
    receiver_qq_match = re.search(r'(?<=(QQ|qq)=)\d+', stripped_arg)
    seconds_match = re.search(r'(?<=(sec|SEC)=)\d+', stripped_arg)

    if receiver_qq_match and seconds_match:
        receiver_qq = int(receiver_qq_match.group(0))
        seconds = int(seconds_match.group(0))

        if seconds > 0:
            user = await base_db.getKusaUser(user_id)
            cost_kusa = seconds
            if user.kusa >= cost_kusa:
                from nonebot import get_bot
                bot = get_bot()
                await bot.set_group_ban(group_id=group_id, user_id=receiver_qq, duration=seconds)
                await base_db.changeKusa(user_id, -cost_kusa)
                await base_db.changeKusa(await get_bot_qq(), cost_kusa)
            else:
                status_msg = '你不够草^ ^'
        else:
            from nonebot import get_bot
            bot = get_bot()
            await bot.set_group_ban(group_id=group_id, user_id=receiver_qq, duration=seconds)
            status_msg = '已解除相关人员的口球(如果有的话)'
    else:
        status_msg = '参数不正确^ ^'

    await send_finish(kusa_ban_cmd, status_msg)


transfer_kusa_cmd = on_command("草转让", priority=5, block=True)

@transfer_kusa_cmd.handle()
async def handle_transfer_kusa(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理草转让命令
    
    支持格式：
    - 草转让 qq=123456 kusa=1000
    - 草转让 id=227 kusa=1000
    - 当qq和id同时传入时，以id为准
    """
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()

    # 解析qq参数
    qq_number_match = re.search(r'(?<=(QQ|qq)=)\d+', stripped_arg)
    # 解析id参数
    id_match = re.search(r'(?<=(ID|id)=)\d+', stripped_arg)
    # 解析草数量
    transfer_kusa_match = re.search(r'(?<=(kusa|Kusa|KUSA)=)[\d,]+[kmbKMB]?', stripped_arg)

    receiver_qq = int(qq_number_match.group(0)) if qq_number_match else None
    receiver_id = int(id_match.group(0)) if id_match else None
    transfer_kusa = convertNumStrToInt(transfer_kusa_match.group(0)) if transfer_kusa_match else 0

    # 检查目标用户
    target_user = None
    if receiver_id:
        # 优先使用id
        target_user = await WarehouseService.get_transfer_target_by_id(receiver_id)
    elif receiver_qq:
        # 使用qq
        target_user = await WarehouseService.get_transfer_target_by_qq(str(receiver_qq))
    else:
        await send_finish(transfer_kusa_cmd, '需要被转让人的QQ号(qq=xxx)或用户ID(id=xxx)！')
        return

    if not transfer_kusa:
        await send_finish(transfer_kusa_cmd, '待转让的草数不合法！')
        return

    if not target_user:
        await send_finish(transfer_kusa_cmd, '你想转让的对象并没有生草账户！')
        return

    result = await WarehouseService.transfer_kusa(userId=user_id, target_userId=target_user.id, amount=transfer_kusa)

    if not result['success']:
        if result['error'] == 'TARGET_NOT_FOUND':
            await send_finish(transfer_kusa_cmd, '你想转让的对象并没有生草账户！')
        elif result['error'] == 'INSUFFICIENT_KUSA':
            await send_finish(transfer_kusa_cmd, '你不够草^ ^')
        else:
            await send_finish(transfer_kusa_cmd, '转让失败')
        return

    nickname = get_nickname_from_event(event)
    announce = f'{nickname}({user_id})转让了{transfer_kusa}个草给你！'
    has_send_private = await send_private_msg(target_user.id, announce) if transfer_kusa >= 10000 else False
    status_msg = '转让成功！' if has_send_private else '转让成功！(未私聊通知被转让者)'

    await send_finish(transfer_kusa_cmd, status_msg)


compress_kusa_cmd = on_command("草压缩", priority=5, block=True)

@compress_kusa_cmd.handle()
async def handle_compress_kusa(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理草压缩命令"""
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()

    kusa_adv_gain = int(stripped_arg) if stripped_arg else 1
    kusa_adv_gain = abs(kusa_adv_gain)

    result = await WarehouseService.compress_kusa(userId=user_id, adv_amount=kusa_adv_gain)

    if not result['success']:
        if result['error'] == 'NO_BASE':
            await send_finish(compress_kusa_cmd, '你没有草压缩基地，无法使用本指令！')
        elif result['error'] == 'INSUFFICIENT_KUSA':
            await send_finish(compress_kusa_cmd, '你不够草^ ^')
        else:
            await send_finish(compress_kusa_cmd, '压缩失败')
        return

    await send_finish(compress_kusa_cmd, result['message'])


give_envelope_cmd = on_command("发草包", priority=5, block=True)

@give_envelope_cmd.handle()
async def handle_give_envelope(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理发草包命令"""
    global kusa_envelope_dict

    user_id = await get_user_id(event, auto_create=True)
    group_id = get_group_id_from_event(event)
    main_group = plugin_config.get('group', {}).get('main')

    if group_id != main_group:
        await send_finish(give_envelope_cmd, '只能在除草器主群中进行发草包^ ^')
        return

    stripped_arg = args.extract_plain_text().strip()
    number_match = re.search(r'(?<=(num|Num|NUM)=)\d+', stripped_arg)
    total_kusa_match = re.search(r'(?<=(kusa|Kusa|KUSA)=)\d+[kmbKMB]?', stripped_arg)

    number = int(number_match.group(0)) if number_match else None
    total_kusa = convertNumStrToInt(total_kusa_match.group(0)) if total_kusa_match else 0

    if not number:
        await send_finish(give_envelope_cmd, '需要发放草包的个数！')
        return
    if number <= 0:
        await send_finish(give_envelope_cmd, '草包个数不合法！')
        return
    if total_kusa < number:
        await send_finish(give_envelope_cmd, '待发的草数不合法！')
        return

    user = await base_db.getKusaUser(user_id)
    if user.kusa < total_kusa:
        await send_finish(give_envelope_cmd, '你不够草^ ^')
        return

    await base_db.changeKusa(user_id, -total_kusa)

    envelope_info = KusaEnvelopeInfo(
        userId=user_id,
        participantIds=set(),
        kusaLimit=total_kusa,
        userLimit=number,
        maxGot=0,
        maxUserId=0,
        startTime=datetime.now()
    )

    envelope_id = str(user_id) + "_" + ''.join(random.choice(string.ascii_letters) for _ in range(8))
    asyncio.create_task(stop_envelope_timer(3600, envelope_id))
    kusa_envelope_dict[envelope_id] = envelope_info

    await send_finish(give_envelope_cmd, f'发出总额为{total_kusa}的{number}人草包成功！')


grab_envelope_cmd = on_command("抢草包", priority=5, block=True)

@grab_envelope_cmd.handle()
async def handle_grab_envelope(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理抢草包命令"""
    global kusa_envelope_dict

    user_id = await get_user_id(event, auto_create=True)
    group_id = get_group_id_from_event(event)
    main_group = plugin_config.get('group', {}).get('main')

    if group_id != main_group:
        await send_finish(grab_envelope_cmd, '只能在除草器主群中进行抢草包^ ^')
        return

    if not kusa_envelope_dict:
        await send_finish(grab_envelope_cmd, await build_at_message(event, user_id, '当前没有草包^ ^'))
        return

    from dbConnection.user import getUnifiedUser
    unified_user = await getUnifiedUser(user_id)
    if unified_user and unified_user.relatedUserId:
        pass

    has_got_flag, output_strs, stop_ids = False, [], []

    for envelope_id, envelope_info in kusa_envelope_dict.items():
        if user_id in envelope_info.participantIds:
            has_got_flag = True
            continue

        if envelope_info.userLimit > 1:
            max_kusa = (envelope_info.kusaLimit - envelope_info.userLimit) / envelope_info.userLimit * 2
            max_kusa = 1 if random.random() < 0.01 else max_kusa
            kusa_got = random.randint(1, max(int(max_kusa), 1))
        else:
            kusa_got = envelope_info.kusaLimit

        envelope_info.kusaLimit -= kusa_got
        envelope_info.userLimit -= 1
        envelope_info.participantIds.add(user_id)
        await base_db.changeKusa(user_id, kusa_got)

        if kusa_got > envelope_info.maxGot:
            envelope_info.maxGot = kusa_got
            envelope_info.maxUserId = user_id

        output_strs.append(f'你抢到了{kusa_got}草！')
        if envelope_info.userLimit <= 0:
            stop_ids.append(envelope_id)

    if output_strs:
        await send_finish(grab_envelope_cmd, await build_at_message(event, user_id, '\n'.join(output_strs)))
    elif has_got_flag:
        await send_finish(grab_envelope_cmd, await build_at_message(event, user_id, '你已经抢过草包了^ ^'))

    for envelope_id in stop_ids:
        await stop_envelope(envelope_id)


vip_upgrade_cmd = on_command("信息员升级", priority=5, block=True)

@vip_upgrade_cmd.handle()
async def handle_vip_upgrade(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理信息员升级命令"""
    user_id = await get_user_id(event, auto_create=True)
    user = await base_db.getKusaUser(user_id)

    if user.vipLevel >= 4:
        await send_finish(vip_upgrade_cmd,
            '你已经是后浪信息员了，不能使用本指令提升信息员等级！如果需要进一步升级，请使用"!进阶信息员升级"。'
        )
        return

    new_level = user.vipLevel + 1
    cost_kusa = 50 * (10 ** new_level)

    if user.kusa >= cost_kusa:
        user.vipLevel = new_level
        await user.save()
        await base_db.changeKusa(user_id, -cost_kusa)
        await base_db.changeKusa(await get_bot_qq(), cost_kusa)
        await send_finish(vip_upgrade_cmd, f'获取成功！你成为了{vip_title_names[new_level]}！')
    else:
        await send_finish(vip_upgrade_cmd, f'成为{vip_title_names[new_level]}需要消耗{cost_kusa}草，你不够草^ ^')


vip_upgrade_2_cmd = on_command("进阶信息员升级", priority=5, block=True)

@vip_upgrade_2_cmd.handle()
async def handle_vip_upgrade_2(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理进阶信息员升级命令"""
    user_id = await get_user_id(event, auto_create=True)
    user = await base_db.getKusaUser(user_id)

    if user.vipLevel < 4:
        await send_finish(vip_upgrade_2_cmd,
            '你还不是后浪信息员，不能使用本指令提升信息员等级！如果需要升级，请使用"!信息员升级"。'
        )
        return
    if user.vipLevel >= 8:
        await send_finish(vip_upgrade_2_cmd, '你已经是当前最高级的信息员了！')
        return

    new_level = user.vipLevel + 1
    cost_adv_point = 10 ** (new_level - 4)

    if user.advKusa >= cost_adv_point:
        user.vipLevel = new_level
        await user.save()
        await base_db.changeAdvKusa(user_id, -cost_adv_point)
        await base_db.changeAdvKusa(await get_bot_qq(), cost_adv_point)
        await send_finish(vip_upgrade_2_cmd, f'获取成功！你成为了{vip_title_names[new_level]}！')
    else:
        await send_finish(vip_upgrade_2_cmd,
            f'成为{vip_title_names[new_level]}需要消耗{cost_adv_point}个草之精华，你的草之精华不够^ ^'
        )


if scheduler:
    @scheduler.scheduled_job('cron', hour=4, misfire_grace_time=500)
    async def daily_report_runner():
        """生草日报"""
        row = await field_db.kusaHistoryTotalReport(86400)
        max_times, max_kusa, max_adv_kusa, max_avg_adv_kusa, max_once_adv_kusa = await field_db.kusaFarmChampion()

        output_str = f"最近24h生草统计:\n" \
                     f"总生草次数: {row['count']}\n" \
                     f"总草产量: {round(row['sumKusa'] / 1000000, 2)}m\n" \
                     f"总草之精华产量: {row['sumAdvKusa']}\n"

        if max_times['count']:
            user1 = await base_db.getKusaUser(max_times['qq'])
            user_name1 = user1.name if user1 and user1.name else str(max_times['qq'])
            user2 = await base_db.getKusaUser(max_kusa['qq'])
            user_name2 = user2.name if user2 and user2.name else str(max_kusa['qq'])
            user3 = await base_db.getKusaUser(max_adv_kusa['qq'])
            user_name3 = user3.name if user3 and user3.name else str(max_adv_kusa['qq'])
            user4 = await base_db.getKusaUser(max_avg_adv_kusa['qq'])
            user_name4 = user4.name if user4 and user4.name else str(max_avg_adv_kusa['qq'])
            user5 = await base_db.getKusaUser(max_once_adv_kusa['qq'])
            user_name5 = user5.name if user5 and user5.name else str(max_once_adv_kusa['qq'])

            output_str += f"\n" \
                          f"生草次数最多: {user_name1}({max_times['count']}次)\n" \
                          f"获得草最多: {user_name2}(共{round(max_kusa['sumKusa'] / 1000000, 2)}m草)\n" \
                          f"获得草之精华最多: {user_name3}(共{max_adv_kusa['sumAdvKusa']}草精)\n" \
                          f"平均草之精华最多: {user_name4}(平均{round(max_avg_adv_kusa['avgAdvKusa'], 2)}草精)\n" \
                          f"单次草之精华最多: {user_name5}({max_once_adv_kusa['maxAdvKusa']}草精)"

        main_group = plugin_config.get('group', {}).get('main')
        await send_group_msg(main_group, output_str)

    @scheduler.scheduled_job('cron', hour=4, minute=1, day_of_week='mon', misfire_grace_time=500)
    async def weekly_report_runner():
        """生草周报"""
        row = await field_db.kusaHistoryTotalReport(604800)
        output_str = f"最近一周生草统计:\n" \
                     f"总生草次数: {row['count']}\n" \
                     f"总草产量: {round(row['sumKusa'] / 1000000)}m\n" \
                     f"总草之精华产量: {row['sumAdvKusa']}"

        main_group = plugin_config.get('group', {}).get('main')
        await send_group_msg(main_group, output_str)

    @scheduler.scheduled_job('cron', hour=4, minute=2, day_of_week='mon', misfire_grace_time=500)
    async def weekly_adv_report_runner():
        """每周草精总榜"""
        output_str = '总草精排行榜：' + await getKusaAdvRank()
        main_group = plugin_config.get('group', {}).get('main')
        await send_group_msg(main_group, output_str)
