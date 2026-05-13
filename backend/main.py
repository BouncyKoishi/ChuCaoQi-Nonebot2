"""
除草器Bot Web API服务

使用方法:
    python -m uvicorn main:app --host 127.0.0.1 --port 8000
"""

import logging
import sys
import os

# 保存 backend 目录路径
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(BACKEND_DIR, '..', 'bot')

# 添加 backend 和 bot 到路径
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, BOT_DIR)

# 设置工作目录到 bot 目录
os.chdir(BOT_DIR)

# Mock nonebot for service imports
sys.modules['nonebot'] = type('NoneType', (), {
    'on_startup': lambda *args, **kwargs: args[0] if args else lambda *a, **k: None,
    'get_bot': lambda: None
})()

import builtins
builtins.on_startup = lambda *args, **kwargs: args[0] if args else lambda *a, **k: None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backend.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

# 导入数据库模块
import dbConnection.db as baseDB

# 导入路由
from routers import auth, farm, warehouse, rank, gmarket, lottery, item, shop, notify, user, donate, analytics

# 导入中间件
from middleware.session_auth import SessionAuthMiddleware
from middleware.rate_limiter import limiter, setup_rate_limiter

from common import ENV

app = FastAPI(
    title="除草器Bot Web API",
    description="除草器机器人的Web API网关",
    version="2.0.0",
    docs_url="/docs" if ENV != "prod" else None,
    redoc_url="/redoc" if ENV != "prod" else None,
    openapi_url="/openapi.json" if ENV != "prod" else None,
)

app.state.limiter = limiter

setup_rate_limiter(app)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session 认证中间件
app.add_middleware(SessionAuthMiddleware)


# ==================== 系统路由 (原 system 模块合并至此) ====================

@app.get("/")
async def root():
    """API 根信息"""
    return {
        "name": "除草器Bot Web API v2.0",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "farm": "/api/farm",
            "warehouse": "/api/warehouse",
            "shop": "/api/item/shop/items",
            "gmarket": "/api/gmarket",
            "lottery": "/api/lottery"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "bot-api"}


@app.get("/api/config")
async def get_config():
    """获取前端配置"""
    from common import ENV
    return {
        "env": ENV,
        "isDev": ENV != 'prod'
    }


# ==================== 全局异常处理器 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    error_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
    logger.error(f"全局异常: {error_msg}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"服务器错误: {type(exc).__name__}",
            "detail": str(exc) if len(str(exc)) < 200 else str(exc)[:200]
        }
    )


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup():
    """启动时初始化数据库"""
    await baseDB.init_db()
    logger.info("✅ Bot API服务启动成功 (http://127.0.0.1:8000)")


# ==================== 注册路由器 ====================

# 认证路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# 用户路由
app.include_router(user.router, prefix="/api/user", tags=["user"])

# 农田路由
app.include_router(farm.router, prefix="/api/farm", tags=["farm"])

# 仓库路由 (包含 VIP)
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])

# 排行榜路由
app.include_router(rank.router, prefix="/api/rank", tags=["rank"])

# G市路由
app.include_router(gmarket.router, prefix="/api/gmarket", tags=["gmarket"])

# 抽奖路由
app.include_router(lottery.router, prefix="/api/lottery", tags=["lottery"])

# 道具路由 (/toggle, /amount, /compose-ticket)
from routers import item
app.include_router(item.router, prefix="/api/item", tags=["item"])

# 商店路由 (/items, /buy, /sell)
from routers import shop
app.include_router(shop.router, prefix="/api/shop", tags=["shop"])

# 通知路由
# 实际路径：/internal/notify, /api/notify/farm-status, /api/notify/kusa-harvested
app.include_router(notify.router, tags=["notify"])

# 捐赠记录路由
app.include_router(donate.router, prefix="/api/donate", tags=["donate"])

# 访问统计路由
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
