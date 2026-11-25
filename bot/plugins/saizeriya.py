"""
萨莉亚菜单插件 - NoneBot2 版本
根据预算随机生成萨莉亚点餐方案
菜单数据启动时从上游仓库拉取，之后每天更新一次
"""

from __future__ import annotations

import random
import typing

import httpx
from nonebot import get_driver, on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg

from kusa_base import plugin_config

try:
    from nonebot_plugin_apscheduler import scheduler
except ImportError:
    scheduler = None


MENU_URL = 'https://raw.githubusercontent.com/TransparentLC/saizeriya/refs/heads/master/src/saizeriya-menu/gd/menu.json'


class SaizeriyaMenuItem(typing.NamedTuple):
    id: int
    name: str
    price: int


# 菜单数据从上游仓库拉取后缓存在内存，拉取失败时保留上一次的数据
saizeriyaGDMenu: typing.Tuple[SaizeriyaMenuItem, ...] = ()
saizeriyaGDMenuPriceTotal = 0


async def refreshMenu() -> None:
    """从上游仓库拉取萨莉亚菜单并更新内存缓存"""
    global saizeriyaGDMenu, saizeriyaGDMenuPriceTotal
    proxy = plugin_config.get('web', {}).get('proxy', '')
    try:
        async with httpx.AsyncClient(proxy=proxy if proxy else None) as client:
            resp = await client.get(MENU_URL, timeout=20)
        if resp.status_code != 200:
            print(f'[萨莉亚] 菜单拉取失败，状态码: {resp.status_code}')
            return
        data = resp.json()
        menu = tuple(
            SaizeriyaMenuItem(id=int(item['id']), name=str(item['name']), price=int(item['price']))
            for item in data
        )
        if not menu:
            print('[萨莉亚] 菜单数据为空，保留原有数据')
            return
        saizeriyaGDMenu = menu
        saizeriyaGDMenuPriceTotal = sum(x.price for x in menu)
        print(f'[萨莉亚] 菜单已更新，共 {len(menu)} 项')
    except Exception as e:
        print(f'[萨莉亚] 菜单拉取异常: {e}')


@get_driver().on_startup
async def _startupRefreshMenu():
    await refreshMenu()


if scheduler:
    @scheduler.scheduled_job('cron', hour=5, minute=0, misfire_grace_time=600)
    async def _dailyRefreshMenu():
        await refreshMenu()


def rollMenu(budgetMin: int, budgetMax: int | None = None) -> str:
    if not saizeriyaGDMenu:
        return '菜单数据还没准备好，请稍后再试 ( ｡•́︿•̀｡ )'
    if budgetMax is None:
        budgetMax = budgetMin
    if budgetMin < 1:
        budgetMin = 1
    if budgetMax < 1:
        budgetMax = 1
    if budgetMin > budgetMax:
        budgetMin, budgetMax = budgetMax, budgetMin
    if budgetMax > 500:
        budgetMax = 500
    if budgetMin > 500:
        return '吃这么多，你是幽幽子吗 ( ｡╹ω╹｡ )'
    if budgetMax < min(x.price for x in saizeriyaGDMenu):
        return '这么点钱能吃啥啊 …_φ(･ω･` )'

    randomizedMenu = list(saizeriyaGDMenu)
    random.shuffle(randomizedMenu)

    budgetTried: set[int] = set()
    result: list[SaizeriyaMenuItem] = []

    for _ in range(64):
        if len(budgetTried) >= (budgetMax - budgetMin + 1) or len(result):
            break
        result = []

        while True:
            budget = random.randint(budgetMin, budgetMax)
            if budget not in budgetTried:
                break
        budgetTried.add(budget)

        if budget == saizeriyaGDMenuPriceTotal:
            result = randomizedMenu
        else:
            subset = [
                [False for _ in range(budget + 1)]
                for _ in range(len(randomizedMenu) + 1)
            ]

            for i in range(budget + 1):
                subset[0][i] = False
            for i in range(len(randomizedMenu) + 1):
                subset[i][0] = True
            for i in range(1, len(randomizedMenu) + 1):
                for j in range(1, budget + 1):
                    subset[i][j] = (
                        subset[i - 1][j]
                        if j < randomizedMenu[i - 1].price else
                        (subset[i - 1][j] or subset[i - 1][j - randomizedMenu[i - 1].price])
                    )
            if subset[len(randomizedMenu)][budget]:
                for i in range(len(randomizedMenu), -1, -1):
                    if subset[i][budget] and not subset[i - 1][budget]:
                        result.append(randomizedMenu[i - 1])
                        budget -= randomizedMenu[i - 1].price
                    if not budget:
                        break

    if not result:
        return '居然找不到符合要求的点餐方案……( >﹏<。)'
    result.sort(key=lambda x: x.id)
    return '\n'.join((
        f'你点了{len(result)}份菜',
        *(f'{x.id} {x.name} {x.price}元' for x in result),
        f'总消费：{sum(x.price for x in result)}元',
    ))


saizeriya_cmd = on_command("点餐", aliases={"saizeriya"}, priority=5, block=True)


@saizeriya_cmd.handle()
async def handle_saizeriya(args: Message = CommandArg()):
    strippedText = args.extract_plain_text().strip()
    if not strippedText:
        return
    try:
        if '-' in strippedText:
            budgetMin, budgetMax = map(int, strippedText.split('-'))
        else:
            budgetMin = budgetMax = int(strippedText)
    except ValueError:
        return
    result = rollMenu(budgetMin, budgetMax)
    await saizeriya_cmd.finish(result)
