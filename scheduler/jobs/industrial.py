"""
A7 每日工业生产

批量结算逻辑已下沉到 core.services.IndustrialService.settle_all_daily()（阶段 4）。
本 job 只做：调服务结算 + 按 env 决定是否发群公告（经 notifier 推 bot）+ 发日志群。
"""

import logging

from core.config import plugin_config
from core.services import IndustrialService
from scheduler import notifier

logger = logging.getLogger("scheduler.jobs.industrial")


async def daily_industrial():
    """每日工业运作（0:00）"""
    result = await IndustrialService.settle_all_daily()

    env = plugin_config.get('env', 'dev')
    if env == 'prod':
        main_group = plugin_config.get('group', {}).get('main')
        await notifier.notify_qq('send_group', {
            'groupId': main_group,
            'message': result['signStr']
        })

    # 运行日志（对齐原 bot 侧 send_log：发往日志群，bot 侧的 print 由本日志替代）
    log_group = plugin_config.get('group', {}).get('log')
    if log_group:
        await notifier.notify_qq('send_group', {
            'groupId': log_group,
            'message': '所有每日工业运作完成！'
        })

    logger.info('所有每日工业运作完成！')


def register(scheduler):
    """注册每日工业任务（参数与原 bot 侧一致）"""
    scheduler.add_job(
        daily_industrial, 'cron',
        hour=0, misfire_grace_time=None,
        id='industrial_daily', name='A7 每日工业生产',
    )
