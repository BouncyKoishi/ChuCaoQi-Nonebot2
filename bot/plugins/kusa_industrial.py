"""
工业系统插件 - NoneBot2 版本
包含生草工厂、草精炼厂、每日产量统计等功能
"""

import math
import random
from typing import Union
from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot

import dbConnection.kusa_system as base_db
import dbConnection.kusa_item as item_db
import dbConnection.kusa_field as field_db
from kusa_base import send_log, is_super_admin, plugin_config, send_group_msg
from services import IndustrialService
from . import scheduler
from multi_platform import (
    get_user_id,
    send_finish,
)


INDUSTRIAL_ITEMS = [
    '生草机器', '生草工厂', '流动生草工厂', '草精炼厂',
    '核心装配工厂', '红茶池', '奖券印刷机',
    '高效草精炼指南', '七曜精炼术', '草精炼厂效率I', '草精炼厂效率II',
    '蕾米球的生产魔法', '冰雪酱的休耕魔法',
    '生草工业园区蓝图', '产业链优化'
]

INDUSTRIAL_TECHS = [
    '试做型机器', '生草工厂新型设备', '生草工厂效率', '生草工厂自动工艺', '核心工厂效率'
]


# ==================== 命令处理器 ====================

daily_output_cmd = on_command("每日产量", priority=5, block=True)

@daily_output_cmd.handle()
async def handle_daily_output(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理每日产量命令"""
    user_id = await get_user_id(event, auto_create=True)
    user = await base_db.getKusaUser(user_id)
    user_name = user.name if user.name else str(user.user_id)

    # 使用 Service 层计算每日产量
    production = await IndustrialService.calculate_daily_production(userId=user_id)

    new_kusa_amount = production['kusaAmount']
    new_adv_kusa_amount = production['advKusaAmount']
    new_core_amount = production['coreAmount']

    output_str = f'{user_name}的每日工业期望产量：{new_kusa_amount}草，'
    if new_adv_kusa_amount:
        output_str += f'{new_adv_kusa_amount}草之精华，'
    if new_core_amount:
        output_str += f'{new_core_amount}自动化核心，'
    output_str = output_str[:-1]

    # 蕾米球的生产魔法加成
    if production.get('remiProductionMagic') and production.get('remiBonus', 0) > 0:
        remi_bonus = production['remiBonus']
        output_str += f'\n由于蕾米球的生产魔法，你将额外获得：{math.ceil(new_kusa_amount * remi_bonus)}草，'
        if new_adv_kusa_amount:
            output_str += f'{math.ceil(new_adv_kusa_amount * remi_bonus)}草之精华，'
        if new_core_amount:
            output_str += f'{math.ceil(new_core_amount * remi_bonus)}自动化核心，'
        output_str = output_str[:-1]

    await send_finish(daily_output_cmd, output_str)


force_industrial_cmd = on_command("强制工业", priority=5, block=True)

@force_industrial_cmd.handle()
async def handle_force_industrial(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理强制工业命令（仅超级管理员可用）"""
    user_id = await get_user_id(event, auto_create=True)
    
    if not await is_super_admin(user_id):
        await send_finish(force_industrial_cmd, '你没有权限执行此命令！')
        return
    
    await force_industrial_cmd.send('开始强制执行工业生产...')
    await daily_industrial()
    await send_finish(force_industrial_cmd, '工业生产执行完成！')


# ==================== 定时任务 ====================

if scheduler:
    @scheduler.scheduled_job('cron', hour=0, misfire_grace_time=None)
    async def daily_industrial_runner():
        """每日工业运作定时器"""
        await daily_industrial()


async def daily_industrial():
    """每日工业运作"""
    kusa_rand_int = random.randint(4, 12)
    core_rand_int = random.randint(4, 12)
    sign_str = f'今日工业运作开始！\n生草机器产量：{kusa_rand_int}\n核心装配工厂产量：{core_rand_int}'
    
    print(sign_str)
    
    env = plugin_config.get('env', 'dev')
    if env == 'prod':
        main_group = plugin_config.get('group', {}).get('main')
        await send_group_msg(main_group, sign_str)
    
    user_list = await base_db.getAllKusaUser()
    user_id_list = [user.user_id for user in user_list]

    print('正在批量获取用户数据...')
    item_amounts = await item_db.batchGetItemAmounts(user_id_list, INDUSTRIAL_ITEMS)
    tech_levels = await item_db.batchGetTechLevels(user_id_list, INDUSTRIAL_TECHS)
    kusa_fields = await field_db.batchGetKusaField(user_id_list)
    
    item_storage_info = await item_db.batchGetItemStorage(user_id_list, ['草精炼厂', '蕾米球的生产魔法', '冰雪酱的休耕魔法'])
    
    remi_magic_users = [
        user_id for user_id in user_id_list
        if item_storage_info.get(user_id, {}).get('蕾米球的生产魔法') and
           item_storage_info[user_id]['蕾米球的生产魔法'].allowUse
    ]
    
    used_capacities = {}
    if remi_magic_users:
        print(f'正在批量消耗{len(remi_magic_users)}个蕾米球用户的承载力...')
        used_capacities = await field_db.batchKusaSoilUseUp(remi_magic_users)
    
    kusa_updates = {}
    adv_kusa_updates = {}
    item_updates = []
    
    for user in user_list:
        user_id = user.user_id
        items = item_amounts.get(user_id, {})
        techs = tech_levels.get(user_id, {})
        kusa_field = kusa_fields.get(user_id)
        
        new_kusa_amount = calculate_daily_kusa_num(items, techs, kusa_rand_int, item_storage_info.get(user_id, {}).get('草精炼厂'))
        new_adv_kusa_amount = calculate_daily_adv_kusa_num(items, item_storage_info.get(user_id, {}))
        new_core_amount = calculate_daily_core_num(items, techs, core_rand_int)
        new_black_tea_amount = calculate_daily_black_tea_num(items)
        
        remi_magic_info = item_storage_info.get(user_id, {}).get('蕾米球的生产魔法')
        if remi_magic_info and remi_magic_info.allowUse and kusa_field:
            extra_magnification = max(0.04 * (kusa_field.soilCapacity - 20), 0)
            new_kusa_amount = math.ceil(new_kusa_amount * (1 + extra_magnification))
            new_adv_kusa_amount = math.ceil(new_adv_kusa_amount * (1 + extra_magnification))
            new_core_amount = math.ceil(new_core_amount * (1 + extra_magnification))
            new_black_tea_amount = math.ceil(new_black_tea_amount * (1 + extra_magnification))
            
            overload_time = 12 * 3600
            used_capacity = used_capacities.get(user_id, 0)
            if used_capacity:
                print(f'{user_id}消耗了{used_capacity}承载量，发动了蕾米球的生草魔法！')
                icy_magic_info = item_storage_info.get(user_id, {}).get('冰雪酱的休耕魔法')
                if icy_magic_info and icy_magic_info.allowUse:
                    print(f'{user_id}发动了冰雪酱的休耕魔法！')
                    await item_db.updateTimeLimitedItem(user_id, '休耕标记', 86300, 2)
                    overload_time = 9 * 3600
            await item_db.updateTimeLimitedItem(user_id, '过载标记', overload_time)
        
        kusa_updates[user_id] = new_kusa_amount
        adv_kusa_updates[user_id] = new_adv_kusa_amount
        
        if new_core_amount != 0:
            item_updates.append((user_id, '自动化核心', new_core_amount))
        if new_black_tea_amount != 0:
            item_updates.append((user_id, '红茶', new_black_tea_amount))
        
        machine_amount = items.get('奖券印刷机', 0)
        if machine_amount > 0:
            normal_ticket, rare_ticket, super_ticket = 0, 0, 0
            for _ in range(machine_amount):
                rand_int = random.randint(1, 8)
                if rand_int <= 5:
                    normal_ticket += 1
                elif rand_int <= 7:
                    rare_ticket += 1
                else:
                    super_ticket += 1
            if normal_ticket > 0:
                item_updates.append((user_id, '十连券', normal_ticket))
            if rare_ticket > 0:
                item_updates.append((user_id, '高级十连券', rare_ticket))
            if super_ticket > 0:
                item_updates.append((user_id, '特级十连券', super_ticket))
    
    print('正在批量更新用户资源...')
    await base_db.batchChangeKusa(kusa_updates)
    await base_db.batchChangeAdvKusa(adv_kusa_updates)
    await item_db.batchChangeItemAmounts(item_updates)
    
    print('所有每日工业运作完成！')
    await send_log('所有每日工业运作完成！')


# ==================== 计算函数 ====================

def calculate_daily_kusa_num(items, techs, machine_rand_int, adv_factory_storage_info=None):
    """计算每日生草数量"""
    machine_amount = items.get('生草机器', 0)
    machine_tech_level = techs.get('试做型机器', 0)
    machine_add_kusa = machine_rand_int * machine_amount
    machine_add_kusa *= {0: 1, 1: 8, 2: 40}.get(machine_tech_level, 1)
    
    factory_amount = items.get('生草工厂', 0)
    mobile_factory_amount = items.get('流动生草工厂', 0)
    factory_new_device_level = techs.get('生草工厂新型设备', 0)
    factory_tech_level = techs.get('生草工厂效率', 0)
    factory_add_kusa = 640 * (factory_amount + mobile_factory_amount)
    factory_add_kusa *= (2 ** factory_new_device_level)
    factory_add_kusa *= (2 ** factory_tech_level)
    
    adv_factory_cost_kusa = 0
    if adv_factory_storage_info and adv_factory_storage_info.allowUse:
        adv_factory_cost_kusa = 5000 * adv_factory_storage_info.amount
    
    return math.ceil(machine_add_kusa + factory_add_kusa - adv_factory_cost_kusa)


def calculate_daily_adv_kusa_num(items, storage_info):
    """计算每日草之精华数量"""
    adv_factory_info = storage_info.get('草精炼厂')
    if not adv_factory_info or not adv_factory_info.allowUse:
        return 0
    
    adv_factory_amount = adv_factory_info.amount
    adv_kusa_base_addition = items.get('高效草精炼指南', 0)
    seven_planet_magic = items.get('七曜精炼术', 0)
    adv_kusa_addition_i = items.get('草精炼厂效率I', 0)
    adv_kusa_addition_ii = items.get('草精炼厂效率II', 0)
    
    adv_kusa = adv_factory_amount
    adv_kusa += (adv_factory_amount // 7) * 4 if seven_planet_magic else 0
    adv_kusa += (adv_factory_amount - 7) if adv_kusa_addition_i and adv_factory_amount > 7 else 0
    
    if adv_kusa_base_addition:
        addition_count = min(adv_kusa_base_addition, adv_factory_amount)
        adv_kusa += addition_count
        if adv_kusa_addition_ii:
            adv_kusa += (addition_count * (addition_count - 1))
    
    return adv_kusa


def calculate_daily_core_num(items, techs, core_factory_rand_int):
    """计算每日核心数量"""
    core_factory_amount = items.get('核心装配工厂', 0)
    core_tech_level = techs.get('核心工厂效率', 0)
    add_core = core_factory_rand_int * core_factory_amount
    add_core *= {0: 1, 1: 2, 2: 4, 3: 8, 4: 12}.get(core_tech_level, 1)
    return math.ceil(add_core)


def calculate_daily_black_tea_num(items):
    """计算每日红茶数量"""
    black_tea_pool = items.get('红茶池', 0)
    return 15 * black_tea_pool


async def get_daily_kusa_num(user_id, machine_rand_int):
    """获取每日生草数量（异步版本）"""
    machine_amount = await item_db.getItemAmount(user_id, '生草机器')
    machine_tech_level = await item_db.getTechLevel(user_id, '试做型机器')
    machine_add_kusa = machine_rand_int * machine_amount
    machine_add_kusa *= {0: 1, 1: 8, 2: 40}.get(machine_tech_level, 1)
    
    factory_amount = await item_db.getItemAmount(user_id, '生草工厂')
    mobile_factory_amount = await item_db.getItemAmount(user_id, '流动生草工厂')
    factory_new_device_level = await item_db.getTechLevel(user_id, '生草工厂新型设备')
    factory_tech_level = await item_db.getTechLevel(user_id, '生草工厂效率')
    factory_add_kusa = 640 * (factory_amount + mobile_factory_amount)
    factory_add_kusa *= (2 ** factory_new_device_level)
    factory_add_kusa *= (2 ** factory_tech_level)
    
    adv_factory_info = await item_db.getItemStorageInfo(user_id, '草精炼厂')
    adv_factory_cost_kusa = 5000 * adv_factory_info.amount if adv_factory_info and adv_factory_info.allowUse else 0
    
    return math.ceil(machine_add_kusa + factory_add_kusa - adv_factory_cost_kusa)


async def get_daily_adv_kusa_num(user_id):
    """获取每日草之精华数量（异步版本）"""
    adv_factory_info = await item_db.getItemStorageInfo(user_id, '草精炼厂')
    if not adv_factory_info or not adv_factory_info.allowUse:
        return 0
    
    adv_kusa_base_addition = await item_db.getItemAmount(user_id, '高效草精炼指南')
    seven_planet_magic = await item_db.getItemAmount(user_id, '七曜精炼术')
    adv_kusa_addition_i = await item_db.getItemAmount(user_id, '草精炼厂效率I')
    adv_kusa_addition_ii = await item_db.getItemAmount(user_id, '草精炼厂效率II')
    
    adv_kusa = adv_factory_info.amount
    adv_kusa += (adv_factory_info.amount // 7) * 4 if seven_planet_magic else 0
    adv_kusa += (adv_factory_info.amount - 7) if adv_kusa_addition_i and adv_factory_info.amount > 7 else 0
    
    if adv_kusa_base_addition:
        addition_count = min(adv_kusa_base_addition, adv_factory_info.amount)
        adv_kusa += addition_count
        if adv_kusa_addition_ii:
            adv_kusa += (addition_count * (addition_count - 1))
    
    return adv_kusa


async def get_daily_core_num(user_id, core_factory_rand_int):
    """获取每日核心数量（异步版本）"""
    core_factory_amount = await item_db.getItemAmount(user_id, '核心装配工厂')
    core_tech_level = await item_db.getTechLevel(user_id, '核心工厂效率')
    add_core = core_factory_rand_int * core_factory_amount
    add_core *= {0: 1, 1: 2, 2: 4, 3: 8, 4: 12}.get(core_tech_level, 1)
    return math.ceil(add_core)


async def get_daily_black_tea_num(user_id):
    """获取每日红茶数量（异步版本）"""
    black_tea_pool = await item_db.getItemAmount(user_id, '红茶池')
    return 15 * black_tea_pool


async def create_lottery_ticket(user_id):
    """奖券印刷机生产十连券"""
    machine_amount = await item_db.getItemAmount(user_id, '奖券印刷机')
    if machine_amount == 0:
        return
    
    normal_ticket, rare_ticket, super_ticket = 0, 0, 0
    for _ in range(machine_amount):
        rand_int = random.randint(1, 8)
        if rand_int <= 5:
            normal_ticket += 1
        elif rand_int <= 7:
            rare_ticket += 1
        else:
            super_ticket += 1
    
    if normal_ticket > 0:
        await item_db.changeItemAmount(user_id, '十连券', normal_ticket)
    if rare_ticket > 0:
        await item_db.changeItemAmount(user_id, '高级十连券', rare_ticket)
    if super_ticket > 0:
        await item_db.changeItemAmount(user_id, '特级十连券', super_ticket)
