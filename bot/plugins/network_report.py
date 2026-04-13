import typing
import httpx
from datetime import datetime
from nonebot import on_command, get_bot
from nonebot.adapters import Bot, Event
from nonebot_plugin_apscheduler import scheduler
from kusa_base import plugin_config
from multi_platform import send_finish, is_onebot_v11_bot


class SysuNetworkReport(typing.NamedTuple):
    title: str
    time: datetime
    content: str

    def __str__(self) -> str:
        return '\n'.join((
            self.title,
            self.time.strftime('%Y-%m-%d %H:%M'),
            '=' * 24,
            self.content,
        ))


latestReport: SysuNetworkReport = None
ENV_PROD = (plugin_config.get('env', 'dev') == 'prod')


if scheduler:
    @scheduler.scheduled_job('cron', hour='8-23', minute='0', second='5', misfire_grace_time=120)
    async def getNetworkReportRunner():
        global latestReport
        if not ENV_PROD:
            return

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get('https://i.akarin.dev/sysu-network-report.json')
                r.raise_for_status()
                d: tuple[SysuNetworkReport, ...] = tuple(
                    SysuNetworkReport(
                        title=x['title'],
                        time=datetime.fromisoformat(x['time']),
                        content=x['content'],
                    )
                    for x in r.json()
                )

                bot = get_bot()
                # 仅在OneBot端进行主动推送
                if is_onebot_v11_bot(bot) and latestReport is not None:
                    for x in filter(lambda x: x.time > latestReport.time, d):
                        await send_group_msg_to_sysu(str(x))
                latestReport = max(d, key=lambda x: x.time)
        except Exception as e:
            print(f'获取网络报告失败: {e}')


    @scheduler.scheduled_job('cron', minute='0', hour='20', day='1-31/4', month='1,7', second='5', misfire_grace_time=120)
    async def vacationMentionRunner():
        if not ENV_PROD:
            return
        bot = get_bot()
        # 仅在OneBot端进行主动推送
        if is_onebot_v11_bot(bot):
            await send_group_msg_to_sysu('给网费按个暂停键！\n寒暑假将至，可以前往 https://netpay.sysu.edu.cn/ 自助办理个人网络服务的暂停和恢复。')


async def send_group_msg_to_sysu(message: str):
    bot = get_bot()
    sysu_group = plugin_config.get('group', {}).get('sysu')
    if not sysu_group:
        return
    
    await bot.send_group_msg(group_id=int(sysu_group), message=message)


校园网_cmd = on_command('校园网', priority=5, block=True)


@校园网_cmd.handle()
async def handle_校园网(bot: Bot, event: Event):
    if not ENV_PROD:
        await send_finish(校园网_cmd, '校园网公告同步功能在测试环境未开启。')
        return
    if latestReport is None:
        await send_finish(校园网_cmd, '暂无校园网公告信息。')
        return
    await send_finish(校园网_cmd, str(latestReport))
