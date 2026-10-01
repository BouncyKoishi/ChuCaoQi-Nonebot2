"""
道具/商店相关路由

合并了原 item 和 shop 模块
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
import sys
import os

from core.services import ItemService
import core.db.kusa_item as itemDB
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter

router = APIRouter()


# ==================== 道具操作接口 ====================

@router.post("/toggle")
async def toggle_item(request: Request):
    """启用/禁用道具"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    item_name = body.get('itemName')
    allow_use = body.get('allowUse', False)
    
    if not item_name:
        return {"success": False, "error": "道具名不能为空"}
    
    try:
        await itemDB.changeItemAllowUse(userId=userId, itemName=item_name, allowUse=allow_use)
        return {"success": True, "message": f"{item_name}已{allow_use and '启用' or '禁用'}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/amount")
async def get_item_amount(request: Request, item_name: str = Query(..., description="物品名")):
    """获取物品持有数量"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    try:
        amount = await itemDB.getItemAmount(userId, item_name)
        return {"success": True, "data": {"amount": amount}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 奖券合成接口 ====================

@router.post("/compose-ticket")
@limiter.limit("60/minute")
async def compose_ticket(request: Request):
    """奖券合成：将低级奖券合成为高级奖券"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    target = body.get('target')
    amount = body.get('amount', 1)
    
    if not target:
        return {"success": False, "error": "合成目标不能为空"}
    
    result = await ItemService.compose_ticket(userId=userId, target=target, amount=int(amount))
    return result


# ==================== 物品转让接口 ====================

async def _resolve_transfer_target(target_user_id, target_qq):
    """按用户ID或QQ号解析接收方，返回 (user, error)"""
    if target_user_id:
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError):
            return None, '用户ID格式不正确'
        return await ItemService.get_transfer_target_by_id(target_user_id), None
    if target_qq:
        return await ItemService.get_transfer_target_by_qq(str(target_qq).strip()), None
    return None, '请输入接收方的QQ号或用户ID'


@router.post("/transfer")
@limiter.limit("30/minute")
async def transfer_item(request: Request):
    """物品转让：将自己的物品转让给指定用户"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}

    body = await request.json()
    item_name = body.get('itemName')
    if not item_name:
        return {"success": False, "error": "物品名不能为空"}

    try:
        amount = int(body.get('amount'))
    except (TypeError, ValueError):
        return {"success": False, "error": "转让数量不合法"}
    if amount <= 0:
        return {"success": False, "error": "转让数量不合法"}

    target, error = await _resolve_transfer_target(body.get('targetUserId'), body.get('targetQq'))
    if error:
        return {"success": False, "error": error}
    if not target:
        return {"success": False, "error": "对方没有生草账户"}

    result = await ItemService.transfer_item(
        from_user_id=userId,
        to_user_id=target.id,
        item_name=item_name,
        amount=amount
    )
    return result
