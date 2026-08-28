"""
A5 G值波动 / A6 G周期重置

从 bot/plugins/kusa_G.py 迁移：
- A5（阶段 2）：生成新 G 值入库。G市图不在 scheduler 生成——bot 侧 G线图命令按需现算
- A6（阶段 4）：重置日 23:45 全用户 G 兑换 + 新周期开启；23:50 发周期总结（含收盘价图）
  群通知经 notifier 推 bot 转发（send_group 动作）
"""

import base64
import io
import logging

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

import core.db.g_value as g_value_db
import core.db.kusa_system as base_db
from core.config import plugin_config
from core.services import GMarketService
from scheduler import notifier

logger = logging.getLogger("scheduler.jobs.gmarket")


async def g_change():
    """G值变化（每 30 分钟，整点/半点触发）"""
    g_values = await g_value_db.getLatestGValues()

    new_values = GMarketService.get_new_g_values({
        'east': g_values.eastValue,
        'south': g_values.southValue,
        'north': g_values.northValue,
        'zhuhai': g_values.zhuhaiValue,
        'shenzhen': g_values.shenzhenValue
    })

    await g_value_db.addNewGValue(
        g_values.cycle, g_values.turn + 1,
        new_values['east'], new_values['south'], new_values['north'],
        new_values['zhuhai'], new_values['shenzhen']
    )

    logger.info(
        f"G值已更新，新的值为：东{new_values['east']} 南{new_values['south']} "
        f"北{new_values['north']} 珠{new_values['zhuhai']} 深{new_values['shenzhen']}"
    )


async def g_reset():
    """G周期重置（重置日 23:45）：全用户 G 自动兑换草、扭秤装置运作、开启新周期"""
    if not GMarketService.reset_date_check():
        return

    all_users = await base_db.getAllKusaUser()
    g_values = await g_value_db.getLatestGValues()

    for user in all_users:
        all_kusa_from_g = await GMarketService.sell_all_g(user.user_id, g_values)
        if all_kusa_from_g > 0:
            logger.info(f'用户{user.user_id}的G已经兑换为{all_kusa_from_g}草')

        creator_result = await GMarketService.process_g_creator_v2(user.user_id)
        if creator_result['success']:
            logger.info(f"用户{user.user_id}的扭秤装置已运作，创造了{creator_result['amount']}个{creator_result['area']}G")

    new_cycle_values = GMarketService.get_new_cycle_values()
    await g_value_db.addNewGValue(
        g_values.cycle + 1, 1,
        new_cycle_values['east'], new_cycle_values['south'], new_cycle_values['north'],
        new_cycle_values['zhuhai'], new_cycle_values['shenzhen']
    )

    main_group = plugin_config.get('group', {}).get('main')
    await notifier.notify_qq('send_group', {
        'groupId': main_group,
        'message': '新的G周期开始了！上个周期的G已经自动兑换为草。'
    })


def _get_g_values_col_map(g_values_list):
    """获取G值列映射"""
    col_map = {'eastValue': [], 'southValue': [], 'northValue': [], 'zhuhaiValue': [], 'shenzhenValue': []}
    for g_values in g_values_list:
        col_map['eastValue'].append(g_values.eastValue)
        col_map['southValue'].append(g_values.southValue)
        col_map['northValue'].append(g_values.northValue)
        col_map['zhuhaiValue'].append(g_values.zhuhaiValue)
        col_map['shenzhenValue'].append(g_values.shenzhenValue)
    return col_map


def _create_g_pic_all(g_values_col_map) -> bytes:
    """创建所有校区G线图（迁移自 kusa_G.py，纯函数无 QQ 依赖）"""
    buf = io.BytesIO()
    plt.plot(list(map(lambda x: x / GMarketService.START_VALUE_MAP['东'], g_values_col_map['eastValue'])), label='East')
    plt.plot(list(map(lambda x: x / GMarketService.START_VALUE_MAP['南'], g_values_col_map['southValue'])), label='South')
    plt.plot(list(map(lambda x: x / GMarketService.START_VALUE_MAP['北'], g_values_col_map['northValue'])), label='North')
    plt.plot(list(map(lambda x: x / GMarketService.START_VALUE_MAP['珠'], g_values_col_map['zhuhaiValue'])), label='Zhuhai')
    plt.plot(list(map(lambda x: x / GMarketService.START_VALUE_MAP['深'], g_values_col_map['shenzhenValue'])), label='Shenzhen')
    plt.xticks([])
    plt.yscale('log')
    plt.legend()
    plt.savefig(buf, format='png')
    plt.close()
    return buf.getvalue()


async def g_reset_summary():
    """G周期重置总结（重置日 23:50）：G神盈亏 + 收盘价 + 上周期G线图"""
    if not GMarketService.reset_date_check():
        return

    main_group = plugin_config.get('group', {}).get('main')

    summary_result = await GMarketService.get_cycle_summary()

    if summary_result['has_records']:
        output_str = (f"上周期的G神为 {summary_result['max_display_name']} 和 {summary_result['min_display_name']}：\n"
                     f"{summary_result['max_display_name']}在G市盈利{summary_result['max_profit']:,}草\n"
                     f"{summary_result['min_display_name']}在G市盈利{summary_result['min_profit']:,}草\n")

        output_str += '\n上周期各G的收盘价为：\n'
        area_value_key_map = {
            '东': 'east_value',
            '南': 'south_value',
            '北': 'north_value',
            '珠': 'zhuhai_value',
            '深': 'shenzhen_value'
        }
        for area in ['东', '南', '北', '珠', '深']:
            end_value = summary_result['end_values'][area_value_key_map[area]]
            start_value = GMarketService.START_VALUE_MAP[area]
            output_str += GMarketService.format_g_value(end_value, start_value, area.replace('珠', '珠海').replace('深', '深圳'))

        # 生成上周期的G线图（裸 base64 经通知通道下发，bot 端组装 MessageSegment）
        last_cycle_g_value = await g_value_db.getLastCycleGValues()
        pic_data = _create_g_pic_all(_get_g_values_col_map(last_cycle_g_value))

        await notifier.notify_qq('send_group', {'groupId': main_group, 'message': output_str})
        await notifier.notify_qq('send_group', {
            'groupId': main_group,
            'message': {'imageBase64': base64.b64encode(pic_data).decode()}
        })
    else:
        await notifier.notify_qq('send_group', {
            'groupId': main_group,
            'message': "上周期暂无G市交易记录"
        })


def register(scheduler):
    """注册G市任务（参数与原 bot 侧一致）"""
    scheduler.add_job(
        g_change, 'cron',
        minute='*/30', misfire_grace_time=None,
        id='gmarket_g_change', name='A5 G值波动',
    )
    scheduler.add_job(
        g_reset, 'cron',
        hour='23', minute='45', misfire_grace_time=None,
        id='gmarket_g_reset', name='A6 G周期重置',
    )
    scheduler.add_job(
        g_reset_summary, 'cron',
        hour='23', minute='50', misfire_grace_time=None,
        id='gmarket_g_reset_summary', name='A6 G周期重置总结',
    )
