"""
生草系统基础模块 - NoneBot2 版本
提供用户检查、消息发送、交易功能等基础功能
"""

import yaml
from typing import Union, List, Dict, Any, Optional
import os

try:
    from config import config
    plugin_config_path = config.plugin_config_path
except ImportError:
    config = None
    plugin_config_path = os.path.join(os.path.dirname(__file__), "config", "plugin_config.yaml")

with open(plugin_config_path, 'r', encoding='utf-8') as f:
    plugin_config: Dict[str, Any] = yaml.safe_load(f)

friend_list: List[str] = []


def _is_onebot_v11_bot(bot) -> bool:
    try:
        from nonebot.adapters.onebot.v11 import Bot as OneBotV11
        return isinstance(bot, OneBotV11)
    except Exception:
        return False


async def send_group_msg(group_id: Union[int, str], message: Union[str, object], 
                         msg_id: Optional[str] = None) -> bool:
    """
    发送群消息 - 使用 OneBot V11
    
    Args:
        group_id: 群号
        message: 消息内容
        msg_id: 消息ID（已废弃，保留参数兼容性）
        
    Returns:
        是否发送成功
    """
    try:
        from nonebot import get_bots
        
        bots = get_bots()
        if not bots:
            return False
        
        for bot in bots.values():
            if _is_onebot_v11_bot(bot):
                await bot.send_group_msg(group_id=int(group_id), message=message)
                return True
        
        return False
    except Exception as e:
        print(f'对群{group_id}发送消息失败：{str(e)}')
        return False


async def send_private_msg(user_id: Union[int, str], message: Union[str, object], 
                           msg_id: Optional[str] = None) -> bool:
    """
    发送私聊消息 - 使用 OneBot V11
    
    Args:
        user_id: UnifiedUser的id
        message: 消息内容
        msg_id: 消息ID（已废弃，保留参数兼容性）
        
    Returns:
        是否发送成功
    """
    global friend_list
    
    try:
        from nonebot import get_bots
        from dbConnection.models import UnifiedUser
        
        bots = get_bots()
        if not bots:
            return False
        
        unified_user = await UnifiedUser.filter(id=int(user_id)).first()
        if not unified_user:
            return False
        
        for bot in bots.values():
            if _is_onebot_v11_bot(bot):
                if not unified_user.realQQ:
                    return False
                
                if not friend_list:
                    try:
                        if hasattr(bot, 'get_friend_list'):
                            friend_list_info = await bot.get_friend_list()
                            friend_list = [str(friend['user_id']) for friend in friend_list_info]
                    except Exception:
                        friend_list = []
                
                if friend_list and str(unified_user.realQQ) not in friend_list:
                    return False
                
                await bot.send_private_msg(user_id=int(unified_user.realQQ), message=message)
                return True
        
        return False
    except Exception as e:
        print(f'对用户{user_id}发送私聊消息失败：{str(e)}')
        return False


async def send_log(message: str) -> bool:
    print('Chucaoqi Log: ' + message)
    
    try:
        from nonebot import get_bots
        bots = get_bots()
        if bots:
            for bot in bots.values():
                if _is_qq_bot(bot):
                    return False
                break
    except Exception:
        pass
    
    log_group = plugin_config.get('group', {}).get('log')
    if log_group:
        return await send_group_msg(log_group, message)
    return False


async def is_super_admin(userId: int) -> bool:
    from dbConnection.models import UnifiedUser
    unified_user = await UnifiedUser.filter(id=userId).first()
    return unified_user is not None and unified_user.isSuperAdmin


async def parse_user_identifier(identifier: Union[int, str]) -> int:
    from dbConnection.models import UnifiedUser
    
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


async def buying(
    userId: int,
    item_name_buying: str,
    item_amount_buying: int,
    total_price: int,
    trade_type: str,
    is_using_adv_kusa: bool = False,
    detail: str = None,
) -> bool:
    import dbConnection.kusa_system as base_db
    import dbConnection.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item = await item_db.getItem(item_name_buying)
    
    if item_amount_buying < 0:
        return False
    if user is None or item is None:
        return False
    if is_using_adv_kusa and user.advKusa < total_price:
        return False
    if not is_using_adv_kusa and user.kusa < total_price:
        return False

    await item_db.changeItemAmount(userId, item_name_buying, item_amount_buying)
    
    bot_qq = plugin_config.get('qq', {}).get('bot', 0)
    
    if is_using_adv_kusa:
        await base_db.changeAdvKusa(userId, -total_price)
        await base_db.changeAdvKusa(bot_qq, total_price)
    else:
        await base_db.changeKusa(userId, -total_price)
        await base_db.changeKusa(bot_qq, total_price)
        
    cost_item_name = '草之精华' if is_using_adv_kusa else '草'
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        detail=detail,
        gainItemName=item_name_buying,
        gainItemAmount=item_amount_buying,
        costItemName=cost_item_name,
        costItemAmount=total_price
    )
    return True


async def selling(
    userId: int,
    item_name_selling: str,
    item_amount_selling: int,
    total_price: int,
    trade_type: str,
    is_using_adv_kusa: bool = False
) -> bool:
    import dbConnection.kusa_system as base_db
    import dbConnection.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item = await item_db.getItem(item_name_selling)
    item_amount = await item_db.getItemAmount(userId, item_name_selling)
    
    if item_amount_selling < 0:
        return False
    if user is None or item is None:
        return False
    if item_amount < item_amount_selling:
        return False
        
    await item_db.changeItemAmount(userId, item_name_selling, -item_amount_selling)
    
    bot_qq = plugin_config.get('qq', {}).get('bot', 0)
    
    if is_using_adv_kusa:
        await base_db.changeAdvKusa(userId, total_price)
        await base_db.changeAdvKusa(bot_qq, -total_price)
    else:
        await base_db.changeKusa(userId, total_price)
        await base_db.changeKusa(bot_qq, -total_price)
        
    gain_item_name = '草之精华' if is_using_adv_kusa else '草'
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        gainItemName=gain_item_name,
        gainItemAmount=total_price,
        costItemName=item_name_selling,
        costItemAmount=item_amount_selling
    )
    return True


async def item_charging(
    userId: int,
    item_name_gain: str,
    item_amount_gain: int,
    item_name_cost: str,
    item_amount_cost: int,
    trade_type: str,
    detail: str = None
) -> bool:
    import dbConnection.kusa_system as base_db
    import dbConnection.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item_gain = await item_db.getItem(item_name_gain)
    item_cost = await item_db.getItem(item_name_cost)
    
    if item_amount_gain < 0 or item_amount_cost < 0:
        return False
    if user is None or item_gain is None or item_cost is None:
        return False
        
    item_cost_now_amount = await item_db.getItemAmount(userId, item_name_cost)
    if item_cost_now_amount < item_amount_cost:
        return False

    await item_db.changeItemAmount(userId, item_name_gain, item_amount_gain)
    await item_db.changeItemAmount(userId, item_name_cost, -item_amount_cost)
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        detail=detail,
        gainItemName=item_name_gain,
        gainItemAmount=item_amount_gain,
        costItemName=item_name_cost,
        costItemAmount=item_amount_cost
    )
    return True


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


async def get_bot_qq() -> int:
    return plugin_config.get('qq', {}).get('bot', 0)
