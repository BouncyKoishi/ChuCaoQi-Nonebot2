"""
统计服务模块

提供所有排行/统计类业务逻辑，供 bot 插件层和 web 路由层共用。
与 warehouse_service（仓库 CRUD）解耦，避免仓库服务承担过多统计职责。
"""

import sys
import os
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timedelta


import core.db.kusa_system as baseDB
import core.db.kusa_item as itemDB
import core.db.user as user_db
from core.db.models import UnifiedUser, KusaBase, KusaHistory


# ===== 通用过滤与缓存 =====

async def _get_active_user_ids(days: int = 90) -> set:
    """获取近 N 天有生草记录的用户 ID 集合"""
    start_ts = (datetime.now() - timedelta(days=days)).timestamp()
    records = await KusaHistory.filter(createTimeTs__gt=start_ts).distinct().values('user_id')
    return {r['user_id'] for r in records}


async def _filter_users(user_list, unified_user_map, level_max, show_inactive, show_subaccount, active_ids=None):
    """通用过滤：等级/小号/不活跃"""
    if not show_inactive and active_ids is None:
        active_ids = await _get_active_user_ids()

    filtered = []
    for user in user_list:
        if user.vipLevel > level_max:
            continue
        uu = unified_user_map.get(user.user_id)
        if not show_subaccount and uu and uu.relatedUserId:
            continue
        if not show_inactive and user.user_id not in active_ids:
            continue
        filtered.append(user)
    return filtered


async def _exclude_bot_users(user_list) -> List:
    """从用户列表中剔除 bot 账号"""
    bot_user_ids = set()
    unified_users = await user_db.getAllRobotUsers()
    for u in unified_users:
        bot_user_ids.add(u.id)
    return [u for u in user_list if u.user_id not in bot_user_ids]


_rank_cache = {}
_cache_ttl = 300


def _get_cache(key):
    if key in _rank_cache:
        data, timestamp = _rank_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return data
        else:
            del _rank_cache[key]
    return None


def _set_cache(key, data):
    _rank_cache[key] = (data, time.time())


# ===== 统计服务 =====

class StatisticService:
    """统计服务类"""

    @staticmethod
    async def get_total_stats() -> Dict[str, Any]:
        """获取系统总统计"""
        user_list = await baseDB.getAllKusaUser()
        total_kusa = sum(user.kusa for user in user_list)
        total_adv_kusa = sum(user.advKusa for user in user_list)

        bot_user_ids = set()
        unified_users = await user_db.getAllRobotUsers()
        for u in unified_users:
            bot_user_ids.add(u.id)

        available_kusa = sum(user.kusa for user in user_list
                           if user.user_id not in bot_user_ids)
        available_adv_kusa = sum(user.advKusa for user in user_list
                                if user.user_id not in bot_user_ids)

        return {
            'totalKusa': total_kusa,
            'totalAdvKusa': total_adv_kusa,
            'availableKusa': available_kusa,
            'availableAdvKusa': available_adv_kusa,
            'userCount': len(user_list)
        }

    @staticmethod
    async def get_kusa_rank(limit: int = 25, level_max: Optional[int] = None,
                            show_inactive: bool = True, show_subaccount: bool = True) -> List[Dict[str, Any]]:
        """获取草排行榜

        默认不过滤（与原始 bot 行为一致），管理后台调用时可传过滤参数。
        """
        user_list = await baseDB.getAllKusaUser()
        user_list = await _exclude_bot_users(user_list)

        unified_user_ids = [u.user_id for u in user_list]
        unified_users_all = await UnifiedUser.filter(id__in=unified_user_ids).all()
        unified_users_map = {u.id: u for u in unified_users_all}

        need_filter = level_max is not None or not show_inactive or not show_subaccount
        if need_filter:
            user_list = await _filter_users(user_list, unified_users_map, level_max or 10, show_inactive, show_subaccount)
        user_list = sorted(user_list, key=lambda x: x.kusa, reverse=True)

        result = []
        for i, user in enumerate(user_list[:limit]):
            unified_user = unified_users_map.get(user.user_id)
            result.append({
                'rank': i + 1,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': user.user_id,
                'name': user.name,
                'kusa': user.kusa,
                'vipLevel': user.vipLevel
            })
        return result

    @staticmethod
    async def get_kusa_rank_with_adv(limit: int = 25, sort_by: str = 'kusa',
                                     level_max: Optional[int] = None, show_inactive: bool = True,
                                     show_subaccount: bool = True) -> List[Dict[str, Any]]:
        """获取草排行榜（包含草之精华）

        默认不过滤（与原始 bot 行为一致），管理后台调用时可传过滤参数。
        """
        user_list = await baseDB.getAllKusaUser()
        user_list = await _exclude_bot_users(user_list)

        unified_user_ids = [u.user_id for u in user_list]
        unified_users_all = await UnifiedUser.filter(id__in=unified_user_ids).all()
        unified_users_map = {u.id: u for u in unified_users_all}

        need_filter = level_max is not None or not show_inactive or not show_subaccount
        if need_filter:
            user_list = await _filter_users(user_list, unified_users_map, level_max or 10, show_inactive, show_subaccount)

        if sort_by == 'advKusa':
            user_list = sorted(user_list, key=lambda x: x.advKusa, reverse=True)
        else:
            user_list = sorted(user_list, key=lambda x: x.kusa, reverse=True)

        result = []
        for i, user in enumerate(user_list[:limit]):
            unified_user = unified_users_map.get(user.user_id)
            result.append({
                'rank': i + 1,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': user.user_id,
                'name': user.name,
                'kusa': user.kusa,
                'advKusa': user.advKusa,
                'vipLevel': user.vipLevel
            })
        return result

    @staticmethod
    async def get_total_adv_kusa_rank(limit: Optional[int] = 25, level_max: int = 10,
                                      show_inactive: bool = False,
                                      show_subaccount: bool = True,
                                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取累计草精排行榜

        limit=None 时返回完整列表（供 bot 端计算"我的排名"上下文使用）。
        累计值 = 当前草精 + 称号草精 + 道具消费草精
        """
        cache_key = f"total_adv_rank_{limit}_{level_max}_{show_inactive}_{show_subaccount}"

        if use_cache:
            cached = _get_cache(cache_key)
            if cached:
                return cached

        user_list = await baseDB.getAllKusaUser()

        unified_user_ids = [user.user_id for user in user_list]
        unified_users = await UnifiedUser.filter(id__in=unified_user_ids).all()
        unified_user_map = {u.id: u for u in unified_users}

        # 去重 + 排除 bot
        seen_user_ids = set()
        deduped = []
        for user in user_list:
            if user.user_id in seen_user_ids:
                continue
            seen_user_ids.add(user.user_id)
            if str(user.user_id) == 'bot':
                continue
            deduped.append(user)

        # 统一过滤（等级/小号/不活跃）
        filtered_users = await _filter_users(deduped, unified_user_map, level_max, show_inactive, show_subaccount)

        all_trade_records = await baseDB.getAllTradeRecordsByCostItem('草之精华')

        user_trade_amount = {}
        for record in all_trade_records:
            if '升级' in (record.tradeType or ''):
                continue
            uid = record.user_id
            if uid not in user_trade_amount:
                user_trade_amount[uid] = 0
            user_trade_amount[uid] += record.costItemAmount

        user_total_adv = []
        for user in filtered_users:
            now_adv = user.advKusa or 0

            title_adv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0

            item_adv = user_trade_amount.get(user.user_id, 0)

            total_adv = now_adv + title_adv + item_adv

            unified_user = unified_user_map.get(user.user_id)
            real_qq = unified_user.realQQ if unified_user else None

            user_total_adv.append({
                'userId': user.user_id,
                'qq': real_qq,
                'name': user.name,
                'vipLevel': user.vipLevel,
                'totalAdvKusa': total_adv,
                'nowAdvKusa': now_adv,
                'titleAdvKusa': title_adv,
                'itemAdvKusa': item_adv
            })

        user_total_adv.sort(key=lambda x: x['totalAdvKusa'], reverse=True)

        for i, item in enumerate(user_total_adv):
            item['rank'] = i + 1

        result = user_total_adv if limit is None else user_total_adv[:limit]

        if use_cache:
            _set_cache(cache_key, result)

        return result

    @staticmethod
    async def get_kusa_once_ranking(limit: int = 25, level_max: Optional[int] = None,
                                    show_inactive: bool = True, show_subaccount: bool = True) -> List[Dict[str, Any]]:
        """获取单次生草打分排行榜（按 KusaHistory 单次记录排序）

        level_max=None 时不做等级过滤，bot 端原始行为不过滤任何用户。
        管理后台调用时可传 level_max/show_inactive/show_subaccount 进行过滤。
        """
        records = await KusaHistory.all().order_by('-kusaResult').limit(limit)

        user_ids = list(set(r.user_id for r in records))
        if not user_ids:
            return []

        kusa_users = await KusaBase.filter(user_id__in=user_ids).all()
        kusa_map = {ku.user_id: ku for ku in kusa_users}
        unified_users = await UnifiedUser.filter(id__in=user_ids).all()
        unified_map = {u.id: u for u in unified_users}

        # 仅在管理后台传了过滤参数时执行用户过滤
        need_filter = level_max is not None or not show_inactive or not show_subaccount
        if need_filter:
            active_ids = None
            if not show_inactive:
                active_ids = await _get_active_user_ids()
            filtered_user_ids = set()
            for uid in user_ids:
                ku = kusa_map.get(uid)
                uu = unified_map.get(uid)
                if level_max is not None and ku and ku.vipLevel > level_max:
                    continue
                if not show_subaccount and uu and uu.relatedUserId:
                    continue
                if not show_inactive and uid not in active_ids:
                    continue
                filtered_user_ids.add(uid)
        else:
            filtered_user_ids = set(user_ids)

        result = []
        rank = 0
        for record in records:
            if record.user_id not in filtered_user_ids:
                continue
            rank += 1
            user = kusa_map.get(record.user_id)
            unified_user = unified_map.get(record.user_id)
            result.append({
                'rank': rank,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': record.user_id,
                'name': user.name if user else None,
                'kusaResult': record.kusaResult,
                'createTimeTs': record.createTimeTs,
                'vipLevel': user.vipLevel if user else 0
            })
        return result

    @staticmethod
    async def get_adv_kusa_once_ranking(limit: int = 25, level_max: Optional[int] = None,
                                        show_inactive: bool = True, show_subaccount: bool = True) -> List[Dict[str, Any]]:
        """获取单次草精打分排行榜（按 KusaHistory 单次记录排序）

        level_max=None 时不做等级过滤，bot 端原始行为不过滤任何用户。
        管理后台调用时可传 level_max/show_inactive/show_subaccount 进行过滤。
        """
        records = await KusaHistory.all().order_by('-advKusaResult').limit(limit)

        user_ids = list(set(r.user_id for r in records))
        if not user_ids:
            return []

        kusa_users = await KusaBase.filter(user_id__in=user_ids).all()
        kusa_map = {ku.user_id: ku for ku in kusa_users}
        unified_users = await UnifiedUser.filter(id__in=user_ids).all()
        unified_map = {u.id: u for u in unified_users}

        # 仅在管理后台传了过滤参数时执行用户过滤
        need_filter = level_max is not None or not show_inactive or not show_subaccount
        if need_filter:
            active_ids = None
            if not show_inactive:
                active_ids = await _get_active_user_ids()
            filtered_user_ids = set()
            for uid in user_ids:
                ku = kusa_map.get(uid)
                uu = unified_map.get(uid)
                if level_max is not None and ku and ku.vipLevel > level_max:
                    continue
                if not show_subaccount and uu and uu.relatedUserId:
                    continue
                if not show_inactive and uid not in active_ids:
                    continue
                filtered_user_ids.add(uid)
        else:
            filtered_user_ids = set(user_ids)

        result = []
        rank = 0
        for record in records:
            if record.user_id not in filtered_user_ids:
                continue
            rank += 1
            user = kusa_map.get(record.user_id)
            unified_user = unified_map.get(record.user_id)
            result.append({
                'rank': rank,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': record.user_id,
                'name': user.name if user else None,
                'advKusaResult': record.advKusaResult,
                'createTimeTs': record.createTimeTs,
                'vipLevel': user.vipLevel if user else 0
            })
        return result

    @staticmethod
    async def get_user_stats(userId: int) -> Dict[str, Any]:
        """获取用户草精统计"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'error': 'USER_NOT_FOUND'}

        unified_user = await user_db.getUnifiedUser(userId)

        now_adv = user.advKusa
        title_adv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0
        trade_records = await baseDB.getTradeRecord(userId=userId, costItemName='草之精华')
        item_adv = sum(record.costItemAmount for record in trade_records if '升级' not in (record.tradeType or ''))

        return {
            'userId': userId,
            'qq': unified_user.realQQ if unified_user else None,
            'name': user.name,
            'vipLevel': user.vipLevel,
            'nowKusa': user.kusa,
            'nowAdvKusa': now_adv,
            'titleAdvKusa': title_adv,
            'itemAdvKusa': item_adv,
            'totalAdvKusa': now_adv + title_adv + item_adv
        }

    @staticmethod
    async def get_item_rank(item_name: str, limit: int = 25,
                            level_max: int = 10, show_inactive: bool = False,
                            show_subaccount: bool = True) -> List[Dict[str, Any]]:
        """物品持有量排行"""
        storages = await itemDB.getStoragesOrderByAmountDesc(item_name)

        if not storages:
            return []

        user_ids = [s.user_id for s in storages]
        unified_users = await UnifiedUser.filter(id__in=user_ids).all()
        kusa_users = await KusaBase.filter(user_id__in=user_ids).all()
        uu_map = {u.id: u for u in unified_users}
        ku_map = {k.user_id: k for k in kusa_users}

        active_ids = None
        if not show_inactive:
            active_ids = await _get_active_user_ids()

        filtered = []
        for s in storages:
            ku = ku_map.get(s.user_id)
            uu = uu_map.get(s.user_id)
            if ku and ku.vipLevel > level_max:
                continue
            if not show_subaccount and uu and uu.relatedUserId:
                continue
            if not show_inactive and s.user_id not in active_ids:
                continue
            filtered.append(s)

        result = []
        for i, s in enumerate(filtered[:limit]):
            uu = uu_map.get(s.user_id)
            ku = ku_map.get(s.user_id)
            name = ku.name if ku else None
            result.append({
                'rank': i + 1,
                'userId': s.user_id,
                'qq': uu.realQQ if uu else None,
                'name': name,
                'amount': s.amount,
                'vipLevel': ku.vipLevel if ku else 0
            })
        return result
