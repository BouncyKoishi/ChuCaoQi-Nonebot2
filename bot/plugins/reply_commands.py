from typing import Dict, Tuple, Callable, Optional, Union
from dataclasses import dataclass
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot
from nonebot.typing import T_State
from utils import extractImgUrls

_reply_command_handlers: Dict[str, Tuple[Callable, str]] = {}
_reply_preprocessors: Dict[str, Callable] = {}
_reply_duel_confirmations: Dict[int, dict] = {}
_reply_stored_results: Dict[str, dict] = {}
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


async def extract_reply_image(event) -> Optional[str]:
    if not hasattr(event, 'reply') or not event.reply:
        return None
    reply_message = event.reply
    if not reply_message:
        return None
    img_urls = extractImgUrls(str(reply_message))
    if not img_urls or len(img_urls) == 0:
        return None
    return img_urls[0]


async def extract_image_from_message(event) -> Optional[str]:
    message = event.get_message()
    img_urls = extractImgUrls(str(message))
    if img_urls and len(img_urls) > 0:
        return img_urls[0]
    return None


async def extract_image(event) -> Optional[str]:
    return await extract_image_from_message(event) or await extract_reply_image(event)


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
            print(f"reply_text_command handler error for '{command}': {e}")
            import traceback
            traceback.print_exc()
        return

    if command not in _reply_command_handlers:
        return

    img_url = await extract_image(event)
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
                if result.stored_id is not None:
                    if sent_msg and 'message_id' in sent_msg:
                        store_result(sent_msg['message_id'], result.stored_id)
                    elif sent_msg and isinstance(sent_msg, dict) and 'message_id' in sent_msg:
                        store_result(sent_msg['message_id'], result.stored_id)
            elif result.stored_id is not None:
                pass
        elif isinstance(result, str):
            await bot.send(event=event, message=result)
    except Exception as e:
        print(f"reply_command handler error for '{command}': {e}")
        import traceback
        traceback.print_exc()


def get_registered_commands():
    return list(_reply_command_handlers.keys())