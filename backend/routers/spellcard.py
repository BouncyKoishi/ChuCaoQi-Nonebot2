"""
符卡对战相关路由 - 仅提供PvP预留接口
"""

from fastapi import APIRouter
import random

router = APIRouter()


@router.get("/dice-seed")
async def get_dice_seed():
    seed = random.randint(1, 2147483646)
    return {"success": True, "data": {"seed": seed}}
