"""
用户信息相关路由
"""

from fastapi import APIRouter, Request
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

import dbConnection.kusa_system as baseDB
from dbConnection.models import UnifiedUser
from middleware.session_auth import get_user_id, get_unified_user

router = APIRouter()


@router.get("/info")
async def get_user_info(request: Request):
    """获取当前用户信息"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {"success": False, "error": "用户不存在"}

    unified_user = get_unified_user(request)
    
    return {
        "success": True,
        "data": {
            "userId": userId,
            "qq": str(unified_user.realQQ) if unified_user else None,
            "name": str(user.name) if user.name else None,
            "title": str(user.title) if user.title else None,
            "vipLevel": int(user.vipLevel),
            "kusa": float(user.kusa),
            "advKusa": float(user.advKusa)
        }
    }


@router.post("/name")
async def update_user_name(request: Request):
    """更新用户名字"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    name = body.get('name')
    
    if not name:
        return {"success": False, "error": "名字不能为空"}
    
    user = await baseDB.getKusaUser(userId)
    if not user:
        return {"success": False, "error": "用户不存在"}

    user.name = name
    await user.save()
    
    return {"success": True, "message": "名字更新成功", "name": name}
