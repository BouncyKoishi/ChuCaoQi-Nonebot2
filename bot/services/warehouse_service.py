"""
仓库服务模块

包含所有与仓库、用户相关的业务逻辑
"""

import sys
import os
from typing import Dict, Any, List
import time

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB
import dbConnection.user as user_db
from dbConnection.models import UnifiedUser

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


class WarehouseService:
    """仓库服务类"""
    
    @staticmethod
    async def get_warehouse_info(userId: int) -> Dict[str, Any]:
        """获取仓库完整信息"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'error': '用户不存在'}

        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None
        
        result = {
            'user': {
                'qq': real_qq,
                'userId': userId,
                'name': user.name,
                'title': user.title,
                'vipLevel': user.vipLevel,
                'kusa': user.kusa,
                'advKusa': user.advKusa
            },
            'items': []
        }
        
        items_wealth = await itemDB.getItemsByType("财产")
        for item in items_wealth:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': '财产',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        items_g = await itemDB.getItemsByType("G")
        for item in items_g:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': 'G',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        items_title = await itemDB.getItemsByType("称号")
        for item in items_title:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': '称号',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        items_blueprint = await itemDB.getItemsByType("图纸")
        for item in items_blueprint:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': '图纸',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        items_ability = await itemDB.getItemsByType("能力")
        for item in items_ability:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': '能力',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        items_useable = await itemDB.getItemsByType("道具")
        for item in items_useable:
            amount = await itemDB.getItemAmount(userId, item.name)
            if amount != 0:
                storage = await itemDB.getItemStorageInfo(userId, item.name)
                result['items'].append({
                    'item': {
                        'name': item.name,
                        'type': '道具',
                        'detail': item.detail,
                        'isControllable': item.isControllable
                    },
                    'amount': amount,
                    'allowUse': storage.allowUse if storage else True
                })
        
        return result
    
    @staticmethod
    async def get_item_detail(userId: int, item_name: str) -> Dict[str, Any]:
        """获取物品详情"""
        item = await itemDB.getItem(item_name)
        if not item:
            return {'error': 'ITEM_NOT_FOUND'}
        
        storage = await itemDB.getItemStorageInfo(userId, item_name)
        
        return {
            'item': {
                'name': item.name,
                'type': item.type,
                'shopPrice': item.shopPrice,
                'sellingPrice': item.sellingPrice,
                'isTransferable': item.isTransferable,
                'isControllable': item.isControllable,
                'detail': item.detail
            },
            'owned': {
                'amount': storage.amount if storage else 0,
                'allowUse': storage.allowUse if storage else True
            }
        }
    
    @staticmethod
    async def compress_kusa(userId: int, adv_amount: int) -> Dict[str, Any]:
        """草压缩"""
        base_exist = await itemDB.getItemAmount(userId, '草压缩基地')
        if not base_exist:
            return {'success': False, 'error': 'NO_BASE', 'message': '没有草压缩基地'}
        
        adv_amount = abs(adv_amount)
        kusa_use = 1000000 * adv_amount
        
        user = await baseDB.getKusaUser(userId)
        if user.kusa < kusa_use:
            return {
                'success': False,
                'error': 'INSUFFICIENT_KUSA',
                'message': f'需要{kusa_use}草来压缩'
            }
        
        await baseDB.changeAdvKusa(userId, adv_amount)
        await baseDB.changeKusa(userId, -kusa_use)
        
        await baseDB.setTradeRecord(
            userId=userId, tradeType='草压缩',
            gainItemName='草之精华', gainItemAmount=adv_amount,
            costItemName='草', costItemAmount=kusa_use
        )
        
        return {
            'success': True,
            'message': f'压缩成功！消耗{kusa_use}草，产出{adv_amount}草之精华',
            'advKusaGained': adv_amount,
            'kusaUsed': kusa_use
        }
    
    @staticmethod
    async def transfer_kusa(userId: int, target_userId: int, amount: int) -> Dict[str, Any]:
        """草转让
        
        Args:
            userId: 转让者用户ID
            target_userId: 接收者用户ID
            amount: 转让数量
            
        Returns:
            Dict: 包含 success, message, error 等字段的结果
        """
        # 检查目标用户是否存在
        target_user = await user_db.getUnifiedUser(target_userId)
        if not target_user:
            return {'success': False, 'error': 'TARGET_NOT_FOUND', 'message': '目标用户不存在'}
        
        # 检查转让者草是否足够
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'success': False, 'error': 'USER_NOT_FOUND', 'message': '用户不存在'}
        if user.kusa < amount:
            return {'success': False, 'error': 'INSUFFICIENT_KUSA', 'message': '草不足'}
        
        # 执行转让
        await baseDB.changeKusa(target_userId, amount)
        await baseDB.changeKusa(userId, -amount)
        
        # 记录交易
        await baseDB.setTradeRecord(
            userId=userId,
            tradeType='草转让',
            gainItemAmount=0,
            gainItemName='',
            costItemAmount=amount,
            costItemName='草',
            detail=f'转让给用户{target_userId}'
        )
        
        return {
            'success': True,
            'message': '转让成功',
            'fromUserId': userId,
            'toUserId': target_userId,
            'amount': amount
        }

    @staticmethod
    async def get_transfer_target_by_qq(real_qq: str) -> UnifiedUser:
        """通过QQ号获取转让目标用户

        Args:
            real_qq: QQ号

        Returns:
            UnifiedUser 或 None
        """
        return await user_db.getUnifiedUserByRealQQ(real_qq)

    @staticmethod
    async def get_transfer_target_by_id(user_id: int) -> UnifiedUser:
        """通过用户ID获取转让目标用户

        Args:
            user_id: 用户ID

        Returns:
            UnifiedUser 或 None
        """
        return await user_db.getUnifiedUser(user_id)

    @staticmethod
    async def change_name(userId: int, name: str) -> Dict[str, Any]:
        """改名"""
        success = await baseDB.changeKusaUserName(userId, name)
        if success:
            return {'success': True, 'message': f'名字已改为{name}'}
        return {'success': False, 'error': 'FAILED'}
    
    @staticmethod
    async def change_title(userId: int, title: str = None) -> Dict[str, Any]:
        """修改称号"""
        success = await baseDB.changeKusaUserTitle(userId, title)
        if success:
            return {'success': True, 'message': f'称号已修改为{title if title else "无"}'}
        return {'success': False, 'error': 'FAILED'}
    
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
    async def get_kusa_rank(limit: int = 25) -> List[Dict[str, Any]]:
        """获取草排行榜"""
        user_list = await baseDB.getAllKusaUser()

        bot_user_ids = set()
        unified_users = await user_db.getAllRobotUsers()
        for u in unified_users:
            bot_user_ids.add(u.id)

        user_list = [u for u in user_list if u.user_id not in bot_user_ids]
        user_list = sorted(user_list, key=lambda x: x.kusa, reverse=True)

        unified_user_ids = [u.user_id for u in user_list[:limit]]
        unified_users_map = {}
        for uid in unified_user_ids:
            uu = await user_db.getUnifiedUser(uid)
            if uu:
                unified_users_map[uid] = uu

        result = []
        for i, user in enumerate(user_list[:limit]):
            unified_user = unified_users_map.get(user.user_id)
            result.append({
                'rank': i + 1,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': user.user_id,
                'name': user.name or str(user.user_id),
                'kusa': user.kusa
            })
        return result
    
    @staticmethod
    async def get_user_stats(userId: int) -> Dict[str, Any]:
        """获取用户统计"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'error': 'USER_NOT_FOUND'}

        unified_user = await user_db.getUnifiedUser(userId)
        
        now_adv = user.advKusa
        title_adv = sum(10 ** (i - 4) for i in range(5, user.vipLevel + 1)) if user.vipLevel > 4 else 0
        trade_records = await baseDB.getTradeRecord(userId=userId, costItemName='草之精华')
        item_adv = sum(record.costItemAmount for record in trade_records)
        
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
    async def get_items_by_type(item_type: str, userId: int = None) -> List[Dict[str, Any]]:
        """获取指定类型物品列表"""
        items = await itemDB.getItemsByType(item_type)
        
        if userId:
            user_items = []
            for item in items:
                amount = await itemDB.getItemAmount(userId, item.name)
                if amount > 0:
                    user_items.append({
                        'name': item.name,
                        'type': item.type,
                        'detail': item.detail,
                        'shopPrice': item.shopPrice
                    })
            return user_items
        else:
            return [
                {
                    'name': item.name,
                    'type': item.type,
                    'detail': item.detail,
                    'shopPrice': item.shopPrice
                }
                for item in items
            ]
    
    @staticmethod
    async def get_kusa_rank_with_adv(limit: int = 25, sort_by: str = 'kusa') -> List[Dict[str, Any]]:
        """获取草排行榜（包含草之精华）"""
        from dbConnection.models import UnifiedUser
        
        user_list = await baseDB.getAllKusaUser()

        bot_user_ids = set()
        unified_users = await user_db.getAllRobotUsers()
        for u in unified_users:
            bot_user_ids.add(u.id)

        user_list = [u for u in user_list if u.user_id not in bot_user_ids]

        if sort_by == 'advKusa':
            user_list = sorted(user_list, key=lambda x: x.advKusa, reverse=True)
        else:
            user_list = sorted(user_list, key=lambda x: x.kusa, reverse=True)

        unified_user_ids = [u.user_id for u in user_list[:limit]]
        unified_users_map = {}
        for uid in unified_user_ids:
            uu = await user_db.getUnifiedUser(uid)
            if uu:
                unified_users_map[uid] = uu
        
        result = []
        for i, user in enumerate(user_list[:limit]):
            unified_user = unified_users_map.get(user.user_id)
            result.append({
                'rank': i + 1,
                'qq': unified_user.realQQ if unified_user else None,
                'userId': user.user_id,
                'name': user.name or str(user.user_id),
                'kusa': user.kusa,
                'advKusa': user.advKusa
            })
        return result
    
    @staticmethod
    async def upgrade_vip(userId: int) -> Dict[str, Any]:
        """VIP升级"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'success': False, 'error': 'USER_NOT_FOUND'}
        
        currentLevel = user.vipLevel
        if currentLevel >= 4:
            return {'success': False, 'error': '请使用进阶升级功能'}
        
        newLevel = currentLevel + 1
        costKusa = 50 * (10 ** newLevel)
        
        if user.kusa < costKusa:
            return {'success': False, 'error': f'草不足，需要{costKusa}草'}
        
        user.kusa -= costKusa
        user.vipLevel = newLevel
        await user.save()
        
        await baseDB.setTradeRecord(
            userId=userId,
            tradeType='web信息员升级',
            gainItemName=f'VIP等级{newLevel}',
            gainItemAmount=1,
            costItemName='草',
            costItemAmount=costKusa
        )
        
        return {
            'success': True,
            'message': f'升级成功！当前等级: Lv{newLevel}',
            'newLevel': newLevel,
            'costKusa': costKusa
        }
    
    @staticmethod
    async def advanced_upgrade_vip(userId: int) -> Dict[str, Any]:
        """VIP进阶升级"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            return {'success': False, 'error': 'USER_NOT_FOUND'}
        
        currentLevel = user.vipLevel
        if currentLevel < 4:
            return {'success': False, 'error': '请先升级到Lv4'}
        
        if currentLevel >= 8:
            return {'success': False, 'error': '已达到最高VIP等级'}
        
        newLevel = currentLevel + 1
        costAdvPoint = 10 ** (newLevel - 4)
        
        if user.advKusa < costAdvPoint:
            return {'success': False, 'error': f'草之精华不足，需要{costAdvPoint}草之精华'}
        
        user.advKusa -= costAdvPoint
        user.vipLevel = newLevel
        await user.save()
        
        await baseDB.setTradeRecord(
            userId=userId,
            tradeType='web进阶信息员升级',
            gainItemName=f'VIP等级{newLevel}',
            gainItemAmount=1,
            costItemName='草之精华',
            costItemAmount=costAdvPoint
        )
        
        return {
            'success': True,
            'message': f'进阶成功！当前等级: Lv{newLevel}',
            'newLevel': newLevel,
            'costAdvPoint': costAdvPoint
        }
    
    @staticmethod
    async def get_total_adv_kusa_rank(limit: int = 25, level_max: int = 10, 
                                      show_inactive: bool = False, 
                                      show_subaccount: bool = True,
                                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取累计草精排行榜"""
        cache_key = f"total_adv_rank_{limit}_{level_max}_{show_inactive}_{show_subaccount}"
        
        if use_cache:
            cached = _get_cache(cache_key)
            if cached:
                return cached
        
        user_list = await baseDB.getAllKusaUser()
        
        from dbConnection.models import UnifiedUser
        unified_user_ids = [user.user_id for user in user_list]
        unified_users = await UnifiedUser.filter(id__in=unified_user_ids).all()
        unified_user_map = {u.id: u for u in unified_users}
        
        filtered_users = []
        for user in user_list:
            if str(user.user_id) == 'bot':
                continue
            if user.vipLevel > level_max:
                continue
            unified_user = unified_user_map.get(user.user_id)
            if not show_subaccount and unified_user and unified_user.relatedUserId:
                continue
            filtered_users.append(user)
        
        all_trade_records = await baseDB.getAllTradeRecordsByCostItem('草之精华')
        
        user_trade_amount = {}
        for record in all_trade_records:
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
                'name': user.name or str(user.user_id),
                'vipLevel': user.vipLevel,
                'totalAdvKusa': total_adv,
                'nowAdvKusa': now_adv,
                'titleAdvKusa': title_adv,
                'itemAdvKusa': item_adv
            })
        
        user_total_adv.sort(key=lambda x: x['totalAdvKusa'], reverse=True)
        
        for i, item in enumerate(user_total_adv[:limit]):
            item['rank'] = i + 1
        
        result = user_total_adv[:limit]
        
        if use_cache:
            _set_cache(cache_key, result)
        
        return result

    @staticmethod
    async def get_grass_statistics(userId: int, personal_period: str = '24小时', total_period: str = '24小时') -> Dict[str, Any]:
        """
        获取生草统计

        Args:
            userId: 用户ID
            personal_period: 个人统计周期 ('24小时', '每日', '每周')
            total_period: 全服统计周期 ('24小时', '每日', '每周')

        Returns:
            Dict: 包含个人和全服统计信息
        """
        import dbConnection.kusa_field as fieldDB
        from datetime import datetime, timedelta

        now = datetime.now()

        # 计算个人统计时间间隔
        if personal_period == "24小时":
            personal_interval = 86400
        elif personal_period == "每日":
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            personal_interval = int((now - today_start).total_seconds())
        elif personal_period == "每周":
            monday_start = now - timedelta(days=now.weekday())
            monday_start = datetime(monday_start.year, monday_start.month, monday_start.day, 0, 0, 0)
            personal_interval = int((now - monday_start).total_seconds())
        else:
            raise ValueError("无效的个人统计周期")

        # 计算全服统计时间间隔
        if total_period == "24小时":
            total_interval = 86400
        elif total_period == "每日":
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            total_interval = int((now - today_start).total_seconds())
        elif total_period == "每周":
            monday_start = now - timedelta(days=now.weekday())
            monday_start = datetime(monday_start.year, monday_start.month, monday_start.day, 0, 0, 0)
            total_interval = int((now - monday_start).total_seconds())
        else:
            raise ValueError("无效的全服统计周期")

        # 获取统计数据
        personal_row = await fieldDB.kusaHistoryReport(userId, datetime.now(), personal_interval)
        total_row = await fieldDB.kusaHistoryTotalReport(total_interval)

        total_avg_kusa = total_row.get('sumKusa', 0) / total_row.get('count', 1) if total_row.get('count', 0) > 0 else 0
        total_avg_adv_kusa = total_row.get('sumAdvKusa', 0) / total_row.get('count', 1) if total_row.get('count', 0) > 0 else 0

        return {
            'personal': {
                'count': personal_row.get('count', 0),
                'sumKusa': personal_row.get('sumKusa', 0),
                'sumAdvKusa': personal_row.get('sumAdvKusa', 0),
                'avgKusa': personal_row.get('avgKusa', 0),
                'avgAdvKusa': personal_row.get('avgAdvKusa', 0)
            },
            'total': {
                'count': total_row.get('count', 0),
                'sumKusa': total_row.get('sumKusa', 0),
                'sumAdvKusa': total_row.get('sumAdvKusa', 0),
                'avgKusa': total_avg_kusa,
                'avgAdvKusa': total_avg_adv_kusa
            }
        }
