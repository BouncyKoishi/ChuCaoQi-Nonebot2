"""
地震查询插件 - NoneBot2 版本
查询中国地震台网（CENC）最新地震信息，支持按省份/城市筛选和震级过滤
数据来源：CENC 官网 www.ceic.ac.cn/data/data.json（当年全量数据，实时更新）
"""

# ==================== 导入模块 ====================

import re
import os
import json
import math
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message

from kusa_base import plugin_config, send_group_msg

# 定时任务调度器，定时推送大地震预警
try:
    from nonebot_plugin_apscheduler import scheduler
except ImportError:
    scheduler = None


# ==================== 配置读取 ====================

_eq_config = plugin_config.get('earthquake', {})

# 大地震预警推送的目标群号列表，空列表表示不推送
EARTHQUAKE_ALERT_GROUPS: list = _eq_config.get('alert_groups', [])

# 大地震预警阈值，震级 >= 此值触发推送
BIG_EARTHQUAKE_THRESHOLD = _eq_config.get('big_threshold', 5.0)

# 每次查询最多返回条数
MAX_RESULTS = _eq_config.get('max_results', 5)

# 城市附近查询半径（km）
NEARBY_RADIUS = _eq_config.get('nearby_radius', 500)

# CENC 官网数据源：当年全量地震数据，实时更新
CENC_API_URL = "https://www.ceic.ac.cn/data/data.json"

# 请求头伪装
USER_AGENT = plugin_config.get('web', {}).get('userAgent',
    'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Mobile Safari/537.36'
)

# 记录已推送过的地震 ID，防止重复推送，程序重启后清空
_PUSHED_IDS: set = set()


# ==================== 地理数据 ====================

# 中国省级行政区名称（用于省份级别字符串匹配）
PROVINCES = {
    '北京', '天津', '上海', '重庆',
    '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽',
    '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '海南',
    '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
    '内蒙古', '广西', '西藏', '宁夏', '新疆',
    '香港', '澳门',
}

# 城市经纬度坐标（WGS84），从 JSON 文件加载，用于附近搜索
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_PLUGIN_DIR))
_CITY_COORDS_PATH = os.path.join(_PROJECT_ROOT, 'resources', 'data', 'city_coords.json')


def _load_city_coords() -> Dict[str, Tuple[float, float]]:
    """从 resources/data/city_coords.json 加载城市坐标表"""
    try:
        with open(_CITY_COORDS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 跳过以 _ 开头的说明字段，转换为 tuple
        return {k: tuple(v) for k, v in data.items() if not k.startswith('_')}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[地震] 城市坐标表加载失败: {e}")
        return {}


CITY_COORDS: Dict[str, Tuple[float, float]] = _load_city_coords()


# ==================== 命令注册 ====================

earthquake_cmd = on_command("地震", priority=5, block=True)


# ==================== 工具函数 ====================

def _parse_user_args(raw_arg: str) -> Tuple[float, str]:
    """
    解析用户 !地震 命令参数，提取震级下限和地点筛选词

    返回: (min_magnitude, location_filter)
      min_magnitude 为 0.0 表示不筛选震级
      location_filter 为空字符串表示不筛选地点

    示例：
      "" -> (0.0, "")
      "5" -> (5.0, "")
      "3.5" -> (3.5, "")
      "四川" -> (0.0, "四川")
      "四川 4" -> (4.0, "四川")
      "成都 3" -> (3.0, "成都")
    """
    if not raw_arg:
        return 0.0, ""

    # 匹配整数或小数（如 5、3.5）
    num_match = re.search(r'\d+(?:\.\d+)?', raw_arg)
    if num_match:
        mag = max(0.0, min(float(num_match.group()), 10.0))
        location = raw_arg.replace(num_match.group(), '', 1).strip()
    else:
        mag = 0.0
        location = raw_arg.strip()

    return mag, location


async def _fetch_cenc_earthquake_data() -> Optional[List[Dict]]:
    """
    从 CENC 官网获取当年全量地震数据

    数据来源：https://www.ceic.ac.cn/data/data.json
    返回 JSON 数组，每条记录字段：id, time, latitude, longitude, depth, magnitude, location
    数据按时间倒序排列（最新在前），约 600+ 条，覆盖当年全量地震
    """
    proxy = plugin_config.get('web', {}).get('proxy', '')

    try:
        async with httpx.AsyncClient(proxy=proxy if proxy else None) as client:
            resp = await client.get(
                CENC_API_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=15
            )

            if resp.status_code != 200:
                print(f"[地震] HTTP 请求失败，状态码: {resp.status_code}")
                return None

            data = resp.json()

            # CENC data.json 是 JSON 数组，直接返回
            if isinstance(data, list):
                print(f"[地震] 成功获取 {len(data)} 条地震数据")
                return data

            print(f"[地震] 数据格式异常，期望数组，得到 {type(data).__name__}")
            return None

    except json.JSONDecodeError as e:
        print(f"[地震] JSON 解析失败: {e}")
        return None
    except httpx.TimeoutException:
        print(f"[地震] 请求超时（15秒）")
        return None
    except Exception as e:
        print(f"[地震] 请求异常: {type(e).__name__}: {e}")
        return None


def _filter_by_location(records: List[Dict], location: str) -> List[Dict]:
    """按地点关键词做子串匹配筛选"""
    return [r for r in records if location in r.get("location", "")]


def _filter_by_magnitude(records: List[Dict], min_mag: float) -> List[Dict]:
    """按震级下限筛选"""
    result = []
    for r in records:
        try:
            mag = float(r.get("magnitude", 0))
            if mag >= min_mag:
                result.append(r)
        except (ValueError, TypeError):
            continue
    return result


def _get_time_range(records: List[Dict]) -> str:
    """从记录中提取日期范围，如 '2026-07-04 ~ 2026-07-17'"""
    dates = sorted(r.get("time", "")[:10] for r in records if r.get("time"))
    if not dates:
        return ""
    start = dates[0]
    end = dates[-1]
    return f"{start} ~ {end}" if start != end else start


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine 公式计算球面距离（km）"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _filter_nearby(records: List[Dict], lat: float, lon: float,
                   radius_km: float = NEARBY_RADIUS) -> List[Dict]:
    """筛选指定坐标 radius_km 范围内的地震，保持时间倒序（原数据顺序）"""
    nearby = []
    for r in records:
        try:
            eq_lat = float(r.get("latitude", 0))
            eq_lon = float(r.get("longitude", 0))
            dist = _haversine_distance(lat, lon, eq_lat, eq_lon)
            if dist <= radius_km:
                nearby.append(r)
        except (ValueError, TypeError):
            continue

    return nearby


def _resolve_location(records: List[Dict], location: str) -> Tuple[List[Dict], List[Dict], str, str]:
    """
    解析地点查询，同时尝试精确匹配和附近搜索

    策略：
      1. 始终尝试字符串匹配（location 字段子串包含）-> 精确匹配
      2. 如果是已知城市（在 CITY_COORDS 中），同时做 Haversine 附近搜索
      3. 附近搜索结果去掉与精确匹配重复的记录

    返回: (exact_matches, nearby_matches, exact_desc, nearby_desc)
      exact_desc 如 "精确匹配：成都"，nearby_desc 如 "成都附近（500km内）" 或空字符串
    """
    exact = _filter_by_location(records, location)
    exact_desc = f"精确匹配：{location}"

    if location in CITY_COORDS:
        lat, lon = CITY_COORDS[location]
        nearby_all = _filter_nearby(records, lat, lon)
        # 去重：排除已在精确匹配中的记录
        exact_ids = {r.get("id") for r in exact}
        nearby = [r for r in nearby_all if r.get("id") not in exact_ids]
        nearby_desc = f"{location}附近（{int(NEARBY_RADIUS)}km内）"
    else:
        nearby = []
        nearby_desc = ""

    return exact, nearby, exact_desc, nearby_desc


def _is_recent(time_str: str, hours: int = 12) -> bool:
    """判断地震时间是否在当前时间的 hours 小时内"""
    try:
        eq_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return datetime.now() - eq_time <= timedelta(hours=hours)
    except (ValueError, TypeError):
        return False


def _format_single_eq(index: int, eq: Dict) -> str:
    """格式化单条地震记录，12小时内添加[新]标记"""
    o_time   = eq.get("time", "未知")
    mag      = eq.get("magnitude", "?")
    lat      = eq.get("latitude", "?")
    lon      = eq.get("longitude", "?")
    depth    = eq.get("depth", "?")
    location = eq.get("location", "未知")
    marker = "[新] " if _is_recent(o_time) else ""
    return (
        f"{index}. {marker}{location}\n"
        f"   震级 {mag}  |  时间 {o_time}\n"
        f"   纬度 {lat}  经度 {lon}  |  深度 {depth}km"
    )


def _format_earthquake_text(exact_records: List[Dict], nearby_records: List[Dict],
                            mag_desc: str = "", data_time_range: str = "",
                            has_location: bool = False) -> str:
    """将地震数据格式化为群聊消息，精确匹配和附近搜索分区域展示"""
    total = len(exact_records) + len(nearby_records)
    if total == 0:
        return ""  # 无结果由 handler 处理

    header = f"最近 {total} 条地震信息（来源：中国地震台网）"
    if mag_desc:
        header += f" ｜ {mag_desc}"
    if data_time_range:
        header += f"\n数据时间范围：{data_time_range}"
    lines = [header]

    # 有地点筛选时始终显示分区头
    show_sections = has_location

    if exact_records:
        if show_sections:
            lines.append("\n[精确匹配]")
        for i, eq in enumerate(exact_records, 1):
            lines.append(_format_single_eq(i, eq))

    if nearby_records:
        if show_sections:
            lines.append(f"\n[附近搜索 {int(NEARBY_RADIUS)}km]")
            start = 1
        else:
            start = len(exact_records) + 1
        for i, eq in enumerate(nearby_records, start):
            lines.append(_format_single_eq(i, eq))

    return "\n".join(lines)


# ==================== 大地震筛选 ====================

def _has_big_earthquake(records: List[Dict]) -> List[Dict]:
    """筛选达到预警阈值且未推送过的大地震"""
    big_ones = []
    for eq in records:
        eq_id = eq.get("id")
        if not eq_id:
            continue
        mag = eq.get("magnitude", 0)
        try:
            mag_val = float(mag)
        except (ValueError, TypeError):
            continue

        if mag_val >= BIG_EARTHQUAKE_THRESHOLD and eq_id not in _PUSHED_IDS:
            big_ones.append(eq)
            _PUSHED_IDS.add(eq_id)

    return big_ones


# ==================== 大地震定时预警推送 ====================

if scheduler:
    @scheduler.scheduled_job('interval', minutes=5, misfire_grace_time=60)
    async def earthquake_alert_task():
        """每 5 分钟检查，出现 >= 阈值大地震时推送到配置的群列表"""
        if not EARTHQUAKE_ALERT_GROUPS:
            return

        records = await _fetch_cenc_earthquake_data()
        if not records:
            return

        # 只检查最新的 10 条（数据已按时间倒序）
        big_ones = _has_big_earthquake(records[:10])
        if not big_ones:
            return

        for eq in big_ones:
            location = eq.get("location", "未知")
            mag = eq.get("magnitude", "?")
            o_time = eq.get("time", "?")
            depth = eq.get("depth", "?")

            alert_msg = (
                f"[大地震速报]\n"
                f"发震位置：{location}\n"
                f"震级：{mag}  深度：{depth}km\n"
                f"发震时间：{o_time}\n"
                f"数据来源：中国地震台网（CENC）"
            )
            print(f"[地震预警] {alert_msg}")

            for group_id in EARTHQUAKE_ALERT_GROUPS:
                await send_group_msg(group_id, alert_msg)


# ==================== 命令处理函数（主入口）====================

@earthquake_cmd.handle()
async def handle_earthquake(args: Message = CommandArg()):
    """
    处理 !地震 命令

    用法：
      !地震          -> 最近 5 条地震
      !地震 5        -> 震级 >= 5.0 的最近 5 条
      !地震 3.5      -> 震级 >= 3.5 的最近 5 条
      !地震 四川     -> 四川省内最近 5 条（精确匹配）
      !地震 成都     -> 成都市内 + 成都附近 500km（精确匹配 + 附近搜索）
      !地震 四川 4   -> 四川省内震级 >= 4.0 的最近 5 条
      !地震 秘鲁     -> 含"秘鲁"的最近 5 条（精确匹配）

    数据来源：CENC 官网，覆盖当年全量地震（约600+条），实时更新
    """
    raw_arg = args.extract_plain_text().strip()
    min_mag, location_filter = _parse_user_args(raw_arg)

    # 拉取全量数据
    records = await _fetch_cenc_earthquake_data()
    if records is None:
        await earthquake_cmd.finish("获取地震信息失败，请稍后重试。")

    # 原始全量数据的时间范围
    data_time_range = _get_time_range(records)

    # 地点筛选：精确匹配 + 附近搜索
    if location_filter:
        exact, nearby, exact_desc, nearby_desc = _resolve_location(records, location_filter)
    else:
        exact, nearby, exact_desc, nearby_desc = records, [], "", ""

    # 震级筛选（分别应用于两组结果）
    if min_mag > 0:
        exact = _filter_by_magnitude(exact, min_mag)
        nearby = _filter_by_magnitude(nearby, min_mag)

    # 各取最多 MAX_RESULTS 条
    exact_result = exact[:MAX_RESULTS]
    nearby_result = nearby[:MAX_RESULTS]

    # 无结果
    if not exact_result and not nearby_result:
        if location_filter:
            msg = f"近期未找到{location_filter}相关的地震记录。"
        elif min_mag > 0:
            msg = f"近期未找到震级≥{min_mag}的地震记录。"
        else:
            msg = "近期无地震记录。"
        if data_time_range:
            msg += f"\n数据时间范围：{data_time_range}"
        await earthquake_cmd.finish(msg)

    # header 仅保留震级筛选，地点由分区头体现
    mag_desc = f"震级≥{min_mag}" if min_mag > 0 else ""
    msg = _format_earthquake_text(exact_result, nearby_result, mag_desc,
                                  data_time_range, has_location=bool(location_filter))
    await earthquake_cmd.finish(msg)
