"""
A4 限时物品清理
"""

import logging

import core.db.kusa_item as item_db

logger = logging.getLogger("scheduler.jobs.item")


async def clean_time_limited_items():
    """清理过期限时物品（每 50 秒）"""
    await item_db.cleanTimeLimitedItems()


def register(scheduler):
    """注册限时物品清理任务"""
    scheduler.add_job(
        clean_time_limited_items, 'interval',
        seconds=50, max_instances=10, misfire_grace_time=500,
        id='item_clean_time_limited', name='A4 限时物品清理',
    )
