"""
地震查询插件 - NoneBot2 版本
查询中国地震台网（CENC）最新地震信息，支持按省份/城市筛选和震级过滤
数据来源：CENC 官网 www.ceic.ac.cn/data/data.json（当年全量数据，实时更新）
"""

# ==================== 导入模块 ====================

import re
import json
import math
import httpx
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

# 主要城市经纬度坐标（WGS84），用于城市级别"附近"查询
CITY_COORDS: Dict[str, Tuple[float, float]] = {
    # 直辖市
    '北京': (39.90, 116.40), '上海': (31.23, 121.47),
    '天津': (39.08, 117.20), '重庆': (29.56, 106.55),
    # 省会
    '石家庄': (38.04, 114.51), '太原': (37.87, 112.55),
    '沈阳': (41.80, 123.43), '长春': (43.82, 125.32),
    '哈尔滨': (45.80, 126.53), '南京': (32.06, 118.80),
    '杭州': (30.27, 120.15), '合肥': (31.82, 117.23),
    '福州': (26.07, 119.30), '南昌': (28.68, 115.86),
    '济南': (36.65, 116.98), '郑州': (34.75, 113.65),
    '武汉': (30.59, 114.31), '长沙': (28.23, 112.94),
    '广州': (23.13, 113.26), '海口': (20.02, 110.35),
    '成都': (30.67, 104.07), '贵阳': (26.65, 106.71),
    '昆明': (25.04, 102.72), '西安': (34.27, 108.95),
    '兰州': (36.06, 103.83), '西宁': (36.62, 101.78),
    '台北': (25.03, 121.57),
    # 自治区首府
    '呼和浩特': (40.84, 111.75), '南宁': (22.82, 108.37),
    '拉萨': (29.65, 91.13), '银川': (38.49, 106.23),
    '乌鲁木齐': (43.83, 87.62),
    # 其他主要城市
    '深圳': (22.55, 114.06), '青岛': (36.07, 120.38),
    '大连': (38.91, 121.60), '厦门': (24.48, 118.09),
    '宁波': (29.87, 121.54), '苏州': (31.30, 120.62),
    '无锡': (31.49, 120.31), '温州': (27.99, 120.67),
    '烟台': (37.46, 121.45), '唐山': (39.63, 118.18),
    '洛阳': (34.62, 112.45), '绵阳': (31.46, 104.73),
    '宜宾': (28.77, 104.62), '南充': (30.84, 106.11),
    '泸州': (28.87, 105.44), '德阳': (31.13, 104.40),
    '西昌': (27.89, 102.27), '康定': (30.05, 101.96),
    '大理': (25.69, 100.16), '丽江': (26.87, 100.23),
    '日喀则': (29.27, 88.88), '林芝': (29.65, 94.36),
    '喀什': (39.47, 75.99), '伊宁': (43.91, 81.33),
    '阿克苏': (41.17, 80.26), '库尔勒': (41.76, 86.15),
    '敦煌': (40.14, 94.66), '格尔木': (36.42, 94.93),
    '海西': (37.37, 97.37), '海北': (36.95, 100.90),
    '玉树': (33.00, 97.01), '果洛': (34.48, 100.24),
}


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


def _is_province(query: str) -> bool:
    """判断查询词是否为省级行政区（用字符串匹配模式）"""
    return query in PROVINCES


def _is_city(query: str) -> bool:
    """判断查询词是否为已知城市（用 Haversine 附近模式）"""
    return query in CITY_COORDS


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
    """筛选指定坐标 radius_km 范围内的地震，按距离排序"""
    nearby = []
    for r in records:
        try:
            eq_lat = float(r.get("latitude", 0))
            eq_lon = float(r.get("longitude", 0))
            dist = _haversine_distance(lat, lon, eq_lat, eq_lon)
            if dist <= radius_km:
                nearby.append((dist, r))
        except (ValueError, TypeError):
            continue

    nearby.sort(key=lambda x: x[0])
    return [r for _, r in nearby]


def _resolve_location(records: List[Dict], location: str) -> Tuple[List[Dict], str]:
    """
    根据地点查询策略解析地震记录

    策略：
      - 省份     -> 字符串匹配（location 字段子串匹配）
      - 城市     -> Haversine 附近模式（以城市坐标为圆心，半径 nearby_radius km）
      - 其他     -> 尝试字符串匹配作为兜底

    返回: (匹配记录列表, 模式描述)
    """
    if _is_province(location):
        matched = _filter_by_location(records, location)
        return matched, f"地点匹配：{location}"

    if _is_city(location):
        lat, lon = CITY_COORDS[location]
        matched = _filter_nearby(records, lat, lon)
        return matched, f"{location}附近（{int(NEARBY_RADIUS)}km内）"

    # 兜底：字符串匹配（可能匹配到国家名、地区名等）
    matched = _filter_by_location(records, location)
    return matched, f"关键词匹配：{location}"


def _format_earthquake_text(records: List[Dict], mode_desc: str = "") -> str:
    """将地震数据列表格式化为群聊可读的纯文本消息"""
    if not records:
        if mode_desc:
            return f"近期未找到{mode_desc}的地震记录。"
        return "近期无地震记录。"

    header = f"🌍 最近 {len(records)} 条地震信息（来源：中国地震台网）"
    if mode_desc:
        header += f" ｜ {mode_desc}"
    time_range = _get_time_range(records)
    if time_range:
        header += f"\n📅 {time_range}"
    lines = [header + "\n"]

    for i, eq in enumerate(records, 1):
        o_time   = eq.get("time", "未知")
        mag      = eq.get("magnitude", "?")
        lat      = eq.get("latitude", "?")
        lon      = eq.get("longitude", "?")
        depth    = eq.get("depth", "?")
        location = eq.get("location", "未知")

        lines.append(
            f"{i}. 📍 {location}\n"
            f"   震级 {mag}  |  时间 {o_time}\n"
            f"   纬度 {lat}  经度 {lon}  |  深度 {depth}km\n"
        )

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
                f"⚠️ 大地震速报 ⚠️\n"
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
      !地震 四川     -> 四川省内最近 5 条（省份字符串匹配）
      !地震 成都     -> 成都附近 500km 内最近 5 条（城市 Haversine）
      !地震 四川 4   -> 四川省内震级 >= 4.0 的最近 5 条
      !地震 秘鲁     -> 含"秘鲁"的最近 5 条（关键词匹配）

    数据来源：CENC 官网，覆盖当年全量地震（约600+条），实时更新
    """
    raw_arg = args.extract_plain_text().strip()
    min_mag, location_filter = _parse_user_args(raw_arg)

    # 拉取全量数据
    records = await _fetch_cenc_earthquake_data()
    if records is None:
        await earthquake_cmd.finish("获取地震信息失败，请稍后重试。")

    # 地点筛选
    if location_filter:
        matched, mode_desc = _resolve_location(records, location_filter)
    else:
        matched = records
        mode_desc = ""

    # 震级筛选
    if min_mag > 0:
        matched = _filter_by_magnitude(matched, min_mag)
        mag_desc = f"震级≥{min_mag}"
        mode_desc = f"{mode_desc} ｜ {mag_desc}" if mode_desc else mag_desc

    # 截取最多 max_results 条
    result = matched[:MAX_RESULTS]

    if not result:
        time_range = _get_time_range(records)
        if mode_desc:
            msg = f"近期未找到{mode_desc}的地震记录。"
        else:
            msg = "近期无地震记录。"
        if time_range:
            msg += f"\n当前数据范围：{time_range}（共{len(records)}条）"
        await earthquake_cmd.finish(msg)

    msg = _format_earthquake_text(result, mode_desc)
    await earthquake_cmd.finish(msg)
