"""
A 类定时任务注册（集中入口）

main.py 只调用 register_jobs()，各业务域任务在 jobs/ 下按插件对应关系拆分：
- farm.py:       A1 生草结算 / A2 承载力基础恢复 / A3 非活跃承载力恢复
- item.py:       A4 限时物品清理
- gmarket.py:    A5 G值波动 / A6 G周期重置(23:45) + 重置总结(23:50)
- industrial.py: A7 每日工业生产
"""

import logging

logger = logging.getLogger("scheduler.jobs")


def register_jobs(scheduler):
    """向 AsyncIOScheduler 注册所有 A 类任务

    阶段 1：空注册（骨架空跑）
    阶段 2：farm(A2/A3) / item(A4) / gmarket(A5)
    阶段 3：notifier 通知通道
    阶段 4：gmarket(A6) / industrial(A7)
    阶段 5：farm(A1 生草结算)
    """
    # TODO(阶段2): from scheduler.jobs import farm, item, gmarket
    # TODO(阶段2): farm.register(scheduler); item.register(scheduler); gmarket.register(scheduler)
    logger.info("任务注册：暂无（阶段 1 骨架空跑）")
