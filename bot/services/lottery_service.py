"""
抽奖服务模块

包含所有与抽奖系统相关的业务逻辑
"""

import sys
import os
import random
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.draw_item as drawItemDB
import dbConnection.kusa_item as itemDB
from services.chat_service import ChatService


class LotteryService:
    """抽奖服务类"""
    
    RARE_DESCRIBE = ['Easy', 'Normal', 'Hard', 'Lunatic']
    
    @staticmethod
    async def draw_with_redraw(userId: int, pool_name: Optional[str] = None, ban_risk: float = 0) -> Dict[str, Any]:
        """
        抽奖（支持重抽逻辑）
        
        Args:
            userId: 用户ID
            pool_name: 奖池名称
            ban_risk: 禁言概率（0表示不检查禁言）
            
        Returns:
            如果被禁言: {'banned': True, 'disabledSeconds': 禁言秒数}
            如果正常抽奖: {'banned': False, 'item': {...}, 'isNew': True/False, 'redrawCount': 重抽次数}
        """
        if ban_risk > 0:
            ban_shield_info = await itemDB.getItemStorageInfo(userId, '量子护盾')
            if ban_shield_info and ban_shield_info.allowUse and ban_shield_info.amount > 0:
                await itemDB.changeItemAmount(userId, '量子护盾', -1)
                ban_risk = ban_risk / 10
            
            import math
            if random.random() < ban_risk:
                disabled_seconds = int(math.pow(1.1, 5 + random.random() * 70))
                return {
                    'banned': True,
                    'disabledSeconds': disabled_seconds
                }
        
        dice_fragment_info = await itemDB.getItemStorageInfo(userId, '骰子碎片')
        dice_fragment_amount = dice_fragment_info.amount if (dice_fragment_info and dice_fragment_info.allowUse) else 0
        max_redraw = min(dice_fragment_amount, 50) + 1
        
        redraw_count = 0
        item = None
        
        for i in range(max_redraw):
            redraw_count = i
            item = await LotteryService._get_random_item(pool_name=pool_name)
            exist_storage = await drawItemDB.getSingleItemStorage(userId, item.id)
            if not exist_storage:
                break
        
        if redraw_count > 0:
            await itemDB.changeItemAmount(userId, '骰子碎片', -redraw_count)
        
        is_new = not await drawItemDB.getSingleItemStorage(userId, item.id)
        
        await drawItemDB.setItemStorage(userId, item.id)
        
        return {
            'banned': False,
            'item': item,
            'isNew': is_new,
            'redrawCount': redraw_count
        }
    
    @staticmethod
    async def draw_ten(userId: int, base_level: int = 0, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """十连抽（注意：调用前需确保已扣除十连券）"""
        items = []
        for _ in range(10):
            item = await LotteryService._get_random_item(start_rare_rank=base_level, pool_name=pool_name)
            exist_storage = await drawItemDB.getSingleItemStorage(userId, item.id)

            items.append({
                'id': item.id,
                'name': item.name,
                'rare': LotteryService.RARE_DESCRIBE[item.rareRank],
                'isNew': not exist_storage
            })

            await drawItemDB.setItemStorage(userId, item.id)

        return {'banned': False, 'items': items}

    @staticmethod
    async def draw_ten_full(userId: int, base_level: int = 0, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        完整的十连抽流程（包含券检查和扣减）

        Args:
            userId: 用户ID
            base_level: 基础稀有度等级 (0-3)
            pool_name: 奖池名称

        Returns:
            Dict: 包含 success, data/error 的结果
        """
        ten_ticket_names = ['十连券', '高级十连券', '特级十连券', '天琴十连券']
        ticket_name = ten_ticket_names[base_level] if 0 <= base_level < len(ten_ticket_names) else '十连券'

        # 检查券数量
        ticket_amount = await itemDB.getItemAmount(userId, ticket_name)
        if ticket_amount < 1:
            return {
                'success': False,
                'error': 'NO_TICKET',
                'message': f'你没有{ticket_name}，无法进行十连抽'
            }

        # 扣除券
        await itemDB.changeItemAmount(userId, ticket_name, -1)

        # 执行十连抽
        draw_result = await LotteryService.draw_ten(userId=userId, base_level=base_level, pool_name=pool_name)

        # 记录交易
        await baseDB.setTradeRecord(
            userId=userId, tradeType='十连抽',
            gainItemAmount=0, gainItemName='',
            costItemAmount=1, costItemName=ticket_name
        )

        return {
            'success': True,
            'data': draw_result
        }
    
    @staticmethod
    async def add_custom_item(
        userId: int, 
        item_name: str, 
        rare_rank: int, 
        pool_name: str,
        detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加自定义物品"""
        exist_item = await drawItemDB.getItemByName(item_name)
        if exist_item:
            return {'success': False, 'error': 'EXIST', 'message': '此物品名已经存在'}
        
        text_to_moderate = item_name
        if detail:
            text_to_moderate += '\n' + detail
        
        moderation_result = await ChatService.moderate_content(text_to_moderate)
        
        if moderation_result.get('api_error'):
            print(f"[审核API错误] 添加物品审核API调用失败: {moderation_result.get('error_msg')}")
            return {
                'success': False,
                'error': 'MODERATION_API_ERROR',
                'message': '内容审核功能异常，暂时无法新增物品'
            }
        
        if not moderation_result['passed']:
            print(f"[审核未通过] 物品: {item_name}, 原因: {moderation_result.get('reason')}, 类别: {moderation_result.get('category')}")
            return {
                'success': False, 
                'error': 'MODERATION_FAILED', 
                'message': '内容审核未通过，请修改后重试'
            }
        
        user = await baseDB.getKusaUser(userId)
        cost_kusa = 1000 * (8 ** rare_rank)
        if user.kusa < cost_kusa:
            return {'success': False, 'error': 'INSUFFICIENT_KUSA', 'message': '草不足'}
        
        await baseDB.changeKusa(userId, -cost_kusa)
        await drawItemDB.addItem(item_name, rare_rank, pool_name, detail, userId)
        
        return {
            'success': True,
            'message': '添加成功',
            'itemName': item_name,
            'costKusa': cost_kusa
        }
    
    @staticmethod
    async def update_item_detail(
        userId: int, 
        item_name: str, 
        detail: str
    ) -> Dict[str, Any]:
        """更新物品说明"""
        item = await drawItemDB.getItemByName(item_name)
        if not item:
            return {'success': False, 'error': 'ITEM_NOT_FOUND', 'message': '物品不存在'}
        
        if str(item.author) != str(userId):
            return {'success': False, 'error': 'NOT_AUTHOR', 'message': '你不是该物品的作者'}
        
        text_to_moderate = item_name + '\n' + detail
        moderation_result = await ChatService.moderate_content(text_to_moderate)
        
        if moderation_result.get('api_error'):
            print(f"[审核API错误] 修改物品审核API调用失败: {moderation_result.get('error_msg')}")
            return {
                'success': False,
                'error': 'MODERATION_API_ERROR',
                'message': '内容审核功能异常，暂时无法修改物品'
            }
        
        if not moderation_result['passed']:
            print(f"[审核未通过] 物品: {item_name}, 原因: {moderation_result.get('reason')}, 类别: {moderation_result.get('category')}")
            return {
                'success': False, 
                'error': 'MODERATION_FAILED', 
                'message': '内容审核未通过，请修改后重试'
            }
        
        await drawItemDB.setItemDetail(item, detail)
        
        return {'success': True, 'message': '修改成功'}
    
    @staticmethod
    async def get_item_storage(userId: int, rare_rank: Optional[int] = None, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取物品仓库"""
        items = await drawItemDB.getItemsWithStorage(userId, rareRank=rare_rank, poolName=pool_name)
        
        result = {
            'total': len(items),
            'byRare': {}
        }
        
        for item in items:
            rare = LotteryService.RARE_DESCRIBE[item.rareRank]
            if rare not in result['byRare']:
                result['byRare'][rare] = {
                    'total': 0,
                    'owned': 0,
                    'items': []
                }
            
            result['byRare'][rare]['total'] += 1
            if item.storage:
                result['byRare'][rare]['owned'] += 1
                result['byRare'][rare]['items'].append({
                    'name': item.name,
                    'amount': item.storage[0].amount
                })
        
        return result
    
    @staticmethod
    async def search_item(keyword: str, page: int = 1, page_size: int = 12) -> Dict[str, Any]:
        """搜索物品（page从1开始）"""
        count, items = await drawItemDB.searchItem(keyword, page_size, (page - 1) * page_size)
        
        return {
            'count': count,
            'items': [
                {
                    'id': item['id'],
                    'name': item['name'],
                    'rare': LotteryService.RARE_DESCRIBE[item['rareRank']]
                }
                for item in items
            ],
            'totalPages': (count + page_size - 1) // page_size
        }
    
    @staticmethod
    async def get_pool_list() -> List[str]:
        """获取奖池列表"""
        pools = await drawItemDB.getPoolList()
        return pools if pools else []
    
    @staticmethod
    async def get_latest_items(limit: int = 5) -> List[Dict[str, Any]]:
        """获取最新物品"""
        items = await drawItemDB.getLatestItems(limit)
        return [
            {
                'id': item.id,
                'name': item.name,
                'rare': LotteryService.RARE_DESCRIBE[item.rareRank]
            }
            for item in items
        ]
    
    @staticmethod
    async def _get_random_item(start_rare_rank: int = 0, pool_name: Optional[str] = None, max_retry: int = 100):
        """从数据库获取随机物品"""
        import random
        
        if max_retry <= 0:
            pool_msg = f"奖池 '{pool_name}'" if pool_name else "默认奖池"
            raise Exception(f"该奖池暂无物品可抽")
        
        easy_rand = 1 if start_rare_rank > 0 else random.random()
        if easy_rand < 0.7:
            item = await drawItemDB.getRandomItem(0, pool_name)
            if item:
                return item
        
        normal_rand = 1 if start_rare_rank > 1 else random.random()
        if normal_rand < 0.7:
            item = await drawItemDB.getRandomItem(1, pool_name)
            if item:
                return item
        
        hard_rand = 1 if start_rare_rank > 2 else random.random()
        if hard_rand < 0.7:
            item = await drawItemDB.getRandomItem(2, pool_name)
            if item:
                return item
        
        lunatic_rand = random.random()
        if lunatic_rand < 0.7:
            item = await drawItemDB.getRandomItem(3, pool_name)
            if item:
                return item
        
        return await LotteryService._get_random_item(start_rare_rank, pool_name, max_retry - 1)
