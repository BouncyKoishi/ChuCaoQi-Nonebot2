import nonebot
from nonebot import on_request, get_bot, on_notice
from nonebot.adapters.onebot.v11 import (
    FriendRequestEvent, GroupRequestEvent,
    LifecycleMetaEvent
)
from kusa_base import config, send_log, is_super_admin, append_friend_list

friendHandleTimestamp = 0


# 处理加群请求
group_add_request = on_request(priority=5, block=True)

@group_add_request.handle()
async def handle_group_request(event: GroupRequestEvent):
    groupNum = event.group_id
    availableList = config['group']['adminAuthGroup']
    if groupNum not in availableList:
        return

    adder_qq = event.user_id
    bot = get_bot()
    st = f"{adder_qq}申请进群。加群备注为：\n" + event.comment
    await bot.send_group_msg(group_id=groupNum, message=st)
    await send_log(f'群聊{groupNum}:' + st)

    # 目前只对SYSU主群开启自动入群管理，其它群聊仅提示
    isSysu = groupNum == config['group']['sysu']
    if not isSysu:
        return

    if event.sub_type == 'add':
        if event.comment.strip() == '':
            # 原napcat实现中没有user2_id！这里是修改了napcat的源码后实现的
            # NoneBot2 中可能需要通过其他方式获取邀请人信息
            rejectReason = '请填写年级专业东方兴趣方向或说明来意' if isSysu else '加群备注不能为空'
            await bot.set_group_add_request(
                flag=event.flag,
                sub_type=event.sub_type,
                approve=False,
                reason=rejectReason,
            )
            await bot.send_group_msg(
                group_id=groupNum,
                message='备注信息为空，已自动拒绝加群申请。',
            )
            await send_log(f'群聊{groupNum}触发空备注风控，已拒绝{adder_qq}的申请')
            return
        for keyword in ('交流学习', '通过一下', '你好', '朋友推荐', ):
            if keyword in event.comment:
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
        try:
            strangerInfo = await bot.get_stranger_info(user_id=adder_qq)
            if 0 < strangerInfo['qqLevel'] < 8:
                await bot.set_group_add_request(
                    flag=event.flag,
                    sub_type=event.sub_type,
                    approve=False,
                    reason='触发风控，已自动拒绝加群申请',
                )
                await bot.send_group_msg(
                    group_id=groupNum,
                    message='触发等级风控，已自动拒绝加群申请。如有需要，请联系该用户通过邀请方式进群。',
                )
                await send_log(f'群聊{groupNum}触发等级风控（{strangerInfo["level"]}），已拒绝{adder_qq}的申请')
            if strangerInfo['qqLevel'] == 0:
                await bot.send_group_msg(
                    group_id=groupNum,
                    message='注意：该用户隐藏了QQ等级，请注意分辨。',
                )
        except Exception as e:
            print(f'获取陌生人信息失败：{e}')


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
    friendCode = getFriendAddCode(str(adderId))
    logInfo = f'收到一个来自{adderId}的好友申请，'
    if event.comment == friendCode:
        await event.approve()
        await send_log(logInfo + '已自动通过')
        await append_friend_list(str(adderId))
    else:
        await event.reject(reason='好友码错误，请向维护者申请好友码')
        await send_log(logInfo + '因好友码错误已自动拒绝')


def getFriendAddCode(friendId):
    hashingStr = friendId + 'confounding'
    return f'{hash(hashingStr) % 100000000 :0>8}'


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
from nonebot.params import CommandArg
from nonebot.adapters import Message

friend_code_cmd = on_command('friend_code', priority=5, block=True)

@friend_code_cmd.handle()
async def handle_friend_code(event: OneBotV11MessageEvent, args: Message = CommandArg()):
    userId = event.user_id
    if not await is_super_admin(userId):
        return
    qq_num = args.extract_plain_text().strip()
    friendCode = getFriendAddCode(qq_num)
    await friend_code_cmd.finish(f"此QQ号的FriendCode为: {friendCode}")
