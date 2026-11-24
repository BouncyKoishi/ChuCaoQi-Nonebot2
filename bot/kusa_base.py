"""
生草系统基础模块 - NoneBot2 版本
提供用户检查、消息发送、交易功能等基础功能
"""

from typing import Union, List, Dict, Any, Optional
import os

from core.config import plugin_config
from multi_platform import is_onebot_v11_bot

friend_list: List[str] = []


async def send_group_msg(group_id: Union[int, str], message: Union[str, object], 
                         msg_id: Optional[str] = None) -> bool:
    """
    发送群消息 - 按当前连接端分发（OneBot / 官机）
    
    Args:
        group_id: QQ 群号
        message: 消息内容
        msg_id: 消息ID（已废弃，保留参数兼容性）
        
    Returns:
        是否发送成功
    """
    from multi_platform import push_group

    result = await push_group(group_id, message)
    if not result.ok:
        print(f'对群{group_id}发送消息失败：{result.reason}')
    return result.ok


async def _resolve_unified_user(identifier: Union[int, str]):
    """按 UnifiedUser.id 解析用户，兼容旧调用方传入的 realQQ"""
    from core.db.models import UnifiedUser

    try:
        num = int(identifier)
    except (TypeError, ValueError):
        return None

    user = await UnifiedUser.filter(id=num).first()
    if user:
        return user
    return await UnifiedUser.filter(realQQ=str(num)).first()


async def send_private_msg(user_id: Union[int, str], message: Union[str, object], 
                           msg_id: Optional[str] = None) -> bool:
    """
    发送私聊消息 - 按当前连接端分发（OneBot / 官机）
    
    Args:
        user_id: UnifiedUser的id（兼容旧调用方传入的 realQQ）
        message: 消息内容
        msg_id: 消息ID（已废弃，保留参数兼容性）
        
    Returns:
        是否发送成功
    """
    global friend_list

    try:
        from nonebot import get_bots
        from multi_platform import push_private

        unified_user = await _resolve_unified_user(user_id)
        if not unified_user:
            return False

        bots = list(get_bots().values())
        onebot_bot = next((bot for bot in bots if is_onebot_v11_bot(bot)), None)
        if onebot_bot is not None:
            if not unified_user.realQQ:
                return False

            if not friend_list:
                try:
                    friend_list_info = await onebot_bot.get_friend_list()
                    friend_list = [str(friend['user_id']) for friend in friend_list_info]
                except Exception:
                    friend_list = []

            if friend_list and str(unified_user.realQQ) not in friend_list:
                return False

        result = await push_private(unified_user.id, message)
        if not result.ok:
            print(f'对用户{user_id}发送私聊消息失败：{result.reason}')
        return result.ok
    except Exception as e:
        print(f'对用户{user_id}发送私聊消息失败：{str(e)}')
        return False


async def send_log(message: str) -> bool:
    print('Chucaoqi Log: ' + message)

    log_group = plugin_config.get('group', {}).get('log')
    if log_group:
        return await send_group_msg(log_group, message)
    return False


async def is_super_admin(userId: int) -> bool:
    from core.db.models import UnifiedUser
    unified_user = await UnifiedUser.filter(id=userId).first()
    return unified_user is not None and unified_user.isSuperAdmin


async def parse_user_identifier(identifier: Union[int, str]) -> int:
    from core.db.models import UnifiedUser
    
    try:
        num = int(identifier)
    except (ValueError, TypeError):
        return None
    
    if num < 1000000:
        user = await UnifiedUser.filter(id=num).first()
        if user:
            return user.id
        user = await UnifiedUser.filter(realQQ=str(num)).first()
        if user:
            return user.id
    else:
        user = await UnifiedUser.filter(realQQ=str(num)).first()
        if user:
            return user.id
    
    return None


async def append_friend_list(qq: Union[str, List[str], int]) -> int:
    global friend_list
    qq_list = qq if isinstance(qq, list) else [qq]
    count = 0
    
    for qq_num in qq_list:
        qq_str = str(qq_num)
        if qq_str not in friend_list:
            friend_list.append(qq_str)
            count += 1
            
    if count:
        print(f'已将{count}个QQ号新增到好友列表，当前列表：{friend_list}')
        
    return count
