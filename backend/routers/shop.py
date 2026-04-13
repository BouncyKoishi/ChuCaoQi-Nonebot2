"""
商店相关路由
"""

from fastapi import APIRouter, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import ItemService, IndustrialService

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter

router = APIRouter()


@router.get("/items")
async def get_shop(request: Request):
    """获取商店列表"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    items = await ItemService.get_shop_list(userId=userId)
    return {"success": True, "data": items}


@router.post("/buy")
@limiter.limit("60/minute")
async def buy_item(request: Request):
    """购买物品"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    item_name = body.get('itemName')
    amount = body.get('amount', 1)
    
    if item_name == '生草工厂':
        result = await IndustrialService.buy_kusa_factory(userId=userId, increase_amount=amount)
        return result
    
    if item_name == '草精炼厂':
        result = await IndustrialService.buy_adv_factory(userId=userId, increase_amount=amount)
        return result
    
    result = await ItemService.buy_item(userId=userId, item_name=item_name, amount=amount)
    return result


@router.post("/sell")
@limiter.limit("60/minute")
async def sell_item(request: Request):
    """出售物品"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    item_name = body.get('itemName')
    amount = body.get('amount', 1)
    
    result = await ItemService.sell_item(userId=userId, item_name=item_name, amount=amount)
    return result
