"""
复读禁言插件 - 改进版

功能：
1. 群体复读检测：连续超过四句话内容相同 → 在复读被打断时禁言倒数第二个复读者
2. 个人复读检测：同一个人连续发相同的一句话两次以上 → 直接禁言此人

仅支持 OneBot V11 协议，仅对特定群生效
"""

from kusa_base import is_super_admin, plugin_config
from multi_platform import get_user_id, is_onebot_v11_event
from nonebot import on_command, on_message
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot, GroupMessageEvent
from typing import cast
from collections import deque


class RepeatBanManager:
    """复读禁言管理器"""
    
    def __init__(self, max_history: int = 10):
        self.enabled = False
        self.max_history = max_history
        self.message_history: deque = deque(maxlen=max_history)
        self.group_contexts: dict = {}
    
    def toggle(self) -> bool:
        """切换开关状态"""
        self.enabled = not self.enabled
        return self.enabled
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def add_message(self, group_id: int, user_id: int, message: str) -> dict:
        """添加消息并返回检测结果
        
        Returns:
            {
                'action': 'none' | 'ban_group_repeat' | 'ban_self_repeat',
                'target_user': int,  # 被禁言的用户ID
                'duration': int,     # 禁言时长（秒）
                'reason': str        # 原因
            }
        """
        if group_id not in self.group_contexts:
            self.group_contexts[group_id] = {
                'messages': deque(maxlen=10),
                'repeat_users': [],
                'is_group_repeating': False
            }
        
        ctx = self.group_contexts[group_id]
        messages = ctx['messages']
        repeat_users = ctx['repeat_users']
        
        result = {'action': 'none'}
        
        if len(messages) >= 1:
            last_msg = messages[-1]
            
            if last_msg['content'] == message:
                if last_msg['user_id'] == user_id:
                    result = {
                        'action': 'ban_self_repeat',
                        'target_user': user_id,
                        'duration': 60,
                        'reason': '个人复读'
                    }
                else:
                    messages.append({'user_id': user_id, 'content': message})
                    repeat_users.append(user_id)
                    
                    same_count = self._count_consecutive_same(messages)
                    
                    if same_count >= 4:
                        ctx['is_group_repeating'] = True
                    else:
                        if ctx['is_group_repeating'] and same_count < 4:
                            if len(repeat_users) >= 2:
                                result = {
                                    'action': 'ban_group_repeat',
                                    'target_user': repeat_users[-2],
                                    'duration': 120,
                                    'reason': '群体复读被打断'
                                }
                            ctx['is_group_repeating'] = False
                            repeat_users.clear()
                
                return result
        
        if ctx['is_group_repeating'] and len(repeat_users) >= 2:
            result = {
                'action': 'ban_group_repeat',
                'target_user': repeat_users[-2],
                'duration': 120,
                'reason': '群体复读被打断'
            }
        
        messages.append({'user_id': user_id, 'content': message})
        ctx['is_group_repeating'] = False
        repeat_users.clear()
        repeat_users.append(user_id)
        
        return result
    
    def _count_consecutive_same(self, messages: deque) -> int:
        """计算从最新消息开始，连续相同内容的消息数量"""
        if not messages:
            return 0
        
        messages_list = list(messages)
        last_content = messages_list[-1]['content']
        count = 1
        
        for i in range(len(messages_list) - 2, -1, -1):
            if messages_list[i]['content'] == last_content:
                count += 1
            else:
                break
        
        return count


ban_manager = RepeatBanManager()


ban_mode_change_cmd = on_command('ban_mode_change', priority=5, block=True)


@ban_mode_change_cmd.handle()
async def handle_ban_mode_change(bot: Bot, event: Event):
    user_id = await get_user_id(event)
    
    if not await is_super_admin(user_id):
        await ban_mode_change_cmd.finish('权限不足')
        return
    
    new_state = ban_manager.toggle()
    await ban_mode_change_cmd.finish(f'Succeed! banMode = {1 if new_state else 0}')


repeat_ban_handler = on_message(priority=10, block=False)


@repeat_ban_handler.handle()
async def handle_repeat_ban(bot: Bot, event: Event):
    if not is_onebot_v11_event(event):
        return
    
    if not isinstance(event, GroupMessageEvent):
        return
    
    if not ban_manager.is_enabled():
        return
    
    group_id = event.group_id
    sysu_group = plugin_config.get('group', {}).get('sysu')
    
    if group_id != sysu_group:
        return
    
    user_qq = event.user_id
    message = event.get_plaintext()
    
    if not message.strip():
        return
    
    result = ban_manager.add_message(group_id, user_qq, message)
    
    if result['action'] != 'none':
        onebot_bot = cast(OneBotV11Bot, bot)
        try:
            await onebot_bot.set_group_ban(
                group_id=group_id,
                user_id=result['target_user'],
                duration=result['duration']
            )
            print(f"[repeat_ban] 已禁言用户 {result['target_user']} {result['duration']}秒，原因：{result['reason']}")
        except Exception as e:
            print(f"[repeat_ban] 禁言失败: {e}")
