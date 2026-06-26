import os
import glob
import random
import pytz
from datetime import datetime

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
from services import pic_archive_service as pic_service
from services.pic_archive_service import ARCHIVE_INFO as archiveInfo


# bot 运行时维护的状态（web 端不共享，进程隔离）
SAVE_PATH = pic_service.get_save_path()
EXAMINE_PATH = pic_service.get_examine_path()

# 初始化各分类的 onlineFilePaths 缓存（rollPic 用，bot 特有）
for value in archiveInfo.values():
    if os.path.exists(value['onlinePath']):
        value['onlineFilePaths'] = [f for f in glob.glob(os.path.join(value['onlinePath'], '*')) if os.path.isfile(f)]
        value['onlineFilePaths'].sort()
    else:
        value['onlineFilePaths'] = []

_pic_md5_set: set[str] = set()


def _build_md5_index():
    """构建 MD5 索引到 bot 内存（commitpic 查重用）"""
    global _pic_md5_set
    _pic_md5_set, total = pic_service.build_md5_index()
    logger.info(f'图库MD5索引构建完成，共 {total} 张图片，{len(_pic_md5_set)} 个唯一MD5')


def _add_to_archive_paths(archive_key: str, file_path: str):
    """分类后更新 bot 的 onlineFilePaths 缓存（rollPic 用）"""
    if file_path not in archiveInfo[archive_key]['onlineFilePaths']:
        archiveInfo[archive_key]['onlineFilePaths'].append(file_path)
        archiveInfo[archive_key]['onlineFilePaths'].sort()


def _download_and_check_dup(imgUrls: list[str], user_id) -> tuple[int, int]:
    """下载图片并查重（复用 service 层，传入 bot 维护的 md5_set）"""
    global _pic_md5_set
    success_count, duplicate_count, _pic_md5_set = pic_service.download_and_check_dup(
        imgUrls, user_id, _pic_md5_set
    )
    if duplicate_count > 0:
        logger.info(f'本次上传拦截 {duplicate_count} 张重复图片')
    return success_count, duplicate_count


_build_md5_index()


def getExamineFiles():
    """获取待审核文件列表（兼容旧接口，复用 service 层路径）"""
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
    ('rollfumo',     [],            'fumo'),
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

            fileName = os.path.basename(currentFile)
            if choice == 'd':
                # 删除时同步从 bot 的 md5_set 移除
                try:
                    file_md5 = pic_service.compute_md5(currentFile)
                    _pic_md5_set.discard(file_md5)
                except Exception:
                    pass
                pic_service.delete_pic(fileName)
                logger.info(f'已删除图片: {currentFile}')
            elif choice == 's':
                pic_service.save_pic(fileName)
                logger.info(f'已保存图片: {fileName}')
            elif choice == '0':
                pass
            elif choice.isdigit():
                archiveIndex = int(choice) - 1
                if 0 <= archiveIndex < len(archive_keys):
                    archiveKey = archive_keys[archiveIndex]
                    pic_service.classify_pic(fileName, archiveKey)
                    # 更新 bot 的 onlineFilePaths 缓存（rollPic 用）
                    new_path = os.path.join(archiveInfo[archiveKey]['onlinePath'], fileName)
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
        fileSize = os.path.getsize(examineFiles[index])
        fileSizeStr = f'{fileSize / 1024:.1f}KB' if fileSize < 1024 * 1024 else f'{fileSize / 1024 / 1024:.1f}MB'
        archiveMenu = _build_archive_menu(archive_keys)
        await examinepic_cmd.reject(f'文件名: {fileName} ({fileSizeStr})\n{archiveMenu}\n请输入选择')
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
