"""
管理路由 - 超级管理员专用

所有端点统一校验 isSuperAdmin 权限
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, FileResponse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import WarehouseService
from services import admin_service
from services import pic_archive_service as pic_service

sys.path.insert(0, os.path.dirname(__file__) + '/..')
from middleware.session_auth import get_user_id, get_unified_user
from middleware.rate_limiter import limiter

router = APIRouter()


# ==================== 权限校验依赖 ====================

def _check_admin(request: Request):
    """校验超级管理员权限，返回 (unified_user, error_response)

    鉴权失败时返回 403 JSONResponse（而非 200 dict），符合 RESTful 惯例
    """
    unified_user = get_unified_user(request)
    if not unified_user or not unified_user.isSuperAdmin:
        return None, JSONResponse({"success": False, "error": "权限不足"}, status_code=403)
    return unified_user, None


# ==================== 用户管理 ====================

@router.get("/users")
async def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    searchId: str = Query(None),
    searchName: str = Query(None)
):
    """用户列表"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_user_list(
        page=page, page_size=pageSize,
        search_id=searchId, search_name=searchName
    )
    return {"success": True, "data": result}


@router.get("/users/{userId}/warehouse")
async def get_user_warehouse(userId: int, request: Request):
    """查看用户仓库详情"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await WarehouseService.get_warehouse_info(userId=userId)
    if 'error' in result:
        return {"success": False, "error": result['error']}
    return {"success": True, "data": result}


@router.post("/users/{userId}/name")
async def update_user_name(userId: int, request: Request):
    """修改用户昵称"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    name = body.get('name')
    if not name:
        return {"success": False, "error": "名字不能为空"}

    result = await WarehouseService.change_name(userId=userId, name=name)
    return result


@router.post("/users/{userId}/title")
async def give_user_title(userId: int, request: Request):
    """授予用户称号"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    title = body.get('title')
    if not title:
        return {"success": False, "error": "称号不能为空"}

    result = await admin_service.give_title(userId, title)
    return result


@router.post("/users/{userId}/donation")
async def set_user_donation(userId: int, request: Request):
    """设置用户捐赠金额"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    amount = body.get('amount')
    source = body.get('source', 'qq')
    if amount is None:
        return {"success": False, "error": "金额不能为空"}

    result = await admin_service.set_donation(userId, float(amount), source)
    return result


@router.get("/users/{userId}/donations")
async def get_user_donations(userId: int, request: Request):
    """查看用户捐赠记录"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_donation_records(userId)
    return result


@router.delete("/users/{userId}/donations/{recordId}")
async def delete_user_donation(userId: int, recordId: int, request: Request):
    """删除单条捐赠记录"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.delete_donation_record(recordId)
    return result


@router.get("/users/{userId}/titles")
async def get_user_titles(userId: int, request: Request):
    """查看用户拥有的所有称号及当前使用的称号"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_user_titles(userId)
    return result


@router.get("/users/{userId}/chat-permission")
async def get_user_chat_permission(userId: int, request: Request):
    """查看用户 chat 权限"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_chat_permission(userId)
    return result


@router.post("/users/{userId}/chat-permission")
async def update_user_chat_permission(userId: int, request: Request):
    """设置用户 chat 权限"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    result = await admin_service.update_chat_permission(
        userId,
        allow_private=body.get('allowPrivate', False),
        allow_role=body.get('allowRole', False),
        allow_advanced_model=body.get('allowAdvancedModel', False),
        daily_limit_mode=body.get('dailyLimitMode', 'default')
    )
    return result


@router.post("/users/{userId}/web-token")
async def generate_user_web_token(userId: int, request: Request):
    """为用户生成 webToken"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.generate_web_token_for_user(userId)
    return result


@router.post("/users/{userId}/friend-code")
async def generate_friend_code(userId: int, request: Request):
    """生成用户好友码"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_user_friend_code(userId)
    return result


@router.get("/users/{userId}/account-marks")
async def get_account_marks(userId: int, request: Request):
    """获取用户帐号标记（小号关联 + 机械臂）"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_account_marks(userId)
    return result


@router.post("/users/{userId}/account-marks")
async def update_account_marks(userId: int, request: Request):
    """设置用户帐号标记"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    related_user_id = body.get('relatedUserId')
    is_robot = body.get('isRobot', False)

    result = await admin_service.update_account_marks(
        userId,
        int(related_user_id) if related_user_id else None,
        bool(is_robot)
    )
    return result


# ==================== 称号管理 ====================

@router.get("/titles")
async def get_titles(request: Request):
    """称号列表（含拥有者）"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_title_list_with_owners()
    return {"success": True, "data": result}


@router.post("/titles")
async def create_title(request: Request):
    """添加新称号"""
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()
    name = body.get('name')
    detail = body.get('detail')
    if not name:
        return {"success": False, "error": "称号名称不能为空"}

    result = await admin_service.create_title(name, detail)
    return result


@router.delete("/titles/{titleName}")
async def delete_title(titleName: str, request: Request):
    """删除称号"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.delete_title(titleName)
    return result


@router.get("/titles/{titleName}/owners")
async def get_title_owners(titleName: str, request: Request):
    """查看称号拥有者详情"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_title_owners(titleName)
    return result


# ==================== 自定义排行榜 ====================

@router.post("/rank/custom")
async def generate_custom_rank(request: Request):
    """生成自定义排行榜

    支持部分传参：未传或传 null 的参数使用默认值
    limit=25, levelMax=10, showInactive=False, showSubaccount=True
    """
    uu, err = _check_admin(request)
    if err:
        return err

    body = await request.json()

    def _opt(val, default):
        return default if val is None else val

    result = await admin_service.generate_custom_rank(
        dimension=_opt(body.get('dimension'), 'kusa'),
        limit=_opt(body.get('limit'), 25),
        level_max=_opt(body.get('levelMax'), 10),
        show_inactive=_opt(body.get('showInactive'), False),
        show_subaccount=_opt(body.get('showSubaccount'), True),
        item_name=body.get('itemName')
    )
    # 把 columns 嵌入 data，避免 axios 拦截器解包时丢失
    if isinstance(result, dict) and result.get('success'):
        return {'success': True, 'data': {'list': result.get('data', []), 'columns': result.get('columns', [])}}
    return result


@router.get("/items/list")
async def get_items_list(request: Request):
    """所有物品名称列表（用于物品排行选择）"""
    uu, err = _check_admin(request)
    if err:
        return err

    result = await admin_service.get_all_item_names()
    return {"success": True, "data": result}


# ==================== 图片审核 ====================

@router.get("/pic-review/categories")
async def get_pic_categories(request: Request):
    """获取图片分类列表（供前端渲染分类按钮）"""
    uu, err = _check_admin(request)
    if err:
        return err
    return {"success": True, "data": pic_service.get_archive_list()}


@router.get("/pic-review/pending")
async def get_pending_pics(request: Request):
    """获取待审核图片列表"""
    uu, err = _check_admin(request)
    if err:
        return err
    return {"success": True, "data": pic_service.get_pending_pics()}


@router.get("/pic-review/image/{filename}")
async def get_pic_image(filename: str, request: Request):
    """获取待审核图片文件（<img> 通过 query token 访问）"""
    uu, err = _check_admin(request)
    if err:
        return err
    path = pic_service.get_pic_abs_path(filename)
    if not path:
        return JSONResponse({"success": False, "error": "文件不存在"}, status_code=404)
    return FileResponse(path)


@router.post("/pic-review/classify")
async def classify_pic(request: Request):
    """分类图片 {filename, category}"""
    uu, err = _check_admin(request)
    if err:
        return err
    data = await request.json()
    filename = data.get("filename")
    category = data.get("category")
    if not filename or not category:
        return JSONResponse({"success": False, "error": "参数缺失"}, status_code=400)
    result = pic_service.classify_pic(filename, category)
    return result


@router.post("/pic-review/save")
async def save_pic(request: Request):
    """移到私藏 {filename}"""
    uu, err = _check_admin(request)
    if err:
        return err
    data = await request.json()
    filename = data.get("filename")
    if not filename:
        return JSONResponse({"success": False, "error": "参数缺失"}, status_code=400)
    return pic_service.save_pic(filename)


@router.post("/pic-review/skip")
async def skip_pic(request: Request):
    """跳过图片 {filename}"""
    uu, err = _check_admin(request)
    if err:
        return err
    data = await request.json()
    filename = data.get("filename")
    if not filename:
        return JSONResponse({"success": False, "error": "参数缺失"}, status_code=400)
    return pic_service.skip_pic(filename)


@router.delete("/pic-review/image/{filename}")
async def delete_pic(filename: str, request: Request):
    """删除待审核图片"""
    uu, err = _check_admin(request)
    if err:
        return err
    return pic_service.delete_pic(filename)
