"""
仓库/用户/VIP 相关路由

合并了原 warehouse 和 vip 模块
"""

from fastapi import APIRouter, Query, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import WarehouseService
from services import IndustrialService
from services import GMarketService

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter

router = APIRouter()


# ==================== 仓库基础接口 ====================

@router.get("/")
async def get_warehouse(request: Request):
    """获取仓库信息"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await WarehouseService.get_warehouse_info(userId=userId)
    return {"success": True, "data": result}


@router.get("/items/{item_type}")
async def get_items_by_type(item_type: str, request: Request):
    """获取指定类型物品列表"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    items = await WarehouseService.get_items_by_type(item_type, userId=userId)
    return {"success": True, "data": items}


@router.post("/title")
async def update_title(request: Request):
    """切换称号"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    title = body.get('title')
    if not title:
        return {"success": False, "error": "称号不能为空"}
    
    result = await WarehouseService.change_title(userId=userId, title=title)
    return result


@router.post("/name")
async def update_name(request: Request):
    """修改名字"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    name = body.get('name')
    if not name:
        return {"success": False, "error": "名字不能为空"}
    
    result = await WarehouseService.change_name(userId=userId, name=name)
    return result


# ==================== VIP 接口 (原 vip 模块合并至此) ====================

@router.post("/vip/upgrade")
@limiter.limit("30/minute")
async def upgrade_vip(request: Request):
    """VIP升级"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await WarehouseService.upgrade_vip(userId=userId)
    return result


@router.post("/vip/advanced-upgrade")
@limiter.limit("30/minute")
async def advanced_upgrade_vip(request: Request):
    """VIP进阶升级"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await WarehouseService.advanced_upgrade_vip(userId=userId)
    return result


# ==================== 每日产量接口 ====================

@router.get("/daily-production")
async def get_daily_production(request: Request):
    """获取每日产量信息"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await IndustrialService.calculate_daily_production(userId=userId)
    return {"success": True, "data": result}


# ==================== 统计接口 ====================

@router.get("/stats/user")
async def get_user_stats(request: Request):
    """获取用户草精统计"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await WarehouseService.get_user_stats(userId=userId)
    if 'error' in result:
        return {"success": False, "error": result['error']}
    return {"success": True, "data": result}


@router.get("/stats/grass/personal")
async def get_grass_stats_personal(
    request: Request,
    period: str = Query("24小时", description="统计周期: 24小时, 昨日, 上周")
):
    """获取个人生草统计"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}

    try:
        from services import FarmService
        stats = await FarmService.get_grass_stats(userId=userId, period=period)
        return {"success": True, "data": stats['personal']}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": True, "data": {"count": 0, "sumKusa": 0, "sumAdvKusa": 0, "avgKusa": 0, "avgAdvKusa": 0}}


@router.get("/stats/grass/total")
async def get_grass_stats_total(
    period: str = Query("24小时", description="统计周期: 24小时, 昨日, 上周")
):
    """获取全服生草统计"""
    try:
        from services import FarmService
        stats = await FarmService.get_grass_stats(period=period)
        return {"success": True, "data": stats['total']}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": True, "data": {"count": 0, "sumKusa": 0, "sumAdvKusa": 0, "avgKusa": 0, "avgAdvKusa": 0}}


@router.get("/stats/gmarket")
async def get_gmarket_stats(request: Request):
    """获取G市统计"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    try:
        # 获取本周期和上周期交易总结
        current_summary = await GMarketService.get_trade_summary(userId)
        last_summary = await GMarketService.get_last_cycle_summary(userId)

        if not current_summary.get('success'):
            return {
                "success": True,
                "data": {
                    "currentProfit": 0, "lastProfit": 0, "currentHoldingsValue": 0,
                    "currentBuyTotal": 0, "currentSellTotal": 0, "lastBuyTotal": 0, "lastSellTotal": 0
                }
            }

        return {
            "success": True,
            "data": {
                "currentProfit": current_summary.get('profit', 0),
                "lastProfit": last_summary.get('profit', 0),
                "currentHoldingsValue": current_summary.get('now_kusa_in_g', 0),
                "currentBuyTotal": current_summary.get('all_cost_kusa', 0),
                "currentSellTotal": current_summary.get('all_gain_kusa', 0),
                "lastBuyTotal": last_summary.get('all_cost_kusa', 0),
                "lastSellTotal": last_summary.get('all_gain_kusa', 0)
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "currentProfit": 0, "lastProfit": 0, "currentHoldingsValue": 0,
                "currentBuyTotal": 0, "currentSellTotal": 0, "lastBuyTotal": 0, "lastSellTotal": 0
            }
        }


@router.get("/stats/gmarket/records")
async def get_gmarket_records(request: Request, page: int = Query(1, description="页码"), pageSize: int = Query(10, description="每页条数")):
    """获取G市操作记录"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    try:
        result = await GMarketService.get_trade_records(userId=userId, page=page, page_size=pageSize)

        # 转换记录格式以兼容前端
        formatted_records = []
        for record in result.get('records', []):
            formatted_records.append({
                "timestamp": record.get('timestamp'),
                "type": record.get('type'),
                "gType": record.get('g_name'),
                "amount": record.get('g_amount'),
                "unitPrice": record.get('unit_price'),
                "totalPrice": record.get('kusa_amount')
            })

        return {"success": True, "data": {"records": formatted_records, "total": result.get('total', 0)}}
    except Exception as e:
        return {"success": True, "data": {"records": [], "total": 0}}


# ==================== 仓库操作接口 ====================

@router.post("/compress-kusa")
@limiter.limit("30/minute")
async def compress_kusa(request: Request):
    """草压缩：将普通草压缩成草之精华"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    amount = body.get('amount', 1)
    
    result = await WarehouseService.compress_kusa(userId=userId, adv_amount=int(amount))
    return result



