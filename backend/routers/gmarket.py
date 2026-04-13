"""
G市相关路由
"""

from fastapi import APIRouter, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import GMarketService

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter

router = APIRouter()


@router.get("/")
async def get_g_status(request: Request):
    """获取G市状态"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    result = await GMarketService.get_status(userId=userId)
    return {"success": True, "data": result}


@router.get("/history")
async def get_g_history(request: Request):
    """获取本周期G值历史"""
    result = await GMarketService.get_cycle_history()
    return {"success": True, "data": result}


@router.post("/buy")
@limiter.limit("60/minute")
async def buy_g(request: Request):
    """买入G"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    amount = body.get('amount')
    g_type = body.get('gType')
    
    type_map = {
        'east': '东',
        'south': '南',
        'north': '北',
        'zhuhai': '珠',
        'shenzhen': '深'
    }
    school = type_map.get(g_type)
    if not school:
        return {"success": False, "error": "无效的G类型"}
    
    result = await GMarketService.buy_g_single(userId=userId, amount=amount, school=school)
    return result


@router.post("/sell")
@limiter.limit("60/minute")
async def sell_g(request: Request):
    """卖出G"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    amount = body.get('amount')
    g_type = body.get('gType')
    
    type_map = {
        'east': '东',
        'south': '南',
        'north': '北',
        'zhuhai': '珠',
        'shenzhen': '深'
    }
    school = type_map.get(g_type)
    if not school:
        return {"success": False, "error": "无效的G类型"}
    
    result = await GMarketService.sell_g_single(userId=userId, amount=amount, school=school)
    return result
