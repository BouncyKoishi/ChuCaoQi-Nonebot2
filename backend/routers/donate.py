"""
捐赠记录相关路由
"""

from fastapi import APIRouter, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from dbConnection.kusa_system import getDonateRecords, getDonateAmount

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.session_auth import get_user_id

router = APIRouter()


@router.get("/records")
async def get_donate_records(request: Request):
    """获取当前用户的捐赠记录"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    records = await getDonateRecords(userId=userId)
    
    result = []
    for record in records:
        result.append({
            "amount": record.amount,
            "date": record.donateDate,
            "source": record.source,
            "remark": record.remark
        })
    
    return {"success": True, "data": result}


@router.get("/total")
async def get_donate_total(request: Request):
    """获取当前用户的捐赠总额"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    total = await getDonateAmount(userId=userId)
    return {"success": True, "data": {"total": total}}
