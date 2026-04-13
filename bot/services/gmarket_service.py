"""
G市服务模块

包含所有与G市交易相关的业务逻辑
"""

import sys
import os
import math
import random
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB
import dbConnection.g_value as gValueDB
import dbConnection.user as user_db
from kusa_base import buying as base_buying, selling as base_selling


class GMarketService:
    """G市服务类"""

    AREA_MAP = {
        '东': ('G(东校区)', 'eastValue'),
        '南': ('G(南校区)', 'southValue'),
        '北': ('G(北校区)', 'northValue'),
        '珠': ('G(珠海校区)', 'zhuhaiValue'),
        '深': ('G(深圳校区)', 'shenzhenValue')
    }

    START_VALUE_MAP = {'东': 9.8, '南': 9.8, '北': 6.67, '珠': 32.0, '深': 120.0}

    @staticmethod
    def area_translate_value(area_name: str) -> str:
        """校区名称转G值字段"""
        return GMarketService.AREA_MAP.get(area_name, (None, None))[1]

    @staticmethod
    def area_translate_item(area_name: str) -> str:
        """校区名称转物品名"""
        return GMarketService.AREA_MAP.get(area_name, (None, None))[0]

    @staticmethod
    def area_start_value(area_name: str) -> float:
        """获取校区起始G值"""
        return GMarketService.START_VALUE_MAP.get(area_name, 0)

    @staticmethod
    async def get_status(userId: Optional[int] = None) -> Dict[str, Any]:
        """
        获取G市状态

        Args:
            userId: 用户ID（可选，用于获取用户持仓信息）
        """
        g_values = await gValueDB.getLatestGValues()
        g_values_last = await gValueDB.getSecondLatestGValues()

        result = {
            'cycle': g_values.cycle if g_values else 0,
            'turn': g_values.turn if g_values else 0,
            'values': {
                'east_value': g_values.eastValue if g_values else 0,
                'south_value': g_values.southValue if g_values else 0,
                'north_value': g_values.northValue if g_values else 0,
                'zhuhai_value': g_values.zhuhaiValue if g_values else 0,
                'shenzhen_value': g_values.shenzhenValue if g_values else 0,
                'east_value_last': g_values_last.eastValue if g_values_last else 0,
                'south_value_last': g_values_last.southValue if g_values_last else 0,
                'north_value_last': g_values_last.northValue if g_values_last else 0,
                'zhuhai_value_last': g_values_last.zhuhaiValue if g_values_last else 0,
                'shenzhen_value_last': g_values_last.shenzhenValue if g_values_last else 0,
            },
            'createTime': g_values.createTime if g_values else '',
            'isTradingTime': await GMarketService.check_trading_time()
        }

        if userId:
            result['holdings'] = await GMarketService.get_all_holdings(userId)
            unified_user = await user_db.getUnifiedUser(userId)
            result['qq'] = unified_user.realQQ if unified_user else None
            result['userId'] = userId

        return result

    @staticmethod
    async def get_all_holdings(userId: int) -> Dict[str, int]:
        """获取用户所有G持仓（返回简化格式）"""
        return {
            '东': await itemDB.getItemAmount(userId, 'G(东校区)'),
            '南': await itemDB.getItemAmount(userId, 'G(南校区)'),
            '北': await itemDB.getItemAmount(userId, 'G(北校区)'),
            '珠': await itemDB.getItemAmount(userId, 'G(珠海校区)'),
            '深': await itemDB.getItemAmount(userId, 'G(深圳校区)')
        }

    @staticmethod
    async def check_trading_time() -> bool:
        """检查是否为交易时间"""
        g_values = await gValueDB.getLatestGValues()
        if g_values and g_values.turn == 1 and datetime.now().minute < 50:
            return False
        return True

    @staticmethod
    async def buy_g(userId: int, amount: int, area_ratios: Dict[str, int], is_buying_all: bool = False) -> Dict[str, Any]:
        """
        买入G（支持多校区批量买入，用于QQ插件）

        Args:
            userId: 用户ID
            amount: 买入数量（每校区）
            area_ratios: 校区比例配置，如 {'东': 1, '南': 2}
            is_buying_all: 是否买入全部（用所有草买入）

        Returns:
            {'success': True/False, 'message': '操作结果', 'trades': [...]}
        """
        if not area_ratios:
            return {'success': False, 'message': '参数不正确^ ^'}

        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'success': False, 'message': '用户不存在'}

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None

        total_kusa = user.kusa
        trades = []

        if is_buying_all:
            total_ratio = sum(area_ratios.values())

            for school_name in '东南北珠深':
                ratio = area_ratios.get(school_name)
                if ratio is None:
                    continue

                g_type = GMarketService.AREA_MAP[school_name][0]
                value_type = GMarketService.AREA_MAP[school_name][1]
                g_value = getattr(g_values, value_type)

                kusa_for_this = math.floor(total_kusa / total_ratio * ratio)
                buying_amount = math.floor(kusa_for_this / g_value)
                total_price = int(buying_amount * g_value)

                if buying_amount > 0:
                    success = await base_buying(userId, g_type, buying_amount, total_price, 'G市(买)')
                    if success:
                        trades.append({
                            'school': school_name,
                            'amount': buying_amount,
                            'g_type': g_type,
                            'cost': total_price
                        })

            if not trades:
                return {'success': False, 'message': '你不够草^ ^'}

        else:
            if amount <= 0:
                return {'success': False, 'message': '参数不正确^ ^'}

            for school_name in '东南北珠深':
                ratio = area_ratios.get(school_name)
                if ratio is None:
                    continue

                g_type = GMarketService.AREA_MAP[school_name][0]
                value_type = GMarketService.AREA_MAP[school_name][1]
                g_value = getattr(g_values, value_type)

                total_price = int(amount * ratio * g_value)
                buying_amount = amount * ratio

                if buying_amount > 0:
                    success = await base_buying(userId, g_type, buying_amount, total_price, 'G市(买)')
                    if success:
                        trades.append({
                            'school': school_name,
                            'amount': buying_amount,
                            'g_type': g_type,
                            'cost': total_price
                        })

            if not trades:
                return {'success': False, 'message': '你不够草^ ^'}

        return {
            'success': True,
            'message': '买入成功',
            'trades': trades,
            'userId': userId,
            'qq': real_qq
        }

    @staticmethod
    async def buy_g_single(userId: int, amount: int, school: str) -> Dict[str, Any]:
        """
        买入G（单个校区，用于web端）

        Args:
            userId: 用户ID
            amount: 买入数量
            school: 校区代码（'东', '南', '北', '珠', '深'）

        Returns:
            {'success': True/False, 'message': '操作结果'}
        """
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        if school not in GMarketService.AREA_MAP:
            return {'success': False, 'message': '无效的校区类型'}

        g_type = GMarketService.AREA_MAP[school][0]
        value_type = GMarketService.AREA_MAP[school][1]
        g_value = getattr(g_values, value_type)

        total_price = int(amount * g_value)
        success = await base_buying(userId, g_type, amount, total_price, 'G市(买)')

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None

        if success:
            return {
                'success': True,
                'message': f'成功买入{amount}{g_type}，花费{total_price}草',
                'userId': userId,
                'qq': real_qq
            }
        else:
            return {'success': False, 'message': '你不够草^ ^'}

    @staticmethod
    async def sell_g(userId: int, amount: int, area_ratios: Dict[str, int], is_selling_all: bool = False) -> Dict[str, Any]:
        """
        卖出G

        Args:
            userId: 用户ID
            amount: 卖出数量（每校区）
            area_ratios: 校区比例配置
            is_selling_all: 是否卖出全部

        Returns:
            {'success': True/False, 'message': '操作结果', 'sell_all': True/False, 'total_kusa': 获得草数量, 'trades': [...]}
        """
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        holdings = await GMarketService.get_all_holdings(userId)

        trades = []
        total_kusa = 0

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None

        if is_selling_all:
            if not area_ratios:
                total = await GMarketService.sell_all_g(userId, g_values)
                return {
                    'success': True,
                    'message': f'已卖出所有G，获得了{total:,}草',
                    'sell_all': True,
                    'total_kusa': total,
                    'userId': userId,
                    'qq': real_qq
                }

            for school_name in '东南北珠深':
                ratio = area_ratios.get(school_name)
                if ratio is None:
                    continue

                g_type = GMarketService.AREA_MAP[school_name][0]
                value_type = GMarketService.AREA_MAP[school_name][1]
                g_value = getattr(g_values, value_type)

                selling_amount = holdings[school_name]
                total_price = int(selling_amount * g_value * (1 - 0.0005))

                if selling_amount > 0:
                    success = await base_selling(userId, g_type, selling_amount, total_price, 'G市(卖)')
                    if success:
                        trades.append({
                            'school': school_name,
                            'amount': selling_amount,
                            'g_type': g_type,
                            'gain': total_price
                        })
                        total_kusa += total_price

            if not trades:
                return {'success': False, 'message': '你没有可卖出的G^ ^'}

        else:
            if amount <= 0:
                return {'success': False, 'message': '参数不正确^ ^'}

            for school_name in '东南北珠深':
                ratio = area_ratios.get(school_name)
                if ratio is None:
                    continue

                g_type = GMarketService.AREA_MAP[school_name][0]
                value_type = GMarketService.AREA_MAP[school_name][1]
                g_value = getattr(g_values, value_type)

                selling_amount = amount * ratio
                total_price = int(selling_amount * g_value * (1 - 0.0005))

                if selling_amount > 0:
                    success = await base_selling(userId, g_type, selling_amount, total_price, 'G市(卖)')
                    if success:
                        trades.append({
                            'school': school_name,
                            'amount': selling_amount,
                            'g_type': g_type,
                            'gain': total_price
                        })
                        total_kusa += total_price

            if not trades:
                return {'success': False, 'message': '你不够G^ ^'}

        return {
            'success': True,
            'message': '卖出成功',
            'sell_all': False,
            'trades': trades,
            'total_kusa': total_kusa,
            'userId': userId,
            'qq': real_qq
        }

    @staticmethod
    async def sell_g_single(userId: int, amount: int, school: str) -> Dict[str, Any]:
        """
        卖出G（单个校区，用于web端）

        Args:
            userId: 用户ID
            amount: 卖出数量
            school: 校区代码（'东', '南', '北', '珠', '深'）

        Returns:
            {'success': True/False, 'message': '操作结果'}
        """
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        if school not in GMarketService.AREA_MAP:
            return {'success': False, 'message': '无效的校区类型'}

        g_type = GMarketService.AREA_MAP[school][0]
        value_type = GMarketService.AREA_MAP[school][1]
        g_value = getattr(g_values, value_type)

        total_price = int(amount * g_value * (1 - 0.0005))
        success = await base_selling(userId, g_type, amount, total_price, 'G市(卖)')

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None

        if success:
            return {
                'success': True,
                'message': f'成功卖出{amount}{g_type}，获得{total_price}草',
                'userId': userId,
                'qq': real_qq
            }
        else:
            return {'success': False, 'message': '卖出失败，G不足'}

    @staticmethod
    async def sell_all_g(userId: int, g_values) -> int:
        """
        卖出所有G

        Returns:
            获得的总草数量
        """
        holdings = await GMarketService.get_all_holdings(userId)

        amounts = [
            holdings['东'],
            holdings['南'],
            holdings['北'],
            holdings['珠'],
            holdings['深']
        ]
        values = [g_values.eastValue, g_values.southValue, g_values.northValue, g_values.zhuhaiValue, g_values.shenzhenValue]
        areas = ['东校区', '南校区', '北校区', '珠海校区', '深圳校区']

        all_kusa = int(sum(amount * value for amount, value in zip(amounts, values)) * (1 - 0.0005))

        await baseDB.changeKusa(userId, all_kusa)

        await itemDB.cleanAllG(userId)

        for amount, area, value in zip(amounts, areas, values):
            if amount > 0:
                kusa_amount = math.ceil(amount * value * (1 - 0.0005))
                await baseDB.setTradeRecord(
                    userId=userId, tradeType='G市(卖)',
                    gainItemName='草', gainItemAmount=kusa_amount,
                    costItemName=f'G({area})', costItemAmount=amount
                )

        return all_kusa

    @staticmethod
    async def get_trade_summary(userId: int) -> Dict[str, Any]:
        """
        获取本周期交易总结

        Args:
            userId: 用户ID

        Returns:
            交易总结数据
        """
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        g_start_ts = GMarketService.get_g_cycle_start_ts(g_values)

        trade_record_buying = await baseDB.getTradeRecord(userId=userId, startTime=g_start_ts, tradeType='G市(买)')
        trade_record_selling = await baseDB.getTradeRecord(userId=userId, startTime=g_start_ts, tradeType='G市(卖)')

        all_cost_kusa = sum(record.costItemAmount for record in trade_record_buying)
        all_gain_kusa = sum(record.gainItemAmount for record in trade_record_selling)

        holdings = await GMarketService.get_all_holdings(userId)
        now_kusa_in_g = int(sum([
            holdings['东'] * g_values.eastValue, holdings['南'] * g_values.southValue,
            holdings['北'] * g_values.northValue, holdings['珠'] * g_values.zhuhaiValue,
            holdings['深'] * g_values.shenzhenValue
        ]))
        profit = now_kusa_in_g + all_gain_kusa - all_cost_kusa

        holdings_detail = {}
        for area in ['东', '南', '北', '珠', '深']:
            value_attr = GMarketService.AREA_MAP[area][1]
            g_value = getattr(g_values, value_attr)
            amount = holdings[area]
            holdings_detail[area] = {
                'amount': amount,
                'value': g_value,
                'kusa_value': int(amount * g_value)
            }

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None

        return {
            'success': True,
            'now_kusa_in_g': now_kusa_in_g,
            'all_cost_kusa': all_cost_kusa,
            'all_gain_kusa': all_gain_kusa,
            'profit': profit,
            'has_holdings': any(holdings[a] > 0 for a in ['东', '南', '北', '珠', '深']),
            'holdings': holdings_detail,
            'userId': userId,
            'qq': real_qq
        }

    @staticmethod
    async def get_last_cycle_summary(userId: int) -> Dict[str, Any]:
        """
        获取上周期交易总结

        Args:
            userId: 用户ID

        Returns:
            交易总结数据
        """
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'success': False, 'message': 'G市数据异常'}

        g_this_cycle_start_ts = GMarketService.get_g_cycle_start_ts(g_values)
        g_last_cycle_start_ts = g_this_cycle_start_ts - 3 * 86400

        trade_record_buying = await baseDB.getTradeRecord(userId=userId, startTime=g_last_cycle_start_ts, endTime=g_this_cycle_start_ts, tradeType='G市(买)')
        trade_record_selling = await baseDB.getTradeRecord(userId=userId, startTime=g_last_cycle_start_ts, endTime=g_this_cycle_start_ts, tradeType='G市(卖)')

        all_cost_kusa = sum(record.costItemAmount for record in trade_record_buying)
        all_gain_kusa = sum(record.gainItemAmount for record in trade_record_selling)
        profit = all_gain_kusa - all_cost_kusa

        return {
            'success': True,
            'all_cost_kusa': all_cost_kusa,
            'all_gain_kusa': all_gain_kusa,
            'profit': profit
        }

    @staticmethod
    async def get_trade_records(userId: int, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        获取本周期交易记录
        
        Args:
            userId: 用户ID
            page: 页码（从1开始）
            page_size: 每页记录数
        
        Returns:
            交易记录数据，包含分页信息
        """
        from utils import rd3
        
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'records': [], 'total_pages': 0, 'total': 0}

        g_start_ts = GMarketService.get_g_cycle_start_ts(g_values)

        trade_record_buying = await baseDB.getTradeRecord(userId=userId, startTime=g_start_ts, tradeType='G市(买)')
        trade_record_selling = await baseDB.getTradeRecord(userId=userId, startTime=g_start_ts, tradeType='G市(卖)')

        all_records = trade_record_buying + trade_record_selling
        all_records.sort(key=lambda r: r.timestamp, reverse=True)
        
        formatted_records = []
        for record in all_records:
            if record.tradeType == 'G市(买)':
                formatted_records.append({
                    'timestamp': record.timestamp,
                    'type': 'buy',
                    'g_name': record.gainItemName,
                    'g_amount': record.gainItemAmount,
                    'kusa_amount': record.costItemAmount,
                    'unit_price': rd3(record.costItemAmount / record.gainItemAmount) if record.gainItemAmount > 0 else 0
                })
            else:
                formatted_records.append({
                    'timestamp': record.timestamp,
                    'type': 'sell',
                    'g_name': record.costItemName,
                    'g_amount': record.costItemAmount,
                    'kusa_amount': record.gainItemAmount,
                    'unit_price': rd3(record.gainItemAmount / record.costItemAmount) if record.costItemAmount > 0 else 0
                })
        
        total = len(formatted_records)
        total_pages = (total + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, total)
        page_records = formatted_records[start_index:end_index]

        return {
            'records': page_records,
            'total_pages': total_pages,
            'total': total,
            'page': page
        }

    @staticmethod
    def get_g_cycle_start_ts(g_values) -> float:
        """获取G周期开始时间戳"""
        g_start_ts = datetime.now().timestamp() - 1800 * (g_values.turn + 10)
        g_start_datetime = datetime.fromtimestamp(g_start_ts)
        g_start_ts = datetime(g_start_datetime.year, g_start_datetime.month, g_start_datetime.day, 23, 50).timestamp()
        return g_start_ts

    @staticmethod
    def format_g_value(current_value: float, last_value: float, campus_name: str) -> str:
        """格式化G值显示"""
        change = current_value - last_value
        percentage_change = (change / last_value * 100) if last_value != 0 else 0
        p_change_sign = '+' if change >= 0 else ''
        return f'{campus_name}校区：{current_value:.3f}({p_change_sign}{percentage_change:.2f}%)\n'

    @staticmethod
    async def process_g_creator(userId: int) -> Optional[Dict[str, Any]]:
        """
        处理扭秤装置创造G

        Returns:
            {'school': '东', 'amount': 100} 或 None
        """
        g_creator_amount = await itemDB.getItemAmount(userId, '扭秤装置')
        if g_creator_amount <= 0:
            return None

        g_creator_stable = await itemDB.getItemAmount(userId, '扭秤稳定理论')

        school_name = random.choice(['东', '南', '北', '珠', '深'])
        single_creator_g = 50 + random.SystemRandom().random() * 450
        create_g_amount = int(g_creator_amount * single_creator_g)

        if g_creator_stable > 0:
            create_g_amount *= (GMarketService.area_start_value('深') / GMarketService.area_start_value(school_name))
            create_g_amount = int(create_g_amount)

        g_type = GMarketService.area_translate_item(school_name)
        await itemDB.changeItemAmount(userId, g_type, create_g_amount)

        return {
            'school': school_name,
            'amount': create_g_amount,
            'type': g_type
        }

    @staticmethod
    def get_new_g(old_g: float, change_range: float) -> float:
        """获取新的G值"""
        from utils import rd3
        rank = change_range * (random.SystemRandom().random() - 0.498)
        new_g = rd3(old_g * (1 + rank))
        return new_g

    @staticmethod
    def reset_date_check() -> bool:
        """检查是否是重置日期"""
        reset_date = datetime(2024, 11, 1)
        delta = datetime.now() - reset_date
        return delta.days % 3 == 0

    @staticmethod
    async def process_g_creator_v2(userId: int) -> Dict[str, Any]:
        """
        处理扭秤装置创造G
        
        Returns:
            {'success': True/False, 'area': '东', 'amount': 100, 'g_type': 'G(东校区)'}
        """
        g_creator_amount = await itemDB.getItemAmount(userId, '扭秤装置')
        if g_creator_amount <= 0:
            return {'success': False, 'message': '没有扭秤装置'}
        
        g_creator_stable = await itemDB.getItemAmount(userId, '扭秤稳定理论')
        
        school_name = random.choice(['东', '南', '北', '珠', '深'])
        single_creator_g = 50 + random.SystemRandom().random() * 450
        create_g_amount = int(g_creator_amount * single_creator_g)
        
        if g_creator_stable > 0:
            create_g_amount *= (GMarketService.START_VALUE_MAP['深'] / GMarketService.START_VALUE_MAP[school_name])
            create_g_amount = int(create_g_amount)
        
        g_type = GMarketService.AREA_MAP[school_name][0]
        await itemDB.changeItemAmount(userId, g_type, create_g_amount)
        
        return {
            'success': True,
            'area': school_name,
            'amount': create_g_amount,
            'g_type': g_type
        }

    @staticmethod
    def get_new_g_values(current_values: Dict[str, float]) -> Dict[str, float]:
        """
        生成新的G值
        
        Args:
            current_values: {'east': 10.0, 'south': 10.0, 'north': 7.0, 'zhuhai': 35.0, 'shenzhen': 130.0}
        
        Returns:
            新的G值字典
        """
        from utils import rd3
        change_ranges = {'east': 0.1, 'south': 0.1, 'north': 0.08, 'zhuhai': 0.1, 'shenzhen': 0.15}
        
        new_values = {}
        for key, old_value in current_values.items():
            rank = change_ranges[key] * (random.SystemRandom().random() - 0.498)
            new_values[key] = rd3(old_value * (1 + rank))
        
        return new_values

    @staticmethod
    def get_new_cycle_values() -> Dict[str, float]:
        """获取新周期的初始G值"""
        return {
            'east': GMarketService.START_VALUE_MAP['东'],
            'south': GMarketService.START_VALUE_MAP['南'],
            'north': GMarketService.START_VALUE_MAP['北'],
            'zhuhai': GMarketService.START_VALUE_MAP['珠'],
            'shenzhen': GMarketService.START_VALUE_MAP['深']
        }

    @staticmethod
    async def get_cycle_summary() -> Dict[str, Any]:
        """获取周期总结（用于定时任务）"""
        g_values = await gValueDB.getLatestGValues()
        if not g_values:
            return {'has_records': False}
        
        g_this_cycle_start_ts = GMarketService.get_g_cycle_start_ts(g_values)
        g_last_cycle_start_ts = g_this_cycle_start_ts - 3 * 86400
        
        trade_records_buying = await baseDB.getTradeRecord(
            startTime=g_last_cycle_start_ts, endTime=g_this_cycle_start_ts, tradeType='G市(买)'
        )
        trade_records_selling = await baseDB.getTradeRecord(
            startTime=g_last_cycle_start_ts, endTime=g_this_cycle_start_ts, tradeType='G市(卖)'
        )
        
        all_records = trade_records_buying + trade_records_selling
        operator_records_map = {}
        for record in all_records:
            operator_records_map.setdefault(record.user_id, []).append(record)
        
        operator_profit_map = {}
        for user_id, records in operator_records_map.items():
            kusa_profit = 0
            for record in records:
                if record.tradeType == 'G市(买)':
                    kusa_profit -= record.costItemAmount
                if record.tradeType == 'G市(卖)':
                    kusa_profit += record.gainItemAmount
            operator_profit_map[user_id] = kusa_profit
        
        if not operator_profit_map:
            return {'has_records': False}
        
        max_profit_user_id = max(operator_profit_map, key=operator_profit_map.get)
        min_profit_user_id = min(operator_profit_map, key=operator_profit_map.get)
        
        name_list = await baseDB.getNameListByKusaUserId([max_profit_user_id, min_profit_user_id])
        max_user_name = name_list.get(max_profit_user_id, max_profit_user_id)
        min_user_name = name_list.get(min_profit_user_id, min_profit_user_id)
        
        last_cycle_g_value = await gValueDB.getLastCycleGValues()
        end_g_values = last_cycle_g_value[-1] if last_cycle_g_value else None
        
        return {
            'has_records': True,
            'max_user_name': max_user_name,
            'min_user_name': min_user_name,
            'max_profit': operator_profit_map[max_profit_user_id],
            'min_profit': operator_profit_map[min_profit_user_id],
            'end_values': {
                'east_value': end_g_values.eastValue if end_g_values else 0,
                'south_value': end_g_values.southValue if end_g_values else 0,
                'north_value': end_g_values.northValue if end_g_values else 0,
                'zhuhai_value': end_g_values.zhuhaiValue if end_g_values else 0,
                'shenzhen_value': end_g_values.shenzhenValue if end_g_values else 0,
            }
        }

    @staticmethod
    async def get_cycle_history() -> Dict[str, Any]:
        """
        获取本周期G值历史（用于web端图表）
        
        Returns:
            {'history': [{'turn': 1, 'eastValue': 9.8, ...}, ...]}
        """
        g_values_list = await gValueDB.getThisCycleGValues()
        
        history = []
        for g_values in g_values_list:
            history.append({
                'turn': g_values.turn,
                'eastValue': g_values.eastValue,
                'southValue': g_values.southValue,
                'northValue': g_values.northValue,
                'zhuhaiValue': g_values.zhuhaiValue,
                'shenzhenValue': g_values.shenzhenValue,
                'createTime': g_values.createTime
            })
        
        return {'history': history}
