"""
Scheduler 通知客户端（双腿 HTTP POST）

- notify_web(path, payload) → POST {backendUrl}/api/notify/*，由 backend 经 ws 推 Web 前端
- notify_qq(action, payload) → POST {botUrl}/internal/notify，由 bot 经 OneBot 发 QQ 消息

对齐 bot 侧现有通知模式：aiohttp + 5s 超时 + 失败仅记日志不阻塞（通知非关键路径）。
token 放 body（与 backend /internal/notify 现有鉴权方式一致）。
"""

import os
import logging

import aiohttp
import yaml

from core.config import PROJECT_ROOT

logger = logging.getLogger("scheduler.notifier")


def _load_config() -> dict:
    path = os.path.join(PROJECT_ROOT, 'config', 'scheduler.yaml')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()

BACKEND_URL = _config.get('backendUrl', 'http://127.0.0.1:8000')
BOT_URL = _config.get('botUrl', 'http://127.0.0.1:8082')
INTERNAL_API_TOKEN = _config.get('internalApiToken', '')


async def _post(url: str, payload: dict, label: str):
    """POST 并吞掉所有异常（通知失败仅记日志）"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    logger.error(f'{label}失败: HTTP {resp.status}')
    except Exception as e:
        logger.error(f'{label}失败: {e}')


async def notify_web(path: str, payload: dict):
    """推 Web 前端：path 为 backend 端点路径（如 /api/notify/kusa-harvested）"""
    await _post(f'{BACKEND_URL}{path}', payload, f'通知web端({path})')


async def notify_qq(action: str, payload: dict):
    """推 QQ 消息：action 为消息类型（如 send_group / send_private / kusa_harvested_event），
    由 bot/plugins/internal_notify.py 解析分发"""
    await _post(
        f'{BOT_URL}/internal/notify',
        {'token': INTERNAL_API_TOKEN, 'action': action, 'data': payload},
        f'通知bot({action})'
    )
