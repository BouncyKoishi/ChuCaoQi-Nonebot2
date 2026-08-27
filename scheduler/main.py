#!/usr/bin/env python3
"""
生草系统 Scheduler - 独立定时任务进程

承载 A 类生草系统基本运行任务（生草结算、承载力恢复、G值波动、
工业生产等），使系统核心运转不依赖 bot 在线。

使用方法:
    venv\\Scripts\\python -m scheduler.main
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import asyncio
import logging
import signal

# 确保项目根目录可导入 core/ 包
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SCHEDULER_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志（对齐 backend/main.py 风格）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(SCHEDULER_DIR, 'scheduler.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger("scheduler")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED

import core.db.db as base_db
from scheduler.jobs import register_jobs


def _on_job_error(event):
    """任务执行异常：记日志，不让单任务异常拖垮进程"""
    logger.error(f"任务执行异常: {getattr(event.job_id, 'job_id', event.job_id)}", exc_info=event.exception)


def _on_job_missed(event):
    """任务错过触发时间：记日志（misfire_grace_time=None 的任务不补跑，需人工关注）"""
    logger.warning(f"任务错过触发时间: {event.job_id} @ {event.scheduled_run_time}")


async def main():
    # 数据库初始化（与 bot/backend 共用 core.db，Tortoise + aiosqlite WAL 模式）
    await base_db.init_db()
    logger.info("--- Database initialized ---")

    scheduler = AsyncIOScheduler(
        timezone="Asia/Shanghai",
        job_defaults={
            "coalesce": True,          # 积压的多次触发合并为一次
            "max_instances": 1,        # 同一任务不并发执行
            "misfire_grace_time": 60,  # 默认允许 60s 内补跑（个别任务注册时显式覆盖为 None）
        },
    )
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
    scheduler.add_listener(_on_job_missed, EVENT_JOB_MISSED)

    # 注册 A 类任务（阶段 1 为空注册，后续阶段逐个填充）
    register_jobs(scheduler)

    scheduler.start()
    logger.info("--- Scheduler started ---")
    for job in scheduler.get_jobs():
        logger.info(f"已注册任务: {job.id} (next_run: {job.next_run_time})")

    # 优雅退出：等待 SIGINT/SIGTERM（Windows 下 add_signal_handler 不支持时依赖 Ctrl+C）
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("--- Scheduler stopped ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
