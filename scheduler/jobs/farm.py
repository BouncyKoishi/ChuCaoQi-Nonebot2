"""
A2 承载力基础恢复 / A3 非活跃承载力恢复

从 bot/plugins/kusa_farm.py 原样迁移（阶段 2），纯 DB 逻辑，无 QQ 依赖。
A1 生草结算在阶段 5 下沉。
"""

import logging

import core.db.kusa_field as field_db
import core.db.kusa_item as item_db

logger = logging.getLogger("scheduler.jobs.farm")


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
    """注册承载力恢复任务（参数与原 bot 侧一致）"""
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
