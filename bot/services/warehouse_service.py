"""
仓库服务模块

包含所有与仓库、用户相关的业务逻辑
"""

import sys
import os
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB
import dbConnection.user as user_db
from dbConnection.models import UnifiedUser, KusaBase


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
        
        if not await baseDB.deductKusa(userId, kusa_use):
            return {
                'success': False,
                'error': 'INSUFFICIENT_KUSA',
                'message': f'需要{kusa_use}草来压缩'
            }
        
        await baseDB.changeAdvKusa(userId, adv_amount)
        
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
        if not await baseDB.deductKusa(userId, amount):
            return {'success': False, 'error': 'INSUFFICIENT_KUSA', 'message': '草不足'}
        
        await baseDB.changeKusa(target_userId, amount)
        
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
        
        if not await baseDB.deductKusa(userId, costKusa):
            return {'success': False, 'error': f'草不足，需要{costKusa}草'}

        await KusaBase.filter(user_id=userId).update(vipLevel=newLevel)
        
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
        
        if not await baseDB.deductKusa(userId, costAdvPoint, type='advKusa'):
            return {'success': False, 'error': f'草之精华不足，需要{costAdvPoint}草之精华'}

        await KusaBase.filter(user_id=userId).update(vipLevel=newLevel)
        
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
