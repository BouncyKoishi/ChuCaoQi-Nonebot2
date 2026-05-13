"""
道具/商店相关路由

合并了原 item 和 shop 模块
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import ItemService
import dbConnection.kusa_item as itemDB
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
