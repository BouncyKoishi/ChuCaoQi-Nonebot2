"""
消息预处理插件 - NoneBot2 版本
处理指令频率限制、黑名单检查等全局预处理
"""

import time
from nonebot import get_bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

from kusa_base import plugin_config
from nonebot_plugin_apscheduler import scheduler

last_spell_record: dict = {}
repeat_warning: dict = {}


@event_preprocessor
async def preprocessor_handler(event):
    """消息预处理处理器 - 全局生效"""
    global last_spell_record, repeat_warning

    if not isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return

    raw_message = event.raw_message if hasattr(event, 'raw_message') else str(event.message)
    if not raw_message.startswith('!') or raw_message.startswith('/') or raw_message.startswith('#'):
        return

    user_id = str(event.user_id)

    ban_list = plugin_config.get('qq', {}).get('ban', [])
    if user_id in ban_list:
        raise IgnoredException("此人处于除草器指令黑名单，跳过指令响应")

    if isinstance(event, GroupMessageEvent):
        allow_groups = plugin_config.get('group', {}).get('allow', [])
        if event.group_id not in allow_groups:
            raise IgnoredException("非可用群，跳过指令响应")

    warning_count = repeat_warning.get(user_id, 0)
    if warning_count >= 5:
        raise IgnoredException("刷指令人员，暂时屏蔽所有服务")

    if user_id in last_spell_record:
        record_time = last_spell_record[user_id]
        if time.time() - record_time <= 0.5:
            repeat_warning[user_id] = warning_count + 1
            if repeat_warning[user_id] >= 8:
                msg = '识别到恶意刷指令。除草器所有服务对你停止1小时。'
                bot = get_bot()
                if isinstance(event, GroupMessageEvent):
                    await bot.send_group_msg(group_id=event.group_id, message=msg)
                else:
                    await bot.send_private_msg(user_id=event.user_id, message=msg)

    last_spell_record[user_id] = time.time()


if scheduler:
    @scheduler.scheduled_job('interval', minutes=67)
    async def clean_warning_runner():
        """定期清理警告记录"""
        global repeat_warning
        for key in repeat_warning:
            repeat_warning[key] = 0
