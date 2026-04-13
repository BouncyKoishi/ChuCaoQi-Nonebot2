import nonebot
from reloader import db_command as on_command
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message

import dbConnection.kusa_system as kusaDB
import dbConnection.work_order as orderDB
import dbConnection.user as userDB
from kusa_base import is_super_admin, send_private_msg
from multi_platform import send_reply, send_finish, get_user_id
from utils import nameDetailSplit


提交工单_cmd = on_command('提交工单', priority=5, block=True)


@提交工单_cmd.handle()
async def handle_提交工单(bot: Bot, event: Event, args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    user_id = await get_user_id(event)
    title, detail = nameDetailSplit(stripped_arg)
    
    if not title:
        await send_finish(提交工单_cmd, '至少需要一个工单标题！')
        return
    if len(title) > 128:
        await send_finish(提交工单_cmd, '标题太长啦！最多128字')
        return
    if detail and len(detail) > 1024:
        await send_finish(提交工单_cmd, '内容太长啦！最多1024字')
        return
    
    await orderDB.addWorkOrder(authorId=user_id, title=title, detail=detail)
    await send_finish(提交工单_cmd, '提交成功！等待开发者回复^ ^')


查看工单_cmd = on_command('查看工单', priority=5, block=True)


@查看工单_cmd.handle()
async def handle_查看工单(bot: Bot, event: Event):
    user_id = await get_user_id(event)
    
    if not await is_super_admin(user_id):
        await send_finish(查看工单_cmd, '目前仅供开发者使用^ ^')
        return

    workOrders = await orderDB.getUnreadWorkOrders()
    outputStr = ""
    if workOrders:
        for order in workOrders:
            kusa_user = await kusaDB.getKusaUser(order.authorId)
            unified_user = await userDB.getUnifiedUser(order.authorId)
            user_name = kusa_user.name if kusa_user and kusa_user.name else str(order.authorId)
            user_qq = unified_user.realQQ if unified_user else "未知"
            outputStr += f"[{order.id}]{order.title}"
            outputStr += f":{order.detail}\n" if order.detail else "\n"
            outputStr += f"提出者: {user_name}({user_qq})\n\n"
        outputStr = outputStr[:-2]
    else:
        outputStr = "没有，别追啦"
    await send_finish(查看工单_cmd, outputStr)


回复工单_cmd = on_command('回复工单', priority=5, block=True)


@回复工单_cmd.handle()
async def handle_回复工单(bot: Bot, event: Event, args: Message = CommandArg()):
    user_id = await get_user_id(event)
    
    if not await is_super_admin(user_id):
        await send_finish(回复工单_cmd, '仅供开发者使用^ ^')
        return

    stripped_arg = args.extract_plain_text().strip()
    args_list = stripped_arg.split(" ", 1)
    orderId, reply = args_list if len(args_list) == 2 else [None, None]
    
    if not orderId or not reply:
        await send_finish(回复工单_cmd, '参数异常，请自检^ ^')
        return

    order = await orderDB.getWorkOrderById(orderId)
    if not order:
        await send_finish(回复工单_cmd, '工单不存在^ ^')
        return
    
    notifyStr = f"开发者回复了你的工单[{order.title}]！\n"
    notifyStr += f"工单详情：{order.detail}\n" if order.detail else ""
    notifyStr += f"回复内容：{reply}"
    
    unified_user = await userDB.getUnifiedUser(order.authorId)
    if unified_user and unified_user.realQQ:
        await send_private_msg(unified_user.realQQ, notifyStr)
    
    await orderDB.replyWorkOrder(order, reply)
    await send_finish(回复工单_cmd, "回复成功^ ^")


删除所有工单_cmd = on_command('删除所有工单', priority=5, block=True)


@删除所有工单_cmd.handle()
async def handle_删除所有工单(bot: Bot, event: Event):
    user_id = await get_user_id(event)
    
    if not await is_super_admin(user_id):
        await send_finish(删除所有工单_cmd, '仅供开发者使用^ ^')
        return

    workOrders = await orderDB.getUnreadWorkOrders()
    if workOrders:
        for order in workOrders:
            await orderDB.replyWorkOrder(order, "---")
            unified_user = await userDB.getUnifiedUser(order.authorId)
            if unified_user and unified_user.realQQ:
                await send_private_msg(unified_user.realQQ, f"开发者删除了你的工单[{order.title}]！")
        await send_finish(删除所有工单_cmd, "已经全部删除^ ^")
    else:
        await send_finish(删除所有工单_cmd, "当前没有未回复的工单！")
