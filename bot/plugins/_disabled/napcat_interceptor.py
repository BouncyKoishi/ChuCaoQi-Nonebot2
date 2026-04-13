"""
NapCat 指令拦截器

使用 PreProcessor 机制，通过抛出 IgnoredException 来忽略事件。
支持使用 @allow_napcat 装饰器来为特定指令配置白名单。

配置项（在 plugin_config.yaml 中）：
    napcat_interceptor:
        enabled: true  # 是否启用拦截器
        command_prefixes:  # 要拦截的指令前缀
            - "!"
            - "/"
        whitelist_commands:  # 白名单指令（不拦截）
            - "!napcat"
            - "!nc"

使用方式：
    from plugins.napcat_interceptor import allow_napcat
    from nonebot import on_command
    
    @allow_napcat("生草", group_ids=[123456789], user_ids=[987654321])
    @on_command("生草", aliases={"!生草"})
    async def handle_kusa():
        ...
    
    @allow_napcat("test", allow_all=True)
    @on_command("test")
    async def handle_test():
        ...
"""

from nonebot import get_driver
from nonebot.message import IgnoredException, event_preprocessor
from nonebot.adapters.onebot.v11 import MessageEvent
from typing import Set, Optional, List, Dict, Callable

driver = get_driver()

config = driver.config

INTERCEPTOR_ENABLED = False
COMMAND_PREFIXES = ["!", "/"]
WHITELIST_COMMANDS = ["!napcat", "!nc", "/napcat", "/nc"]

ALLOWED_RULES: Dict[str, dict] = {}

try:
    import yaml
    import os
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "plugin_config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            plugin_config = yaml.safe_load(f) or {}
            napcat_config = plugin_config.get("napcat_interceptor", {})
            INTERCEPTOR_ENABLED = napcat_config.get("enabled", False)
            COMMAND_PREFIXES = napcat_config.get("command_prefixes", ["!", "/"])
            WHITELIST_COMMANDS = napcat_config.get("whitelist_commands", ["!napcat", "!nc"])
except Exception as e:
    print(f"[NapCat Interceptor] 加载配置失败: {e}")


def match_command(message_text: str) -> Optional[str]:
    """匹配消息中的指令名"""
    msg = message_text.strip()
    if not msg:
        return None
    
    first_char = msg[0]
    if first_char not in COMMAND_PREFIXES:
        return None
    
    cmd = msg[1:].split()[0] if len(msg) > 1 else ""
    return cmd


@event_preprocessor
async def intercept_command(event: MessageEvent):
    """
    预处理器 - 拦截 NapCat 端的指令消息
    
    注意：这个预处理器只对 OneBot V11 的 MessageEvent 生效，
    因为参数类型声明为 MessageEvent。
    官方 QQ Bot 的事件类型不匹配，预处理器不会执行。
    """
    if not INTERCEPTOR_ENABLED:
        return
    
    message_text = str(event.message).strip()
    
    if not message_text:
        return
    
    first_char = message_text[0]
    
    if first_char not in COMMAND_PREFIXES:
        return
    
    for whitelist_cmd in WHITELIST_COMMANDS:
        if message_text.lower().startswith(whitelist_cmd.lower()):
            print(f"[NapCat Interceptor] 放行（白名单指令）: {message_text[:30]}...")
            return
    
    cmd_name = match_command(message_text)
    
    group_id = getattr(event, 'group_id', None)
    user_id = getattr(event, 'user_id', None)
    
    is_group = group_id is not None
    
    if cmd_name and cmd_name in ALLOWED_RULES:
        rule = ALLOWED_RULES[cmd_name]
        
        if rule.get('allow_all'):
            print(f"[NapCat Interceptor] 放行（allow_all）: 指令 {cmd_name}")
            return
        
        if is_group:
            if group_id and group_id in rule.get('group_ids', set()):
                print(f"[NapCat Interceptor] 放行（群白名单）: 指令 {cmd_name}, 群 {group_id}")
                return
        else:
            if user_id and user_id in rule.get('user_ids', set()):
                print(f"[NapCat Interceptor] 放行（用户白名单）: 指令 {cmd_name}, 用户 {user_id}")
                return
    
    if group_id:
        print(f"[NapCat Interceptor] 拦截群指令: 群 {group_id}, 用户 {user_id}, 内容: {message_text[:50]}...")
    elif user_id:
        print(f"[NapCat Interceptor] 拦截私聊指令: 用户 {user_id}, 内容: {message_text[:50]}...")
    
    raise IgnoredException(f"NapCat interceptor blocked: {message_text[:30]}...")


def allow_napcat(command: str, 
                 group_ids: Optional[List[int]] = None, 
                 user_ids: Optional[List[int]] = None, 
                 allow_all: bool = False):
    """
    装饰器：为特定指令配置 NapCat 端白名单
    
    使用方式：
        @allow_napcat("生草", group_ids=[123456789], user_ids=[987654321])
        @on_command("生草")
        async def handle_kusa():
            ...
        
        @allow_napcat("test", allow_all=True)
        @on_command("test")
        async def handle_test():
            ...
    
    参数：
        command: 指令名（不包括前缀，如 "生草"、"test"）
        group_ids: 允许的群号列表。私聊时忽略此参数。
        user_ids: 允许的用户QQ列表。群聊时忽略此参数。
        allow_all: 是否允许所有人使用（相当于禁用此指令的拦截）。
    
    逻辑：
        - 私聊：检查用户QQ是否在 user_ids 中
        - 群聊：检查群号是否在 group_ids 中
        - allow_all 为 True 时：所有人都可以使用
    """
    group_set = set(group_ids) if group_ids else set()
    user_set = set(user_ids) if user_ids else set()
    
    ALLOWED_RULES[command] = {
        'group_ids': group_set,
        'user_ids': user_set,
        'allow_all': allow_all
    }
    
    if allow_all:
        print(f"[Allow NapCat] 指令 '{command}' 已启用完全放行模式")
    else:
        print(f"[Allow NapCat] 指令 '{command}' 已配置白名单: groups={list(group_set)}, users={list(user_set)}")
    
    def decorator(matcher) -> Callable:
        return matcher
    
    return decorator


def set_interceptor_enabled(enabled: bool):
    """
    设置拦截器开关
    
    Args:
        enabled: 是否启用
    """
    global INTERCEPTOR_ENABLED
    INTERCEPTOR_ENABLED = enabled
    print(f"[NapCat Interceptor] 拦截器状态: {'启用' if enabled else '禁用'}")


def add_whitelist_command(command: str):
    """
    添加白名单指令
    
    Args:
        command: 指令（如 "!napcat"）
    """
    if command not in WHITELIST_COMMANDS:
        WHITELIST_COMMANDS.append(command)
        print(f"[NapCat Interceptor] 添加白名单指令: {command}")


def remove_whitelist_command(command: str):
    """
    移除白名单指令
    
    Args:
        command: 指令
    """
    if command in WHITELIST_COMMANDS:
        WHITELIST_COMMANDS.remove(command)
        print(f"[NapCat Interceptor] 移除白名单指令: {command}")


def get_interceptor_status() -> dict:
    """
    获取拦截器状态
    
    Returns:
        包含拦截器状态的字典
    """
    return {
        "enabled": INTERCEPTOR_ENABLED,
        "command_prefixes": COMMAND_PREFIXES,
        "whitelist_commands": WHITELIST_COMMANDS,
        "allowed_rules": {k: {**v, 'group_ids': list(v['group_ids']), 'user_ids': list(v['user_ids'])} 
                         for k, v in ALLOWED_RULES.items()}
    }
