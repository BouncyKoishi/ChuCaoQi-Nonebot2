import re
import os
import glob
import random
import pytz
import shutil
import hashlib
from datetime import datetime
from urllib.request import urlretrieve

from nonebot import on_command, get_bot, logger
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg, Arg
from nonebot.adapters import Message
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageSegment as ms
from nonebot.exception import FinishedException, PausedException, RejectedException
from nonebot.typing import T_State

from kusa_base import plugin_config, is_super_admin
from multi_platform import send_reply, send_finish, get_user_id, is_group_message, is_onebot_v11_event
from utils import extractImgUrls, imgLocalPathToBase64


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
    "nczw": {"onlinePath": os.path.join(BASE_PIC_PATH, '鸟澄珠乌'), "displayName": "鸟澄珠乌"},
}

for value in archiveInfo.values():
    if os.path.exists(value['onlinePath']):
        value['onlineFilePaths'] = [f for f in glob.glob(os.path.join(value['onlinePath'], '*')) if os.path.isfile(f)]
        value['onlineFilePaths'].sort()
    else:
        value['onlineFilePaths'] = []

_pic_md5_set: set[str] = set()


def _compute_md5(file_path: str) -> str:
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def _build_md5_index():
    global _pic_md5_set
    _pic_md5_set = set()
    all_dirs = [EXAMINE_PATH, SAVE_PATH] + [v['onlinePath'] for v in archiveInfo.values()]
    total = 0
    for dir_path in all_dirs:
        if not os.path.exists(dir_path):
            continue
        for file_path in glob.glob(os.path.join(dir_path, '*')):
            if not os.path.isfile(file_path):
                continue
            try:
                _pic_md5_set.add(_compute_md5(file_path))
                total += 1
            except Exception as e:
                logger.warning(f'计算MD5失败: {file_path}, {e}')
    logger.info(f'图库MD5索引构建完成，共 {total} 张图片，{len(_pic_md5_set)} 个唯一MD5')


def _add_to_archive_paths(archive_key: str, file_path: str):
    if file_path not in archiveInfo[archive_key]['onlineFilePaths']:
        archiveInfo[archive_key]['onlineFilePaths'].append(file_path)
        archiveInfo[archive_key]['onlineFilePaths'].sort()


def _extract_ext_from_url(url: str) -> str:
    from urllib.parse import urlparse
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5 and ext.lstrip('.').isalnum():
        return ext
    return '.jpg'


def _download_and_check_dup(imgUrls: list[str], user_id) -> tuple[int, int]:
    os.makedirs(EXAMINE_PATH, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    success_count = 0
    duplicate_count = 0
    for i, url in enumerate(imgUrls):
        ext = _extract_ext_from_url(url)
        safeFilename = re.sub(r'[^\w\.-]', '_', f"pic_{i}") + ext
        newFilename = f'{user_id}-{timestamp}-{safeFilename}'
        file_path = os.path.join(EXAMINE_PATH, newFilename)
        try:
            urlretrieve(url, file_path)
            file_md5 = _compute_md5(file_path)
            if file_md5 in _pic_md5_set:
                os.remove(file_path)
                duplicate_count += 1
                logger.info(f'重复图片已拦截: {newFilename}, MD5: {file_md5}')
            else:
                _pic_md5_set.add(file_md5)
                success_count += 1
        except Exception as e:
            logger.error(f'下载图片失败: {e}')
    return success_count, duplicate_count


_build_md5_index()


def getExamineFiles():
    if os.path.exists(EXAMINE_PATH):
        return glob.glob(os.path.join(EXAMINE_PATH, '*'))
    return []


if scheduler:
    @scheduler.scheduled_job('cron', day='*', misfire_grace_time=500)
    async def dailyJunRunner():
        bot = get_bot()
        now = datetime.now(pytz.timezone('Asia/Shanghai'))
        paths = archiveInfo['jun']['onlineFilePaths']
        if not paths:
            return
        picPath = random.choice(paths)
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

    picPath = random.choice(paths)
    print(f'本次发送的图片：{picPath}')
    return imgLocalPathToBase64(picPath)


_ROLL_COMMANDS = [
    ('rolllj',       [],            'jun'),
    ('rollpurelj',   [],            'junOrigin'),
    ('rollxhb',      ['rollzh5'],   'xhb'),
    ('rolltd',       [],            'tudou'),
    ('rolljdm',      ['rollzdm', 'rollmd'], 'zundamon'),
    ('rollpurejdm',  ['rollpurezdm', 'rollpuremd'], 'zundamon2'),
    ('rollmmc',      ['rolllg'],    'pusheen'),
    ('rollgm',       [],            'cat'),
    ('roll251',      [],            '251'),
    ('rollxb',       [],            'xiba'),
    ('rollnczw',     ['rollhorou'], 'nczw'),
]

_roll_matchers = {}
for _cmd_name, _aliases, _archive_key in _ROLL_COMMANDS:
    _matcher = on_command(_cmd_name, aliases=set(_aliases) if _aliases else None, priority=5, block=True)

    @_matcher.handle()
    async def _roll_handler(bot: Bot, event: Event, _archive=_archive_key, _m=_matcher):
        result = await rollPic(event, _archive)
        if result:
            await send_finish(_m, result)

    _roll_matchers[_cmd_name] = _matcher


commitpic_cmd = on_command("commitpic", aliases={'commitlj', 'commitpurelj', 'commitxhb'}, priority=5, block=True)


@commitpic_cmd.handle()
async def handle_commitpic(event: Event, args: Message = CommandArg()):
    if not is_onebot_v11_event(event):
        await send_finish(commitpic_cmd, "该功能目前仅支持OneBot平台")
        return

    imgUrls = extractImgUrls(args)
    if imgUrls:
        success_count, duplicate_count = _download_and_check_dup(imgUrls, event.user_id)
        msg = f'上传完成：{success_count} 张成功'
        if duplicate_count > 0:
            msg += f'，{duplicate_count} 张重复已拦截'
        await send_finish(commitpic_cmd, msg)


@commitpic_cmd.got("image", prompt="请上传图片")
async def handle_commitpic_got(event: Event, image: Message = Arg()):
    try:
        imgUrls = extractImgUrls(image)
        if not imgUrls:
            await send_finish(commitpic_cmd, "非图片，取消本次上传")
            return

        success_count, duplicate_count = _download_and_check_dup(imgUrls, event.user_id)
        msg = f'上传完成：{success_count} 张成功'
        if duplicate_count > 0:
            msg += f'，{duplicate_count} 张重复已拦截'
        await send_finish(commitpic_cmd, msg)
    except (FinishedException, PausedException, RejectedException):
        raise
    except Exception as e:
        logger.error(f'handle_commitpic_got error: {e}')
        import traceback
        traceback.print_exc()


examinepic_cmd = on_command("examinepic", priority=5, block=True)


@examinepic_cmd.handle()
async def handle_examinepic(event: Event, state: T_State):
    if "examine_init" not in state:
        user_id = await get_user_id(event)

        if not await is_super_admin(user_id):
            await send_finish(examinepic_cmd, '该账号没有对应权限')
            return

        if not is_onebot_v11_event(event):
            await send_finish(examinepic_cmd, "该功能目前仅支持OneBot平台")
            return

        examineFiles = getExamineFiles()
        if not examineFiles:
            await send_finish(examinepic_cmd, '没有待审核图片')
            return

        state["examineFiles"] = examineFiles
        state["index"] = 0
        state["archive_keys"] = list(archiveInfo.keys())
        state["examine_init"] = True

        await send_reply(examinepic_cmd, f'开始审核，共有 {len(examineFiles)} 张待审核图片')

    try:
        examineFiles = state["examineFiles"]
        index = state["index"]
        archive_keys = state["archive_keys"]

        if index >= len(examineFiles):
            remainingCount = len(getExamineFiles())
            await send_finish(examinepic_cmd, f'审核结束，剩余 {remainingCount} 张待审核图片')
            return

        currentFile = examineFiles[index]

        if "examine_init" in state and state.get("_processed"):
            message = event.get_message()
            choice = message.extract_plain_text().strip().lower()

            if choice == 'q':
                remainingCount = len(getExamineFiles())
                await send_finish(examinepic_cmd, f'审核结束，剩余 {remainingCount} 张待审核图片')
                return

            if choice == 'd':
                try:
                    file_md5 = _compute_md5(currentFile)
                    _pic_md5_set.discard(file_md5)
                except Exception:
                    pass
                os.remove(currentFile)
                logger.info(f'已删除图片: {currentFile}')
            elif choice == 's':
                os.makedirs(SAVE_PATH, exist_ok=True)
                fileName = os.path.basename(currentFile)
                new_path = os.path.join(SAVE_PATH, fileName)
                shutil.move(currentFile, new_path)
                logger.info(f'已保存图片: {fileName}')
            elif choice == '0':
                pass
            elif choice.isdigit():
                archiveIndex = int(choice) - 1
                if 0 <= archiveIndex < len(archive_keys):
                    archiveKey = archive_keys[archiveIndex]
                    targetPath = archiveInfo[archiveKey]['onlinePath']
                    os.makedirs(targetPath, exist_ok=True)
                    fileName = os.path.basename(currentFile)
                    new_path = os.path.join(targetPath, fileName)
                    shutil.move(currentFile, new_path)
                    _add_to_archive_paths(archiveKey, new_path)
                    logger.info(f'已分类到 {archiveInfo[archiveKey]["displayName"]}: {fileName}')
            else:
                await examinepic_cmd.reject("无效选择，请重新输入")

            state["index"] = index + 1
            index = state["index"]

        state["_processed"] = True

        if index >= len(examineFiles):
            remainingCount = len(getExamineFiles())
            await send_finish(examinepic_cmd, f'审核结束，剩余 {remainingCount} 张待审核图片')
            return

        await send_reply(examinepic_cmd, imgLocalPathToBase64(examineFiles[index]))
        fileName = os.path.basename(examineFiles[index])
        archiveMenu = _build_archive_menu(archive_keys)
        await examinepic_cmd.reject(f'文件名: {fileName}\n{archiveMenu}\n请输入选择')
    except (FinishedException, PausedException, RejectedException):
        raise
    except Exception as e:
        logger.error(f'examinepic error: {e}')
        import traceback
        traceback.print_exc()
        await send_finish(examinepic_cmd, f'处理出错: {e}')


def _build_archive_menu(archive_keys):
    menu = "请进行图库分类：\n"
    for i, key in enumerate(archive_keys, 1):
        menu += f"{i}. {archiveInfo[key]['displayName']}\n"
    menu += "0. 跳过此图片\n"
    menu += "d. 删除此图片\n"
    menu += "s. 移动到保存目录\n"
    menu += "q. 退出审核"
    return menu
