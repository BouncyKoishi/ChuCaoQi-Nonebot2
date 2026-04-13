"""
网易云音乐搜索插件 - NoneBot2 版本
"""

import json
import httpx
from urllib import parse
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message

from kusa_base import plugin_config


netease_music_cmd = on_command("music", priority=5, block=True)


@netease_music_cmd.handle()
async def handle_music(args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    if not stripped_arg:
        await netease_music_cmd.finish('未输入搜索内容。')
    
    music_info = await get_music_info_from_netease(stripped_arg, 0)
    await send_music_info(music_info)


async def get_music_info_from_netease(name: str, offset: int) -> dict:
    name_quote = parse.quote_plus(name)
    api_url = f'http://music.163.com/api/search/pc?s={name_quote}&offset={offset}&limit=1&type=1'
    
    web_config = plugin_config.get('web', {})
    headers = {
        'User-Agent': web_config.get('userAgent', 'Mozilla/5.0'),
        'Cookie': web_config.get('neteaseMusic', {}).get('cookie', '')
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers, timeout=10)
        return response.json()


async def send_music_info(info: dict):
    if info.get('code') != 200:
        await netease_music_cmd.finish('网易云查询服务异常。')
        return
    
    if 'songs' not in info.get('result', {}):
        await netease_music_cmd.finish('查无结果。')
        return
    
    song = info['result']['songs'][0]
    song_id = song['id']
    artist_name = song['artists'][0]['name']
    album_name = song['album']['name']
    
    url = f'https://music.163.com/#/song?id={song_id}'
    name = song['name']
    detail_info = f'艺术家：{artist_name}\n专辑：{album_name}'
    message = f'{url}\n曲名：{name}\n{detail_info}'
    await netease_music_cmd.finish(message)
