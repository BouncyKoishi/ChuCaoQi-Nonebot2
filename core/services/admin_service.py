"""
管理服务模块

提供超级管理员后台管理功能（用户管理、称号管理、自定义排行榜等）
供 Web 后端路由直接调用，复用现有 core.db 层和 core.services 层。
"""

import sys
import os
from typing import Dict, Any, List, Optional


import core.db.kusa_system as baseDB
import core.db.kusa_item as itemDB
import core.db.user as user_db
import core.db.chat as chatDB
from core.db.models import UnifiedUser, KusaBase, KusaItemList, KusaItemStorage
from tortoise.expressions import Q
from core.services import WarehouseService
from core.services import StatisticService
from core.services import identity_service

# ===== 用户管理 =====

async def get_user_list(
    page: int = 1,
    page_size: int = 20,
    search_id: Optional[str] = None,
    search_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    分页查询用户列表，联表查询 UnifiedUser + KusaBase

    Returns: {list, total, page, pageSize}
    """
    query = UnifiedUser.all()

    if search_id:
        # 同时匹配 id 和 realQQ
        query = query.filter(
            Q(id__icontains=search_id) | Q(realQQ__icontains=search_id)
        )

    if search_name:
        # 昵称在 KusaBase 表，需要先查出匹配的 userIds
        matching_kusa = await KusaBase.filter(name__icontains=search_name).values('user_id')
        matching_ids = [k['user_id'] for k in matching_kusa]
        if matching_ids:
            query = query.filter(id__in=matching_ids)
        else:
            # 无匹配，直接返回空
            return {'list': [], 'total': 0, 'page': page, 'pageSize': page_size}

    total = await query.count()
    users = await query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量查 KusaBase
    user_ids = [u.id for u in users]
    kusa_users = await KusaBase.filter(user_id__in=user_ids).all()
    kusa_map = {ku.user_id: ku for ku in kusa_users}

    result = []
    for u in users:
        ku = kusa_map.get(u.id)
        result.append({
            'id': u.id,
            'qq': u.realQQ,
            'name': ku.name if ku else None,
            'title': ku.title if ku else None,
            'vipLevel': ku.vipLevel if ku else 0,
            'kusa': ku.kusa if ku else 0,
            'advKusa': ku.advKusa if ku else 0,
        })

    return {'list': result, 'total': total, 'page': page, 'pageSize': page_size}


async def give_title(userId: int, title_name: str) -> Dict[str, Any]:
    """授予用户称号（从 kusa_statistics.py GIVE_TITLE 迁移）"""
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {'success': False, 'error': '用户不存在'}

    item = await itemDB.getItem(title_name)
    if not item or item.type != '称号':
        return {'success': False, 'error': '该称号不存在'}

    # 检查是否已有该称号，避免重复授予导致数量叠加
    existing = await itemDB.getItemAmount(userId, title_name)
    if existing > 0:
        return {'success': True, 'message': f'用户{userId}已拥有称号{title_name}', 'alreadyOwned': True}

    await itemDB.changeItemAmount(userId, title_name, 1)
    return {'success': True, 'message': f'成功赠送用户{userId}称号{title_name}'}


async def set_donation(userId: int, amount: float, source: str = 'qq') -> Dict[str, Any]:
    """设置用户捐赠金额（从 kusa_statistics.py SET_DONATION 迁移）

    自动称号规则：仅在跨阈值时发放
    - 投喂者：累计≥20元
    - 猫粮供应商：累计≥200元
    """
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {'success': False, 'error': '用户不存在'}

    # 投喂前累计总额
    old_total = await baseDB.getDonateAmount(userId)

    await baseDB.setDonateRecord(userId, float(amount), source)

    new_total = await baseDB.getDonateAmount(userId)
    auto_titles = []

    # 投喂者：跨20元阈值时发放
    if old_total < 20 <= new_total:
        have = await itemDB.getItemAmount(userId, "投喂者")
        if not have:
            granted = await itemDB.changeItemAmount(userId, "投喂者", 1)
            if granted:
                auto_titles.append("投喂者")

    # 猫粮供应商：跨200元阈值时发放
    if old_total < 200 <= new_total:
        have = await itemDB.getItemAmount(userId, "猫粮供应商")
        if not have:
            granted = await itemDB.changeItemAmount(userId, "猫粮供应商", 1)
            if granted:
                auto_titles.append("猫粮供应商")

    return {
        'success': True,
        'message': f'已设置用户{userId}捐赠金额{amount}元（来源: {source}）',
        'totalDonate': new_total,
        'autoTitles': auto_titles
    }


async def get_donation_records(userId: int) -> Dict[str, Any]:
    """获取用户捐赠记录列表"""
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {'success': False, 'error': '用户不存在'}

    records = await baseDB.getDonateRecords(userId)
    total = await baseDB.getDonateAmount(userId)

    record_list = []
    for r in records:
        record_list.append({
            'id': r.id,
            'amount': r.amount,
            'donateDate': r.donateDate,
            'source': r.source
        })

    return {
        'success': True,
        'total': total,
        'records': record_list
    }


async def delete_donation_record(record_id: int) -> Dict[str, Any]:
    """删除单条捐赠记录

    自动称号回收规则（与发放逻辑对称，仅在跨阈值下降时回收）：
    - 投喂者：累计从≥20降到<20时回收
    - 猫粮供应商：累计从≥200降到<200时回收
    回收时若用户当前正在使用该称号，则清空当前称号。
    """
    from core.db.models import DonateRecord
    record = await DonateRecord.filter(id=record_id).first()
    if not record:
        return {'success': False, 'error': '记录不存在'}

    userId = record.user_id
    old_total = await baseDB.getDonateAmount(userId)
    await record.delete()
    new_total = await baseDB.getDonateAmount(userId)

    revoked_titles = []

    async def _revoke_title(title_name: str):
        """回收指定称号：删除持有记录，若正在使用则清空当前称号"""
        have = await itemDB.getItemAmount(userId, title_name)
        if have <= 0:
            return
        await itemDB.changeItemAmount(userId, title_name, -have)
        user = await baseDB.getKusaUser(userId)
        if user and user.title == title_name:
            user.title = None
            await user.save()
        revoked_titles.append(title_name)

    # 投喂者：从≥20降到<20时回收
    if old_total >= 20 > new_total:
        await _revoke_title("投喂者")

    # 猫粮供应商：从≥200降到<200时回收
    if old_total >= 200 > new_total:
        await _revoke_title("猫粮供应商")

    return {
        'success': True,
        'message': '记录已删除',
        'totalDonate': new_total,
        'revokedTitles': revoked_titles
    }


async def get_user_titles(userId: int) -> Dict[str, Any]:
    """获取用户拥有的所有称号及当前使用的称号"""
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {'success': False, 'error': '用户不存在'}

    title_items = await itemDB.getItemsByType("称号")
    owned_titles = []
    for item in title_items:
        amount = await itemDB.getItemAmount(userId, item.name)
        if amount > 0:
            owned_titles.append({
                'name': item.name,
                'detail': item.detail,
                'amount': amount,
                'inUse': user.title == item.name
            })

    return {
        'success': True,
        'currentTitle': user.title,
        'titles': owned_titles
    }


async def get_title_owners(title_name: str) -> Dict[str, Any]:
    """获取指定称号的所有拥有者（用户列表格式）"""
    item = await itemDB.getItem(title_name)
    if not item:
        return {'success': False, 'error': '称号不存在'}

    storages = await itemDB.getStoragesOrderByAmountDesc(title_name)

    owners = []
    for s in storages:
        if s.amount <= 0:
            continue
        ku = await baseDB.getKusaUser(s.user_id)
        uu = await user_db.getUnifiedUser(s.user_id)
        owners.append({
            'id': s.user_id,
            'qq': uu.realQQ if uu else None,
            'name': ku.name if ku else None,
            'title': ku.title if ku else None,
            'vipLevel': ku.vipLevel if ku else 0,
            'kusa': ku.kusa if ku else 0,
            'advKusa': ku.advKusa if ku else 0,
        })

    return {'success': True, 'owners': owners}


async def get_chat_permission(userId: int) -> Dict[str, Any]:
    """查看用户 chat 权限"""
    chat_user = await chatDB.getChatUser(userId)
    if not chat_user:
        return {
            'success': True,
            'data': {
                'activated': False,
                'allowPrivate': False,
                'allowRole': False,
                'allowAdvancedModel': False,
                'chosenModel': None,
                'tokenUse': 0,
                'todayTokenUse': 0,
                'dailyTokenLimit': 10000,
            }
        }

    return {
        'success': True,
        'data': {
            'activated': True,
            'allowPrivate': chat_user.allowPrivate,
            'allowRole': chat_user.allowRole,
            'allowAdvancedModel': chat_user.allowAdvancedModel,
            'chosenModel': chat_user.chosenModel,
            'tokenUse': chat_user.tokenUse,
            'todayTokenUse': chat_user.todayTokenUse,
            'dailyTokenLimit': chat_user.dailyTokenLimit,
        }
    }


async def update_chat_permission(
    userId: int,
    allow_private: bool = False,
    allow_role: bool = False,
    allow_advanced_model: bool = False,
    daily_limit_mode: str = 'default'
) -> Dict[str, Any]:
    """
    设置用户 chat 权限

    daily_limit_mode: 'default'(1万) | 'high'(100万) | 'unlimited'(-1)
    """
    # 转换为 updateChatUser 的 mode 字符串
    mode = ''
    if allow_private:
        mode += 'p'
    if allow_role:
        mode += 'r'
    if allow_advanced_model:
        mode += 'm'
    if daily_limit_mode == 'unlimited':
        mode += 'u'
    elif daily_limit_mode == 'high':
        mode += 'v'

    await chatDB.updateChatUser(userId, mode)
    return {'success': True, 'message': f'已更新用户{userId}的chat权限'}


async def generate_web_token_for_user(userId: int) -> Dict[str, Any]:
    """为用户生成 webToken（复用 identity_service）"""
    unified_user = await user_db.getUnifiedUser(userId)
    if not unified_user:
        return {'success': False, 'error': '用户不存在'}

    token = await identity_service.generate_web_token(unified_user)
    return {'success': True, 'token': token}


async def get_user_friend_code(userId: int) -> Dict[str, Any]:
    """生成用户的好友码（确定性计算，跨进程一致）"""
    unified_user = await user_db.getUnifiedUser(userId)
    if not unified_user:
        return {'success': False, 'error': '用户不存在'}
    if not unified_user.realQQ:
        return {'success': False, 'error': '用户未绑定QQ号'}

    code = identity_service.generate_friend_code(unified_user.realQQ)
    return {'success': True, 'code': code, 'qq': unified_user.realQQ}


async def get_account_marks(userId: int) -> Dict[str, Any]:
    """获取用户帐号标记（小号关联 + 机械臂标记）"""
    unified_user = await user_db.getUnifiedUser(userId)
    if not unified_user:
        return {'success': False, 'error': '用户不存在'}

    related_user = None
    if unified_user.relatedUserId:
        related_uu = await user_db.getUnifiedUser(unified_user.relatedUserId)
        if related_uu:
            related_ku = await baseDB.getKusaUser(unified_user.relatedUserId)
            related_user = {
                'userId': related_uu.id,
                'qq': related_uu.realQQ,
                'name': related_ku.name if related_ku else None
            }

    return {
        'success': True,
        'relatedUserId': unified_user.relatedUserId,
        'relatedUser': related_user,
        'isRobot': unified_user.isRobot
    }


async def update_account_marks(userId: int, related_user_id: Optional[int], is_robot: bool) -> Dict[str, Any]:
    """设置用户帐号标记

    校验：
    - relatedUserId 不能等于自身（防自关联）
    - relatedUserId 指向的用户必须存在
    - 防循环关联：目标用户的 relatedUserId 不能等于当前 userId
    """
    unified_user = await user_db.getUnifiedUser(userId)
    if not unified_user:
        return {'success': False, 'error': '用户不存在'}

    # 处理小号关联
    if related_user_id is not None:
        if related_user_id == userId:
            return {'success': False, 'error': '不能关联到自身'}
        target_user = await user_db.getUnifiedUser(related_user_id)
        if not target_user:
            return {'success': False, 'error': '关联的目标用户不存在'}
        # 防循环：目标用户不能已关联到当前用户
        if target_user.relatedUserId == userId:
            return {'success': False, 'error': '不能形成循环关联'}
        unified_user.relatedUserId = related_user_id
    else:
        unified_user.relatedUserId = None

    unified_user.isRobot = is_robot
    await unified_user.save()

    return {
        'success': True,
        'message': f'已更新用户{userId}的帐号标记',
        'relatedUserId': unified_user.relatedUserId,
        'isRobot': unified_user.isRobot
    }


# ===== 称号管理 =====

async def get_title_list_with_owners() -> List[Dict[str, Any]]:
    """获取称号列表及拥有者信息"""
    titles = await itemDB.getItemsByType("称号")
    result = []

    for title in titles:
        # 查询拥有该称号的用户
        storages = await KusaItemStorage.filter(item=title, amount__gt=0).all()
        owner_ids = [s.user_id for s in storages]

        owners = []
        if owner_ids:
            kusa_users = await KusaBase.filter(user_id__in=owner_ids).all()
            kusa_map = {ku.user_id: ku for ku in kusa_users}
            for uid in owner_ids:
                ku = kusa_map.get(uid)
                owners.append({
                    'userId': uid,
                    'name': ku.name if ku else str(uid)
                })

        result.append({
            'name': title.name,
            'detail': title.detail,
            'ownerCount': len(owner_ids),
            'owners': owners
        })

    return result


async def create_title(name: str, detail: str = None) -> Dict[str, Any]:
    """添加新称号"""
    existing = await itemDB.getItem(name)
    if existing:
        return {'success': False, 'error': '该名称的物品已存在'}

    await KusaItemList.create(name=name, type='称号', detail=detail)
    return {'success': True, 'message': f'称号"{name}"已创建'}


async def delete_title(name: str) -> Dict[str, Any]:
    """删除称号及其所有持有记录"""
    item = await itemDB.getItem(name)
    if not item:
        return {'success': False, 'error': '称号不存在'}

    if item.type != '称号':
        return {'success': False, 'error': '该物品不是称号'}

    # 查询持有者数量
    storages = await KusaItemStorage.filter(item=item, amount__gt=0).all()
    owner_count = len(storages)

    # 删除所有持有记录
    await KusaItemStorage.filter(item=item).delete()
    # 删除称号定义
    await item.delete()

    return {
        'success': True,
        'message': f'称号"{name}"已删除（原持有者{owner_count}人）',
        'ownerCount': owner_count
    }


# ===== 自定义排行榜 =====

async def generate_custom_rank(
    dimension: str,
    limit: int = 25,
    level_max: int = 10,
    show_inactive: bool = False,
    show_subaccount: bool = True,
    item_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成自定义排行榜

    dimension: 'kusa' | 'advKusa' | 'totalAdvKusa' | 'kusaOnce' | 'advKusaOnce' | 'item'
    """
    if dimension == 'kusa':
        data = await StatisticService.get_kusa_rank(
            limit=limit, level_max=level_max,
            show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'kusa', 'vipLevel']}

    elif dimension == 'advKusa':
        data = await StatisticService.get_kusa_rank_with_adv(
            limit=limit, sort_by='advKusa',
            level_max=level_max, show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'advKusa', 'vipLevel']}

    elif dimension == 'totalAdvKusa':
        data = await StatisticService.get_total_adv_kusa_rank(
            limit=limit, level_max=level_max,
            show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'totalAdvKusa', 'nowAdvKusa', 'titleAdvKusa', 'itemAdvKusa', 'vipLevel']}

    elif dimension == 'kusaOnce':
        data = await StatisticService.get_kusa_once_ranking(
            limit=limit, level_max=level_max,
            show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'kusaResult', 'createTimeTs', 'vipLevel']}

    elif dimension == 'advKusaOnce':
        data = await StatisticService.get_adv_kusa_once_ranking(
            limit=limit, level_max=level_max,
            show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'advKusaResult', 'createTimeTs', 'vipLevel']}

    elif dimension == 'item':
        if not item_name:
            return {'success': False, 'error': '物品排行需要指定物品名称'}
        data = await StatisticService.get_item_rank(
            item_name, limit,
            level_max=level_max, show_inactive=show_inactive, show_subaccount=show_subaccount
        )
        return {'success': True, 'data': data, 'columns': ['rank', 'name', 'amount', 'vipLevel']}

    return {'success': False, 'error': f'未知的排序维度: {dimension}'}


async def get_all_item_names() -> List[Dict[str, str]]:
    """获取所有物品名称列表（用于物品排行选择，排除称号）"""
    items = await KusaItemList.exclude(type='称号').values('name', 'type')
    return [{'name': item['name'], 'type': item['type']} for item in items]
