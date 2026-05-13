"""
API 限流中间件

使用 slowapi 实现多层级限流：
- L1: IP 地址全局限流 (1000次/分钟)
- L2: sessionToken 用户限流 (300次/分钟)
- L3: 接口级限流 (各接口单独配置)
"""

from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


def get_identifier(request: Request) -> str:
    """
    获取限流标识符
    优先使用 sessionToken，其次使用 IP 地址
    """
    session_token = request.headers.get('X-Session-Token')
    if session_token:
        return f"session:{session_token}"
    
    ip = get_remote_address(request)
    return f"ip:{ip}"


def get_ip_identifier(request: Request) -> str:
    """获取 IP 地址标识符"""
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_identifier,
    default_limits=["300/minute"],
    storage_uri="memory://",
    enabled=True
)

ip_limiter = Limiter(
    key_func=get_ip_identifier,
    default_limits=["1000/minute"],
    storage_uri="memory://",
    enabled=True
)


def rate_limit(limit: str, key_func: Optional[Callable] = None):
    """
    限流装饰器
    
    Args:
        limit: 限流规则，如 "5/minute", "10/minute"
        key_func: 可选的自定义标识符函数
    """
    def decorator(func):
        func.__rate_limit__ = limit
        func.__rate_limit_key_func__ = key_func or get_identifier
        return func
    return decorator


RATE_LIMITS = {
    'auth_login': '5/minute',
    'auth_verify_session': '30/minute',
    'lottery_draw': '60/minute',
    'lottery_draw_ten': '60/minute',
    'lottery_add': '10/minute',
    'lottery_search': '30/minute',
    'lottery_update': '20/minute',
    'lottery_delete': '20/minute',
    'shop_buy': '60/minute',
    'shop_sell': '60/minute',
    'gmarket_buy': '60/minute',
    'gmarket_sell': '60/minute',
    'warehouse_vip_upgrade': '30/minute',
    'warehouse_vip_advanced_upgrade': '30/minute',
    'warehouse_compress_kusa': '30/minute',
    'farm_plant': '60/minute',
    'farm_harvest': '60/minute',
    'farm_test_recover_capacity': '30/minute',
    'farm_release_spare_capacity': '30/minute',
    'item_compose_ticket': '60/minute',
    'analytics_pageview': '60/minute',
}


def setup_rate_limiter(app):
    """
    配置限流器
    
    Args:
        app: FastAPI 应用实例
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        ip_key = get_ip_identifier(request)
        
        ip_limit_reached = False
        try:
            for rule in ip_limiter._storage.get_limits(ip_key):
                if not ip_limiter._storage.hit(rule, ip_key, ip_key, False):
                    ip_limit_reached = True
                    break
        except Exception:
            pass
        
        if ip_limit_reached:
            logger.warning(f"IP 限流触发: {get_remote_address(request)}")
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error": "请求过于频繁，请稍后再试",
                    "code": "RATE_LIMIT_EXCEEDED"
                }
            )
        
        response = await call_next(request)
        return response
    
    logger.info("API 限流器已启用")
