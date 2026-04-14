import re
import os
import glob
import random
import pytz
from datetime import datetime
from urllib.request import urlretrieve
from typing import Optional

from nonebot import on_command, get_bot
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageSegment as ms

from kusa_base import plugin_config, is_super_admin
from multi_platform import send_reply, send_finish, get_user_id, is_group_message, is_onebot_v11_event, build_at_message
from utils import extractImgUrls, imgLocalPathToBase64, nameDetailSplit


BASE_PIC_PATH = os.path.join(plugin_config.get('basePath', ''), 'picArchive')
SAVE_PATH = os.path.join(BASE_PIC_PATH, '私藏')
EXAMINE_PATH = os.path.join(BASE_PIC_PATH, '待分类')

archiveInfo = {
    "jun": {"onlinePath": os.path.join(BASE_PIC_PATH, 'jun', 'online'), "displayName": "罗俊"},
    "junOrigin": {"onlinePath": os.path.join(BASE_PIC_PATH, 'jun', 'origin'), "displayName": "纯净罗俊"},
    "xhb": {"onlinePath": os.path.join(BASE_PIC_PATH, 'xhb'), "displayName": "xhb"},
    "tudou": {"onlinePath": os.path.join(BASE_PIC_PATH, '土豆泥'), "displayName": "土豆"},
    "zundamon": {"onlinePath": os.path.join(BASE_PIC_PATH, '豆包2.0'), "displayName": "俊达萌"},
    "zundamon2": {"onlinePath": os.path.join(BASE_PIC_PATH, '豆包'), "displayName": "俊达萌美图"},
    "pusheen": {"onlinePath": os.path.join(BASE_PIC_PATH, 'libmmc'), "displayName": "猫猫虫"},
    "cat": {"onlinePath": os.path.join(BASE_PIC_PATH, 'cat'), "displayName": "怪猫"},
    "251": {"onlinePath": os.path.join(BASE_PIC_PATH, '251图库'), "displayName": "251"},
    "xiba": {"onlinePath": os.path.join(BASE_PIC_PATH, '西八兔子图库'), "displayName": "西八兔"},
}

for value in archiveInfo.values():
    if os.path.exists(value['onlinePath']):
        value['onlineFilePaths'] = glob.glob(os.path.join(value['onlinePath'], '*.*'))
        value['onlineFilePaths'].sort()
    else:
        value['onlineFilePaths'] = []


def getExamineFiles():
    if os.path.exists(EXAMINE_PATH):
        return glob.glob(os.path.join(EXAMINE_PATH, '*.*'))
    return []


if scheduler:
    @scheduler.scheduled_job('cron', day='*', misfire_grace_time=500)
    async def dailyJunRunner():
        bot = get_bot()
        now = datetime.now(pytz.timezone('Asia/Shanghai'))
        paths = archiveInfo['jun']['onlineFilePaths']
        if not paths:
            return
        picPath = paths[int(random.random() * len(paths))]
        st = f'新的一天！今天是{now.year}年{now.month}月{now.day}日！今天的精选罗俊是——'
        
        sysu_group = plugin_config.get('group', {}).get('sysu')
        if sysu_group:
            from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
            from typing import cast
            onebot_bot = cast(OneBotV11Bot, bot)
            await onebot_bot.send_group_msg(group_id=int(sysu_group), message=st)
            await onebot_bot.send_group_msg(group_id=int(sysu_group), message=imgLocalPathToBase64(picPath))


async def rollPic(event: Event, imageArchiveName: str):
    if not is_group_message(event):
        return None
    
    if not is_onebot_v11_event(event):
        return "该功能目前仅支持OneBot平台"
    
    imageArchive = archiveInfo.get(imageArchiveName)
    if not imageArchive:
        return None
    
    paths = imageArchive['onlineFilePaths']
    if not paths:
        return f'{imageArchive["displayName"]} 图库为空'
    
    picPath = paths[int(random.random() * len(paths))]
    print(f'本次发送的图片：{picPath}')
    return imgLocalPathToBase64(picPath)


rolllj_cmd = on_command('rolllj', priority=5, block=True)


@rolllj_cmd.handle()
async def handle_rolllj(bot: Bot, event: Event):
    result = await rollPic(event, "jun")
    if result:
        await send_finish(rolllj_cmd, result)


rollpurelj_cmd = on_command('rollpurelj', priority=5, block=True)


@rollpurelj_cmd.handle()
async def handle_rollpurelj(bot: Bot, event: Event):
    result = await rollPic(event, "junOrigin")
    if result:
        await send_finish(rollpurelj_cmd, result)


rollxhb_cmd = on_command('rollxhb', priority=5, block=True)


@rollxhb_cmd.handle()
async def handle_rollxhb(bot: Bot, event: Event):
    result = await rollPic(event, "xhb")
    if result:
        await send_finish(rollxhb_cmd, result)


rolltd_cmd = on_command('rolltd', priority=5, block=True)


@rolltd_cmd.handle()
async def handle_rolltd(bot: Bot, event: Event):
    result = await rollPic(event, "tudou")
    if result:
        await send_finish(rolltd_cmd, result)


rolljdm_cmd = on_command('rolljdm', aliases={'rollzdm', 'rollmd'}, priority=5, block=True)


@rolljdm_cmd.handle()
async def handle_rolljdm(bot: Bot, event: Event):
    result = await rollPic(event, "zundamon")
    if result:
        await send_finish(rolljdm_cmd, result)


rollpurejdm_cmd = on_command('rollpurejdm', aliases={'rollpurezdm', 'rollpuremd'}, priority=5, block=True)


@rollpurejdm_cmd.handle()
async def handle_rollpurejdm(bot: Bot, event: Event):
    result = await rollPic(event, "zundamon2")
    if result:
        await send_finish(rollpurejdm_cmd, result)


rollmmc_cmd = on_command('rollmmc', aliases={'rolllg',}, priority=5, block=True)


@rollmmc_cmd.handle()
async def handle_rollmmc(bot: Bot, event: Event):
    result = await rollPic(event, "pusheen")
    if result:
        await send_finish(rollmmc_cmd, result)


rollgm_cmd = on_command('rollgm', priority=5, block=True)


@rollgm_cmd.handle()
async def handle_rollgm(bot: Bot, event: Event):
    result = await rollPic(event, "cat")
    if result:
        await send_finish(rollgm_cmd, result)


roll251_cmd = on_command('roll251', priority=5, block=True)


@roll251_cmd.handle()
async def handle_roll251(bot: Bot, event: Event):
    result = await rollPic(event, "251")
    if result:
        await send_finish(roll251_cmd, result)


rollxb_cmd = on_command('rollxb', priority=5, block=True)


@rollxb_cmd.handle()
async def handle_rollxb(bot: Bot, event: Event):
    result = await rollPic(event, "xiba")
    if result:
        await send_finish(rollxb_cmd, result)


commitpic_cmd = on_command("commitpic", aliases={'commitlj', 'commitpurelj', 'commitxhb'}, priority=5, block=True)


@commitpic_cmd.handle()
async def handle_commitpic(bot: Bot, event: Event, args: Message = CommandArg()):
    if not is_onebot_v11_event(event):
        await send_finish(commitpic_cmd, "该功能目前仅支持OneBot平台")
        return
    
    user_id = event.user_id
    await send_reply(commitpic_cmd, await build_at_message(event, user_id, '请上传图片'))
    
    stripped_arg = args.extract_plain_text().strip()
    if stripped_arg:
        imgUrls = extractImgUrls(stripped_arg)
        if not imgUrls:
            await send_finish(commitpic_cmd, "非图片，取消本次上传")
            return
        
        os.makedirs(EXAMINE_PATH, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        for i, url in enumerate(imgUrls):
            safeFilename = re.sub(r'[^\w\.-]', '_', f"pic_{i}")
            newFilename = f'{user_id}-{timestamp}-{safeFilename}'
            try:
                urlretrieve(url, os.path.join(EXAMINE_PATH, newFilename))
            except Exception as e:
                print(f'下载图片失败: {e}')
        await send_finish(commitpic_cmd, '上传成功，等待加入图库')


examinepic_cmd = on_command("examinepic", priority=5, block=True)


@examinepic_cmd.handle()
async def handle_examinepic(bot: Bot, event: Event):
    user_id = await get_user_id(event)
    
    if not await is_super_admin(user_id):
        await send_finish(examinepic_cmd, '该账号没有对应权限')
        return
    
    if not is_onebot_v11_event(event):
        await send_finish(examinepic_cmd, "该功能目前仅支持OneBot平台")
        return
    
    examineFiles = getExamineFiles()
    await send_reply(examinepic_cmd, f'开始审核，共有 {len(examineFiles)} 张待审核图片')

    archiveMenu = "请进行图库分类：\n"
    archive_keys = list(archiveInfo.keys())
    for i, key in enumerate(archive_keys, 1):
        archiveMenu += f"{i}. {archiveInfo[key]['displayName']}\n"
    archiveMenu += "0. 跳过此图片\n"
    archiveMenu += "d. 删除此图片\n"
    archiveMenu += "s. 移动到保存目录\n"
    archiveMenu += "q. 退出审核"

    index = 0
    while index < len(examineFiles):
        currentFile = examineFiles[index]

        await send_reply(examinepic_cmd, imgLocalPathToBase64(currentFile))

        try:
            fileName = os.path.basename(currentFile)
            prompt = f'文件名: {fileName}\n{archiveMenu}\n请输入选择'
            
            await send_reply(examinepic_cmd, prompt)
            return

        except Exception as e:
            await send_reply(examinepic_cmd, f'处理时出现错误: {e}')
            index += 1
            continue

    remainingCount = len(getExamineFiles())
    await send_finish(examinepic_cmd, f'审核结束，剩余 {remainingCount} 张待审核图片')
