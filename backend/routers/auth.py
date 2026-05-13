"""
认证相关路由
"""

from fastapi import APIRouter, Request
import sys
import os
import secrets
import string
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.rate_limiter import limiter


def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

import dbConnection.kusa_system as baseDB
from dbConnection.models import UnifiedUser
from common import ALLOW_LEGACY_LOGIN

router = APIRouter()

SESSION_TOKEN_EXPIRE_DAYS = 7


def generate_session_token() -> str:
    alphabet = string.ascii_letters + string.digits
    return 'sess_' + ''.join(secrets.choice(alphabet) for _ in range(32))


async def create_session_token(unified_user: UnifiedUser) -> str:
    token = generate_session_token()
    expires_at = get_utc_now() + timedelta(days=SESSION_TOKEN_EXPIRE_DAYS)
    unified_user.sessionToken = token
    unified_user.sessionTokenExpiresAt = expires_at
    await unified_user.save()
    return token


async def verify_session_token(token: str):
    if not token:
        return None
    unified_user = await UnifiedUser.filter(sessionToken=token).first()
    if not unified_user:
        return None
    expires_at = unified_user.sessionTokenExpiresAt
    if expires_at:
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        if expires_at < get_utc_now():
            unified_user.sessionToken = None
            unified_user.sessionTokenExpiresAt = None
            await unified_user.save()
            return None
    return unified_user


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request):
    """用户登录 - 使用QQ号和Token登录，返回sessionToken"""
    body = await request.json()
    qq = body.get('qq')
    token = body.get('token')
    
    if not qq:
        return {"success": False, "error": "QQ号不能为空"}
    
    qq_int = int(qq)
    
    unified_user = await UnifiedUser.filter(realQQ=qq_int).first()
    
    if not unified_user:
        return {"success": False, "error": "用户不存在，请先在Bot中使用过"}
    
    # Token验证逻辑
    if token:
        # 有token，验证token
        if unified_user.webToken != token:
            return {"success": False, "error": "Token错误，请检查输入是否正确"}
    else:
        # 无token的情况
        if unified_user.webToken:
            # 用户已设置TOKEN，必须验证
            return {"success": False, "error": "该账号已设置Token，请输入Token登录。Token可在Bot中通过 !查看token 获取"}
        elif not ALLOW_LEGACY_LOGIN:
            # 用户未设置TOKEN，但兼容模式关闭
            return {"success": False, "error": "请使用Token登录，Token可在Bot中通过 !生成token 获取"}
        # 用户未设置TOKEN且兼容模式开启，允许登录
    
    # 生成 sessionToken
    session_token = await create_session_token(unified_user)
    
    userId = unified_user.id
    user = await baseDB.getKusaUser(userId)
    
    return {
        "success": True,
        "data": {
            "sessionToken": session_token,
            "userId": userId,
            "qq": str(unified_user.realQQ),
            "name": str(user.name) if user and user.name else None,
            "title": str(user.title) if user and user.title else None,
            "vipLevel": int(user.vipLevel) if user else 0,
            "kusa": float(user.kusa) if user else 0,
            "advKusa": float(user.advKusa) if user else 0,
            "isSuperAdmin": bool(unified_user.isSuperAdmin),
            "isRobot": bool(unified_user.isRobot)
        }
    }


@router.post("/verify-session")
@limiter.limit("30/minute")
async def verify_session(request: Request):
    """验证sessionToken有效性"""
    body = await request.json()
    session_token = body.get('sessionToken')
    
    if not session_token:
        return {"success": False, "error": "sessionToken不能为空"}
    
    unified_user = await verify_session_token(session_token)
    if not unified_user:
        return {"success": False, "error": "Session无效或已过期"}
    
    user = await baseDB.getKusaUser(unified_user.id)
    
    return {
        "success": True,
        "data": {
            "userId": unified_user.id,
            "qq": str(unified_user.realQQ),
            "name": str(user.name) if user and user.name else None,
            "title": str(user.title) if user and user.title else None,
            "vipLevel": int(user.vipLevel) if user else 0,
            "kusa": float(user.kusa) if user else 0,
            "advKusa": float(user.advKusa) if user else 0,
            "isSuperAdmin": bool(unified_user.isSuperAdmin),
            "isRobot": bool(unified_user.isRobot)
        }
    }


@router.post("/logout")
async def logout(request: Request):
    """用户登出 - 清除sessionToken"""
    body = await request.json()
    session_token = body.get('sessionToken')
    
    if session_token:
        unified_user = await UnifiedUser.filter(sessionToken=session_token).first()
        if unified_user:
            unified_user.sessionToken = None
            unified_user.sessionTokenExpiresAt = None
            await unified_user.save()
    
    return {"success": True}
