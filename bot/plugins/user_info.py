"""用户捐助信息插件

从 simple_commands 迁出的捐助相关指令。官机未绑定账号整插件禁止。
"""

import datetime

from nonebot.adapters import Message
from nonebot.params import CommandArg

from reloader import bound_db_command as on_command
from platform_context import Ctx
from multi_platform import send_finish
import core.db.kusa_system as db


thanks_cmd = on_command('THANKS', priority=5, block=True)


@thanks_cmd.handle()
async def handle_thanks(ctx: Ctx, args: Message = CommandArg()):
    user_id = await ctx.get_user_id()
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
async def handle_捐助记录(ctx: Ctx):
    user_id = await ctx.get_user_id()
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
