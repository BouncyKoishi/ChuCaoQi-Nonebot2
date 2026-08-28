"""
A 类定时任务注册（集中入口）

main.py 只调用 register_jobs()，各业务域任务在 jobs/ 下按插件对应关系拆分：
- farm.py:       A1 生草结算(阶段5) / A2 承载力基础恢复 / A3 非活跃承载力恢复
- item.py:       A4 限时物品清理
- gmarket.py:    A5 G值波动 / A6 G周期重置(阶段4，需通知通道)
- industrial.py: A7 每日工业生产(阶段4，需通知通道)
"""

import logging

from scheduler.jobs import farm, item, gmarket, industrial

logger = logging.getLogger("scheduler.jobs")


def register_jobs(scheduler):
    """向 AsyncIOScheduler 注册所有 A 类任务"""
    farm.register(scheduler)
    item.register(scheduler)
    gmarket.register(scheduler)
    industrial.register(scheduler)

    # TODO(阶段5): farm 增加 A1 生草结算注册
    logger.info("任务注册完成：farm(A2/A3) item(A4) gmarket(A5/A6) industrial(A7)")
