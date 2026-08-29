"""
A1 生草结算 / A2 承载力基础恢复 / A3 非活跃承载力恢复

A2/A3 从 bot/plugins/kusa_farm.py 原样迁移（阶段 2），纯 DB 逻辑，无 QQ 依赖。
A1 结算逻辑在 core.services.FarmService.settle_due_fields（阶段 5 下沉），
本 job 只做：调服务结算 → web 通知（backend）→ QQ 事件推送（bot）。
"""

import logging

import core.db.kusa_field as field_db
import core.db.kusa_item as item_db
from core.services import FarmService
from scheduler import notifier

logger = logging.getLogger("scheduler.jobs.farm")


async def kusa_harvest_runner():
    """生草结算轮询（每 15 秒，每轮最多 2 块）"""
    results = await FarmService.settle_due_fields()

    for result in results:
        # web 通知：调用方由 bot 切换至 scheduler（原 bot 侧 notify_web_kusa_harvested）
        await notifier.notify_web('/api/notify/kusa-harvested', result['web'])
        # QQ 事件：喜报/围殴/私聊提示由 bot 执行（结算与玩法分离）
        await notifier.notify_qq('kusa_harvested_event', {'actions': result['actions']})

    if results:
        logger.info(f"生草结算完成：{len(results)} 块田地")


async def soil_capacity_increase_base():
    """承载力基础恢复（每 90 分钟）"""
    all_fields = await field_db.getAllKusaField()
    bad_soil_fields = [field for field in all_fields if field.soilCapacity < 25]

    for field in bad_soil_fields:
        await field_db.kusaSoilRecover(field.user_id)

    full_soil_fields = [field for field in all_fields if field.soilCapacity >= 25]
    overfill_tech_users = await item_db.getUserIdListByItem('肥力贮存技术I')

    for field in full_soil_fields:
        if field.user_id not in overfill_tech_users:
            continue

        spare_cap_limit = await item_db.getItemAmount(field.user_id, '肥力贮存仓')
        now_spare_cap = await item_db.getItemAmount(field.user_id, '后备承载力')

        if now_spare_cap >= spare_cap_limit:
            continue

        now_spare_cap_unit = await item_db.getItemAmount(field.user_id, '后备承载力单元')
        overfill_tech_level = await item_db.getTechLevel(field.user_id, '肥力贮存技术')
        spare_cap_unit_update_amount = 5 - overfill_tech_level

        if spare_cap_unit_update_amount <= now_spare_cap_unit + 1:
            await item_db.changeItemAmount(field.user_id, '后备承载力', 1)
            await item_db.changeItemAmount(field.user_id, '后备承载力单元', 1 - spare_cap_unit_update_amount)
        else:
            await item_db.changeItemAmount(field.user_id, '后备承载力单元', 1)

    logger.info(f"承载力基础恢复完成：低承载力田 {len(bad_soil_fields)} 块，满承载力田 {len(full_soil_fields)} 块")


async def soil_capacity_increase_for_inactive():
    """非活跃用户承载力恢复（每小时第 33 分 33 秒，沿用原 bot 侧 cron 语义）"""
    bad_soil_fields = await field_db.getAllKusaField(onlySoilNotBest=True)

    for field in bad_soil_fields:
        if field.kusaFinishTs:
            continue

        overload = await item_db.getItemAmount(field.user_id, '过载标记')
        if overload:
            continue

        await field_db.kusaSoilRecover(field.user_id)

    logger.info(f"非活跃承载力恢复完成：处理田地 {len(bad_soil_fields)} 块")


def register(scheduler):
    """注册生草结算与承载力恢复任务（参数与原 bot 侧一致）"""
    scheduler.add_job(
        kusa_harvest_runner, 'interval',
        seconds=15, max_instances=10, misfire_grace_time=60,
        id='farm_kusa_harvest', name='A1 生草结算',
    )
    scheduler.add_job(
        soil_capacity_increase_base, 'interval',
        minutes=90, misfire_grace_time=None,
        id='farm_soil_capacity_base', name='A2 承载力基础恢复',
    )
    scheduler.add_job(
        soil_capacity_increase_for_inactive, 'cron',
        minute=33, second=33, misfire_grace_time=None,
        id='farm_soil_capacity_inactive', name='A3 非活跃承载力恢复',
    )
