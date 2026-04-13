"""
工厂服务模块

包含所有与工厂相关的业务逻辑
"""

import sys
import os
import math
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_item as itemDB


class IndustrialService:
    """工厂服务类"""
    
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
            import dbConnection.kusa_field as fieldDB
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
