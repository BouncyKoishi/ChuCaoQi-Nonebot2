"""
工业系统插件 - NoneBot2 版本
包含生草工厂、草精炼厂、每日产量统计等功能
定时批量结算已下沉至 scheduler 进程（core.services.IndustrialService.settle_all_daily）
"""

from typing import Union
from reloader import kusa_command as on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot

import core.db.kusa_system as base_db
import core.db.user as user_db
from kusa_base import send_log, is_super_admin
from core.services import IndustrialService
from multi_platform import (
    get_user_id,
    send_finish,
)


# ==================== 命令处理器 ====================

daily_output_cmd = on_command("每日产量", priority=5, block=True)

@daily_output_cmd.handle()
async def handle_daily_output(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理每日产量命令"""
    user_id = await get_user_id(event, auto_create=True)
    user = await base_db.getKusaUser(user_id)
    user_qq = await user_db.getRealQQByUserId(user_id)
    user_name = user.name if user.name else (user_qq or str(user.user_id))

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
# A7 每日工业生产已下沉至 scheduler/jobs/industrial.py（阶段 4），
# 批量结算逻辑位于 core.services.IndustrialService.settle_all_daily()


async def daily_industrial():
    """每日工业运作（供"强制工业"命令调用；定时执行在 scheduler 进程）"""
    result = await IndustrialService.settle_all_daily()
    print(result['signStr'])
    print('所有每日工业运作完成！')
    await send_log('所有每日工业运作完成！')


