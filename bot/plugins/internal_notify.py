"""
接收 scheduler 进程推送的内部通知端点

scheduler 的 A 类任务（G周期重置、每日工业、生草结算等）结算完成后，
经 HTTP POST 将消息事件推到本端点，由 bot 经 OneBot 发往 QQ。

鉴权：body 中 token 须与 config/backend.yaml 的 internalApiToken 一致；
端点随 bot 的 FastAPI 服务监听（127.0.0.1:8082），仅接受本机调用。
"""

import os

import yaml
import nonebot
from fastapi import Request
from fastapi.responses import JSONResponse

from kusa_base import send_group_msg, send_private_msg

from nonebot import logger

from core.config import PROJECT_ROOT


def _load_token() -> str:
    path = os.path.join(PROJECT_ROOT, 'config', 'backend.yaml')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get('internalApiToken', '')
    return ''


INTERNAL_API_TOKEN = _load_token()

# ==================== 消息动作分发 ====================

def _build_message(message):
    """将 JSON 消息转为 OneBot 消息对象

    message 为 str 时直接作为文本发送；
    为 dict 时支持 {'imageBase64': '<裸base64>'}（scheduler 端无 nonebot 依赖，只传原始数据）。
    """
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        from nonebot.adapters.onebot.v11 import MessageSegment
        if message.get('imageBase64'):
            return MessageSegment.image(f"base64://{message['imageBase64']}")
    return None


async def _handle_send_group(data: dict) -> bool:
    """发群消息：{groupId, message}"""
    group_id = data.get('groupId')
    message = _build_message(data.get('message'))
    if not group_id or message is None:
        return False
    await send_group_msg(group_id, message)
    return True


async def _handle_send_private(data: dict) -> bool:
    """发私聊消息：{userId, message}"""
    user_id = data.get('userId')
    message = _build_message(data.get('message'))
    if not user_id or message is None:
        return False
    await send_private_msg(user_id, message)
    return True


# 阶段 5 接入：生草完成事件 → 喜报/围殴激活/私聊提示
# TODO(阶段5): _handle_kusa_harvested_event


ACTION_HANDLERS = {
    'send_group': _handle_send_group,
    'send_private': _handle_send_private,
}


@nonebot.get_driver().on_startup
async def _mount_internal_notify():
    """在 bot 的 FastAPI 应用上挂载 /internal/notify 路由"""
    app = nonebot.get_app()
    token = INTERNAL_API_TOKEN

    async def internal_notify(request: Request):
        body = await request.json()

        # 仅接受本机调用（bot 的 FastAPI 只监听 127.0.0.1，此处再校验一次来源）
        client_host = request.client.host if request.client else ''
        if client_host not in ('127.0.0.1', '::1', 'localhost'):
            return JSONResponse({'success': False, 'error': 'Forbidden'}, status_code=403)

        if body.get('token') != token:
            return JSONResponse({'success': False, 'error': 'Invalid token'}, status_code=401)

        action = body.get('action')
        data = body.get('data') or {}

        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            return JSONResponse({'success': False, 'error': f'Unknown action: {action}'}, status_code=400)

        try:
            ok = await handler(data)
        except Exception as e:
            logger.error(f'处理内部通知失败 action={action}: {e}')
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

        if not ok:
            return JSONResponse({'success': False, 'error': 'Invalid payload'}, status_code=400)
        return {'success': True}

    app.router.add_api_route('/internal/notify', internal_notify, methods=['POST'])
    logger.info('[internal_notify] /internal/notify 端点已挂载')
