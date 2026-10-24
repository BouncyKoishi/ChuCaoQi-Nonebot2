"""Soku 插件。

指令：/putgame IPv4:端口，将对局发布到 Konni。
该指令为服务器维护用的内部指令，仅白名单用户可用；
白名单在 config/plugin_config.yaml 的 soku.allowed_users 中配置（QQ 号列表），空列表表示不响应任何人。
"""

from ipaddress import IPv4Address
from typing import Optional, Tuple

import httpx
from nonebot import logger, on_command
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg

from core.config import plugin_config


KONNI_URL = "https://konni.delthas.fr/games"
# 服务端源码（konni/api.go）里 PUT /games 在没拿到结果时最多等 30 秒才返回，
# 这是上限不是常态；客户端留出余量，避免"已发布却报超时"
REQUEST_TIMEOUT = 35.0
USAGE = "用法：/putgame 180.213.164.55:10800（端口范围 1–65535）"

putgame = on_command("putgame", priority=5, block=True)

_soku_config = plugin_config.get('soku') or {}
_allowed_users = {
    str(user_id) for user_id in (_soku_config.get('allowed_users') or [])
}
_web_proxy = plugin_config.get('web', {}).get('proxy') or None

if not _allowed_users:
    logger.warning("soku: 未配置 soku.allowed_users，/putgame 不会响应任何用户")


def _parse_game_address(text: str) -> Optional[Tuple[str, int]]:
    """解析 IPv4:端口，非法输入返回 None。"""
    try:
        host_text, port_text = text.split(":")
        host = str(IPv4Address(host_text))
        if not port_text.isascii() or not port_text.isdecimal():
            return None
        port = int(port_text)
        if not 1 <= port <= 65535:
            return None
    except ValueError:
        return None
    return host, port


@putgame.handle()
async def handle_putgame(event: Event, args: Message = CommandArg()):
    user_id = event.get_user_id()
    if user_id not in _allowed_users:
        # 内部指令，非白名单用户静默忽略，只留日志
        logger.info(f"soku: 非白名单用户 {user_id} 尝试使用 /putgame，已忽略")
        return

    parsed = _parse_game_address(args.extract_plain_text().strip())
    if parsed is None:
        await putgame.finish(USAGE)
        return
    host, port = parsed

    payload = {"host": host, "port": port, "profile_name": "", "message": "ChuCaoQi IP Put"}
    logger.info(f"soku: 用户 {user_id} 发布 {host}:{port}，请求 {KONNI_URL} payload={payload}")
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT, proxy=_web_proxy
        ) as client:
            response = await client.put(KONNI_URL, json=payload)
    except httpx.RequestError as error:
        logger.warning(f"soku: 发布 {host}:{port} 请求失败：{error!r}")
        await putgame.finish("Konni 请求失败或超时，请稍后重试。")
        return

    if not response.is_success:
        # Konni 的失败原因都在响应体里，回显出来；截断防止代理错误页刷屏
        detail = response.text.strip()[:200]
        logger.warning(f"soku: 发布 {host}:{port} 失败：HTTP {response.status_code} {detail}")
        suffix = f"：{detail}" if detail else ""
        await putgame.finish(f"Konni 发布失败：HTTP {response.status_code}{suffix}")
        return

    logger.info(f"soku: 发布 {host}:{port} 成功：HTTP {response.status_code}")
    await putgame.finish(f"已推送到 Konni：{host}:{port}")
