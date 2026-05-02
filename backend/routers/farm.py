"""
农田/生草相关路由
"""

from fastapi import APIRouter, Query, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import FarmService
import dbConnection.kusa_item as itemDB
import dbConnection.kusa_field as fieldDB

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from websocket_manager import manager
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter
from common import ENV

ENV_PROD = ENV == 'prod'

router = APIRouter()


@router.get("/")
async def get_farm_status(request: Request):
    """获取百草园状态"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await FarmService.get_status(userId=userId)
    if 'error' in result:
        return {"success": False, "error": result['error']}
    return {"success": True, "data": result}


@router.post("/plant")
@limiter.limit("60/minute")
async def plant_kusa(request: Request):
    """开始生草"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    kusa_type = body.get('kusaType')
    overload = body.get('overload', False)
    
    spiritual_machine = await itemDB.getItemStorageInfo(userId, '灵性自动分配装置')
    auto_assigned = False
    if spiritual_machine and spiritual_machine.allowUse:
        spiritual_sign = await itemDB.getItemAmount(userId, '灵性标记')
        if not spiritual_sign:
            kusa_type = '不灵草'
            auto_assigned = True
    
    result = await FarmService.start_planting(userId=userId, kusa_type=kusa_type, overload=overload)
    
    if result.get("success") and auto_assigned:
        result['data']['autoAssigned'] = True
    
    if result.get("success"):
        status = await FarmService.get_status(userId=userId)
        await manager.send_personal_message({
            "type": "farm_status_update",
            "data": status
        }, str(userId))
    
    return result


@router.post("/harvest")
@limiter.limit("60/minute")
async def harvest_kusa(request: Request):
    """除草"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await FarmService.harvest(userId=userId)
    
    if result.get("success"):
        status = await FarmService.get_status(userId=userId)
        await manager.send_personal_message({
            "type": "farm_status_update",
            "data": status
        }, str(userId))
    
    return result


@router.get("/history")
async def get_farm_history(request: Request):
    """获取生草历史"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}

    history = await FarmService.get_history(userId=userId, limit=20)
    # 转换格式以兼容前端
    return {"success": True, "data": [
        {
            'timestamp': h.get('timestamp'),
            'kusaType': h.get('kusaType'),
            'kusaResult': h.get('kusaResult'),
            'advKusaResult': h.get('advKusaResult')
        }
        for h in history
    ]}


@router.get("/available-kusa-types")
async def get_available_kusa_types(request: Request):
    """获取可种植的草类型"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await FarmService.get_available_kusa_types(userId=userId)
    return {"success": True, "data": result}


@router.post("/test-recover-capacity")
@limiter.limit("30/minute")
async def test_recover_capacity(request: Request):
    """测试接口：直接恢复承载力到满值（仅开发环境可用）"""
    if ENV_PROD:
        return {"success": False, "error": "此接口在生产环境不可用"}
    
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    try:
        await fieldDB.kusaSoilRecover(userId=userId, recoveryAmount=25)
        return {"success": True, "message": "承载力已强制恢复到25", "newCapacity": 25}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/release-spare-capacity")
@limiter.limit("30/minute")
async def release_spare_capacity(request: Request):
    """释放后备承载力"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await FarmService.release_spare_capacity(userId=userId)
    if 'success' in result:
        if result['success']:
            return {"success": True, "data": result}
        else:
            return result
    return {"success": False, "error": "未知错误"}


@router.get("/overload-magic")
async def check_overload_magic(request: Request):
    """检查是否有过载魔法"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    result = await FarmService.check_overload_magic(userId=userId)
    return {"success": True, "data": result}
