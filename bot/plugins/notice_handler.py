import nonebot
from nonebot import on_request, get_bot, on_notice
from nonebot.adapters.onebot.v11 import (
    FriendRequestEvent, GroupRequestEvent,
    LifecycleMetaEvent, Bot
)
from kusa_base import plugin_config, send_log, is_super_admin, append_friend_list
from multi_platform import get_user_id
from core.services import identity_service

friendHandleTimestamp = 0


group_add_request = on_request(priority=5, block=True)

@group_add_request.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent):
    groupNum = event.group_id
    availableList = plugin_config['group']['adminAuthGroup']
    if groupNum not in availableList:
        return

    adder_qq = event.user_id
    st = f"{adder_qq}申请进群。加群备注为：" + event.comment
    await bot.send_group_msg(group_id=groupNum, message=st)
    await send_log(f'群聊{groupNum}:' + st)

    # 目前只对SYSU主群开启自动入群管理，其它群聊仅提示
    isSysu = groupNum == plugin_config['group']['sysu']
    if not isSysu:
        return

    if event.sub_type == 'add':
        comment = (event.comment or '').strip()

        # 注意：原版 NapCat 无法区分“用户主动申请”和“群员邀请他人后待审核”，
        # 后者同样上报为 sub_type='add' 且 comment 为空，因此其余风控只提示不拒绝。
        # 唯一会主动拒绝加群申请的规则：关键词风控（防广告号）
        for keyword in ('交流学习', '通过一下', '你好', '朋友推荐', ):
            if keyword in comment:
                await bot.set_group_add_request(
                    flag=event.flag,
                    sub_type=event.sub_type,
                    approve=False,
                    reason='触发风控，已自动拒绝加群申请',
                )
                await bot.send_group_msg(
                    group_id=groupNum,
                    message='触发关键词风控，已自动拒绝加群申请。如有需要，请联系该用户通过邀请方式进群。',
                )
                await send_log(f'群聊{groupNum}触发关键词风控（{keyword}），已拒绝{adder_qq}的申请')
                return

        # 以下风控仅群内提示并保留申请
        warnReasons = []
        if comment == '':
            warnReasons.append('未填写备注（可能是群员邀请后待审核）')
        try:
            strangerInfo = await bot.get_stranger_info(user_id=adder_qq)
            qqLevel = strangerInfo.get('qqLevel', strangerInfo.get('level'))
            if qqLevel is not None and 0 < qqLevel < 8:
                warnReasons.append(f'QQ等级较低（{qqLevel}级）')
            elif qqLevel == 0:
                warnReasons.append('隐藏了QQ等级')
        except Exception as e:
            print(f'获取陌生人信息失败：{e}')

        if warnReasons:
            reasonText = '、'.join(warnReasons)
            await bot.send_group_msg(
                group_id=groupNum,
                message=f'注意：{adder_qq} 的加群申请{reasonText}，请管理员人工确认。',
            )
            await send_log(f'群聊{groupNum}触发提示（{reasonText}），已保留{adder_qq}的申请，等待人工审核')


# 处理好友请求
friend_request = on_request(priority=5, block=True)

@friend_request.handle()
async def handle_friend_request(event: FriendRequestEvent):
    global friendHandleTimestamp
    # 因不明原因一次好友申请会收到多条消息，加个防抖
    import time
    if time.time() - friendHandleTimestamp < 2:
        return
    friendHandleTimestamp = time.time()

    adderId = event.user_id
    friendCode = identity_service.generate_friend_code(str(adderId))
    logInfo = f'收到一个来自{adderId}的好友申请，'
    if event.comment == friendCode:
        await event.approve()
        await send_log(logInfo + '已自动通过')
        await append_friend_list(str(adderId))
    else:
        await event.reject(reason='好友码错误，请向维护者申请好友码')
        await send_log(logInfo + '因好友码错误已自动拒绝')


# WebSocket 连接初始化 - 使用 LifecycleMetaEvent
from nonebot import on_metaevent

ws_connect = on_metaevent(priority=5, block=False)

@ws_connect.handle()
async def handle_meta_event(event: LifecycleMetaEvent):
    # 当 OneBot 连接建立时，初始化好友列表
    if event.sub_type == "connect":
        try:
            # 获取所有Bot，找到OneBot V11的Bot
            bots = nonebot.get_bots()
            onebot_v11_bot = None
            for bot_id, bot in bots.items():
                if hasattr(bot, 'get_friend_list'):
                    onebot_v11_bot = bot
                    break
            
            if not onebot_v11_bot:
                print(f'未找到支持好友列表的OneBot V11 Bot')
                return
            
            friendListInfo = await onebot_v11_bot.get_friend_list()
            friendListQQ = [str(friend['user_id']) for friend in friendListInfo]
            await append_friend_list(friendListQQ)
            print(f'OneBot V11 好友列表初始化完成，共{len(friendListQQ)}个好友')
        except Exception as e:
            print(f'好友列表初始化失败：{e}')


# 导入所需的模块
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.qq import MessageEvent as QQMessageEvent
from nonebot.params import CommandArg
from nonebot.adapters import Message
from typing import Union

friend_code_cmd = on_command('friend_code', priority=5, block=True)

@friend_code_cmd.handle()
async def handle_friend_code(event: Union[OneBotV11MessageEvent, QQMessageEvent], args: Message = CommandArg()):
    userId = await get_user_id(event)
    if not await is_super_admin(userId):
        return
    qq_num = args.extract_plain_text().strip()
    friendCode = getFriendAddCode(qq_num)
    await friend_code_cmd.finish(f"此QQ号的FriendCode为: {friendCode}")
