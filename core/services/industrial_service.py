"""
工厂服务模块

包含所有与工厂相关的业务逻辑
"""

import sys
import os
import math
import random
from typing import Dict, Any


import core.db.kusa_system as baseDB
import core.db.kusa_item as itemDB


class IndustrialService:
    """工厂服务类"""

    # 每日工业批量结算涉及的物品与技术（从 bot 插件迁移）
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
    
    @staticmethod
    async def buy_kusa_factory(userId: int, increase_amount: int) -> Dict[str, Any]:
        """购买生草工厂"""
        if increase_amount > 100:
            return {'success': False, 'error': 'MAX_AMOUNT', 'message': '一次最多新建100个工厂'}
        
        cheap_level = await IndustrialService._get_factory_vip_level(userId)
        factory_amount = await itemDB.getItemAmount(userId, '生草工厂')
        core_amount = await itemDB.getItemAmount(userId, '自动化核心')
        core_cost = IndustrialService._calculate_cost(cheap_level, factory_amount, increase_amount)
        
        if core_amount < core_cost:
            return {
                'success': False,
                'error': 'INSUFFICIENT_CORE',
                'message': f'新建{increase_amount}个工厂需要{core_cost}个自动化核心，你不够核心^ ^',
                'coreCost': core_cost,
                'available': core_amount
            }
        
        await itemDB.changeItemAmount(userId, '自动化核心', -core_cost)
        await itemDB.changeItemAmount(userId, '生草工厂', increase_amount)
        
        trade_detail = f'购买前已有生草工厂{factory_amount}个，购买时等效信息员等级为{cheap_level}'
        await baseDB.setTradeRecord(
            userId=userId, tradeType='商店(买)', detail=trade_detail,
            gainItemName='生草工厂', gainItemAmount=increase_amount,
            costItemName='自动化核心', costItemAmount=core_cost
        )
        
        return {
            'success': True,
            'message': f'建造成功！新建了{increase_amount}个工厂，消耗了{core_cost}个自动化核心，你的当前工厂数为{factory_amount + increase_amount}。',
            'newFactories': increase_amount,
            'coreCost': core_cost,
            'totalFactories': factory_amount + increase_amount
        }
    
    @staticmethod
    async def get_next_factory_cost(userId: int) -> int:
        """获取下一个工厂的价格"""
        cheap_level = await IndustrialService._get_factory_vip_level(userId)
        factory_amount = await itemDB.getItemAmount(userId, '生草工厂')
        return IndustrialService._calculate_cost(cheap_level, factory_amount, 1)
    
    @staticmethod
    async def buy_adv_factory(userId: int, increase_amount: int) -> Dict[str, Any]:
        """购买草精炼厂"""
        blueprint = await itemDB.getItemAmount(userId, '生草工业园区蓝图')
        if blueprint == 0:
            return {'success': False, 'error': 'NO_BLUEPRINT', 'message': '你没有工业园区蓝图，无法建设草精炼厂^ ^'}
        
        base_factory_amount = await itemDB.getItemAmount(userId, '生草工厂')
        mobile_factory_amount = await itemDB.getItemAmount(userId, '流动生草工厂')
        total_base_amount = base_factory_amount + mobile_factory_amount
        
        limit_improved = await itemDB.getItemAmount(userId, '产业链优化')
        adv_factory_limit = total_base_amount // 8 if limit_improved else total_base_amount // 10
        
        old_adv_amount = await itemDB.getItemAmount(userId, '草精炼厂')
        if old_adv_amount >= adv_factory_limit:
            return {
                'success': False,
                'error': 'MAX_LIMIT',
                'message': '你的草精炼厂数量已到达上限！',
                'current': old_adv_amount,
                'limit': adv_factory_limit
            }
        
        new_amount = min(increase_amount, adv_factory_limit - old_adv_amount)
        need_core = new_amount * 500
        core_amount = await itemDB.getItemAmount(userId, '自动化核心')
        
        if core_amount >= need_core:
            await itemDB.changeItemAmount(userId, '草精炼厂', new_amount)
            await itemDB.changeItemAmount(userId, '自动化核心', -need_core)
            
            await baseDB.setTradeRecord(
                userId=userId, tradeType='商店(买)',
                gainItemName='草精炼厂', gainItemAmount=new_amount,
                costItemName='自动化核心', costItemAmount=need_core
            )
            
            return {
                'success': True,
                'message': f'{new_amount}个草精炼厂建造成功！消耗了{need_core}个自动化核心。',
                'newFactories': new_amount,
                'coreCost': need_core
            }
        else:
            return {
                'success': False,
                'error': 'INSUFFICIENT_CORE',
                'message': f'建造{new_amount}个草精炼厂需要{need_core}个自动化核心，你不够核心^ ^',
                'needCore': need_core,
                'available': core_amount
            }
    
    @staticmethod
    async def _get_factory_vip_level(userId: int) -> int:
        """获取工厂VIP等级"""
        user = await baseDB.getKusaUser(userId)
        return user.vipLevel + await itemDB.getTechLevel(userId, '生草工厂自动工艺')
    
    @staticmethod
    def _calculate_cost(cheap_level_all: int, now_factory: int, new_factory: int) -> int:
        """计算工厂成本"""
        base = 1 + 0.5 * math.exp(-0.255 * cheap_level_all)
        return int((base ** now_factory) * (base ** new_factory - 1) / (base - 1))

    @staticmethod
    async def calculate_daily_production(userId: int) -> Dict[str, Any]:
        """
        计算每日产量

        Args:
            userId: 用户ID

        Returns:
            Dict: 包含每日产量详细计算结果
        """
        factory_amount = await itemDB.getItemAmount(userId, '生草工厂')
        mobile_factory_amount = await itemDB.getItemAmount(userId, '流动生草工厂')
        machine_amount = await itemDB.getItemAmount(userId, '生草机器')
        machine_tech_level = await itemDB.getTechLevel(userId, '试做型机器')
        factory_tech_level = await itemDB.getTechLevel(userId, '生草工厂效率')
        adv_factory_info = await itemDB.getItemStorageInfo(userId, '草精炼厂')
        core_factory_amount = await itemDB.getItemAmount(userId, '核心装配工厂')
        core_tech_level = await itemDB.getTechLevel(userId, '核心工厂效率')
        black_tea_pool = await itemDB.getItemAmount(userId, '红茶池')

        kusa_rand_int = 8
        core_rand_int = 8

        # 机器产量计算
        machine_add_kusa = kusa_rand_int * machine_amount
        machine_add_kusa *= {0: 1, 1: 8, 2: 40}.get(machine_tech_level, 1)

        # 工厂产量计算
        factory_new_device_level = await itemDB.getTechLevel(userId, '生草工厂新型设备')
        factory_add_kusa = 640 * (factory_amount + mobile_factory_amount)
        factory_add_kusa *= (2 ** factory_new_device_level)
        factory_add_kusa *= (2 ** factory_tech_level)

        # 精炼厂消耗
        adv_factory_cost_kusa = 5000 * adv_factory_info.amount if adv_factory_info and adv_factory_info.allowUse else 0
        daily_kusa = math.ceil(machine_add_kusa + factory_add_kusa - adv_factory_cost_kusa)

        # 草之精华产量计算
        daily_adv_kusa = 0
        adv_kusa_base_addition = 0
        seven_planet_magic = 0
        adv_kusa_addition_i = 0
        adv_kusa_addition_ii = 0
        if adv_factory_info and adv_factory_info.allowUse:
            adv_kusa = adv_factory_info.amount
            seven_planet_magic = await itemDB.getItemAmount(userId, '七曜精炼术')
            if seven_planet_magic:
                adv_kusa += (adv_factory_info.amount // 7) * 4
            adv_kusa_addition_i = await itemDB.getItemAmount(userId, '草精炼厂效率I')
            if adv_factory_info.amount > 7 and adv_kusa_addition_i:
                adv_kusa += (adv_factory_info.amount - 7)
            adv_kusa_base_addition = await itemDB.getItemAmount(userId, '高效草精炼指南')
            if adv_kusa_base_addition:
                addition_count = min(adv_kusa_base_addition, adv_factory_info.amount)
                adv_kusa += addition_count
                adv_kusa_addition_ii = await itemDB.getItemAmount(userId, '草精炼厂效率II')
                if adv_kusa_addition_ii:
                    adv_kusa += addition_count * (addition_count - 1)
            daily_adv_kusa = adv_kusa

        # 核心产量计算
        add_core = core_rand_int * core_factory_amount
        add_core *= {0: 1, 1: 2, 2: 4, 3: 8, 4: 12}.get(core_tech_level, 1)
        daily_core = math.ceil(add_core)

        # 红茶产量
        daily_black_tea = 15 * black_tea_pool

        # 蕾米球的生产魔法加成
        remi_production_magic = await itemDB.getItemStorageInfo(userId, '蕾米球的生产魔法')
        remi_bonus = 0
        if remi_production_magic and remi_production_magic.allowUse:
            import core.db.kusa_field as fieldDB
            kusa_field = await fieldDB.getKusaField(userId)
            extra_magnification = max(0.04 * (kusa_field.soilCapacity - 20), 0)
            remi_bonus = extra_magnification

        return {
            'kusaAmount': daily_kusa,
            'advKusaAmount': daily_adv_kusa,
            'coreAmount': daily_core,
            'blackTeaAmount': daily_black_tea,
            'machineAmount': machine_amount,
            'machineRandInt': kusa_rand_int,
            'machineTechLevel': machine_tech_level,
            'factoryAmount': factory_amount,
            'mobileFactoryAmount': mobile_factory_amount,
            'factoryNewDeviceLevel': factory_new_device_level,
            'factoryTechLevel': factory_tech_level,
            'advFactoryAmount': adv_factory_info.amount if adv_factory_info else 0,
            'advKusaBaseAddition': adv_kusa_base_addition,
            'sevenPlanetMagic': seven_planet_magic,
            'advKusaAdditionI': adv_kusa_addition_i,
            'advKusaAdditionII': adv_kusa_addition_ii,
            'coreFactoryAmount': core_factory_amount,
            'coreTechLevel': core_tech_level,
            'coreRandInt': core_rand_int,
            'remiProductionMagic': remi_production_magic and remi_production_magic.allowUse,
            'remiBonus': remi_bonus
        }

    # ==================== 每日工业批量结算（从 bot/plugins/kusa_industrial.py 下沉） ====================

    @staticmethod
    async def settle_all_daily() -> Dict[str, Any]:
        """全用户每日工业批量结算

        Returns:
            Dict: {'kusaRandInt', 'coreRandInt', 'signStr'} 签到信息，供调用方发公告
        """
        import core.db.kusa_field as fieldDB

        kusa_rand_int = random.randint(4, 12)
        core_rand_int = random.randint(4, 12)
        sign_str = f'今日工业运作开始！\n生草机器产量：{kusa_rand_int}\n核心装配工厂产量：{core_rand_int}'

        user_list = await baseDB.getAllKusaUser()
        user_id_list = [user.user_id for user in user_list]

        item_amounts = await itemDB.batchGetItemAmounts(user_id_list, IndustrialService.INDUSTRIAL_ITEMS)
        tech_levels = await itemDB.batchGetTechLevels(user_id_list, IndustrialService.INDUSTRIAL_TECHS)
        kusa_fields = await fieldDB.batchGetKusaField(user_id_list)

        item_storage_info = await itemDB.batchGetItemStorage(
            user_id_list, ['草精炼厂', '蕾米球的生产魔法', '冰雪酱的休耕魔法']
        )

        remi_magic_users = [
            user_id for user_id in user_id_list
            if item_storage_info.get(user_id, {}).get('蕾米球的生产魔法') and
               item_storage_info[user_id]['蕾米球的生产魔法'].allowUse
        ]

        used_capacities = {}
        if remi_magic_users:
            used_capacities = await fieldDB.batchKusaSoilUseUp(remi_magic_users)

        kusa_updates = {}
        adv_kusa_updates = {}
        item_updates = []

        for user in user_list:
            user_id = user.user_id
            items = item_amounts.get(user_id, {})
            techs = tech_levels.get(user_id, {})
            kusa_field = kusa_fields.get(user_id)

            new_kusa_amount = IndustrialService._settle_daily_kusa_num(
                items, techs, kusa_rand_int, item_storage_info.get(user_id, {}).get('草精炼厂'))
            new_adv_kusa_amount = IndustrialService._settle_daily_adv_kusa_num(
                items, item_storage_info.get(user_id, {}))
            new_core_amount = IndustrialService._settle_daily_core_num(items, techs, core_rand_int)
            new_black_tea_amount = IndustrialService._settle_daily_black_tea_num(items)

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
                    icy_magic_info = item_storage_info.get(user_id, {}).get('冰雪酱的休耕魔法')
                    if icy_magic_info and icy_magic_info.allowUse:
                        await itemDB.updateTimeLimitedItem(user_id, '休耕标记', 86300, 2)
                        overload_time = 9 * 3600
                await itemDB.updateTimeLimitedItem(user_id, '过载标记', overload_time)

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

        await baseDB.batchChangeKusa(kusa_updates)
        await baseDB.batchChangeAdvKusa(adv_kusa_updates)
        await itemDB.batchChangeItemAmounts(item_updates)

        return {
            'kusaRandInt': kusa_rand_int,
            'coreRandInt': core_rand_int,
            'signStr': sign_str,
        }

    @staticmethod
    def _settle_daily_kusa_num(items, techs, machine_rand_int, adv_factory_storage_info=None):
        """计算每日生草数量（批量结算版）"""
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

    @staticmethod
    def _settle_daily_adv_kusa_num(items, storage_info):
        """计算每日草之精华数量（批量结算版）"""
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

    @staticmethod
    def _settle_daily_core_num(items, techs, core_factory_rand_int):
        """计算每日核心数量（批量结算版）"""
        core_factory_amount = items.get('核心装配工厂', 0)
        core_tech_level = techs.get('核心工厂效率', 0)
        add_core = core_factory_rand_int * core_factory_amount
        add_core *= {0: 1, 1: 2, 2: 4, 3: 8, 4: 12}.get(core_tech_level, 1)
        return math.ceil(add_core)

    @staticmethod
    def _settle_daily_black_tea_num(items):
        """计算每日红茶数量（批量结算版）"""
        black_tea_pool = items.get('红茶池', 0)
        return 15 * black_tea_pool
