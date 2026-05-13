"""
后端 API 路由模块

包含以下路由模块:
- auth: 认证相关
- farm: 农田/生草相关
- warehouse: 仓库/用户/VIP相关
- rank: 排行榜相关
- gmarket: G市相关
- lottery: 抽奖相关
- item: 道具/商店相关
- notify: 通知/WebSocket相关
"""

from . import auth
from . import farm
from . import warehouse
from . import rank
from . import gmarket
from . import lottery
from . import item
from . import notify
from . import analytics

__all__ = [
    'auth',
    'farm',
    'warehouse',
    'rank',
    'gmarket',
    'lottery',
    'item',
    'notify',
    'analytics',
]
