"""
排行榜相关路由
"""

from fastapi import APIRouter, Query
import sys
import os

from core.services import StatisticService

router = APIRouter()


@router.get("/kusa")
async def get_kusa_rank(sort_by: str = Query('kusa', description="排序字段: kusa按草排序, advKusa按草之精华排序")):
    """获取草排行榜"""
    if sort_by not in ['kusa', 'advKusa']:
        sort_by = 'kusa'
    result = await StatisticService.get_kusa_rank_with_adv(sort_by=sort_by)
    return {"success": True, "data": result}


@router.get("/total-adv-kusa")
async def get_total_adv_kusa_rank(
    limit: int = Query(25, description="返回前N名"),
    level_max: int = Query(10, description="最大VIP等级限制")
):
    """获取累计草精排行榜"""
    result = await StatisticService.get_total_adv_kusa_rank(
        limit=limit,
        level_max=level_max,
        show_inactive=False,
        show_subaccount=True,
        use_cache=True
    )
    return {"success": True, "data": result}
