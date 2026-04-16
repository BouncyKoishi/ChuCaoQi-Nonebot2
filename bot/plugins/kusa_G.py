"""
G市系统插件 - NoneBot2 版本
包含G值查询、G买入/卖出、交易记录、G线图等功能
"""

import io
import re
import codecs
import random
from typing import Optional, Dict, Union
from datetime import datetime
from collections import Counter

from reloader import kusa_command as on_command
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, Bot as OneBotV11Bot
from nonebot.adapters.qq import MessageEvent as QQMessageEvent, Bot as QQBot
from nonebot.params import CommandArg
from nonebot.adapters import Message, Bot

from kusa_base import plugin_config, send_group_msg
from utils import imgBytesToBase64
import dbConnection.kusa_system as base_db
import dbConnection.g_value as g_value_db
from services import GMarketService
from .pagination_helper import register_pagination_handler, set_pagination_state
from . import scheduler
from multi_platform import (
    get_user_id,
    is_onebot_v11_event,
    is_qq_event,
    send_finish,
)

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

systemRandom = random.SystemRandom()
g_pic_cache: Dict[str, Optional[bytes]] = {
    '东': None,
    '南': None,
    '北': None,
    '珠': None,
    '深': None,
    'all': None,
}


# ==================== G市查询命令 ====================

check_g_cmd = on_command("测G", priority=5, block=True)

@check_g_cmd.handle()
async def handle_check_g(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理测G命令"""
    user_id = await get_user_id(event, auto_create=True)
    
    status = await GMarketService.get_status()
    holdings = await GMarketService.get_all_holdings(user_id)
    
    st = 'G市有风险，炒G需谨慎！\n'
    if status['turn'] != 1:
        st += '当前G值为：\n'
        for area in ['东', '南', '北', '珠', '深']:
            value_field = GMarketService.AREA_MAP[area][1]
            value_key = value_field.replace('Value', '_value').lower()
            current = status['values'][value_key]
            last = status['values'][f"{value_key}_last"]
            st += GMarketService.format_g_value(current, last, area)
        st += f'当前为本周期第{status["turn"]}期数值。\n\n'
    else:
        st += f'当前为本周期的第一期数值！\n当前G值为：\n'
        for area in ['东', '南', '北', '珠', '深']:
            start_val = GMarketService.START_VALUE_MAP[area]
            st += f'{GMarketService.AREA_MAP[area][0].replace("G(", "").replace(")", "")}：{start_val}\n'
        st += '\n'
    
    st += '您拥有的G：\n'
    has_g = False
    for area in ['东', '南', '北', '珠', '深']:
        amount = holdings[area]
        if amount > 0:
            campus_name = GMarketService.AREA_MAP[area][0].replace('G(', '').replace(')', '')
            st += f'{campus_name}： {amount}\n'
            has_g = True
    if not has_g:
        st += '您当前没有任何G!\n'
    
    st += '\n使用 !G市帮助 可以查看G市交易相关指令。'
    await send_finish(check_g_cmd, st[:-1])


# G市帮助命令
g_help_cmd = on_command("G市帮助", priority=5, block=True)

@g_help_cmd.handle()
async def handle_g_help(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理G市帮助命令"""
    try:
        with codecs.open('text/生草系统-G市帮助.txt', 'r', 'utf-8') as f:
            await send_finish(g_help_cmd, f.read().strip())
    except FileNotFoundError:
        await send_finish(g_help_cmd, '帮助文件未找到')


# 测F命令
check_f_cmd = on_command("测F", priority=5, block=True)

@check_f_cmd.handle()
async def handle_check_f(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理测F命令"""
    await send_finish(check_f_cmd, '啊，这……')


# 测H命令
check_h_cmd = on_command("测H", priority=5, block=True)

@check_h_cmd.handle()
async def handle_check_h(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理测H命令"""
    await send_finish(check_h_cmd, '您不够H^ ^')


# 测*命令
check_star_cmd = on_command("测*", priority=5, block=True)

@check_star_cmd.handle()
async def handle_check_star(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理测*命令"""
    await send_finish(check_star_cmd, '*^ ^*')


# 交易总结命令
trade_summary_cmd = on_command("交易总结", priority=5, block=True)

@trade_summary_cmd.handle()
async def handle_trade_summary(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理交易总结命令"""
    if not await GMarketService.check_trading_time():
        await send_finish(trade_summary_cmd, '请在G市结算完成后再查询交易总结^ ^')
        return
    
    user_id = await get_user_id(event, auto_create=True)
    
    summary = await GMarketService.get_trade_summary(user_id)
    
    st = '您本周期的G市交易总结：\n'
    st += f"当前持仓相当于{summary['now_kusa_in_g']:,}草，本周期共投入{summary['all_cost_kusa']:,}草，共取出{summary['all_gain_kusa']:,}草。\n"
    st += f"本周期盈亏估值：{summary['profit']:,}草。\n\n"
    
    if not summary['has_holdings']:
        st += '您当前在G市暂无持仓。\n'
    else:
        st += '您的具体持仓如下：\n'
        for area in ['东', '南', '北', '珠', '深']:
            holding = summary['holdings'][area]
            if holding['amount'] > 0:
                campus_name = GMarketService.AREA_MAP[area][0].replace('G(', '').replace(')', '')
                st += f"{campus_name}： {holding['amount']}G * {holding['value']:.3f} = {holding['kusa_value']:,}草\n"
    
    await send_finish(trade_summary_cmd, st[:-1])


# 上期交易总结命令
last_trade_summary_cmd = on_command("上期交易总结", priority=5, block=True)

@last_trade_summary_cmd.handle()
async def handle_last_trade_summary(event: Union[OneBotV11MessageEvent, QQMessageEvent]):
    """处理上期交易总结命令"""
    if not await GMarketService.check_trading_time():
        await send_finish(last_trade_summary_cmd, '请在G市结算完成后再查询上期交易总结^ ^')
        return
    
    user_id = await get_user_id(event, auto_create=True)
    
    summary = await GMarketService.get_last_cycle_summary(user_id)
    
    st = '您上周期的G市交易总结：\n'
    st += f"上周期共投入{summary['all_cost_kusa']:,}草，共取出{summary['all_gain_kusa']:,}草，总盈亏：{summary['profit']:,}草。"
    await send_finish(last_trade_summary_cmd, st)


# 交易记录命令 - 支持全局翻页
trade_record_cmd = on_command("交易记录", priority=5, block=True)

@trade_record_cmd.handle()
async def handle_trade_record(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理交易记录命令"""
    user_id = await get_user_id(event, auto_create=True)
    
    records_result = await GMarketService.get_trade_records(user_id, page=1, page_size=10)
    
    if not records_result['records']:
        await send_finish(trade_record_cmd, '您本周期暂无G市交易记录= =')
        return
    
    if records_result['total_pages'] > 1:
        set_pagination_state(str(user_id), 'trade_record', {
            'user_id': user_id,
            'current_page': 1,
            'total_pages': records_result['total_pages'],
            'page_size': 10
        })
    
    output_str = await format_trade_records(records_result['records'], records_result['page'], records_result['total_pages'])
    
    if records_result['total_pages'] > 1:
        output_str += f"\n(共{records_result['total_pages']}页，输入!下一页或!上一页翻页)"
    
    await send_finish(trade_record_cmd, output_str)


async def format_trade_records(records: list, current_page: int, total_pages: int) -> str:
    """格式化交易记录"""
    output_str = f'您本周期的G市交易记录如下(第{current_page}/{total_pages}页)：\n'
    for record in records:
        record_time = datetime.fromtimestamp(record['timestamp']).strftime('%m-%d %H:%M')
        if record['type'] == 'buy':
            output_str += f"{record_time}：买入{record['g_amount']}{record['g_name']}，花费{record['kusa_amount']:,}草，等效单价为{record['unit_price']}\n"
        else:
            output_str += f"{record_time}：卖出{record['g_amount']}{record['g_name']}，获得{record['kusa_amount']:,}草，等效单价为{record['unit_price']}\n"
    return output_str[:-1]  # 去掉最后的换行


# ==================== G买入/卖出命令 ====================

g_buy_cmd = on_command("G买入", priority=5, block=True)

@g_buy_cmd.handle()
async def handle_g_buy(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理G买入命令"""
    if not await GMarketService.check_trading_time():
        await send_finish(g_buy_cmd, '当前是结算时间，无法进行G交易^ ^')
        return

    user_id = await get_user_id(event, auto_create=True)
    st = ''
    stripped_arg = args.extract_plain_text().strip()
    buying_amount = re.findall(r'\d+', stripped_arg)
    buying_amount = int(buying_amount[0]) if buying_amount else 0
    is_buying_all = bool(re.findall(r'all', stripped_arg))
    school_ratio = Counter()
    school_ratio.update(re.findall(r'[东南北珠深]', stripped_arg))
    
    area_ratios = {}
    for school_name in '东南北珠深':
        ratio = school_ratio.get(school_name)
        if ratio is not None:
            area_ratios[school_name] = ratio
    
    if not area_ratios:
        await send_finish(g_buy_cmd, '参数不正确^ ^')
        return
    
    result = await GMarketService.buy_g(user_id, buying_amount, area_ratios, is_buying_all)
    
    if result['success']:
        for trade in result['trades']:
            st += f"花费{trade['cost']:,}草，买入了{trade['amount']}{trade['g_type']}\n"
        st = st.strip()
    else:
        st = result['message']
    
    await send_finish(g_buy_cmd, st)


g_sell_cmd = on_command("G卖出", priority=5, block=True)

@g_sell_cmd.handle()
async def handle_g_sell(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理G卖出命令"""
    if not await GMarketService.check_trading_time():
        await send_finish(g_sell_cmd, '当前是结算时间，无法进行G交易^ ^')
        return

    user_id = await get_user_id(event, auto_create=True)
    st = ''
    stripped_arg = args.extract_plain_text().strip()
    selling_amount = re.findall(r'\d+', stripped_arg)
    selling_amount = int(selling_amount[0]) if selling_amount else 0
    is_selling_all = bool(re.findall(r'all', stripped_arg))
    school_ratio = Counter()
    school_ratio.update(re.findall(r'[东南北珠深]', stripped_arg))
    
    area_ratios = {}
    for school_name in '东南北珠深':
        ratio = school_ratio.get(school_name)
        if ratio is not None:
            area_ratios[school_name] = ratio
    
    result = await GMarketService.sell_g(user_id, selling_amount, area_ratios, is_selling_all)
    
    if result['success']:
        if result['sell_all']:
            await send_finish(g_sell_cmd, f"已卖出所有G，获得了{result['total_kusa']:,}草")
            return
        for trade in result['trades']:
            st += f"卖出了{trade['amount']}{trade['g_type']}，获得了{trade['gain']:,}草\n"
        st = st.strip()
    else:
        st = result['message']
    
    await send_finish(g_sell_cmd, st)


# ==================== G线图命令 ====================

g_pic_cmd = on_command("G线图", priority=5, block=True)

@g_pic_cmd.handle()
async def handle_g_pic(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    """处理G线图命令"""
    stripped_arg = args.extract_plain_text().strip()
    school = re.findall(r'[东南北珠深]', stripped_arg)
    school = school[0] if school and school[0] in '东南北珠深' else 'all'
    
    if g_pic_cache[school] is None:
        await create_g_pic()
    
    # 根据平台使用不同的图片发送方式
    if is_onebot_v11_event(event):
        # OneBot V11 使用 base64 图片
        pic = imgBytesToBase64(g_pic_cache[school])
        await send_finish(g_pic_cmd, pic)
    elif is_qq_event(event):
        # QQ 官方 Bot 使用 file_image
        from nonebot.adapters.qq import MessageSegment as QQMS
        pic = QQMS.file_image(g_pic_cache[school])
        await send_finish(g_pic_cmd, pic)
    else:
        await send_finish(g_pic_cmd, "当前平台不支持图片发送")


def get_g_values_col_map(g_values_list):
    """获取G值列映射"""
    g_values_col_map = {'eastValue': [], 'southValue': [], 'northValue': [], 'zhuhaiValue': [], 'shenzhenValue': []}
    for g_values in g_values_list:
        g_values_col_map['eastValue'].append(g_values.eastValue)
        g_values_col_map['southValue'].append(g_values.southValue)
        g_values_col_map['northValue'].append(g_values.northValue)
        g_values_col_map['zhuhaiValue'].append(g_values.zhuhaiValue)
        g_values_col_map['shenzhenValue'].append(g_values.shenzhenValue)
    return g_values_col_map


async def create_g_pic():
    """创建G线图"""
    global g_pic_cache
    start_ts = datetime.now().timestamp()
    g_values_list = await g_value_db.getThisCycleGValues()
    g_values_col_map = get_g_values_col_map(g_values_list)
    
    for school in '东南北珠深':
        g_type = area_translate_value(school)
        g_pic_cache[school] = create_g_pic_single(g_values_col_map[g_type])
    
    g_pic_cache['all'] = create_g_pic_all(g_values_col_map)
    end_ts = datetime.now().timestamp()
    print(f'G线图生成时间：{end_ts - start_ts}')


def create_g_pic_single(g_values_col):
    """创建单个校区G线图"""
    buf = io.BytesIO()
    plt.plot(g_values_col)
    plt.xticks([])
    plt.savefig(buf, format='png')
    plt.close()
    return buf.getvalue()


def create_g_pic_all(g_values_col_map):
    """创建所有校区G线图"""
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


# ==================== 定时任务 ====================

if scheduler:
    @scheduler.scheduled_job('cron', minute='*/30', misfire_grace_time=None)
    async def g_change_runner():
        """G值变化定时器"""
        g_values = await g_value_db.getLatestGValues()
        
        # 使用服务层生成新G值
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
        
        now_time = datetime.now().strftime('%H:%M')
        print(f"{now_time}: G值已更新，新的值为：东{new_values['east']} 南{new_values['south']} 北{new_values['north']} 珠{new_values['zhuhai']} 深{new_values['shenzhen']}")
        await create_g_pic()
    
    @scheduler.scheduled_job('cron', hour='23', minute='45', misfire_grace_time=None)
    async def g_reset_runner():
        """G周期重置定时器"""
        if not GMarketService.reset_date_check():
            return
        
        all_users = await base_db.getAllKusaUser()
        g_values = await g_value_db.getLatestGValues()
        bot = get_bot()
        main_group = plugin_config.get('group', {}).get('main')
        
        for user in all_users:
            all_kusa_from_g = await GMarketService.sell_all_g(user.user_id, g_values)
            if all_kusa_from_g > 0:
                print(f'用户{user.user_id}的G已经兑换为{all_kusa_from_g}草')
            
            creator_result = await GMarketService.process_g_creator_v2(user.user_id)
            if creator_result['success']:
                print(f"用户{user.user_id}的扭秤装置已运作，创造了{creator_result['amount']}个{creator_result['area']}G")
        
        # 使用服务层获取新周期初始值
        new_cycle_values = GMarketService.get_new_cycle_values()
        await g_value_db.addNewGValue(
            g_values.cycle + 1, 1,
            new_cycle_values['east'], new_cycle_values['south'], new_cycle_values['north'],
            new_cycle_values['zhuhai'], new_cycle_values['shenzhen']
        )
        
        await bot.send_group_msg(group_id=main_group, message='新的G周期开始了！上个周期的G已经自动兑换为草。')
    
    @scheduler.scheduled_job('cron', hour='23', minute='50', misfire_grace_time=None)
    async def g_reset_summary_runner():
        """G周期重置总结定时器"""
        if not GMarketService.reset_date_check():
            return
        
        main_group = plugin_config.get('group', {}).get('main')
        
        # 使用服务层获取上周期总结
        summary_result = await GMarketService.get_cycle_summary()
        
        if summary_result['has_records']:
            output_str = (f"上周期的G神为 {summary_result['max_user_name']} 和 {summary_result['min_user_name']}：\n"
                         f"{summary_result['max_user_name']}在G市盈利{summary_result['max_profit']:,}草\n"
                         f"{summary_result['min_user_name']}在G市盈利{summary_result['min_profit']:,}草\n")
            
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
                campus_name = GMarketService.AREA_MAP[area][0].replace('G(', '').replace(')', '')
                output_str += GMarketService.format_g_value(end_value, start_value, area.replace('珠', '珠海').replace('深', '深圳'))
            
            # 生成上周期的G线图
            last_cycle_g_value = await g_value_db.getLastCycleGValues()
            pic_data = create_g_pic_all(get_g_values_col_map(last_cycle_g_value))
            
            # 获取Bot实例并根据平台发送
            from multi_platform import get_napcat_bot, is_onebot_v11_bot, is_qq_bot
            bot = get_napcat_bot()
            if bot:
                if is_onebot_v11_bot(bot):
                    # OneBot V11 使用 base64 图片
                    from utils import imgBytesToBase64
                    pic = imgBytesToBase64(pic_data)
                    await send_group_msg(main_group, output_str)
                    await send_group_msg(main_group, pic)
                elif is_qq_bot(bot):
                    # QQ 官方 Bot 使用 file_image
                    from nonebot.adapters.qq import MessageSegment as QQMS
                    await send_group_msg(main_group, output_str)
                    pic = QQMS.file_image(pic_data)
                    await send_group_msg(main_group, pic)
                else:
                    await send_group_msg(main_group, output_str + "\n[当前平台不支持图片发送]")
            else:
                await send_group_msg(main_group, output_str + "\n[无法获取Bot实例]")
        else:
            output_str = "上周期暂无G市交易记录"
            await send_group_msg(main_group, output_str)


def area_translate_value(area_name):
    """校区名称转G值字段"""
    value_map = {'东': 'eastValue', '南': 'southValue', '北': 'northValue', '珠': 'zhuhaiValue', '深': 'shenzhenValue'}
    return value_map[area_name]


# 注册交易记录翻页处理器
async def handle_trade_record_next_page(user_id: str, state: dict, next_page: int) -> str:
    """处理交易记录翻页"""
    target_user_id = state['user_id']
    page_size = state['page_size']
    total_pages = state['total_pages']
    
    # 重新获取交易记录
    records_result = await GMarketService.get_trade_records(target_user_id, page=next_page, page_size=page_size)
    
    if not records_result['records']:
        return '没有更多记录了'
    
    output = await format_trade_records(records_result['records'], next_page, total_pages)
    
    if next_page < total_pages:
        output += f'\n(第{next_page}/{total_pages}页，输入!下一页或!上一页翻页)'
    else:
        output += f'\n(第{next_page}/{total_pages}页，最后一页)'
    
    return output


register_pagination_handler('trade_record', handle_trade_record_next_page)
