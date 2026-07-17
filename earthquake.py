"""
地震查询插件 - NoneBot2 版本
查询中国地震台网（CENC）最新地震信息
"""

# ==================== 导入模块 ====================

import re
import json
import httpx
from typing import Optional, List, Dict

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message

from kusa_base import plugin_config

# 定时任务调度器，定时推送大地震预警
try:
    from nonebot_plugin_apscheduler import scheduler
except ImportError:
    scheduler = None

# OneBot 消息段，发送图片
try:
    from nonebot.adapters.onebot.v11 import MessageSegment
except ImportError:
    MessageSegment = None


# ==================== 常量定义 ====================

# 直接访问 ceic.ac.cn 被防火墙拦截，改用第三方代理 api.wolfx.jp
# 数据来源仍是CENC，每 5 分钟同步一次
CENC_API_URL = "https://api.wolfx.jp/cenc_eqlist.json"

# 请求头伪装：从配置文件读取 User-Agent
USER_AGENT = plugin_config.get('web', {}).get('userAgent',
    'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Mobile Safari/537.36'
)

# 默认查询条数和最大限制
DEFAULT_COUNT = 6       # 无参数时默认返回条数
MAX_COUNT = 20          # 最多允许查询条数

# 大地震预警阈值，震级 >= 此值触发推送，单位：级
BIG_EARTHQUAKE_THRESHOLD = 5.0

# 大地震预警推送的目标群号，0 表示不推送
EARTHQUAKE_ALERT_GROUP = 0

# 记录已推送过的地震 ID，防止重复推送，程序重启后清空
_PUSHED_IDS: set = set()


# ==================== 命令注册 ====================

# 监听 !地震 或 /地震
earthquake_cmd = on_command("地震", priority=5, block=True)


# ==================== 工具函数 ====================

def _parse_user_args(raw_arg: str) -> int:
    """
    解析用户 !地震 命令后面的参数，提取出想要查询的条数

    参数解析规则：
      - 输入为空      → 返回默认值 6
      - 输入 "10"     → 返回 10
      - 输入 "四川 5"  → 提取第一个数字 5 返回
      - 输入 "abc"    → 没有数字，返回默认值 6
      - 输入 "50"     → 超出上限，截断为 MAX_COUNT (20)
    """
    if not raw_arg:
        return DEFAULT_COUNT

    # 正则提取参数中第一个连续数字
    match = re.search(r'\d+', raw_arg)
    if not match:
        return DEFAULT_COUNT

    num = int(match.group())
    # 限制在 1 ~ MAX_COUNT 之间（至少查 1 条）
    return max(1, min(num, MAX_COUNT))


async def _fetch_cenc_earthquake_data(count: int = DEFAULT_COUNT) -> Optional[List[Dict]]:
    """
    数据来源：api.wolfx.jp（CENC 数据第三方代理，每 5 分钟同步一次）

    API 返回格式（JSON）：
      {
        "No1": {
          "type": "reviewed",        ← 数据类型（reviewed = 正式速报）
          "EventID": "CD.202607...", ← 地震事件唯一 ID
          "time": "2026-07-17 10:41:25",   ← 发震时刻
          "magnitude": "3.3",        ← 震级
          "latitude": "41.36",       ← 纬度
          "longitude": "83.46",      ← 经度
          "depth": "14",             ← 深度(km)
          "location": "新疆阿克苏...",   ← 参考位置
          "intensity": "4"           ← 烈度
        },
        "No2": { ... },
        ...
      }

    Args:
        count: 查询条数，默认 6

    Returns:
        地震记录列表（转为 [{...}, {...}] 格式），失败返回 None
    """
    # 获取代理配置
    proxy = plugin_config.get('web', {}).get('proxy', '')

    try:
        # 使用 httpx.AsyncClient 进行异步 HTTP 请求
        async with httpx.AsyncClient(proxy=proxy if proxy else None) as client:
            resp = await client.get(
                CENC_API_URL,
                headers={"User-Agent": USER_AGENT},    # 请求头伪装
                timeout=15                             # 15 秒超时
            )

            # HTTP 状态码检查
            if resp.status_code != 200:
                print(f"[地震] HTTP 请求失败，状态码: {resp.status_code}")
                return None

            data = resp.json()

            # 返回格式是 {No1: {...}, No2: {...}, ...}
            # 按序提取 No1~No{count}，转为列表
            records = []
            for i in range(1, count + 1):
                key = f"No{i}"
                if key in data:
                    records.append(data[key])

            print(f"[地震] 成功获取 {len(records)} 条地震数据")
            return records

    except json.JSONDecodeError as e:
        # JSON 解析失败
        print(f"[地震] JSON 解析失败: {e}")
        return None
    except httpx.TimeoutException:
        # 请求超时
        print(f"[地震] 请求超时（15秒）")
        return None
    except Exception as e:
        # 异常捕获
        print(f"[地震] 请求异常: {type(e).__name__}: {e}")
        return None


def _format_earthquake_text(records: List[Dict]) -> str:
    """
    将地震数据列表格式化为群聊可读的纯文本消息

    每条地震显示格式：
        1. 📍 参考位置
           震级 5.2  |  烈度 6度  |  时间 2026-07-17 14:30
           纬度 31.25  经度 103.48  |  深度 10km

    Args:
        records: 地震记录列表（来自 _fetch_cenc_earthquake_data）

    Returns:
        格式化后的字符串，可直接用 cmd.finish() 发送
    """
    if not records:
        return "近期无地震记录。"

    # 用列表收集每一行，最后用 \n 拼接
    lines = [f"🌍 最近 {len(records)} 条地震信息（来源：中国地震台网）\n"]

    for i, eq in enumerate(records, 1):
        # dict.get() 设置缺省值
        # Wolfx API 字段名与原 CENC 不同，注意映射
        o_time   = eq.get("time", "未知")              # 发震时刻
        mag      = eq.get("magnitude", "?")            # 震级
        lat      = eq.get("latitude", "?")             # 纬度
        lon      = eq.get("longitude", "?")            # 经度
        depth    = eq.get("depth", "?")                # 深度(km)
        location = eq.get("location", "未知")           # 参考位置
        intensity = eq.get("intensity", "?")           # 烈度（中国地震烈度）

        # 拼接单条记录（比原 CENC 多显示烈度信息）
        lines.append(
            f"{i}. 📍 {location}\n"
            f"   震级 {mag}  |  烈度 {intensity}度  |  时间 {o_time}\n"
            f"   纬度 {lat}  经度 {lon}  |  深度 {depth}km\n"
        )

    return "\n".join(lines)


# ==================== 大地震筛选 ====================

def _has_big_earthquake(records: List[Dict]) -> List[Dict]:
    """
    从记录中筛选出达到预警阈值的大地震

    Args:
        records: 所有地震记录

    Returns:
        震级 >= BIG_EARTHQUAKE_THRESHOLD 且未推送过的记录列表
    """
    big_ones = []
    for eq in records:
        eq_id = eq.get("EventID")
        mag = eq.get("magnitude", "0")
        try:
            mag_val = float(mag)
        except (ValueError, TypeError):
            continue

        # 震级达标 且 未推送过
        if mag_val >= BIG_EARTHQUAKE_THRESHOLD and eq_id not in _PUSHED_IDS:
            big_ones.append(eq)
            _PUSHED_IDS.add(eq_id)  # 标记为已推送

    return big_ones


# ==================== 大地震定时预警推送 ====================

if scheduler:
    @scheduler.scheduled_job('interval', minutes=5, misfire_grace_time=60)
    async def earthquake_alert_task():
        """
        每 5 分钟自动检查一次，如果出现 >=5 级大地震则推送到指定群

        只有 EARTHQUAKE_ALERT_GROUP 不为 0 时才实际推送
        """
        if EARTHQUAKE_ALERT_GROUP == 0:
            return  # 未配置推送群号，跳过

        records = await _fetch_cenc_earthquake_data(count=10)
        if not records:
            return

        big_ones = _has_big_earthquake(records)
        if not big_ones:
            return

        # 逐条发送大地震预警
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

            # 导入并调用发送群消息函数
            from kusa_base import send_group_msg
            await send_group_msg(EARTHQUAKE_ALERT_GROUP, alert_msg)


# ==================== 命令处理函数（主入口）====================

@earthquake_cmd.handle()
async def handle_earthquake(args: Message = CommandArg()):
    """
    处理 !地震 命令

    用法示例：
      !地震        → 查询最近 6 条地震
      !地震 10     → 查询最近 10 条地震
      !地震 3      → 查询最近 3 条地震

    执行流程：
      1. 提取并解析用户参数
      2. 调用 CENC API 获取数据
      3. 格式化数据为文本
      4. 通过 cmd.finish() 发送到群聊
    """
    # 提取命令参数
    raw_arg = args.extract_plain_text().strip()

    # 解析参数
    count = _parse_user_args(raw_arg)

    # 异步调用 CENC API
    records = await _fetch_cenc_earthquake_data(count)

    # 错误处理
    if records is None:
        # API 请求失败
        await earthquake_cmd.finish("获取地震信息失败，请稍后重试。")

    # 格式化并发送
    msg = _format_earthquake_text(records)
    await earthquake_cmd.finish(msg)