"""
后端 API 共享配置和工具函数

此模块用于存储需要在多个路由模块间共享的配置和函数，
避免循环导入问题。
"""

import os
import yaml
from datetime import datetime
from typing import Dict, Tuple

_config_path = os.path.join(os.path.dirname(__file__), '..', 'bot', 'config', 'plugin_config.yaml')
if os.path.exists(_config_path):
    with open(_config_path, 'r', encoding='utf-8') as f:
        _plugin_config: Dict = yaml.safe_load(f) or {}
else:
    _plugin_config = {}

INTERNAL_API_TOKEN = _plugin_config.get('backend', {}).get('internalApiToken', 'default_token')

# 是否允许无token登录（兼容模式，过渡期使用）
# 生产环境建议设置为 false，强制使用 token 验证
ALLOW_LEGACY_LOGIN = os.getenv('ALLOW_LEGACY_LOGIN', 'true').lower() == 'true'

# 禁用用户字典: {userId: 解禁时间戳(毫秒)}
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
        # 解禁时间已过，移除禁用记录
        del disabled_users[userId_str]
        return False, 0
