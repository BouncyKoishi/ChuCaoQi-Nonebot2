from typing import Dict, Tuple, Callable, Optional, Union
from dataclasses import dataclass
from collections import OrderedDict
from nonebot import on_message, logger
from nonebot.adapters import Bot
from nonebot.typing import T_State
from platform_context import get_context

_reply_command_handlers: Dict[str, Tuple[Callable, str]] = {}
_reply_preprocessors: Dict[str, Callable] = {}
_reply_duel_confirmations: Dict[int, dict] = {}
# 搜图存储结果：限制条数避免长期运行内存缓涨，先进先出
_MAX_STORED_RESULTS = 200
_reply_stored_results: "OrderedDict[str, dict]" = OrderedDict()
_reply_text_handlers: Dict[str, Tuple[Callable, str, bool]] = {}

_reply_main_handler = on_message(priority=10, block=False)


@dataclass
class ReplyCommandResult:
    # bytes 表示图片数据，由分发器按当前平台构造图片消息
    message: Union[str, bytes] = ''
    stored_id: Optional[dict] = None
    # 文本类 # 指令发送成功后回调，用于埋点等旁路逻辑；不得影响发送结果。
    on_sent: Optional[Callable] = None


def reply_command(command: str, preprocessor: Optional[Callable] = None):
    def decorator(func: Callable):
        _reply_command_handlers[command] = (func, func.__name__)
        if preprocessor:
            _reply_preprocessors[command] = preprocessor
        return func
    return decorator


def reply_text_command(command: str, with_args: bool = False):
    """注册文本类 # 指令；with_args=True 时把指令后文字作为第三个参数传给 handler"""
    def decorator(func: Callable):
        _reply_text_handlers[command] = (func, func.__name__, with_args)
        return func
    return decorator


def extract_reply_images(event) -> list:
    """提取所回复消息中的全部图片 URL（多图支持）

    #指令只处理所回复的消息：#消息本身仅作触发器，不入参解析。
    """
    quote = get_context(event).quote
    return list(quote.images) if quote else []


def extract_reply_content(event) -> Tuple[str, list]:
    """提取所回复消息的纯文本与全部图片 URL，供内容型 #指令（如 #chat）使用

    返回 (text, img_urls)；未回复消息时返回 ('', [])。
    不感知上层具体类型（如 chat 的 TextPart/ImagePart），保持依赖方向：
    reply_commands 不依赖具体业务内容结构。
    """
    quote = get_context(event).quote
    if not quote:
        return '', []
    return quote.text, list(quote.images)


def extract_reply_image(event) -> Optional[str]:
    """提取所回复消息中的第一张图片 URL"""
    urls = extract_reply_images(event)
    return urls[0] if urls else None


def extract_image_from_message(event) -> Optional[str]:
    """提取当前消息中的第一张图片 URL（回复时会把图副本附在当前#消息里）"""
    images = get_context(event).images
    return images[0] if images else None


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


def get_sent_message_id(sent) -> Optional[str]:
    """取发送返回的消息 ID：OneBot 为 dict['message_id']，QQ 官方为模型 id"""
    if sent is None:
        return None
    if isinstance(sent, dict):
        value = sent.get('message_id') or sent.get('id')
    else:
        value = getattr(sent, 'message_id', None) or getattr(sent, 'id', None)
    return str(value) if value is not None else None


async def _send(bot: Bot, event, ctx, message):
    """按当前平台发送：bytes 视作图片数据，其余原样交给适配器"""
    if isinstance(message, (bytes, bytearray)):
        message = ctx.build_image(bytes(message))
    return await bot.send(event=event, message=message)


@_reply_main_handler.handle()
async def handle_reply_command(bot: Bot, event, state: T_State):
    ctx = get_context(event, bot)
    if not ctx.quote:
        return

    # 取纯文本而非 str(Message)：str() 会带 CQ 码与转义，命令名和参数都会被污染
    message_text = ctx.text

    if not message_text.startswith('#'):
        return

    # 首个空白前为命令名，其后为参数文本（参数保持原样，不做 lower）
    parts = message_text[1:].strip().split(maxsplit=1)
    if not parts:
        return
    command = parts[0].lower()
    arg_text = parts[1].strip() if len(parts) > 1 else ''

    if command in _reply_text_handlers:
        handler, _, with_args = _reply_text_handlers[command]
        try:
            result = await (handler(event, bot, arg_text) if with_args else handler(event, bot))
            if isinstance(result, ReplyCommandResult):
                if result.message:
                    sent = await _send(bot, event, ctx, result.message)
                    if result.on_sent:
                        try:
                            result.on_sent(sent)
                        except Exception as exc:
                            logger.warning(f"reply_text_command on_sent callback failed for '{command}': {exc}")
            elif result:
                await _send(bot, event, ctx, result)
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
                await _send(bot, event, ctx, state_data)
            return

    handler = _reply_command_handlers[command][0]

    try:
        result = await handler(event, img_url, bot)

        if isinstance(result, ReplyCommandResult):
            if result.message:
                sent_msg = await _send(bot, event, ctx, result.message)
                message_id = get_sent_message_id(sent_msg)
                if result.stored_id is not None and message_id:
                    store_result(message_id, result.stored_id)
        elif isinstance(result, str):
            await _send(bot, event, ctx, result)
    except Exception as e:
        logger.error(f"reply_command handler error for '{command}': {e}")
        import traceback
        traceback.print_exc()