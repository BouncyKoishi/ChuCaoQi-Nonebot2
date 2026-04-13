"""
物品服务模块

包含所有与商店、物品相关的业务逻辑
"""

import sys
import os
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB
import dbConnection.user as user_db
from dbConnection.models import UnifiedUser


class ItemService:
    """物品服务类"""

    @staticmethod
    async def transfer_item(
        from_user_id: int,
        to_user_id: int,
        item_name: str,
        amount: int
    ) -> Dict[str, Any]:
        """转让物品

        Args:
            from_user_id: 转让者用户ID
            to_user_id: 接收者用户ID
            item_name: 物品名称
            amount: 转让数量

        Returns:
            Dict: 包含 success, message, error 等字段的结果
        """
        # 检查接收者是否存在
        target_user = await user_db.getUnifiedUser(to_user_id)
        if not target_user:
            return {'success': False, 'error': 'TARGET_NOT_FOUND', 'message': '目标用户不存在'}

        # 检查物品是否存在
        item = await itemDB.getItem(item_name)
        if not item:
            return {'success': False, 'error': 'ITEM_NOT_FOUND', 'message': '物品不存在'}

        # 检查物品是否可转让
        if not item.isTransferable:
            return {'success': False, 'error': 'NOT_TRANSFERABLE', 'message': '此物品不能转让'}

        # 检查转让者物品数量
        item_amount = await itemDB.getItemAmount(from_user_id, item_name)
        if item_amount < amount:
            return {'success': False, 'error': 'INSUFFICIENT_ITEM', 'message': f'你不够{item_name}'}

        # 执行转让
        await itemDB.changeItemAmount(from_user_id, item_name, -amount)
        await itemDB.changeItemAmount(to_user_id, item_name, amount)

        # 记录交易
        await baseDB.setTradeRecord(
            userId=from_user_id,
            tradeType='物品转让',
            gainItemAmount=0,
            gainItemName='',
            costItemAmount=amount,
            costItemName=item_name,
            detail=f'转让给{to_user_id}'
        )

        return {
            'success': True,
            'message': '转让成功',
            'fromUserId': from_user_id,
            'toUserId': to_user_id,
            'itemName': item_name,
            'amount': amount
        }

    @staticmethod
    async def get_transfer_target_by_qq(real_qq: str) -> Optional[UnifiedUser]:
        """通过QQ号获取转让目标用户

        Args:
            real_qq: QQ号

        Returns:
            UnifiedUser 或 None
        """
        return await user_db.getUnifiedUserByRealQQ(real_qq)

    @staticmethod
    async def get_transfer_target_by_id(user_id: int) -> Optional[UnifiedUser]:
        """通过用户ID获取转让目标用户

        Args:
            user_id: 用户ID

        Returns:
            UnifiedUser 或 None
        """
        return await user_db.getUnifiedUser(user_id)

    @staticmethod
    async def buy_item(userId: int, item_name: str, amount: int) -> Dict[str, Any]:
        """购买物品"""
        if item_name == '生草工厂':
            from services import IndustrialService
            return await IndustrialService.buy_kusa_factory(userId, amount)
        if item_name == '草精炼厂':
            from services import IndustrialService
            return await IndustrialService.buy_adv_factory(userId, amount)

        item = await itemDB.getItem(item_name)
        if not item:
            return {'success': False, 'error': 'ITEM_NOT_FOUND', 'message': '物品不存在'}

        if item.shopPrice is None:
            return {'success': False, 'error': 'NOT_FOR_SALE', 'message': '不可购买'}

        now_amount = await itemDB.getItemAmount(userId, item_name)

        if item.amountLimit:
            if now_amount >= item.amountLimit:
                return {'success': False, 'error': 'MAX_AMOUNT', 'message': '已达上限'}
            amount = min(amount, item.amountLimit - now_amount)

        if item.shopPreItems:
            pre_items = item.shopPreItems.split(',')
            for pre_item in pre_items:
                if pre_item.startswith('Lv'):
                    user = await baseDB.getKusaUser(userId)
                    if user.vipLevel < int(pre_item[2:]):
                        return {'success': False, 'error': 'PREREQ_NOT_MET', 'message': f'需要{pre_item}才能购买'}
                else:
                    if not await itemDB.getItemAmount(userId, pre_item):
                        return {'success': False, 'error': 'PREREQ_NOT_MET', 'message': f'需要{pre_item}才能购买'}

        total_price = amount * item.shopPrice
        if item.priceRate:
            total_price = sum(int(item.shopPrice * (item.priceRate ** (now_amount + i))) for i in range(amount))

        price_type = item.priceType

        if price_type == '草':
            user = await baseDB.getKusaUser(userId)
            if user.kusa < total_price:
                return {'success': False, 'error': 'INSUFFICIENT_KUSA', 'message': '草不足'}
            await baseDB.changeKusa(userId, -total_price)
        elif price_type == '草之精华':
            user = await baseDB.getKusaUser(userId)
            if user.advKusa < total_price:
                return {'success': False, 'error': 'INSUFFICIENT_ADV_KUSA', 'message': '草精不足'}
            await baseDB.changeAdvKusa(userId, -total_price)
        elif price_type == '自动化核心':
            from kusa_base import item_charging
            success = await item_charging(userId, item_name, amount, '自动化核心', total_price, '商店(买)')
            if not success:
                return {'success': False, 'error': 'INSUFFICIENT_AUTO_CORE', 'message': '自动化核心不足'}
            await baseDB.setTradeRecord(
                userId=userId, tradeType='商店(买)',
                gainItemName=item_name, gainItemAmount=amount,
                costItemName=price_type, costItemAmount=total_price
            )
            if amount == 1:
                message = f'购买成功！购买了{item_name}。消耗了{total_price}{price_type}。'
            else:
                message = f'购买成功！购买了{amount}个{item_name}。消耗了{total_price}{price_type}。'

            return {
                'success': True,
                'message': message,
                'itemName': item_name,
                'buyingAmount': amount,
                'totalPrice': total_price,
                'priceType': price_type
            }

        await itemDB.changeItemAmount(userId, item_name, amount)

        await baseDB.setTradeRecord(
            userId=userId, tradeType='商店(买)',
            gainItemName=item_name, gainItemAmount=amount,
            costItemName=price_type, costItemAmount=total_price
        )

        if item.amountLimit == 1:
            message = f'购买成功！购买了{item_name}。消耗了{total_price}{price_type}。'
        else:
            message = f'购买成功！购买了{amount}个{item_name}。消耗了{total_price}{price_type}。'

        return {
            'success': True,
            'message': message,
            'itemName': item_name,
            'buyingAmount': amount,
            'totalPrice': total_price,
            'priceType': price_type
        }

    @staticmethod
    async def sell_item(userId: int, item_name: str, amount: int) -> Dict[str, Any]:
        """出售物品"""
        item = await itemDB.getItem(item_name)
        if not item:
            return {'success': False, 'error': 'ITEM_NOT_FOUND', 'message': '物品不存在'}

        if item.sellingPrice is None:
            return {'success': False, 'error': 'NOT_FOR_SALE', 'message': '不可出售'}

        if item.priceRate:
            return {'success': False, 'error': 'FLOATING_PRICE', 'message': '浮动价格物品不能出售'}

        owned = await itemDB.getItemAmount(userId, item_name)
        if owned < amount:
            return {'success': False, 'error': 'INSUFFICIENT_ITEM', 'message': '物品不足'}

        total_price = amount * item.sellingPrice
        price_type = item.priceType

        await itemDB.changeItemAmount(userId, item_name, -amount)

        if price_type == '草':
            await baseDB.changeKusa(userId, total_price)
        elif price_type == '草之精华':
            await baseDB.changeAdvKusa(userId, total_price)

        await baseDB.setTradeRecord(
            userId=userId, tradeType='商店(卖)',
            gainItemName=price_type, gainItemAmount=total_price,
            costItemName=item_name, costItemAmount=amount
        )

        return {
            'success': True,
            'message': f'出售成功！出售了{amount}个{item_name}。获得了{total_price}{price_type}。',
            'itemName': item_name,
            'amount': amount,
            'totalPrice': total_price,
            'priceType': price_type
        }

    @staticmethod
    async def get_shop_list(userId: int, shop_type: str = '全部') -> List[Dict[str, Any]]:
        """获取商店物品列表"""
        from dbConnection.kusa_item import KusaItemList

        if shop_type == '全部':
            shop_items = await KusaItemList.filter(shopPrice__not_isnull=True).order_by('priceType', 'shopPrice').all()
        else:
            shop_items = await KusaItemList.filter(shopPrice__not_isnull=True, priceType=shop_type).order_by('shopPrice').all()

        items = []
        user = await baseDB.getKusaUser(userId)

        for item in shop_items:
            count = await itemDB.getItemAmount(userId, item.name)

            actual_price = item.shopPrice
            if item.priceRate and item.priceRate > 1:
                actual_price = int(item.shopPrice * (item.priceRate ** count))

            items.append({
                'name': item.name,
                'detail': item.detail,
                'type': item.type,
                'isControllable': item.isControllable,
                'isTransferable': item.isTransferable,
                'shopPrice': item.shopPrice,
                'actualPrice': actual_price,
                'sellingPrice': item.sellingPrice,
                'priceRate': item.priceRate,
                'priceType': item.priceType,
                'amountLimit': item.amountLimit,
                'shopPreItems': item.shopPreItems
            })

        if shop_type in ['全部', '自动化核心']:
            try:
                from services.industrial_service import IndustrialService
                next_factory_cost = await IndustrialService.get_next_factory_cost(userId)
                items.append({
                    'name': '生草工厂',
                    'detail': '生草工厂，每天自动生产草。购买成本随数量增加而增加。',
                    'type': '财产',
                    'isControllable': False,
                    'isTransferable': False,
                    'shopPrice': next_factory_cost,
                    'actualPrice': next_factory_cost,
                    'sellingPrice': 0,
                    'priceRate': 1.5,
                    'priceType': '自动化核心',
                    'amountLimit': None,
                    'shopPreItems': None
                })
            except Exception:
                items.append({
                    'name': '生草工厂',
                    'detail': '生草工厂，每天自动生产草。购买成本随数量增加而增加。',
                    'type': '财产',
                    'isControllable': False,
                    'isTransferable': False,
                    'shopPrice': 1,
                    'actualPrice': 1,
                    'sellingPrice': 0,
                    'priceRate': 1.5,
                    'priceType': '自动化核心',
                    'amountLimit': None,
                    'shopPreItems': None
                })

        price_type_order = {'草': 1, '自动化核心': 2, '草之精华': 3}

        def sort_key(item):
            price_type = item.get('priceType', '')
            actual_price = item.get('actualPrice', 0) or 0
            order = price_type_order.get(price_type, 999)
            return (order, actual_price)

        items.sort(key=sort_key)

        return items

    @staticmethod
    async def compose_ticket(userId: int, target: str, amount: int) -> Dict[str, Any]:
        """
        合成奖券

        Args:
            userId: 用户ID
            target: 合成目标（'高级十连券', '特级十连券', '天琴十连券'）
            amount: 合成数量

        Returns:
            Dict: 包含 success, message, error 等字段的结果
        """
        # 检查是否有合成机
        machine_exist = await itemDB.getItemAmount(userId, '奖券合成机')
        if not machine_exist:
            return {'success': False, 'error': 'NO_MACHINE', 'message': '你没有奖券合成机，无法进行奖券合成'}

        # 合成配方
        compose_list = {'高级十连券': '十连券', '特级十连券': '高级十连券', '天琴十连券': '特级十连券'}
        if target not in compose_list:
            return {'success': False, 'error': 'INVALID_TARGET', 'message': '此物品无法进行合成'}

        source = compose_list[target]
        need_amount = amount * 10

        # 检查材料数量
        source_amount = await itemDB.getItemAmount(userId, source)
        if source_amount < need_amount:
            return {'success': False, 'error': 'INSUFFICIENT', 'message': f'你不够{source}，需要{need_amount}个'}

        # 执行合成
        await itemDB.changeItemAmount(userId, source, -need_amount)
        await itemDB.changeItemAmount(userId, target, amount)

        # 记录交易
        await baseDB.setTradeRecord(
            userId=userId, tradeType='奖券合成',
            gainItemName=target, gainItemAmount=amount,
            costItemName=source, costItemAmount=need_amount
        )

        return {
            'success': True,
            'message': f'合成成功！消耗{need_amount}个{source}，获得{amount}个{target}',
            'target': target,
            'amount': amount,
            'source': source,
            'sourceAmount': need_amount
        }
