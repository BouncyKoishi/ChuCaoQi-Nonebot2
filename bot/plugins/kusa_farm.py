"""
生草系统核心插件 - NoneBot2 版本
包含生草、除草、百草园、围殴等核心功能
支持 OneBot V11 和 QQ 官方 Bot 双平台
"""

import asyncio
import dataclasses
import random
import string
from typing import Dict, Union
from datetime import datetime

from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.qq import MessageEvent as QQMessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment as MS
from nonebot.params import CommandArg
from nonebot.adapters import Message

import core.db.kusa_system as base_db
import core.db.kusa_field as field_db
import core.db.kusa_item as item_db
from core.db.user import getUnifiedUser
from kusa_base import plugin_config, send_private_msg, send_group_msg
from core.services import FarmService
from multi_platform import (
    get_user_id,
    get_group_id,
    is_onebot_v11_event,
    is_group_message,
    send_reply,
    send_finish,
    build_at_message,
)

import aiohttp


async def notify_web_status_update(user_id):
    """通知web端状态更新（生草开始时调用）"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://127.0.0.1:8000/api/notify/farm-status',
                json={'userId': user_id},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    print(f'通知web端失败: {resp.status}')
    except Exception as e:
        print(f'通知web端状态更新失败: {e}')


async def notify_web_kusa_harvested(payload: dict):
    """通知web端生草完毕（bot 本地命令路径使用，如 KUSA_FINISH 强制收获）

    常规结算路径的 web 通知已随 A1 下沉至 scheduler/jobs/farm.py（阶段 5），
    由 scheduler 直接推 backend；payload 为 FarmService.settle_field 返回的 web 字段。
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://127.0.0.1:8000/api/notify/kusa-harvested',
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    print(f'通知web端生草完毕失败: {resp.status}')
    except Exception as e:
        print(f'通知web端生草完毕失败: {e}')


@dataclasses.dataclass
class RobInfo:
    """围殴信息"""
    targetId: int
    participantIds: set
    robCount: int
    robLimit: int
    extraKusaAdv: bool = False


systemRandom = random.SystemRandom()
rob_dict: Dict[str, RobInfo] = {}
# 喜报判定/连号/过载奖励等常量表已随结算逻辑移至 core/services/farm_service.py（阶段 5）


def format_plant_result(data: dict, prefix: str = "开始") -> str:
    """格式化生草结果输出
    
    Args:
        data: 生草结果数据
        prefix: 开头文本，如"开始"、"开始过载"、"自动开始"
    
    Returns:
        格式化后的输出字符串
    """
    kusa_type = data['kusaType']
    grow_time = data['growTimeMinutes']
    predict_time = datetime.fromisoformat(data['predictFinishTime'])
    
    output_str = f"{prefix}生{kusa_type}。"
    
    magic_immediate = data.get('magicImmediate', False)
    magic_quick = data.get('magicQuick', False)
    spiritless_immediate = data.get('spiritlessImmediate', False)
    
    if magic_immediate:
        output_str += '\n时光魔法吟唱中……\n(ﾉ≧∀≦)ﾉ ‥…━━━★\n'
    elif spiritless_immediate:
        output_str += '\n不灵草速生模块生效中，你的不灵草将在一分钟内长成！\n'
    elif magic_quick:
        output_str += f'\n剩余时间：{grow_time}min(-77.7%)\n'
    else:
        output_str += f'\n剩余时间：{grow_time}min\n'
    
    if not magic_immediate and not spiritless_immediate:
        output_str += f'预计生草完成时间：{predict_time.hour:02d}:{predict_time.minute:02d}\n'
    
    if data.get('isPrescient'):
        output_str += f"预知：生草量为{data.get('kusaResult')}"
        if data.get('advKusaResult'):
            output_str += f"，草之精华获取量为{data.get('advKusaResult')}"
    else:
        predict_range = data.get('predictRange', {})
        if predict_range:
            output_str += f"预估生草量：{predict_range['min']} ~ {predict_range['max']}"
    
    if data.get('soilCapacity', 25) <= 12:
        output_str += f'\n当前承载力低！目前承载力：{data["soilCapacity"]}'
    
    return output_str


plant_kusa_cmd = on_command("生草", priority=5, block=True)

@plant_kusa_cmd.handle()
async def handle_plant_kusa(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理生草命令"""
    user_id = await get_user_id(event, auto_create=True)
    kusa_type = args.extract_plain_text().strip() or None
    
    if kusa_type == '神灵草':
        pray_result = await FarmService.pray_for_divine(user_id)
        if not pray_result['success']:
            await send_finish(plant_kusa_cmd, pray_result.get('errorMsg', '祈愿失败'))
            return
        output_str = f"祈愿{pray_result['rolls']}次，种出了神灵草！\n"
        output_str += format_plant_result(pray_result['data'], "开始")
        await send_finish(plant_kusa_cmd, output_str)
        await notify_web_status_update(user_id)
        return
    
    result = await FarmService.start_planting(
        userId=user_id, kusa_type=kusa_type
    )
    
    if not result['success']:
        error_code = result.get('error', 'UNKNOWN_ERROR')
        
        if error_code == 'ALREADY_GROWING':
            data = result.get('data', {})
            output_str = result['errorMsg']
            if 'predictFinishTime' in data:
                predict_time = datetime.fromisoformat(data['predictFinishTime'])
                output_str += f'\n预计生草完成时间：{predict_time.hour:02d}:{predict_time.minute:02d}'
            await send_finish(plant_kusa_cmd, output_str)
        elif error_code in ['ALMOST_DONE', 'OVERLOADED', 'SOIL_PROTECTED', 'NO_SOIL_CAPACITY', 'INVALID_KUSA_TYPE']:
            await send_finish(plant_kusa_cmd, result['errorMsg'])
        else:
            await send_finish(plant_kusa_cmd, result.get('errorMsg', '操作失败'))
        return
    
    output_str = format_plant_result(result['data'], "开始")
    await send_finish(plant_kusa_cmd, output_str)
    await notify_web_status_update(user_id)


overload_plant_cmd = on_command("过载生草", priority=5, block=True)

@overload_plant_cmd.handle()
async def handle_overload_plant(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理过载生草命令"""
    user_id = await get_user_id(event, auto_create=True)
    overload_magic = await item_db.getItemAmount(user_id, '奈奈的过载魔法')
    
    if not overload_magic:
        await send_finish(overload_plant_cmd, '你未学会过载魔法，无法进行过载生草^ ^')
        return
    
    kusa_type = args.extract_plain_text().strip() or None
    result = await FarmService.start_planting(userId=user_id, kusa_type=kusa_type, overload=True)
    
    if not result['success']:
        await send_finish(overload_plant_cmd, result.get('errorMsg', '操作失败'))
        return
    
    output_str = format_plant_result(result['data'], "开始过载")
    await send_finish(overload_plant_cmd, output_str)
    await notify_web_status_update(user_id)


weed_cmd = on_command("除草", priority=5, block=True)

@weed_cmd.handle()
async def handle_weed(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理除草命令"""
    user_id = await get_user_id(event, auto_create=True)
    result = await FarmService.weed(userId=user_id)

    if not result['success']:
        error_code = result.get('error', 'UNKNOWN_ERROR')
        if error_code == 'NO_WEEDER':
            await send_finish(weed_cmd, '你没有除草机，无法除草^ ^')
        elif error_code == 'NO_KUSA_TO_HARVEST':
            await send_finish(weed_cmd, '当前没有生草，无法除草^ ^')
        else:
            await send_finish(weed_cmd, '除草失败')
        return

    await send_reply(weed_cmd, '除草成功^ ^')

    try:
        if await base_db.getFlagValue(user_id, '除草后自动生草'):
            auto_result = await FarmService.start_planting(userId=user_id)
            if auto_result['success']:
                output_str = format_plant_result(auto_result['data'], "自动开始")
                await send_reply(weed_cmd, output_str)
    except Exception as e:
        print(f'除草后自动生草失败: {e}')


bai_cao_yuan_cmd = on_command("百草园", priority=5, block=True)

@bai_cao_yuan_cmd.handle()
async def handle_bai_cao_yuan(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理百草园命令"""
    user_id = await get_user_id(event, auto_create=True)
    result = await FarmService.get_status(userId=user_id)
    
    if 'error' in result:
        await send_finish(bai_cao_yuan_cmd, '获取百草园状态失败')
        return
    
    field_data = result
    output = '百草园：\n'
    
    if field_data.get('isGrowing'):
        grow_info = field_data.get('growInfo', {})
        remaining = grow_info.get('remainingSeconds', 0)
        
        if remaining > 60:
            output += f'距离{field_data.get("kusaType")}长成还有{int(remaining // 60)}min\n'
            predict_time_str = grow_info.get('predictFinishTime', '')
            if predict_time_str:
                predict_time = datetime.fromisoformat(predict_time_str)
                output += f'预计生草完成时间：{predict_time.hour:02d}:{predict_time.minute:02d}\n'
        else:
            output += f'你的{field_data.get("kusaType")}将在一分钟内长成！\n'
        
        if grow_info.get('isPrescient'):
            output += f"预知：生草量为{grow_info.get('kusaResult')}"
            if grow_info.get('advKusaResult'):
                output += f"，草之精华获取量为{grow_info.get('advKusaResult')}"
        else:
            min_predict = field_data.get('predictKusaMin', 0)
            max_predict = field_data.get('predictKusaMax', 10)
            output += f'预估生草量：{min_predict} ~ {max_predict}'
        
        output += '\n\n'
    else:
        if field_data.get('isOverloaded'):
            overload_end = field_data.get('overloadEndTime', '')
            if overload_end:
                dt = datetime.fromisoformat(overload_end)
                output += f'土地过载中，无法生草！\n过载结束时间：{dt.hour:02d}:{dt.minute:02d}\n'
            else:
                output += '土地过载中，无法生草！\n'
        else:
            output += '当前没有生草。\n'
    
    default_type = field_data.get('defaultKusaType', '草')
    output += f'你选择的默认草种为：{default_type}\n'
    output += f'当前的土壤承载力为：{field_data.get("soilCapacity")}\n'
    
    spare = field_data.get('spareCapacity', 0)
    if spare:
        output += f'可用后备承载力为：{spare}\n'
    
    show_detail = await base_db.getFlagValue(user_id, '生草预估详情展示')
    calc_details = field_data.get('calculationDetails', {})
    if calc_details and show_detail:
        output += '\n生草数量计算详情:\n'
        output += f"基础生草量：{calc_details.get('baseKusa', '0 ~ 10')}\n"
        
        vip_bonus = calc_details.get('vipBonus', 0)
        if vip_bonus > 0:
            output += f"信息员等级加成：{vip_bonus}\n"
        
        field_amount = calc_details.get('fieldAmount', 1)
        output += f"草地数量 * {field_amount}\n"
        
        if calc_details.get('isUsingKela'):
            output += "施用金坷垃 * 2\n"
        
        biogas_effect = calc_details.get('biogasEffect', 1)
        if biogas_effect != 1:
            output += f"沼气影响 * {biogas_effect}\n"
        
        if calc_details.get('doubleMagic'):
            output += "已掌握双生法术 * 2\n"
        
        if calc_details.get('isMirroring'):
            output += "镜映 * 2\n"
        
        kusa_tech_effect = calc_details.get('kusaTechEffect', 1)
        if kusa_tech_effect > 1:
            output += f"生草科技影响 * {kusa_tech_effect}\n"
        
        kusa_type_effect = calc_details.get('kusaTypeEffect', 1)
        if kusa_type_effect != 1:
            output += f"当前草种影响 * {kusa_type_effect}\n"
        
        if calc_details.get('spiritualSign'):
            output += "灵性保留 * 2\n"
        
        fallow_sign = calc_details.get('fallowSign', 0)
        if fallow_sign > 0 and fallow_sign < 3:
            fallow_effect = [1, 2, 3][fallow_sign]
            output += f"休耕肥力 * {fallow_effect}\n"
        
        soil_effect = calc_details.get('soilEffect', 1)
        if soil_effect < 1:
            output += f"土壤承载力影响 * {soil_effect:.1f}\n"
    
    await send_finish(bai_cao_yuan_cmd, output[:-1])


default_kusa_type_cmd = on_command("默认草种", priority=5, block=True)

@default_kusa_type_cmd.handle()
async def handle_default_kusa_type(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理默认草种命令"""
    user_id = await get_user_id(event, auto_create=True)
    kusa_type = args.extract_plain_text().strip()
    if not kusa_type:
        kusa_type = "草"
    
    result = await FarmService.set_default_type(userId=user_id, kusa_type=kusa_type)
    
    if result['success']:
        await send_finish(default_kusa_type_cmd, result['message'])
    else:
        error_msg = result.get('message', '设置失败')
        await send_finish(default_kusa_type_cmd, error_msg)


recover_capacity_cmd = on_command("承载力补充", aliases={"补充承载力"}, priority=5, block=True)

@recover_capacity_cmd.handle()
async def handle_recover_capacity(
    event: Union[OneBotV11MessageEvent, QQMessageEvent],
    args: Message = CommandArg()
):
    """处理承载力补充命令"""
    user_id = await get_user_id(event, auto_create=True)
    stripped_arg = args.extract_plain_text().strip()
    
    amount = int(stripped_arg) if stripped_arg and stripped_arg.isdigit() else None
    
    result = await FarmService.recover_capacity(userId=user_id, amount=amount)
    
    if not result['success']:
        error_code = result.get('error', 'UNKNOWN_ERROR')
        if error_code == 'ALREADY_FULL':
            await send_finish(recover_capacity_cmd, '当前承载力是满的，无需补充^ ^')
        elif error_code == 'INSUFFICIENT_SPARE':
            available = result.get('available', 0)
            await send_finish(recover_capacity_cmd, f'你的后备承载力不足，当前仅有{available}点后备承载力^ ^')
        else:
            await send_finish(recover_capacity_cmd, '承载力补充失败')
    else:
        recovered = result.get('recovered', 0)
        await send_finish(recover_capacity_cmd, f'承载力补充成功，当前承载力提升了{recovered}点^ ^')


kusa_brief_cmd = on_command("生草简报", priority=5, block=True)

@kusa_brief_cmd.handle()
async def handle_kusa_brief(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理生草简报命令"""
    user_id = await get_user_id(event, auto_create=True)
    stats = await FarmService.get_grass_stats(userId=user_id, period='24小时')
    p = stats['personal']

    if not p['count']:
        await send_finish(kusa_brief_cmd, '最近24小时未生出草！')
        return

    await send_finish(kusa_brief_cmd,
        f'最近24小时共生草{p["count"]}次\n'
        f'收获{p["sumKusa"]}草，平均每次{p["avgKusa"]}草\n'
        f'收获{p["sumAdvKusa"]}草之精华，平均每次{p["avgAdvKusa"]}草之精华'
    )


kusa_daily_cmd = on_command("生草日报", priority=5, block=True)

@kusa_daily_cmd.handle()
async def handle_kusa_daily(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理生草日报命令"""
    user_id = await get_user_id(event, auto_create=True)
    stats = await FarmService.get_grass_stats(userId=user_id, period='昨日')
    p = stats['personal']

    if not p['count']:
        await send_finish(kusa_daily_cmd, '昨日未生出草！')
        return

    await send_finish(kusa_daily_cmd,
        f'昨日共生草{p["count"]}次\n'
        f'收获{p["sumKusa"]}草，平均每次{p["avgKusa"]}草\n'
        f'收获{p["sumAdvKusa"]}草之精华，平均每次{p["avgAdvKusa"]}草之精华'
    )


kusa_weekly_cmd = on_command("生草周报", priority=5, block=True)

@kusa_weekly_cmd.handle()
async def handle_kusa_weekly(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理生草周报命令"""
    user_id = await get_user_id(event, auto_create=True)
    stats = await FarmService.get_grass_stats(userId=user_id, period='上周')
    p = stats['personal']

    if not p['count']:
        await send_finish(kusa_weekly_cmd, '上周未生出草！')
        return

    await send_finish(kusa_weekly_cmd,
        f'上周共生草{p["count"]}次\n'
        f'收获{p["sumKusa"]}草，平均每次{p["avgKusa"]}草\n'
        f'收获{p["sumAdvKusa"]}草之精华，平均每次{p["avgAdvKusa"]}草之精华'
    )


kusa_total_cmd = on_command("生草总计", priority=5, block=True)

@kusa_total_cmd.handle()
async def handle_kusa_total(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理生草总计命令"""
    user_id = await get_user_id(event, auto_create=True)
    stats = await FarmService.get_grass_stats(userId=user_id, period='总计')
    p = stats['personal']

    if not p['count']:
        await send_finish(kusa_total_cmd, '你还没有生草记录！')
        return

    await send_finish(kusa_total_cmd,
        f'历史共生草{p["count"]}次\n'
        f'收获{p["sumKusa"]}草，平均每次{p["avgKusa"]}草\n'
        f'收获{p["sumAdvKusa"]}草之精华，平均每次{p["avgAdvKusa"]}草之精华'
    )


rob_cmd = on_command("围殴", priority=5, block=True)

@rob_cmd.handle()
async def handle_rob(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理围殴命令"""
    global rob_dict
    
    user_id = await get_user_id(event, auto_create=True)
    
    if not is_group_message(event):
        await send_finish(rob_cmd, '只能在群聊中进行围殴^ ^')
        return
    
    if not rob_dict:
        await send_finish(rob_cmd, await build_at_message(event, user_id, '当前没有可围殴对象^ ^'))
        return
    
    unified_user = await getUnifiedUser(user_id)
    if unified_user and unified_user.isRobot:
        await send_finish(rob_cmd, await build_at_message(event, user_id, '机械臂不能围殴^ ^'))
        return
    
    self_rob_flag, has_robbed_flag, rob_records, stop_robbing_ids = False, False, [], []
    
    for rob_id, rob_info in rob_dict.items():
        if user_id == rob_info.targetId:
            self_rob_flag = True
            continue
        if user_id in rob_info.participantIds:
            has_robbed_flag = True
            continue
        
        kusa_robbed = random.randint(round(rob_info.robLimit * 0.04), round(rob_info.robLimit * 0.15))
        await base_db.changeKusa(rob_info.targetId, -kusa_robbed)
        rob_info.robCount += kusa_robbed
        rob_info.participantIds.add(user_id)
        
        target_user = await base_db.getKusaUser(rob_info.targetId)
        target_user_name = target_user.name if target_user and target_user.name else str(rob_info.targetId)

        record = f'围殴 {target_user_name} 成功！你获得了{kusa_robbed}草！'
        user = await base_db.getKusaUser(user_id)
        adv_bonus = 1 if (rob_info.extraKusaAdv and user and user.vipLevel >= 5) else 0
        await base_db.changeKusaAndAdvKusa(user_id, kusa_robbed, adv_bonus)
        if adv_bonus:
            record += '额外获得了1草之精华！'
        rob_records.append(await build_at_message(event, user_id, record))
        
        if rob_info.robCount > rob_info.robLimit:
            stop_robbing_ids.append(rob_id)
    
    if rob_records:
        for record in rob_records:
            await send_finish(rob_cmd, record)
            await asyncio.sleep(0.3)
    elif has_robbed_flag:
        await send_finish(rob_cmd, await build_at_message(event, user_id, '你已经围殴过了^ ^'))
    elif self_rob_flag:
        await send_finish(rob_cmd, await build_at_message(event, user_id, '不能围殴自己^ ^'))
    
    for rob_id in stop_robbing_ids:
        await stop_robbing(rob_id)


async def stop_robbing(rob_id: str):
    """结束围殴"""
    global rob_dict
    if rob_id not in rob_dict:
        return
    
    rob_info = rob_dict.pop(rob_id)
    user = await base_db.getKusaUser(rob_info.targetId)
    user_name = user.name if user and user.name else str(rob_info.targetId)
    
    main_group = plugin_config.get('group', {}).get('main')
    await send_group_msg(main_group, f'本次围殴结束，玩家 {user_name} 一共损失{rob_info.robCount}草！')


async def stop_robbing_timer(duration: int, rob_id: str):
    """围殴定时器"""
    await asyncio.sleep(duration)
    await stop_robbing(rob_id)


async def start_robbing(target_id: int, rob_limit: int, extra_kusa_adv: bool):
    """激活围殴（事件驱动版，阶段 5）

    原 activate_robbing 随喜报发送内联在结算链中；结算下沉后由结算事件
    （core.services.FarmService._send_report 生成的 robbing action）触发。
    """
    global rob_dict
    duration = random.randint(120, 300)

    rob_info = RobInfo(
        targetId=target_id,
        participantIds=set(),
        robCount=0,
        robLimit=rob_limit,
        extraKusaAdv=extra_kusa_adv
    )

    rob_id = str(target_id) + "_" + ''.join(random.choice(string.ascii_letters) for _ in range(8))
    asyncio.create_task(stop_robbing_timer(duration, rob_id))
    rob_dict[rob_id] = rob_info


async def execute_harvest_actions(actions):
    """执行生草结算事件动作

    动作由 core.services.FarmService.settle_field 生成（结算在 scheduler 完成），
    bot 只负责 QQ 侧玩法：私聊提示、主群喜报/悲报、围殴激活。
    调用方：internal_notify.py（scheduler 经 /internal/notify 推送）、
    hidden.py 的 KUSA_FINISH（本地强制收获）。
    """
    main_group = plugin_config.get('group', {}).get('main')

    for act in actions:
        kind = act.get('action')
        if kind == 'private':
            await send_private_msg(act['userId'], act['message'])
        elif kind == 'group':
            await send_group_msg(main_group, act['message'])
        elif kind == 'robbing':
            await start_robbing(act['targetId'], act['robLimit'], act.get('extraKusaAdv', False))


# A1 生草结算已下沉至 scheduler/jobs/farm.py + core.services.FarmService.settle_due_fields（阶段 5）
# A2 承载力基础恢复 / A3 非活跃承载力恢复已下沉至 scheduler/jobs/farm.py（阶段 2）


# 结算链（kusa_harvest/good_news_report/get_chain_bonus/get_overload_bonus/send_report_msg）
# 已整体下沉至 core/services/farm_service.py（阶段 5），QQ 侧玩法经 execute_harvest_actions 事件驱动。
