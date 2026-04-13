"""
全局翻页辅助模块
提供统一的翻页功能，所有需要翻页的模块都可以使用
"""

from typing import Dict, Any, Optional, Callable
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent

# 全局翻页状态存储
# key: user_id, value: 翻页状态
pagination_state: Dict[str, Dict[str, Any]] = {}


# 注册翻页处理器
# key: type, value: 处理函数
pagination_handlers: Dict[str, Callable] = {}


def register_pagination_handler(pagination_type: str, handler: Callable):
    """
    注册翻页处理器
    
    Args:
        pagination_type: 翻页类型标识，如 'warehouse', 'search', 'trade_record'
        handler: 处理函数，接收 (user_id, state, next_page) 参数，返回输出字符串
    """
    pagination_handlers[pagination_type] = handler


def set_pagination_state(user_id: str, pagination_type: str, state_data: Dict[str, Any]):
    """
    设置用户的翻页状态
    
    Args:
        user_id: 用户ID
        pagination_type: 翻页类型
        state_data: 状态数据，必须包含 current_page, total_pages, page_size
    """
    pagination_state[user_id] = {
        'type': pagination_type,
        **state_data
    }


def get_pagination_state(user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户的翻页状态"""
    return pagination_state.get(user_id)


def clear_pagination_state(user_id: str):
    """清除用户的翻页状态"""
    if user_id in pagination_state:
        del pagination_state[user_id]


# 全局下一页命令
下一页_cmd = on_command('下一页', aliases={'next', 'n'}, priority=5, block=True)

@下一页_cmd.handle()
async def handle_下一页(event: OneBotV11MessageEvent):
    """处理全局下一页命令"""
    user_id = str(event.user_id)
    
    # 检查是否有翻页状态
    state = get_pagination_state(user_id)
    if not state:
        await 下一页_cmd.finish('没有可翻页的内容，请先使用带翻页功能的命令')
        return
    
    pagination_type = state.get('type')
    current_page = state.get('current_page', 1)
    total_pages = state.get('total_pages', 1)
    
    if current_page >= total_pages:
        await 下一页_cmd.finish('已经是最后一页了')
        return
    
    # 检查是否有对应的处理器
    handler = pagination_handlers.get(pagination_type)
    if not handler:
        await 下一页_cmd.finish(f'未知的翻页类型: {pagination_type}')
        return
    
    # 计算下一页
    next_page = current_page + 1
    
    # 调用对应的处理器
    try:
        output = await handler(user_id, state, next_page)
        # 更新状态
        state['current_page'] = next_page
        await 下一页_cmd.finish(output)
    except Exception as e:
        # 检查是否是 FinishedException（正常结束），不是才报错
        if 'FinishedException' not in type(e).__name__:
            await 下一页_cmd.finish(f'翻页失败: {str(e)}')


# 全局上一页命令
上一页_cmd = on_command('上一页', aliases={'prev', 'p', 'previous'}, priority=5, block=True)

@上一页_cmd.handle()
async def handle_上一页(event: OneBotV11MessageEvent):
    """处理全局上一页命令"""
    user_id = str(event.user_id)
    
    # 检查是否有翻页状态
    state = get_pagination_state(user_id)
    if not state:
        await 上一页_cmd.finish('没有可翻页的内容，请先使用带翻页功能的命令')
        return
    
    pagination_type = state.get('type')
    current_page = state.get('current_page', 1)
    
    if current_page <= 1:
        await 上一页_cmd.finish('已经是第一页了')
        return
    
    # 检查是否有对应的处理器
    handler = pagination_handlers.get(pagination_type)
    if not handler:
        await 上一页_cmd.finish(f'未知的翻页类型: {pagination_type}')
        return
    
    # 计算上一页
    prev_page = current_page - 1
    
    # 调用对应的处理器
    try:
        output = await handler(user_id, state, prev_page)
        # 更新状态
        state['current_page'] = prev_page
        await 上一页_cmd.finish(output)
    except Exception as e:
        # 检查是否是 FinishedException（正常结束），不是才报错
        if 'FinishedException' not in type(e).__name__:
            await 上一页_cmd.finish(f'翻页失败: {str(e)}')
