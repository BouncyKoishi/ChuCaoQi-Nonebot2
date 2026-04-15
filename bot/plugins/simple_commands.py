import json
import codecs
import datetime
import numpy as np
from typing import cast
import dbConnection.kusa_system as db
from nonebot import on_command, get_bot
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message
from kusa_base import plugin_config
from urllib import request
from services import WarehouseService
from nonebot_plugin_apscheduler import scheduler
from multi_platform import (
    get_user_id,
    get_real_qq_by_event,
    get_group_id,
    is_group_message,
    is_onebot_v11_bot,
    send_finish,
)


help_cmd = on_command('help', priority=5, block=True)

@help_cmd.handle()
async def handle_help(bot: Bot, event: Event):
    with codecs.open(u'text/指令帮助.txt', 'r', 'utf-8') as f:
        await send_finish(help_cmd, f.read().strip())


生草系统_cmd = on_command('生草系统', priority=5, block=True)

@生草系统_cmd.handle()
async def handle_生草系统(bot: Bot, event: Event):
    with codecs.open(u'text/生草系统-指令帮助.txt', 'r', 'utf-8') as f:
        await send_finish(生草系统_cmd, f.read().strip())


公告_cmd = on_command('公告', priority=5, block=True)

@公告_cmd.handle()
async def handle_公告(bot: Bot, event: Event):
    with codecs.open(u'text/公告.txt', 'r', 'utf-8') as f:
        await send_finish(公告_cmd, f.read().strip())


晚安_cmd = on_command('晚安', priority=5, block=True)

@晚安_cmd.handle()
async def handle_晚安(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(晚安_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'晚安！你获得的睡眠时间：'
    await sleep(bot, event, msg, 400, 50, 1)


午睡_cmd = on_command('午睡', priority=5, block=True)

@午睡_cmd.handle()
async def handle_午睡(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(午睡_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'午安！你获得的睡眠时间：'
    await sleep(bot, event, msg, 60, 10, 1)


醒了_cmd = on_command('醒了', priority=5, block=True)

@醒了_cmd.handle()
async def handle_醒了(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(醒了_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'你可以睡个回笼觉。你获得的睡眠时间：'
    await sleep(bot, event, msg, 60, 10, 1)


async def sleep(bot: Bot, event: Event, msg, base, summa, size):
    allow_list = plugin_config.get('group', {}).get('adminAuthGroup', [])
    group_id = get_group_id(event)
    user_qq = await get_real_qq_by_event(event)
    
    if not group_id or not user_qq:
        return
    
    group_id_int = int(group_id)
    if is_onebot_v11_bot(bot) and group_id_int in allow_list:
        durTime = sleepTimeCalculation(base, summa, size)
        msg += f'{durTime}sec！'
        from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
        onebot_bot = cast(OneBotV11Bot, bot)
        await onebot_bot.set_group_ban(group_id=group_id_int, user_id=int(user_qq), duration=durTime)
        await onebot_bot.send_group_msg(group_id=group_id_int, message=msg)
    elif not is_onebot_v11_bot(bot):
        msg += '该功能仅在OneBot平台可用'
        await send_finish(晚安_cmd, msg)


def sleepTimeCalculation(base, summa, size):
    x = np.random.uniform(size=size)
    y = np.random.uniform(size=size)
    z = np.sqrt(-2 * np.log(x)) * np.cos(2 * np.pi * y)
    dur_time_min = base + float(z[0]) * summa
    return int(dur_time_min * 60)


thanks_cmd = on_command('THANKS', priority=5, block=True)

@thanks_cmd.handle()
async def handle_thanks(bot: Bot, event: Event, args: Message = CommandArg()):
    user_id = await get_user_id(event)
    if not user_id:
        return
    
    # 从命令参数中获取年份
    year_str = args.extract_plain_text().strip()
    year = year_str if year_str and year_str.isdigit() and 2020 <= int(year_str) <= 2099 else None
    donateAmount = await db.getDonateAmount(int(user_id))
    output = ''

    if donateAmount > 0:
        output += '感谢您对生草系统的支援！\n'
        output += f"您的累计捐助金额为：{donateAmount:.2f}元\n"
        if year:
            thisYearAmount = await db.getDonateAmount(int(user_id), year)
            output += f"您的{year}年度捐助金额为：{thisYearAmount}元\n" if thisYearAmount > 0 else ''
        output += '若需要查询您的所有捐助记录，请使用【!捐助记录】指令\n\n'

    output += '感谢所有生草系统的资助者！\n'
    donateRank = await db.getDonateRank(year=year)

    if len(donateRank) == 0:
        output += f'{year}年度暂无捐助信息= ='
        await send_finish(thanks_cmd, output)
        return
    output += f'以下是{year}年度的捐助信息' if year else '以下是累计捐助信息'
    output += f'(篇幅较长，仅展示前25条)：\n' if len(donateRank) > 25 else '：\n'

    nameList = await db.getNameListByKusaUserId(list(donateRank.keys()))
    for userId, amount in list(donateRank.items())[:25]:
        displayName = nameList.get(userId, str(userId))
        output += f'{displayName}：{amount:.2f}元\n'
    await send_finish(thanks_cmd, output[:-1])


捐助记录_cmd = on_command('捐助记录', aliases={'捐赠记录'}, priority=5, block=True)

@捐助记录_cmd.handle()
async def handle_捐助记录(bot: Bot, event: Event):
    user_id = await get_user_id(event)
    if not user_id:
        return
    
    output = ''
    donateRecords = await db.getDonateRecords(int(user_id))
    if not donateRecords:
        output += '您还没有捐助记录哦~'
    else:
        output += '您的捐助记录如下：\n'
        for record in donateRecords:
            output += f"{record.donateDate}：{record.amount:.2f}元\n"
    await send_finish(捐助记录_cmd, output[:-1])


爆柠檬_cmd = on_command('爆柠檬', priority=5, block=True)

@爆柠檬_cmd.handle()
async def handle_爆柠檬(bot: Bot, event: Event):
    await send_finish(爆柠檬_cmd, '🍋')


timestamp_cmd = on_command('timestamp', priority=5, block=True)

@timestamp_cmd.handle()
async def handle_timestamp(bot: Bot, event: Event):
    await send_finish(timestamp_cmd, str(datetime.datetime.now().timestamp()))


if scheduler:
    @scheduler.scheduled_job('cron', day='*', hour='9', minute='0', second='10', misfire_grace_time=500)
    async def read60sRunner():
        msg = await get60sNewsPic()
        bot = get_bot()
        for qq_group in plugin_config.get('sendNews', {}).get('group', []):
            try:
                if is_onebot_v11_bot(bot):
                    from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
                    onebot_bot = cast(OneBotV11Bot, bot)
                    await onebot_bot.send_group_msg(group_id=qq_group, message=msg)
            except Exception as e:
                print(f'发送新闻到群{qq_group}失败：{e}')


news_cmd = on_command('news', priority=5, block=True)

@news_cmd.handle()
async def handle_news(bot: Bot, event: Event):
    msg = await get60sNewsPic()
    await send_finish(news_cmd, msg)


async def get60sNewsPic():
    url = "https://api.2xb.cn/zaob"
    http_req = request.Request(url)
    http_req.add_header('User-Agent', plugin_config.get('web', {}).get('userAgent', ''))
    with request.urlopen(http_req) as req:
        data = req.read().decode('utf-8')
        data = ''.join(x for x in data if x.isprintable())
        retData = json.loads(data)
        lst = retData['imageUrl']
        try:
            # 尝试导入 OneBot 的 MessageSegment
            from nonebot.adapters.onebot.v11 import MessageSegment as MS
            return MS.image(lst)
        except ImportError:
            # QQ 官方平台暂时不支持图片
            return lst
