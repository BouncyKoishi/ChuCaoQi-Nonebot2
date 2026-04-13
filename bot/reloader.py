"""
重载函数模块 - 封装 NoneBot2 的 matcher 创建函数，自动添加用户注册等规则
"""

from typing import Union
from nonebot import on_command as _on_command, on_message as _on_message, on_notice as _on_notice
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.qq import GroupAtMessageCreateEvent

import dbConnection.user as user_db
import dbConnection.kusa_system as kusa_db


async def _get_platform_info(event) -> tuple:
    """获取平台类型和平台ID"""
    if isinstance(event, GroupMessageEvent):
        return "onebot", str(event.user_id)
    elif isinstance(event, PrivateMessageEvent):
        return "onebot", str(event.user_id)
    elif isinstance(event, GroupAtMessageCreateEvent):
        return "qqbot", event.author.id
    return None, None


async def _register_unified_user(event: Union[GroupMessageEvent, PrivateMessageEvent, GroupAtMessageCreateEvent]) -> bool:
    """注册统一用户"""
    platform, platform_id = await _get_platform_info(event)
    if not platform:
        return True
    
    unified_user = await user_db.getUnifiedUserByPlatform(platform, platform_id)
    if not unified_user:
        if platform == "onebot":
            await user_db.createUnifiedUserForOnebot(platform_id)
        elif platform == "qqbot":
            await user_db.createUnifiedUserForQQBot(platform_id)
    
    return True


async def _register_kusa_user(event: Union[GroupMessageEvent, PrivateMessageEvent, GroupAtMessageCreateEvent]) -> bool:
    """注册生草系统用户（包含统一用户）"""
    await _register_unified_user(event)
    
    platform, platform_id = await _get_platform_info(event)
    if platform:
        unified_user = await user_db.getUnifiedUserByPlatform(platform, platform_id)
        if unified_user:
            await kusa_db.createKusaUser(unified_user.id)
    
    return True


def kusa_command(cmd, **kwargs):
    """
    生草系统插件专用 on_command
    自动注册生草用户（包含统一用户）
    
    用法:
        from reloader import kusa_command as on_command
        
        my_cmd = on_command("生草")
    """
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_kusa_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_command(cmd, rule=final_rule, **kwargs)


def db_command(cmd, **kwargs):
    """
    数据库交互插件专用 on_command
    自动注册统一用户
    
    用法:
        from reloader import db_command as on_command
        
        my_cmd = on_command("绑定")
    """
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_unified_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_command(cmd, rule=final_rule, **kwargs)


def kusa_message(**kwargs):
    """生草系统插件专用 on_message"""
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_kusa_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_message(rule=final_rule, **kwargs)


def db_message(**kwargs):
    """数据库交互插件专用 on_message"""
    rule = kwargs.pop('rule', None)
    base_rule = Rule(_register_unified_user)
    final_rule = base_rule & rule if rule else base_rule
    return _on_message(rule=final_rule, **kwargs)
