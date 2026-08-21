import json
import codecs
import os
import datetime
import numpy as np
from typing import cast
import core.db.kusa_system as db
from nonebot import on_command, get_bot
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.consts import PREFIX_KEY, CMD_ARG_KEY
from nonebot.typing import T_State
from kusa_base import plugin_config, is_super_admin, send_group_msg
from core.config import RESOURCE_DIR
from urllib import request
from nonebot_plugin_apscheduler import scheduler
from multi_platform import (
    get_user_id,
    get_real_qq_by_event,
    get_group_id,
    is_group_message,
    is_onebot_v11_bot,
    send_finish,
    get_napcat_bot,
)


help_cmd = on_command('help', priority=5, block=True)

@help_cmd.handle()
async def handle_help(bot: Bot, event: Event):
    with codecs.open(os.path.join(RESOURCE_DIR, 'text', '指令帮助.txt'), 'r', 'utf-8') as f:
        await send_finish(help_cmd, f.read().strip())


生草系统_cmd = on_command('生草系统', priority=5, block=True)

@生草系统_cmd.handle()
async def handle_生草系统(bot: Bot, event: Event):
    with codecs.open(os.path.join(RESOURCE_DIR, 'text', '生草系统-指令帮助.txt'), 'r', 'utf-8') as f:
        await send_finish(生草系统_cmd, f.read().strip())


公告_cmd = on_command('公告', priority=5, block=True)

@公告_cmd.handle()
async def handle_公告(bot: Bot, event: Event):
    with codecs.open(os.path.join(RESOURCE_DIR, 'text', '公告.txt'), 'r', 'utf-8') as f:
        await send_finish(公告_cmd, f.read().strip())


晚安_cmd = on_command('晚安', priority=5, block=True)

@晚安_cmd.handle()
async def handle_晚安(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(晚安_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'晚安！你获得的睡眠时间：'
    await sleep(晚安_cmd, bot, event, msg, 400, 50, 1)


午睡_cmd = on_command('午睡', priority=5, block=True)

@午睡_cmd.handle()
async def handle_午睡(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(午睡_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'午安！你获得的睡眠时间：'
    await sleep(午睡_cmd, bot, event, msg, 60, 10, 1)


醒了_cmd = on_command('醒了', priority=5, block=True)

@醒了_cmd.handle()
async def handle_醒了(bot: Bot, event: Event):
    if not is_group_message(event):
        await send_finish(醒了_cmd, '该指令只能在群聊中使用^ ^')
        return
    msg = f'你可以睡个回笼觉。你获得的睡眠时间：'
    await sleep(醒了_cmd, bot, event, msg, 60, 10, 1)


async def sleep(matcher, bot: Bot, event: Event, msg, base, summa, size):
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
        try:
            await onebot_bot.set_group_ban(group_id=group_id_int, user_id=int(user_qq), duration=durTime)
        except Exception as e:
            print(f'禁言失败: {e}')
        await send_finish(matcher, msg)
    elif not is_onebot_v11_bot(bot):
        msg += '该功能仅在OneBot平台可用'
        await send_finish(matcher, msg)


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
    
    # 从命令参数中获取年份或ALL
    year_str = args.extract_plain_text().strip()
    current_year = str(datetime.datetime.now().year)
    if year_str.upper() == 'ALL':
        year = None
    elif year_str and year_str.isdigit() and 2020 <= int(year_str) <= 2099:
        year = year_str
    else:
        year = current_year
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
    output += f'以下是{year}年度的捐助信息' if year else '以下是全部累计捐助信息'
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


# ============================================================
# 推送功能（仅超级管理员可用）
# !推送 <内容>：将指令后的文字/图片等消息内容原样推送至指定群聊
# 默认目标群为 log 发送群，二次确认时可输入新群号切换并重复确认
# ============================================================

# 推送会话管理：session_id -> {"job": APScheduler Job, "bot": Bot, "event": Event}
_push_sessions = {}
_PUSH_CONFIRM_TIMEOUT = 120  # 二次确认超时秒数


def _push_clear_session(session_id: str):
    """清理推送会话及其超时任务"""
    info = _push_sessions.pop(session_id, None)
    if info:
        job = info.get("job")
        try:
            if job and job.next_run_time:
                job.remove()
        except Exception:
            pass


def _push_arm_timeout(session_id: str, bot: Bot, event: Event):
    """（重新）武装二次确认超时任务并登记会话"""
    _push_clear_session(session_id)
    job = scheduler.add_job(
        _push_timeout_cancel, "date",
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=_PUSH_CONFIRM_TIMEOUT),
        args=[session_id],
    )
    _push_sessions[session_id] = {"job": job, "bot": bot, "event": event}


def _push_end_session(session_id: str, state: T_State):
    """结束推送会话：清理超时任务与会话标记"""
    _push_clear_session(session_id)
    state.pop("push_state", None)


async def _push_timeout_cancel(session_id: str):
    """二次确认超时：通知用户并结束本次推送会话"""
    info = _push_sessions.pop(session_id, None)
    if not info:
        return
    try:
        await info["bot"].send(
            info["event"], '推送超时，已取消本次推送，如需推送请重新发起 !推送'
        )
    except Exception as e:
        print(f'推送超时通知失败: {e}')


推送_cmd = on_command('推送', priority=5, block=True)


@推送_cmd.handle()
async def handle_推送(bot: Bot, event: Event, state: T_State):
    # 首次发起推送
    if "push_state" not in state:
        user_id = await get_user_id(event)
        if not user_id or not await is_super_admin(user_id):
            return  # 非超级管理员静默忽略

        # 从 state 读取命令参数（首轮由 TrieRule 解析写入）
        args = state.get(PREFIX_KEY, {}).get(CMD_ARG_KEY) or Message()
        plain_text = args.extract_plain_text().strip()
        has_image = any(getattr(seg, 'type', '') == 'image' for seg in args)
        if not plain_text and not has_image:
            await send_finish(推送_cmd, '请输入要推送的内容')
            return

        log_group = plugin_config.get('group', {}).get('log', 0)
        if not log_group:
            await send_finish(推送_cmd, '未配置 log 发送群，无法推送')
            return

        # 存储推送内容与默认目标群（log 发送群）
        state["push_state"] = True
        state["push_content"] = args
        state["push_target"] = str(log_group)

        # 获取 bot 所在的群集合，用于切换群号时校验（获取失败则跳过校验）
        valid_groups = None
        napcat_bot = get_napcat_bot()
        if napcat_bot:
            try:
                group_list = await napcat_bot.get_group_list()
                valid_groups = {str(g['group_id']) for g in group_list}
            except Exception:
                valid_groups = None
        state["push_valid_groups"] = valid_groups

        # 登记会话并启动超时
        _push_arm_timeout(event.get_session_id(), bot, event)

        await 推送_cmd.reject(f'你的消息将被推送至群聊{log_group}，确认？[y/n/切换群号]')
        return

    # 二次确认阶段（reject 回环重入本函数）
    session_id = event.get_session_id()

    # 超时或已结束的会话不再处理
    if session_id not in _push_sessions:
        _push_end_session(session_id, state)
        await send_finish(推送_cmd, '本次推送已超时或已取消，如需推送请重新发起 !推送')
        return

    # 重新武装超时（每次确认提示获得一轮新的等待窗口）
    _push_arm_timeout(session_id, bot, event)

    content = state.get("push_content")
    target_group = state.get("push_target")
    valid_groups = state.get("push_valid_groups")

    reply_text = event.get_plaintext().strip().lower()
    if reply_text in ('y', 'yes', '是'):
        _push_end_session(session_id, state)
        ok = await send_group_msg(target_group, content)
        if not ok:
            await send_finish(推送_cmd, f'推送失败：无法将消息发送至群聊{target_group}')
        await 推送_cmd.finish()  # 推送成功，静默
    elif reply_text in ('n', 'no', '否'):
        _push_end_session(session_id, state)
        await send_finish(推送_cmd, '已取消推送')
    elif reply_text.isdigit():
        if valid_groups is None or reply_text in valid_groups:
            state["push_target"] = reply_text
            await 推送_cmd.reject(f'你的消息将被推送至群聊{reply_text}，确认？[y/n/切换群号]')
        else:
            await 推送_cmd.reject(
                f'bot 不在群聊{reply_text}中，无法推送。当前目标群仍为{target_group}，确认？[y/n/切换群号]'
            )
    else:
        await 推送_cmd.reject(
            f'无法识别的输入，你的消息仍将推送至群聊{target_group}，确认？[y/n/切换群号]'
        )
