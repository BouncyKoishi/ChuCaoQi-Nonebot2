from fastapi import APIRouter, Request, Query
from middleware.session_auth import get_user_id, get_unified_user
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from dbConnection.models import PageView

router = APIRouter()

VALID_PATH_RE = re.compile(r'^/[a-z0-9/_-]*$')

TZ_SHANGHAI = timezone(timedelta(hours=8))


@router.post("/pageview")
async def record_pageview(request: Request):
    user_id = get_user_id(request)
    try:
        body = await request.json()
    except Exception:
        return {"success": True}
    if not isinstance(body, dict):
        return {"success": True}
    path = body.get("path", "")
    page_name = body.get("pageName", "")

    if not path or not VALID_PATH_RE.match(path):
        return {"success": True}

    try:
        await PageView.create(
            userId=user_id,
            path=path[:128],
            pageName=page_name[:64] if page_name else None,
        )
    except Exception:
        pass
    return {"success": True}


@router.get("/stats")
async def get_stats(request: Request, days: int = Query(30, description="统计天数", ge=1, le=365)):
    unified_user = get_unified_user(request)
    if not unified_user or not unified_user.isSuperAdmin:
        return {"success": False, "error": "权限不足"}

    now = datetime.now(TZ_SHANGHAI)
    start_date = (now - timedelta(days=days)).astimezone(timezone.utc)

    records = await PageView.filter(createdAt__gte=start_date)

    total_pv = len(records)
    unique_users = set()
    page_stats = {}

    hourly_pv = defaultdict(int)
    hourly_uv = defaultdict(set)
    daily_pv = defaultdict(int)
    daily_uv = defaultdict(set)

    for r in records:
        uid = r.userId
        if uid is not None:
            unique_users.add(uid)

        if r.createdAt:
            local_dt = r.createdAt.astimezone(TZ_SHANGHAI) if r.createdAt.tzinfo else r.createdAt
            hour_key = local_dt.strftime("%Y-%m-%d %H:00")
            hourly_pv[hour_key] += 1
            if uid is not None:
                hourly_uv[hour_key].add(uid)

            day_key = local_dt.strftime("%Y-%m-%d")
            daily_pv[day_key] += 1
            if uid is not None:
                daily_uv[day_key].add(uid)

        path = r.path
        if path not in page_stats:
            page_stats[path] = {"path": path, "pageName": r.pageName, "pv": 0}
        page_stats[path]["pv"] += 1

    if days == 1:
        trend_data = []
        for i in range(23, -1, -1):
            hour_dt = now - timedelta(hours=i)
            hour_key = hour_dt.strftime("%Y-%m-%d %H:00")
            trend_data.append({
                "date": hour_key,
                "pv": hourly_pv.get(hour_key, 0),
                "uv": len(hourly_uv.get(hour_key, set())),
            })
    else:
        trend_data = []
        for i in range(days):
            day = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            trend_data.append({
                "date": day,
                "pv": daily_pv.get(day, 0),
                "uv": len(daily_uv.get(day, set())),
            })

    page_ranking = sorted(page_stats.values(), key=lambda x: x["pv"], reverse=True)

    return {
        "success": True,
        "data": {
            "totalPv": total_pv,
            "totalUv": len(unique_users),
            "days": days,
            "daily": trend_data,
            "pages": page_ranking,
        },
    }
