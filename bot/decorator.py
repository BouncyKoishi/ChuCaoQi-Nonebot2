import time
from functools import wraps
from typing import Optional, List, Callable

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from kusa_base import send_log
from utils import getUserAndGroupMsg


def on_reply_command(commands: Optional[List[str]] = None):
    """回复消息指令装饰器 - NoneBot2 版本"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(event: OneBotV11MessageEvent, *args, **kwargs):
            from nonebot.adapters.onebot.v11 import Reply
            
            # 检查是否有回复消息
            reply_msg = None
            for seg in event.get_message():
                if seg.type == "reply":
                    reply_msg = seg
                    break
            
            if not reply_msg:
                return

            # 获取指令文本
            message_text = event.get_message().extract_plain_text().strip()
            if not message_text.startswith('#'):
                return

            # 检查是否是有效的指令（支持带空格的情况，如"#nsfw"）
            if commands is not None:
                commandMatch = False
                for cmd in commands:
                    if message_text == cmd or message_text.startswith(cmd + ' '):
                        commandMatch = True
                        break
                if not commandMatch:
                    return

            replyId = str(reply_msg.data['id'])
            bot = get_bot()
            try:
                replyMessageCtx = await bot.get_msg(message_id=replyId)
                return await func(event, replyMessageCtx=replyMessageCtx, *args, **kwargs)
            except Exception as e:
                print(f'获取回复消息失败：{e}')
                return

        return wrapper
    return decorator
