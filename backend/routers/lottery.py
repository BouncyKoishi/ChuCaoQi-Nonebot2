"""
抽奖相关路由
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import LotteryService
import dbConnection.draw_item as drawItemDB
import dbConnection.user as userDB

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from common import check_user_disabled
from middleware.session_auth import get_user_id
from middleware.rate_limiter import limiter

router = APIRouter()


@router.get("/storage")
async def get_lottery_storage(request: Request, rare: Optional[str] = None, pool: Optional[str] = None):
    """获取抽奖物品仓库"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    try:
        rare_rank = {'Easy': 0, 'Normal': 1, 'Hard': 2, 'Lunatic': 3}.get(rare) if rare else None
        result = await LotteryService.get_item_storage(userId=userId, rare_rank=rare_rank, pool_name=pool)
        return {"success": True, "data": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/pools")
async def get_lottery_pools():
    """获取奖池列表"""
    pools = await LotteryService.get_pool_list()
    return {"success": True, "data": pools}


@router.get("/search")
@limiter.limit("30/minute")
async def search_lottery_items(request: Request, keyword: str = Query(..., description="搜索关键词"), page: int = Query(0, description="页码")):
    """搜索抽奖物品"""
    result = await LotteryService.search_item(keyword=keyword, page=page, page_size=12)
    return {"success": True, "data": result}


@router.get("/item/{item_name}")
async def get_lottery_item_detail(item_name: str, request: Request):
    """获取抽奖物品详情"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    item = await drawItemDB.getItemByName(item_name)
    if not item:
        return {"success": False, "error": "ITEM_NOT_FOUND"}
    
    item_storage = await drawItemDB.getSingleItemStorage(userId, item.id)
    person_count, number_count = await drawItemDB.getItemStorageCount(item.id)
    
    author_qq = None
    if item.authorId:
        author = await userDB.getUnifiedUser(item.authorId)
        author_qq = author.realQQ if author else None
    
    return {
        "success": True,
        "data": {
            "id": item.id,
            "name": item.name,
            "rare": LotteryService.RARE_DESCRIBE[item.rareRank],
            "rareRank": item.rareRank,
            "detail": item.detail,
            "pool": item.pool,
            "authorQQ": author_qq,
            "amount": item_storage.amount if item_storage else 0,
            "personCount": person_count,
            "numberCount": number_count
        }
    }


@router.post("/draw")
@limiter.limit("20/minute")
async def lottery_draw(request: Request):
    """单抽（支持骰子碎片重抽）"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    pool = body.get('pool')
    
    is_disabled, remaining = check_user_disabled(userId)
    if is_disabled:
        return {"success": False, "error": "DISABLED", "data": {"remaining": remaining}}
    
    try:
        result = await LotteryService.draw_with_redraw(userId=userId, pool_name=pool)
        
        if result.get('banned'):
            return {
                "success": True,
                "data": {
                    "banned": True,
                    "disabledSeconds": result['disabledSeconds']
                }
            }
        
        item = result['item']
        return {
            "success": True, 
            "data": {
                "banned": False,
                "item": {
                    "id": item.id,
                    "name": item.name,
                    "rare": LotteryService.RARE_DESCRIBE[item.rareRank],
                    "rareRank": item.rareRank,
                    "detail": item.detail
                },
                "isNew": result['isNew'],
                "redrawCount": result['redrawCount']
            }
        }
    except Exception as e:
        error_msg = str(e)
        if "奖池" in error_msg or "empty" in error_msg.lower():
            return {"success": False, "error": "EMPTY_POOL", "message": "该奖池暂无物品可抽"}
        import traceback
        print(f"[抽奖错误] {error_msg}")
        print(traceback.format_exc())
        return {"success": False, "error": "DRAW_ERROR", "message": f"抽奖失败: {error_msg}"}


@router.post("/draw-ten")
@limiter.limit("10/minute")
async def lottery_draw_ten(request: Request):
    """十连抽"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    pool = body.get('pool')
    base_level = body.get('baseLevel', 0)

    is_disabled, remaining = check_user_disabled(userId)
    if is_disabled:
        return {"success": False, "error": "DISABLED", "data": {"remaining": remaining}}

    try:
        result = await LotteryService.draw_ten_full(userId=userId, base_level=base_level, pool_name=pool)

        if not result.get('success'):
            return result

        return {"success": True, "data": result['data']}
    except Exception as e:
        error_msg = str(e)
        if "奖池" in error_msg or "empty" in error_msg.lower():
            return {"success": False, "error": "EMPTY_POOL", "message": "该奖池暂无物品可抽"}
        import traceback
        print(f"[十连抽错误] {error_msg}")
        print(traceback.format_exc())
        return {"success": False, "error": "DRAW_ERROR", "message": f"十连抽失败: {error_msg}"}


@router.post("/add")
@limiter.limit("10/minute")
async def add_lottery_item(request: Request):
    """添加自定义物品"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    item_name = body.get('itemName')
    rare_rank = body.get('rareRank', 0)
    pool = body.get('pool', '默认')
    detail = body.get('detail')
    
    if not item_name:
        return {"success": False, "error": "物品名不能为空"}
    
    result = await LotteryService.add_custom_item(
        userId=userId,
        item_name=item_name,
        rare_rank=rare_rank,
        pool_name=pool,
        detail=detail
    )
    return result


@router.get("/my-items")
async def get_my_lottery_items(request: Request, rare: Optional[str] = None, pool: Optional[str] = None):
    """获取自制物品列表"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    rare_rank = {'Easy': 0, 'Normal': 1, 'Hard': 2, 'Lunatic': 3}.get(rare) if rare else None
    items = await drawItemDB.getItemListByAuthorId(userId, rare_rank, pool)
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "name": item.name,
            "rare": LotteryService.RARE_DESCRIBE[item.rareRank],
            "rareRank": item.rareRank,
            "pool": item.pool,
            "detail": item.detail
        })
    
    return {"success": True, "data": result}


@router.post("/update")
@limiter.limit("20/minute")
async def update_lottery_item(request: Request):
    """修改物品说明"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    body = await request.json()
    item_name = body.get('itemName')
    detail = body.get('detail')
    
    if not item_name:
        return {"success": False, "error": "物品名不能为空"}
    
    result = await LotteryService.update_item_detail(userId=userId, item_name=item_name, detail=detail)
    return result


@router.delete("/item/{item_name}")
@limiter.limit("20/minute")
async def delete_lottery_item(item_name: str, request: Request):
    """删除物品"""
    userId = get_user_id(request)
    if not userId:
        return {"success": False, "error": "未登录或登录已过期"}
    
    item = await drawItemDB.getItemByName(item_name)
    if not item:
        return {"success": False, "error": "ITEM_NOT_FOUND"}
    
    if item.author != str(userId):
        return {"success": False, "error": "NOT_AUTHOR"}
    
    await drawItemDB.deleteItem(item)
    return {"success": True, "message": "删除成功"}
