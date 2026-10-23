"""Soku 插件。

指令：/putgame IPv4:端口，将对局发布到 Konni。
"""

from ipaddress import IPv4Address

import httpx
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg


KONNI_URL = "https://konni.delthas.fr/games"
putgame = on_command("putgame", priority=5, block=True)


@putgame.handle()
async def handle_putgame(args: Message = CommandArg()):
    try:
        host, port_text = args.extract_plain_text().strip().split(":")
        host = str(IPv4Address(host))
        if not port_text.isascii() or not port_text.isdecimal():
            raise ValueError("invalid port")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError("invalid port")
    except ValueError:
        await putgame.finish("用法：/putgame 180.213.164.55:10800（端口范围 1–65535）")
        return

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.put(
                KONNI_URL,
                json={"host": host, "port": port, "profile_name": "", "message": ""},
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        await putgame.finish(f"Konni 发布失败：HTTP {error.response.status_code}")
        return
    except httpx.RequestError:
        await putgame.finish("Konni 请求失败或超时，请稍后重试。")
        return

    await putgame.finish(f"已推送到 Konni：{host}:{port}")
