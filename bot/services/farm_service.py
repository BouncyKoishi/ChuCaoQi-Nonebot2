"""
生草服务模块

包含所有与生草、农田相关的业务逻辑
"""

import sys
import os
import random
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.kusa_field as fieldDB
import dbConnection.kusa_item as itemDB
import dbConnection.user as user_db


ADV_KUSA_PROBABILITY_DICT = {0: 0, 1: 0.125, 2: 0.5, 3: 0.5, 4: 0.625}
KUSA_TYPE_EFFECT_MAP = {
    '巨草': 2, '巨巨草': 3, '巨灵草': 4, '速草': 0.75, '速速草': 0.5,
    '灵草': 2, '不灵草': 0, '灵草II': 3, '灵草III': 4, '灵草IV': 5,
    '灵草V': 6, '灵草VI': 7, '灵草VII': 8, '灵草VIII': 9, '神灵草': 10
}
ADV_KUSA_TYPE_EFFECT_MAP = {
    '巨草': 2, '巨巨草': 3, '巨灵草': 4, '灵草': 2, '灵草II': 3,
    '灵草III': 4, '灵草IV': 5, '灵草V': 6, '灵草VI': 7, '灵草VII': 8,
    '灵草VIII': 9, '神灵草': 10
}
KUSA_TYPE_TIME_MULTIPLIER_MAP = {'巨草': 2, '巨灵草': 2, '巨巨草': 4, '速草': 0.5}
PLANT_COSTING_MAP = {'巨草': 2, '巨灵草': 2, '巨巨草': 4}
KUSA_TECH_LEVEL_EFFECT_DICT = {0: 1, 1: 2.5, 2: 4, 3: 6, 4: 8.4}


class FarmService:
    """生草服务类"""
    
    @staticmethod
    async def get_status(userId: int) -> Dict[str, Any]:
        """获取农田状态"""
        user = await baseDB.getKusaUser(userId)
        if not user:
            await baseDB.createKusaUser(userId)
            user = await baseDB.getKusaUser(userId)
        
        unified_user = await user_db.getUnifiedUser(userId)
        real_qq = unified_user.realQQ if unified_user else None
        
        field = await fieldDB.getKusaField(userId)
        if not field:
            from dbConnection.models import KusaField
            unified_user = await user_db.getUnifiedUser(userId)
            field = await KusaField.create(
                user=unified_user,
                soilCapacity=25,
                defaultKusaType="草"
            )
        field_amount = await itemDB.getItemAmount(userId, '草地')
        double_magic = await itemDB.getItemAmount(userId, '双生法术卷轴')
        spiritual_sign = await itemDB.getItemAmount(userId, '灵性标记')
        biogas_storage = await itemDB.getItemStorageInfo(userId, '沼气池')
        black_tea = await itemDB.getItemStorageInfo(userId, '红茶')
        fallow_sign = await itemDB.getItemAmount(userId, '休耕标记')
        kela_storage = await itemDB.getItemStorageInfo(userId, '金坷垃')
        weeder_amount = await itemDB.getItemAmount(userId, '除草机')
        mirror_plugin = await itemDB.getItemStorageInfo(userId, '镜中草基因模块')
        spare_capacity = await itemDB.getItemAmount(userId, '后备承载力')
        kusa_quality_level = await itemDB.getTechLevel(userId, '生草质量')
        kusa_tech_level = await itemDB.getTechLevel(userId, '生草数量')
        kusa_tech_effect = KUSA_TECH_LEVEL_EFFECT_DICT.get(kusa_tech_level, 1)
        soil_effect = 1 - 0.1 * (10 - field.soilCapacity) if field.soilCapacity <= 10 else 1
        
        divine_plugin = await itemDB.getItemStorageInfo(userId, '神灵草基因模块')
        spiritless_divine_plugin = await itemDB.getItemStorageInfo(userId, '不灵草灵生模块')
        must_grow = await itemDB.getItemAmount(userId, '生草控制论')
        chain_magic = await itemDB.getItemAmount(userId, '纯酱的生草魔法')
        overload_magic = await itemDB.getItemAmount(userId, '奈奈的过载魔法')
        spiritual_machine = await itemDB.getItemStorageInfo(userId, '灵性自动分配装置')
        
        vip_bonus = 0.5 * (2 ** (user.vipLevel - 1)) if user and user.vipLevel > 0 else 0
        
        result = {
            'userId': userId,
            'qq': real_qq,
            'kusaType': field.kusaType,
            'soilCapacity': field.soilCapacity,
            'defaultKusaType': field.defaultKusaType,
            'isGrowing': bool(field.kusaFinishTs),
            'fieldAmount': field_amount,
            'vipLevel': user.vipLevel if user else 0,
            'vipBonus': vip_bonus,
            'kelaAvailable': kela_storage is not None and kela_storage.amount >= field_amount if kela_storage else False,
            'kelaAmount': kela_storage.amount if kela_storage else 0,
            'doubleMagic': double_magic > 0,
            'spiritualSign': spiritual_sign > 0,
            'biogasAvailable': biogas_storage is not None and biogas_storage.allowUse and field.kusaType != '不灵草' if biogas_storage else False,
            'hasBlackTea': black_tea is not None and black_tea.allowUse if black_tea else False,
            'biogasEffect': field.biogasEffect if hasattr(field, 'biogasEffect') else 1,
            'fallowSign': fallow_sign,
            'hasWeeder': weeder_amount > 0,
            'mirrorPluginAvailable': mirror_plugin is not None and mirror_plugin.allowUse and spare_capacity > 0,
            'kusaQualityLevel': kusa_quality_level,
            'kusaQualityEffect': 1 + kusa_quality_level * 0.2 if kusa_quality_level > 0 else 1,
            'kusaTechLevel': kusa_tech_level,
            'kusaTechEffect': kusa_tech_effect,
            'soilEffect': soil_effect,
            'isUsingKela': field.isUsingKela if hasattr(field, 'isUsingKela') else False,
            'isMirroring': field.isMirroring if hasattr(field, 'isMirroring') else False,
            'kusaTypeEffect': KUSA_TYPE_EFFECT_MAP.get(field.kusaType, 1) if field.kusaType else 1,
            'advKusaTypeEffect': ADV_KUSA_TYPE_EFFECT_MAP.get(field.kusaType, 1) if field.kusaType else 1,
            'spareCapacity': spare_capacity,
            'isOverloaded': False,
            'growInfo': None,
            'divinePluginAvailable': divine_plugin is not None and divine_plugin.allowUse,
            'spiritlessDivinePluginAvailable': spiritless_divine_plugin is not None and spiritless_divine_plugin.allowUse,
            'mustGrow': must_grow > 0,
            'chainMagic': chain_magic > 0,
            'overloadMagic': overload_magic > 0,
            'spiritualMachineAvailable': spiritual_machine is not None and spiritual_machine.allowUse,
        }
        
        if field.kusaFinishTs:
            predict_time = datetime.fromtimestamp(field.kusaFinishTs) + timedelta(minutes=1)
            rest_time = predict_time - datetime.now()
            
            result['growInfo'] = {
                'finishTimestamp': field.kusaFinishTs,
                'predictFinishTime': predict_time.isoformat(),
                'remainingSeconds': max(0, rest_time.total_seconds()),
                'kusaResult': field.kusaResult,
                'advKusaResult': field.advKusaResult,
                'isPrescient': field.isPrescient
            }
        
        overload = await itemDB.getItemStorageInfo(userId, '过载标记')
        result['isOverloaded'] = overload is not None
        if overload:
            result['overloadEndTime'] = datetime.fromtimestamp(overload.timeLimitTs).isoformat()
        
        min_predict, max_predict = await FarmService.get_predict(field)
        result['predictKusaMin'] = min_predict
        result['predictKusaMax'] = max_predict
        
        if field.kusaFinishTs and field.isPrescient:
            result['predictAdvKusa'] = field.advKusaResult or 0
        else:
            result['predictAdvKusa'] = 0
        
        result['calculationDetails'] = {
            'baseKusa': '0 ~ 10',
            'vipBonus': vip_bonus,
            'fieldAmount': field_amount,
            'doubleMagic': double_magic > 0,
            'spiritualSign': spiritual_sign > 0,
            'kusaTechEffect': kusa_tech_effect,
            'soilEffect': soil_effect,
            'kusaTypeEffect': KUSA_TYPE_EFFECT_MAP.get(field.kusaType, 1) if field.kusaType else 1,
            'isUsingKela': field.isUsingKela if hasattr(field, 'isUsingKela') else False,
            'isMirroring': field.isMirroring if hasattr(field, 'isMirroring') else False,
            'biogasEffect': field.biogasEffect if hasattr(field, 'biogasEffect') else 1,
            'fallowSign': fallow_sign
        }
        
        return result
    
    @staticmethod
    async def start_planting(userId: int, kusa_type: Optional[str] = None, overload: bool = False) -> Dict[str, Any]:
        """开始生草
        
        Args:
            userId: 用户ID
            kusa_type: 生草类型
            overload: 是否过载
        """
        field = await fieldDB.getKusaField(userId)
        
        if not field:
            from dbConnection.models import KusaField
            unified_user = await user_db.getUnifiedUser(userId)
            field = await KusaField.create(
                user=unified_user,
                soilCapacity=25,
                defaultKusaType="草"
            )
        
        if field.kusaFinishTs:
            predict_time = datetime.fromtimestamp(field.kusaFinishTs) + timedelta(minutes=1)
            rest_time = predict_time - datetime.now()
            
            if rest_time.total_seconds() > 60:
                return {
                    'success': False,
                    'error': 'ALREADY_GROWING',
                    'errorMsg': f'你的{field.kusaType}还在生。剩余时间：{int(rest_time.total_seconds() // 60)}min',
                    'data': {
                        'remainingSeconds': rest_time.total_seconds(),
                        'predictFinishTime': predict_time.isoformat()
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'ALMOST_DONE',
                    'errorMsg': f'你的{field.kusaType}将在一分钟内长成！'
                }
        
        current_overload = await itemDB.getItemStorageInfo(userId, '过载标记')
        if current_overload:
            overload_end_time = datetime.fromtimestamp(current_overload.timeLimitTs).strftime('%H:%M')
            return {
                'success': False,
                'error': 'OVERLOADED',
                'errorMsg': f'土地过载中，无法生草！过载结束时间：{overload_end_time}'
            }
        
        if overload:
            overload_magic = await itemDB.getItemAmount(userId, '奈奈的过载魔法')
            if not overload_magic:
                return {
                    'success': False,
                    'error': 'NO_OVERLOAD_MAGIC',
                    'errorMsg': '你未学会过载魔法，无法进行过载生草'
                }
        
        soil_saver = await itemDB.getItemStorageInfo(userId, '土壤保护装置')
        if soil_saver and soil_saver.allowUse and field.soilCapacity <= 10:
            return {
                'success': False,
                'error': 'SOIL_PROTECTED',
                'errorMsg': f'当前承载力为{field.soilCapacity}，强制土壤保护启用中，不允许生草'
            }
        
        if field.soilCapacity <= 0:
            return {
                'success': False,
                'error': 'NO_SOIL_CAPACITY',
                'errorMsg': f'当前承载力为{field.soilCapacity}，不允许生草'
            }
        
        actual_type = kusa_type if kusa_type else field.defaultKusaType
        actual_type = "草" if not actual_type else actual_type
        
        spiritual_machine = await itemDB.getItemStorageInfo(userId, '灵性自动分配装置')
        auto_assigned = False
        if spiritual_machine and spiritual_machine.allowUse:
            spiritual_sign = await itemDB.getItemAmount(userId, '灵性标记')
            if not spiritual_sign and not kusa_type:
                actual_type = '不灵草'
                auto_assigned = True
        
        if actual_type != '草':
            validation = await FarmService._validate_kusa_type(userId, actual_type)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': 'INVALID_KUSA_TYPE',
                    'errorMsg': validation['message']
                }
        
        divine_plugin = await itemDB.getItemStorageInfo(userId, '神灵草基因模块')
        if divine_plugin and divine_plugin.allowUse and actual_type != '不灵草':
            spiritless_divine_plugin = await itemDB.getItemStorageInfo(userId, '不灵草灵生模块')
            spiritual_sign = await itemDB.getItemAmount(userId, '灵性标记')
            divine_percent = 0.1 if spiritless_divine_plugin and spiritual_sign else 0.05
            if random.random() < divine_percent:
                actual_type = '神灵草'
        
        is_mirroring = False
        mirror_plugin = await itemDB.getItemStorageInfo(userId, '镜中草基因模块')
        if mirror_plugin and mirror_plugin.allowUse and actual_type != '不灵草':
            spare_capacity = await itemDB.getItemAmount(userId, '后备承载力')
            if spare_capacity > 0 and random.random() < 0.5:
                await itemDB.changeItemAmount(userId, '后备承载力', -1)
                is_mirroring = True
        
        if actual_type == "半灵草":
            actual_type = "灵草" if random.random() < 0.5 else "草"
        if actual_type == "半灵巨草":
            actual_type = "巨灵草" if random.random() < 0.5 else "巨草"
        if actual_type == "灵灵草":
            spirit_type_name = ['草', '灵草', '灵草II', '灵草III', '灵草IV', '灵草V', '灵草VI', '灵草VII', '灵草VIII']
            spirit_level = min(8, int(-math.log2(random.random())))
            actual_type = spirit_type_name[spirit_level]
        
        grow_time = random.randint(40, 80)
        bio_gas_effect = 1
        biogas_storage = await itemDB.getItemStorageInfo(userId, '沼气池')
        field_amount = await itemDB.getItemAmount(userId, '草地')
        
        if biogas_storage and biogas_storage.allowUse and actual_type != '不灵草':
            bio_gas_effect = round(random.uniform(0.5, 2), 2)
            black_tea = await itemDB.getItemStorageInfo(userId, '红茶')
            if black_tea and black_tea.allowUse:
                bio_gas_effect = round(random.uniform(1.2, 2), 2)
                await itemDB.changeItemAmount(userId, '红茶', -1)
        
        is_using_kela = False
        kela_storage = await itemDB.getItemStorageInfo(userId, '金坷垃')
        if kela_storage and kela_storage.allowUse and kela_storage.amount >= field_amount:
            is_using_kela = True
            grow_time = math.ceil(grow_time / 2)
            await itemDB.changeItemAmount(userId, '金坷垃', -field_amount)
        
        grow_time = math.ceil(grow_time * KUSA_TYPE_TIME_MULTIPLIER_MAP.get(actual_type, 1))
        grow_time = random.randint(1, 5) if actual_type == "速速草" else grow_time
        
        magic_immediate = False
        magic_quick = False
        spiritless_immediate = False
        
        kusa_speed_magic = await itemDB.getItemAmount(userId, '奈奈的时光魔法')
        if kusa_speed_magic:
            nana_title = await itemDB.getItemAmount(userId, '祝福之色赠予结缘之人')
            immediate_percent = 0.07 if nana_title else 0.007
            magic_immediate = random.random() < immediate_percent
            magic_quick = not magic_immediate and random.random() < 0.07
            
            if magic_immediate:
                grow_time = 0
                await itemDB.updateTimeLimitedItem(userId, '时光胶囊标记', 60)
            elif magic_quick:
                grow_time = math.ceil(grow_time * (1 - 0.777))
        
        spiritless_immediate_plugin = await itemDB.getItemAmount(userId, '不灵草速生模块')
        if spiritless_immediate_plugin and actual_type == "不灵草" and random.random() < 0.5:
            spiritless_immediate = True
            grow_time = 0
        
        plant_costing = PLANT_COSTING_MAP.get(actual_type, 1)
        
        junior_prescient = await itemDB.getItemStorageInfo(userId, '初级生草预知')
        senior_prescient = await itemDB.getItemStorageInfo(userId, '生草预知')
        is_prescient = bool((junior_prescient and junior_prescient.allowUse) or (senior_prescient and senior_prescient.allowUse))
        
        weed_costing = 2 if (junior_prescient and junior_prescient.allowUse and 
                             not (senior_prescient and senior_prescient.allowUse)) else 0
        
        kusa_finish_ts = datetime.timestamp(datetime.now() + timedelta(minutes=grow_time))
        
        soil_capacity_before = field.soilCapacity
        
        await fieldDB.kusaStartGrowing(
            userId, kusa_finish_ts, is_using_kela, bio_gas_effect, actual_type,
            plant_costing, weed_costing, is_prescient, overload, is_mirroring
        )
        
        new_field = await fieldDB.getKusaField(userId)
        base_kusa_num = 10 * random.random()
        final_kusa_num = await FarmService._calculate_kusa_num(new_field, base_kusa_num, soil_capacity_before)
        final_adv_kusa_num = await FarmService._calculate_adv_kusa_num(new_field, soil_capacity_before)
        await fieldDB.updateKusaResult(userId, final_kusa_num, final_adv_kusa_num)
        
        min_predict, max_predict = await FarmService.get_predict(new_field)
        
        if is_prescient:
            predict_info = {
                'isPrescient': True,
                'kusaResult': final_kusa_num,
                'advKusaResult': final_adv_kusa_num
            }
        else:
            predict_info = {
                'isPrescient': False,
                'predictRange': {'min': min_predict, 'max': max_predict}
            }
        
        return {
            'success': True,
            'data': {
                'kusaType': actual_type,
                'growTimeMinutes': grow_time,
                'growTime': grow_time,
                'predictFinishTime': (datetime.now() + timedelta(minutes=grow_time + 1)).isoformat(),
                'soilCapacity': new_field.soilCapacity,
                **predict_info,
                'isMirroring': False,
                'isUsingKela': is_using_kela,
                'biogasEffect': bio_gas_effect,
                'overload': overload,
                'autoAssigned': auto_assigned,
                'magicImmediate': magic_immediate,
                'magicQuick': magic_quick,
                'spiritlessImmediate': spiritless_immediate
            }
        }
    
    @staticmethod
    async def harvest(userId: int) -> Dict[str, Any]:
        """除草"""
        field = await fieldDB.getKusaField(userId)
        
        if not field:
            return {'success': False, 'error': 'FIELD_NOT_FOUND'}
        
        if not field.kusaFinishTs:
            return {'success': False, 'error': 'NO_KUSA_TO_HARVEST'}
        
        weeder = await itemDB.getItemAmount(userId, '除草机')
        if not weeder:
            return {'success': False, 'error': 'NO_WEEDER'}
        
        await fieldDB.kusaStopGrowing(field, True)
        await itemDB.removeTimeLimitedItem(userId, '灵性标记')
        
        fallow_sign = await itemDB.getItemAmount(userId, '休耕标记')
        if fallow_sign:
            await itemDB.changeItemAmount(userId, '休耕标记', -1)
        
        return {'success': True, 'message': '除草成功', 'data': {'action': 'weed_removal'}}
    
    @staticmethod
    async def set_default_type(userId: int, kusa_type: Optional[str]) -> Dict[str, Any]:
        """设置默认草种"""
        validation = await FarmService._validate_kusa_type(userId, kusa_type)
        if not validation['valid']:
            return {
                'success': False,
                'error': 'INVALID_KUSA_TYPE',
                'message': validation['message']
            }
        
        field = await fieldDB.getKusaField(userId)
        if not field:
            from dbConnection.models import KusaField
            unified_user = await user_db.getUnifiedUser(userId)
            field = await KusaField.create(
                user=unified_user,
                soilCapacity=25,
                defaultKusaType="草"
            )
        await fieldDB.updateDefaultKusaType(userId, kusa_type)
        if kusa_type == '草':
            return {
                'success': True,
                'message': '你的生草默认草种已经设置为普通草',
                'defaultKusaType': '草'
            }
        else:
            return {
                'success': True,
                'message': f'你的生草默认草种已经设置为{kusa_type}',
                'defaultKusaType': kusa_type
            }
    
    @staticmethod
    async def recover_capacity(userId: int, amount: Optional[int] = None) -> Dict[str, Any]:
        """补充承载力"""
        field = await fieldDB.getKusaField(userId)
        
        if not field:
            return {'success': False, 'error': 'FIELD_NOT_FOUND', 'message': '田地不存在'}
        
        if field.soilCapacity >= 25:
            return {'success': False, 'error': 'ALREADY_FULL', 'message': '当前承载力是满的'}
        
        to_full = 25 - field.soilCapacity
        need = min(to_full, amount) if amount else to_full
        
        spare = await itemDB.getItemAmount(userId, '后备承载力')
        
        actual_need = min(need, spare)
        
        if actual_need <= 0:
            return {
                'success': False,
                'error': 'INSUFFICIENT_SPARE',
                'message': '后备承载力不足',
                'available': spare,
                'needed': need
            }
        
        await itemDB.changeItemAmount(userId, '后备承载力', -actual_need)
        await fieldDB.kusaSoilRecover(userId, actual_need)
        
        return {
            'success': True,
            'message': f'承载力提升了{actual_need}点',
            'recovered': actual_need,
            'newCapacity': field.soilCapacity + actual_need
        }
    
    @staticmethod
    async def get_predict(field) -> tuple[int, int]:
        """获取生草预估"""
        min_p = await FarmService._calculate_kusa_num(field, 0)
        max_p = await FarmService._calculate_kusa_num(field, 10)
        return min_p, max_p
    
    @staticmethod
    async def get_history(userId: int, limit: int = 20) -> List[Dict[str, Any]]:
        """获取生草历史"""
        history = await fieldDB.getRecentKusaHistory(userId, limit)
        return [
            {
                'timestamp': h.createTimeTs,
                'kusaType': h.kusaType,
                'kusaResult': h.kusaResult,
                'advKusaResult': h.advKusaResult
            }
            for h in history
        ]
    
    @staticmethod
    async def get_grass_stats(userId: int = None, period: str = '24小时') -> Dict[str, Any]:
        """
        统一生草统计方法

        Args:
            userId: 用户ID，为None时只返回全服统计
            period: 统计周期 ('24小时', '昨日', '上周')

        Returns:
            Dict: 包含 personal（如有userId）和 total 统计信息
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)

        if period == "24小时":
            end_time = now
            interval = 86400
        elif period == "昨日":
            end_time = today_start
            interval = 86400
        elif period == "上周":
            monday_start = today_start - timedelta(days=now.weekday())
            end_time = monday_start
            interval = 604800
        else:
            raise ValueError(f"无效的统计周期: {period}")

        result = {}

        if userId is not None:
            personal_row = await fieldDB.kusaHistoryReport(userId, end_time, interval)
            result['personal'] = {
                'count': personal_row.get('count') or 0,
                'sumKusa': personal_row.get('sumKusa') or 0,
                'sumAdvKusa': personal_row.get('sumAdvKusa') or 0,
                'avgKusa': round(personal_row.get('avgKusa') or 0, 2),
                'avgAdvKusa': round(personal_row.get('avgAdvKusa') or 0, 2)
            }

        total_row = await fieldDB.kusaHistoryTotalReport(interval, endTime=end_time)
        total_count = total_row.get('count') or 0
        result['total'] = {
            'count': total_count,
            'sumKusa': total_row.get('sumKusa') or 0,
            'sumAdvKusa': total_row.get('sumAdvKusa') or 0,
            'avgKusa': round((total_row.get('sumKusa') or 0) / total_count, 2) if total_count > 0 else 0,
            'avgAdvKusa': round((total_row.get('sumAdvKusa') or 0) / total_count, 2) if total_count > 0 else 0
        }

        return result

    @staticmethod
    async def get_available_types(userId: int) -> List[Dict[str, Any]]:
        """获取可用草种"""
        grass_types = ['草', '巨草', '巨巨草', '速草', '速速草',
                      '灵草', '半灵草', '灵灵草', '半灵巨草', '不灵草']
        
        available = []
        for gtype in grass_types:
            if gtype == '草':
                available.append({'name': '草', 'displayName': '普通草', 'available': True})
            else:
                gene_name = f"{gtype}基因图谱"
                item = await itemDB.getItem(gene_name)
                if item:
                    info = await itemDB.getItemStorageInfo(userId, gene_name)
                    available.append({'name': gtype, 'displayName': gtype, 'available': info is not None})
        
        return available
    
    @staticmethod
    async def _validate_kusa_type(userId: int, kusa_type: str) -> Dict[str, Any]:
        """验证草种"""
        if kusa_type == '草':
            return {'valid': True}
        
        gene_name = f"{kusa_type}基因图谱"
        item = await itemDB.getItem(gene_name)
        if not item:
            return {'valid': False, 'message': '草种不存在'}
        
        info = await itemDB.getItemStorageInfo(userId, gene_name)
        if not info:
            return {'valid': False, 'message': '无法种植这种草'}
        
        return {'valid': True}
    
    @staticmethod
    async def _calculate_kusa_num(field, base_kusa: float, soil_capacity_before: Optional[int] = None) -> int:
        """计算生草产量"""
        user = await baseDB.getKusaUser(field.user_id)
        field_amount = await itemDB.getItemAmount(field.user_id, '草地')
        double_magic = await itemDB.getItemAmount(field.user_id, '双生法术卷轴')
        spiritual_sign = await itemDB.getItemAmount(field.user_id, '灵性标记')
        fallow_sign = await itemDB.getItemAmount(field.user_id, '休耕标记')
        fallow_effect = [1, 2, 3][fallow_sign] if 0 < fallow_sign < 3 else 1
        kusa_tech_effect = await FarmService._get_kusa_tech_effect(field.user_id)
        soil_capacity_for_calc = soil_capacity_before if soil_capacity_before is not None else field.soilCapacity
        soil_effect = 1 - 0.1 * (10 - soil_capacity_for_calc) if soil_capacity_for_calc <= 10 else 1
        
        kusa_num = base_kusa
        kusa_num += 0.5 * (2 ** (user.vipLevel - 1)) if user.vipLevel > 0 else 0
        kusa_num *= KUSA_TYPE_EFFECT_MAP.get(field.kusaType, 1)
        kusa_num *= 2 if field.isUsingKela else 1
        kusa_num *= 2 if field.isMirroring else 1
        kusa_num *= 2 if double_magic else 1
        kusa_num *= 2 if spiritual_sign else 1
        kusa_num *= field.biogasEffect
        kusa_num *= field_amount
        kusa_num *= soil_effect
        kusa_num *= kusa_tech_effect
        kusa_num *= fallow_effect
        return math.ceil(kusa_num)
    
    @staticmethod
    async def _calculate_adv_kusa_num(field, soil_capacity_before: Optional[int] = None) -> int:
        """计算草之精华产量"""
        adv_level = await itemDB.getTechLevel(field.user_id, '生草质量')
        soil_capacity_for_calc = soil_capacity_before if soil_capacity_before is not None else field.soilCapacity
        soil_effect = 1 - 0.1 * (10 - soil_capacity_for_calc) if soil_capacity_for_calc <= 10 else 1
        prob = ADV_KUSA_PROBABILITY_DICT[adv_level] * soil_effect
        
        adv_num = 0
        if adv_level >= 3:
            while random.random() < prob:
                adv_num += 1
        else:
            if random.random() < prob:
                adv_num = 1
        
        must_grow = await itemDB.getItemAmount(field.user_id, '生草控制论')
        spiritual_sign = await itemDB.getItemStorageInfo(field.user_id, '灵性标记')
        fallow_sign = await itemDB.getItemAmount(field.user_id, '休耕标记')
        fallow_effect = [1, 2, 3][fallow_sign] if 0 < fallow_sign < 3 else 1
        
        adv_num = 1 if must_grow and adv_num == 0 else adv_num
        adv_num *= ADV_KUSA_TYPE_EFFECT_MAP.get(field.kusaType, 1)
        adv_num *= 2 if spiritual_sign and field.kusaType != '不灵草' else 1
        adv_num *= 2 if field.isMirroring else 1
        adv_num *= fallow_effect
        return math.floor(adv_num)
    
    @staticmethod
    async def _get_kusa_tech_effect(userId: int) -> float:
        """获取生草科技效果"""
        level = await itemDB.getTechLevel(userId, '生草数量')
        return KUSA_TECH_LEVEL_EFFECT_DICT.get(level, 1)
    
    @staticmethod
    async def get_available_kusa_types(userId: int) -> List[Dict[str, Any]]:
        """获取可种植的草类型（别名）"""
        return await FarmService.get_available_types(userId)
    
    @staticmethod
    async def release_spare_capacity(userId: int) -> Dict[str, Any]:
        """释放后备承载力"""
        field = await fieldDB.getKusaField(userId)
        if not field:
            return {'success': False, 'error': 'FIELD_NOT_FOUND'}
        
        spare = await itemDB.getItemAmount(userId, '后备承载力')
        if spare <= 0:
            return {'success': False, 'error': 'NO_SPARE_CAPACITY'}
        
        needed = 25 - field.soilCapacity
        if needed <= 0:
            return {'success': False, 'error': 'ALREADY_FULL'}
        
        release_amount = min(spare, needed)
        await itemDB.changeItemAmount(userId, '后备承载力', -release_amount)
        await fieldDB.kusaSoilRecover(userId, release_amount)
        
        return {
            'success': True,
            'message': f'已释放{release_amount}点后备承载力',
            'released': release_amount,
            'newCapacity': min(field.soilCapacity + release_amount, 25)
        }
    
    @staticmethod
    async def check_overload_magic(userId: int) -> Dict[str, Any]:
        """检查是否有过载魔法"""
        overload_magic = await itemDB.getItemAmount(userId, '奈奈的过载魔法')
        return {'hasOverloadMagic': overload_magic > 0}
