"""
Session验证中间件
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timezone
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

from dbConnection.models import UnifiedUser


def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_token = request.headers.get('X-Session-Token')
        
        request.state.userId = None
        request.state.unifiedUser = None
        
        if session_token:
            unified_user = await UnifiedUser.filter(sessionToken=session_token).first()
            
            if unified_user:
                expires_at = unified_user.sessionTokenExpiresAt
                if expires_at:
                    if expires_at.tzinfo is not None:
                        expires_at = expires_at.replace(tzinfo=None)
                    if expires_at > get_utc_now():
                        request.state.userId = unified_user.id
                        request.state.unifiedUser = unified_user
                    else:
                        unified_user.sessionToken = None
                        unified_user.sessionTokenExpiresAt = None
                        await unified_user.save()
        
        response = await call_next(request)
        return response


def get_user_id(request: Request) -> Optional[int]:
    """从请求状态获取用户ID"""
    return getattr(request.state, 'userId', None)


def get_unified_user(request: Request) -> Optional[UnifiedUser]:
    """从请求状态获取统一用户对象"""
    return getattr(request.state, 'unifiedUser', None)
