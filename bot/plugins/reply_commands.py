from typing import Dict, Tuple, Callable, Optional, Union
from dataclasses import dataclass
from collections import OrderedDict
from nonebot import on_message, logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.typing import T_State
from utils import extractImgUrls

_reply_command_handlers: Dict[str, Tuple[Callable, str]] = {}
_reply_preprocessors: Dict[str, Callable] = {}
_reply_duel_confirmations: Dict[int, dict] = {}
# 搜图存储结果：限制条数避免长期运行内存缓涨，先进先出
_MAX_STORED_RESULTS = 200
_reply_stored_results: "OrderedDict[str, dict]" = OrderedDict()
_reply_text_handlers: Dict[str, Tuple[Callable, str]] = {}

_reply_main_handler = on_message(priority=10, block=False)


@dataclass
class ReplyCommandResult:
    message: str = ''
    stored_id: Optional[dict] = None


def reply_command(
    command: str,
    preprocessor: Optional[Callable] = None
):
    def decorator(func: Callable):
        _reply_command_handlers[command] = (func, func.__name__)
        if preprocessor:
            _reply_preprocessors[command] = preprocessor
        return func
    return decorator


def reply_text_command(command: str):
    def decorator(func: Callable):
        _reply_text_handlers[command] = (func, func.__name__)
        return func
    return decorator


def _proper_reply_message(event) -> Optional["Message"]:
    """获取事件所回复消息的 Message 对象（未回复/异常返回 None）

    直接取 event.reply.message：适配器的 Reply 模型自带完整被回复消息，
    用 str(event.reply) 会得到 pydantic repr 而非 CQ 码，无法解析图片。
    """
    if not hasattr(event, 'reply') or not event.reply:
        return None
    reply = event.reply
    try:
        msg = reply.message
    except AttributeError:
        return None
    return msg if msg else None


def extract_reply_images(event) -> list:
    """提取所回复消息中的全部图片 URL（多图支持）

    #指令只处理所回复的消息：#消息本身仅作触发器，不入参解析。
    """
    msg = _proper_reply_message(event)
    if msg is None:
        return []
    return extractImgUrls(msg)


def extract_reply_image(event) -> Optional[str]:
    """提取所回复消息中的第一张图片 URL"""
    urls = extract_reply_images(event)
    return urls[0] if urls else None


def extract_image_from_message(event) -> Optional[str]:
    """提取当前消息中的第一张图片 URL（NapCat 回复时会把图副本附在当前#消息里）"""
    message = event.get_message()
    img_urls = extractImgUrls(message)
    if img_urls:
        return img_urls[0]
    return None


def extract_image(event) -> Optional[str]:
    """提取可用于#指令的图片 URL

    #指令只处理所回复的消息（用户回复的目标），当前#消息自带的图仅兜底，
    因此在来源冲突时优先回复消息的图。
    """
    return extract_reply_image(event) or extract_image_from_message(event)


def set_duel_confirmations(user_id: int, info: dict):
    global _reply_duel_confirmations
    _reply_duel_confirmations[user_id] = info


def get_duel_confirmations():
    global _reply_duel_confirmations
    return _reply_duel_confirmations


def del_duel_confirmations(user_id: int):
    global _reply_duel_confirmations
    if user_id in _reply_duel_confirmations:
        del _reply_duel_confirmations[user_id]


def store_result(message_id, result: dict):
    _reply_stored_results[str(message_id)] = result
    # 限制缓存条数，超出则淘汰最旧的（先进先出）
    while len(_reply_stored_results) > _MAX_STORED_RESULTS:
        _reply_stored_results.popitem(last=False)


def get_stored_result(message_id) -> Optional[dict]:
    return _reply_stored_results.get(str(message_id))


@_reply_main_handler.handle()
async def handle_reply_command(bot: Bot, event, state: T_State):
    if not hasattr(event, 'reply') or not event.reply:
        return

    message = event.get_message()
    message_text = str(message)
    stripped_text = message_text.strip()

    if not stripped_text.startswith('#'):
        return

    command = stripped_text[1:].strip().lower()

    if command in _reply_text_handlers:
        handler = _reply_text_handlers[command][0]
        try:
            result = await handler(event, bot)
            if result:
                await bot.send(event=event, message=result)
        except Exception as e:
            logger.error(f"reply_text_command handler error for '{command}': {e}")
            import traceback
            traceback.print_exc()
        return

    if command not in _reply_command_handlers:
        return

    img_url = extract_image(event)
    if not img_url:
        return

    if command in _reply_preprocessors:
        preprocessor = _reply_preprocessors[command]
        should_continue, state_data = await preprocessor(event, img_url)
        if not should_continue:
            if state_data:
                await bot.send(event=event, message=state_data)
            return

    handler = _reply_command_handlers[command][0]

    try:
        result = await handler(event, img_url, bot)

        if isinstance(result, ReplyCommandResult):
            if result.message:
                sent_msg = await bot.send(event=event, message=result.message)
                if result.stored_id is not None and sent_msg.get('message_id'):
                    store_result(sent_msg['message_id'], result.stored_id)
        elif isinstance(result, str):
            await bot.send(event=event, message=result)
    except Exception as e:
        logger.error(f"reply_command handler error for '{command}': {e}")
        import traceback
        traceback.print_exc()