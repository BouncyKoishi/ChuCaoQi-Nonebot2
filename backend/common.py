"""
后端 API 共享配置和工具函数

此模块用于存储需要在多个路由模块间共享的配置和函数，
避免循环导入问题。
"""

import os
import yaml
from datetime import datetime
from typing import Any, Dict, Tuple

from core.config import PROJECT_ROOT, plugin_config


def _load_yaml(path: str) -> Dict:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


_backend_config_path = os.path.join(PROJECT_ROOT, 'config', 'backend.yaml')
_backend_config = _load_yaml(_backend_config_path)

ENV = _backend_config.get('env', plugin_config.get('env', 'dev'))

INTERNAL_API_TOKEN = os.getenv(
    'INTERNAL_API_TOKEN',
    _backend_config.get('internalApiToken', 'default_token')
)

ALLOW_LEGACY_LOGIN = os.getenv(
    'ALLOW_LEGACY_LOGIN',
    str(_backend_config.get('allowLegacyLogin', False))
).lower() == 'true'

draw_config = plugin_config.get('drawItem', {})
BAN_RISK = draw_config.get('banRisk', 0)

disabled_users: Dict[str, int] = {}


def check_user_disabled(userId: str) -> Tuple[bool, int]:
    """
    检查用户是否被禁用

    Args:
        userId: 用户ID

    Returns:
        (是否被禁用, 剩余秒数)
    """
    userId_str = str(userId)
    if userId_str not in disabled_users:
        return False, 0

    until = disabled_users[userId_str]
    now = int(datetime.now().timestamp() * 1000)

    if until > now:
        remaining = int((until - now) / 1000)
        return True, remaining
    else:
        del disabled_users[userId_str]
        return False, 0


def set_user_disabled(userId, disabled_seconds: int):
    """设置用户禁用状态"""
    until = int((datetime.now().timestamp() + disabled_seconds) * 1000)
    disabled_users[str(userId)] = until


# ==================== 转让相关共享工具 ====================

async def resolve_transfer_target(service: Any, target_user_id, target_qq):
    """按用户ID或QQ号解析转让接收方

    Args:
        service: 提供 get_transfer_target_by_id / get_transfer_target_by_qq 的服务类
                 （WarehouseService 或 ItemService）
        target_user_id: 接收方用户ID，优先级高于QQ号
        target_qq: 接收方QQ号

    Returns:
        (target_user, error)：解析成功时 error 为 None，失败时 target_user 为 None
    """
    if target_user_id:
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError):
            return None, '用户ID格式不正确'
        return await service.get_transfer_target_by_id(target_user_id), None
    if target_qq:
        return await service.get_transfer_target_by_qq(str(target_qq).strip()), None
    return None, '请输入接收方的QQ号或用户ID'
