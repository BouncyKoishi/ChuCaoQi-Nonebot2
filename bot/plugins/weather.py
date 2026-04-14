"""
天气/台风查询插件 - NoneBot2 版本
支持台风查询、雷达回波图查询及GIF动态图、降雨预报及大雨预警
"""

import re
import os
import asyncio
import hashlib
import httpx
from io import BytesIO
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message

from kusa_base import plugin_config, send_group_msg

try:
    from nonebot_plugin_apscheduler import scheduler
except ImportError:
    scheduler = None

try:
    from nonebot.adapters.onebot.v11 import MessageSegment
except ImportError:
    MessageSegment = None

HEAVY_RAIN_THRESHOLD = 2.5
RAIN_ALERT_GROUP = 597468560
CAMPUS_HEAVY_RAIN_LAST: Dict[str, datetime] = {}
_PRECIP_CACHE: Dict[str, Tuple[dict, str]] = {}

USER_AGENT = plugin_config.get('web', {}).get('userAgent', 'Mozilla/5.0')
CMA_INDEX_URL = "http://www.nmc.cn/publish/typhoon/typhoon_new.html"
CMA_DETAIL_URL = "http://www.nmc.cn/f/rest/getContent?dataId="
NMC_RADAR_BASE_URL = "http://www.nmc.cn/publish/radar/"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "radar")
GIF_CACHE_DIR = os.path.join(CACHE_DIR, "gif")

MAX_GIF_SIZE = 1024 * 1024
GIF_DURATION = 200
MAX_FRAMES = 30

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(GIF_CACHE_DIR, exist_ok=True)

SYSU_CAMPUSES = {
    '南校园': (23.1061, 113.3245),
    '北校园': (23.1272, 113.3118),
    '东校园': (23.0677, 113.3918),
    '珠海校区': (22.3626, 113.5400),
    '深圳校区': (22.7997, 113.9598),
}

RADAR_NAME_DICT = {
    '全国': 'chinaall.html', '华北': 'huabei.html', '东北': 'dongbei.html', '华东': 'huadong.html',
    '华中': 'huazhong.html', '华南': 'huanan.html', '西南': 'xinan.html', '西北': 'xibei.html',
    '海口': 'hai-nan/hai-kou.htm', '三亚': 'hai-nan/san-ya.htm', '三沙': 'hai-nan/san-sha.htm',
    '广州': 'guang-dong/guang-zhou.htm', '韶关': 'guang-dong/shao-guan.htm', '梅州': 'guang-dong/mei-zhou.htm',
    '阳江': 'guang-dong/yang-jiang.htm', '汕头': 'guang-dong/shan-tou.htm', '深圳': 'guang-dong/shen-zhen.htm',
    '湛江': 'guang-dong/zhan-jiang.htm', '河源': 'guang-dong/he-yuan.htm', '汕尾': 'guang-dong/shan-wei.htm',
    '肇庆': 'guang-dong/zhao-qing.htm', '连州': 'guang-dong/lian-zhou.htm', '福州': 'fu-jian/fu-zhou.htm',
    '厦门': 'fu-jian/xia-men.htm', '杭州': 'zhe-jiang/hang-zhou.htm', '宁波': 'zhe-jiang/ning-bo.htm',
    '温州': 'zhe-jiang/wen-zhou.htm', '嵊泗': 'zhe-jiang/cheng-si.htm', '金华': 'zhe-jiang/jin-hua.htm',
    '上海': 'shang-hai/qing-pu.htm', '南京': 'jiang-su/nan-jing.htm', '北京': 'bei-jing/da-xing.htm',
    '天津': 'tian-jin/tian-jin.htm', '石家庄': 'he-bei/shi-jia-zhuang.htm',
    '太原': 'shan-xi/tai-yuan.htm', '呼和浩特': 'nei-meng/hu-he-hao-te.htm', '南宁': 'guang-xi/nan-ning.htm',
    '沈阳': 'liao-ning/shen-yang.htm', '长春': 'ji-lin/chang-chun.htm', '哈尔滨': 'hei-long-jiang/ha-er-bin.htm',
    '合肥': 'an-hui/he-fei.htm', '南昌': 'jiang-xi/nan-chang.htm', '济南': 'shan-dong/ji-nan.htm',
    '郑州': 'he-nan/zheng-zhou.htm', '武汉': 'hu-bei/wu-han.htm', '长沙': 'hu-nan/chang-sha.htm',
    '重庆': 'chong-qing/chong-qing.htm', '成都': 'si-chuan/cheng-du.htm', '贵阳': 'gui-zhou/gui-yang.htm',
    '昆明': 'yun-nan/kun-ming.htm', '拉萨': 'xi-zang/la-sa.htm', '西安': 'shan-xi/xi-an.htm',
    '兰州': 'gan-su/lan-zhou.htm', '西宁': 'qing-hai/xin-ning.htm', '银川': 'ning-xia/yin-chuan.htm',
    '乌鲁木齐': 'xin-jiang/wu-lu-mu-qi.htm'
}

GIF_FLAG = '-gif'

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "font")

def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    font_path = os.path.join(_FONT_DIR, name)
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

try:
    _FONT = _load_font("HarmonyOS_Sans_SC_Medium.ttf", 13)
    _FONT_BOLD = _load_font("HarmonyOS_Sans_SC_Bold.ttf", 14)
    _FONT_SMALL = _load_font("HarmonyOS_Sans_SC_Light.ttf", 11)
    _FONT_TITLE = _load_font("HarmonyOS_Sans_SC_Bold.ttf", 16)
except Exception:
    _FONT = ImageFont.load_default()
    _FONT_BOLD = _FONT
    _FONT_SMALL = _FONT
    _FONT_TITLE = _FONT

typhoon_cmd = on_command("台风", priority=5, block=True)
radar_cmd = on_command("雷达回波", priority=5, block=True, aliases={"雷达"})
precip_cmd = on_command("降雨", priority=5, block=True, aliases={"降水"})


# ==================== 工具函数 ====================

def _get_timestamp_hash(region: str, timestamps: List[str]) -> str:
    key = f"{region}_{'_'.join(timestamps[:10])}"
    return hashlib.md5(key.encode()).hexdigest()


def _get_cached_gif_path(region: str, timestamps: List[str]) -> Optional[str]:
    cache_key = _get_timestamp_hash(region, timestamps)
    cached_path = os.path.join(GIF_CACHE_DIR, f"{cache_key}.gif")
    if os.path.exists(cached_path):
        stat = os.stat(cached_path)
        if datetime.fromtimestamp(stat.st_mtime) > datetime.now() - timedelta(minutes=10):
            return cached_path
    return None


def _save_gif_to_cache(region: str, timestamps: List[str], gif_data: bytes) -> str:
    cache_key = _get_timestamp_hash(region, timestamps)
    cached_path = os.path.join(GIF_CACHE_DIR, f"{cache_key}.gif")
    with open(cached_path, 'wb') as f:
        f.write(gif_data)
    return cached_path


def _resize_image(img: Image.Image, max_size: int = 1200) -> Image.Image:
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        return img.resize(new_size, Image.LANCZOS)
    return img


def _create_gif(images: list, duration: int = GIF_DURATION) -> Optional[bytes]:
    if not images:
        return None

    try:
        for i, img in enumerate(images):
            if img.mode != 'RGB':
                images[i] = img.convert('RGB')

        output = BytesIO()
        images[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0,
            optimize=True
        )
        gif_data = output.getvalue()

        if len(gif_data) > MAX_GIF_SIZE:
            resized_images = []
            target_size = 600
            for img in images:
                if max(img.size) > target_size:
                    ratio = target_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    resized_images.append(img.resize(new_size, Image.LANCZOS))
                else:
                    resized_images.append(img)

            output = BytesIO()
            resized_images[0].save(
                output,
                format='GIF',
                save_all=True,
                append_images=resized_images[1:],
                duration=duration,
                loop=0,
                optimize=True
            )
            gif_data = output.getvalue()

        return gif_data
    except Exception as e:
        print(f"[雷达GIF] 创建GIF失败: {e}")
        return None


def _parse_radar_args(raw_args: str) -> Tuple[Optional[str], bool]:
    if not raw_args:
        return None, False

    args = raw_args.strip()

    if args.endswith(GIF_FLAG):
        potential_region = args[:-len(GIF_FLAG)].strip()
        if potential_region and potential_region in RADAR_NAME_DICT:
            return potential_region, True
        region_candidates = [k for k in RADAR_NAME_DICT.keys() if potential_region.startswith(k)]
        if region_candidates:
            longest = max(region_candidates, key=len)
            if args.endswith(longest + GIF_FLAG) or args == longest + GIF_FLAG:
                return longest, True
    elif args.startswith(GIF_FLAG):
        potential_region = args[len(GIF_FLAG):].strip()
        if potential_region and potential_region in RADAR_NAME_DICT:
            return potential_region, True
        region_candidates = [k for k in RADAR_NAME_DICT.keys() if potential_region.startswith(k)]
        if region_candidates:
            longest = max(region_candidates, key=len)
            if args.startswith(GIF_FLAG + longest) or args.startswith(longest + GIF_FLAG):
                return longest, True

    if args in RADAR_NAME_DICT:
        return args, False

    region_candidates = [k for k in RADAR_NAME_DICT.keys() if args.startswith(k)]
    if region_candidates:
        return max(region_candidates, key=len), False

    return None, False


# ==================== 台风模块 ====================

@typhoon_cmd.handle()
async def handle_typhoon(args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    prev_amount = _get_prev_amount(stripped_arg)
    time_data = await _get_cma_time(CMA_INDEX_URL)

    if not time_data:
        await typhoon_cmd.finish('获取台风信息失败，请稍后重试。')

    cma_report = await _get_cma_simple_report(time_data[prev_amount].get('data-id') if time_data else None)
    await typhoon_cmd.finish(cma_report + "\n具体路径信息：http://typhoon.zjwater.gov.cn")


def _get_prev_amount(stripped_arg: str) -> int:
    if "prev" not in stripped_arg:
        return 0
    prev_str = re.findall(r'(?<=prev)\d+', stripped_arg)
    if not prev_str:
        return 1
    return int(prev_str[0])


async def _get_cma_time(url: str):
    try:
        page_data = await _get_web_page_data(url)
        if not page_data:
            return None
        bs_data = BeautifulSoup(page_data, "html.parser")
        return bs_data("p", "time")
    except Exception as e:
        print(f'[台风] 获取时间数据失败: {e}')
        return None


async def _get_cma_simple_report(data_id: Optional[str]) -> str:
    try:
        if data_id:
            report_data = await _get_web_page_data(CMA_DETAIL_URL + data_id)
        else:
            report_data = await _get_web_page_data(CMA_INDEX_URL)

        if not report_data:
            return "获取台风报文失败。"

        report_bs = BeautifulSoup(report_data, "html.parser")

        if "提示：当前无台风，下列产品为上一个台风产品" in report_data:
            return "当前无台风或热带低压。"
        if report_bs("div", "nodata"):
            return "CMA报文编码异常。"

        report_detail = report_bs("div", "writing")[0]
        for tr in report_detail("tr"):
            for td in tr("td"):
                td.string = td.get_text().replace("\xa0", "")
            tr.append("\n")

        return report_detail.get_text()
    except Exception as e:
        print(f'[台风] 获取报文失败: {e}')
        return "获取台风报文失败。"


# ==================== 雷达回波模块 ====================

@radar_cmd.handle()
async def handle_radar(args: Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    region, use_gif = _parse_radar_args(raw_args)

    if not region:
        help_text = (
            f"地区未指定^ ^\n"
            f"使用方式：雷达回波 <地区> [-gif]\n"
            f"示例：雷达回波 全国\n"
            f"示例：雷达回波 广州 -gif\n"
            f"添加 -gif 参数可生成动态GIF图\n"
            f"支持的地区：{'、'.join(RADAR_NAME_DICT.keys())}"
        )
        await radar_cmd.finish(help_text)

    radar_url = NMC_RADAR_BASE_URL + RADAR_NAME_DICT[region]

    if not use_gif:
        print(f'[雷达回波] 正在获取: {radar_url}')
        radar_pic_url = await _get_radar_pic_url(radar_url)

        if not radar_pic_url:
            await radar_cmd.finish("获取雷达回波图失败^ ^")

        async with httpx.AsyncClient() as client:
            response = await client.get(radar_pic_url, timeout=15)
            image_bytes = response.content

        pic = MessageSegment.image(image_bytes)
        await radar_cmd.finish(pic)
    else:
        await radar_cmd.send("正在获取雷达回波GIF，请稍候...")

        gif_data, message = await _generate_radar_gif(region, radar_url)

        if not gif_data:
            await radar_cmd.finish(message)

        pic = MessageSegment.image(gif_data)
        await radar_cmd.finish(pic)


async def _get_radar_pic_url(url: str) -> Optional[str]:
    try:
        page_data = await _get_web_page_data(url)
        if not page_data:
            return None
        bs_data = BeautifulSoup(page_data, "html.parser")
        img_block_div = bs_data("div", "imgblock")[0]
        img_tag = img_block_div("img")[0]
        return img_tag.get("src")
    except Exception as e:
        print(f'[雷达回波] 获取图片URL失败: {e}')
        return None


async def _get_web_page_data(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"[天气] HTTP请求出错: {response.status_code}")
                return None
    except Exception as e:
        print(f"[天气] HTTP请求异常: {e}")
        return None


async def _get_historical_timestamps(radar_url: str) -> List[Tuple[str, str]]:
    try:
        page_data = await _get_web_page_data(radar_url)
        if not page_data:
            return []

        bs_data = BeautifulSoup(page_data, "html.parser")
        timestamps = []

        time_elements = bs_data.find_all("div", class_="time")
        for time_elem in time_elements:
            time_text = time_elem.get_text().strip()
            if re.match(r'\d{2}/\d{2} \d{2}:\d{2}', time_text):
                img_url = time_elem.get("data-img", "")
                if img_url:
                    img_url = img_url.split("?")[0]
                    timestamps.append((time_text, img_url))

        return timestamps
    except Exception as e:
        print(f"[雷达GIF] 获取历史时间戳失败: {e}")
        return []


async def _download_radar_image(image_url: str) -> Optional[bytes]:
    if not image_url:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, headers={"User-Agent": USER_AGENT}, timeout=20)
            if response.status_code == 200 and len(response.content) > 1000:
                return response.content
    except Exception as e:
        print(f"[雷达GIF] 下载失败: {e}")

    return None


def _parse_radar_timestamp(ts_str: str, now: datetime) -> Optional[datetime]:
    try:
        parts = ts_str.split(' ')
        if len(parts) != 2:
            return None
        month_day, hour_min = parts
        m, d = map(int, month_day.split('/'))
        h, mi = map(int, hour_min.split(':'))

        if now.month == m and now.day == d:
            return now.replace(hour=h, minute=mi, second=0)
        elif now.month == m and now.day - d == 1 and h <= now.hour:
            return (now - timedelta(days=1)).replace(hour=h, minute=mi, second=0)
        elif now.month == 1 and m == 12:
            return (now - timedelta(days=30)).replace(hour=h, minute=mi, second=0)
        elif now.month == m + 1 and d >= 28:
            return (now + timedelta(days=1)).replace(day=d, hour=h, minute=mi, second=0)
        else:
            return None
    except Exception:
        return None


async def _generate_radar_gif(region: str, radar_url: str) -> Tuple[Optional[bytes], str]:
    timestamp_url_pairs = await _get_historical_timestamps(radar_url)
    if not timestamp_url_pairs:
        return None, "获取历史时间戳失败，请稍后重试。"

    latest_ts, latest_url = timestamp_url_pairs[0]
    now = datetime.now()
    latest_dt = _parse_radar_timestamp(latest_ts, now) or now

    cutoff_time = latest_dt - timedelta(hours=1)

    valid_pairs = []
    for ts, url in timestamp_url_pairs:
        ts_dt = _parse_radar_timestamp(ts, now)
        if ts_dt and ts_dt >= cutoff_time:
            valid_pairs.append((ts, url))

    if len(valid_pairs) < 3:
        if len(timestamp_url_pairs) >= 3:
            valid_pairs = timestamp_url_pairs[:MAX_FRAMES]
        else:
            return None, f"历史数据不足（{len(timestamp_url_pairs)} 个时间点），无法生成GIF。"

    valid_pairs = valid_pairs[:MAX_FRAMES]

    cached_gif = _get_cached_gif_path(region, [ts for ts, _ in valid_pairs])
    if cached_gif:
        try:
            with open(cached_gif, 'rb') as f:
                gif_data = f.read()
            return gif_data, f"雷达回波GIF（{len(valid_pairs)}帧·缓存）"
        except Exception:
            pass

    images = []
    failed_count = 0

    for ts, img_url in valid_pairs:
        cache_key = hashlib.md5(f"{region}_{ts}".encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.png")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    img_data = f.read()
                img = Image.open(BytesIO(img_data))
                images.append(img)
                continue
            except Exception:
                pass

        img_data = await _download_radar_image(img_url)

        if img_data:
            try:
                img = Image.open(BytesIO(img_data))
                img = _resize_image(img)
                images.append(img)

                with open(cache_file, 'wb') as f:
                    f.write(img_data)
            except Exception as e:
                failed_count += 1
        else:
            failed_count += 1

        await asyncio.sleep(0.2)

    if len(images) < 3:
        return None, f"成功获取 {len(images)} 帧，数据不足无法生成GIF。"

    if failed_count > len(valid_pairs) * 0.5:
        print(f"[雷达GIF] 警告: {failed_count}/{len(valid_pairs)} 帧下载失败")

    images.reverse()

    gif_data = _create_gif(images)
    if not gif_data:
        return None, "GIF生成失败，请稍后重试。"

    if len(images) <= MAX_FRAMES:
        _save_gif_to_cache(region, [ts for ts, _ in valid_pairs], gif_data)

    return gif_data, f"雷达回波GIF（{len(images)}帧）"


async def _get_precipitation_forecast(lat: float, lon: float) -> Optional[dict]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": "precipitation",
        "hourly": "precipitation_probability,weathercode",
        "forecast_days": 2,
        "timezone": "Asia/Shanghai"
    }

    proxy = plugin_config.get('web', {}).get('proxy', '')

    try:
        async with httpx.AsyncClient(proxy=proxy if proxy else None) as client:
            response = await client.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                minutely_15 = data.get("minutely_15", {})
                precipitation = minutely_15.get("precipitation", [])
                times = minutely_15.get("time", [])

                now = datetime.now()
                now_iso = now.isoformat()

                start_idx = None
                for i, t in enumerate(times):
                    if t >= now_iso:
                        start_idx = i
                        break

                if start_idx is None:
                    return None

                result = []
                for i in range(start_idx, min(start_idx + 24, len(times))):
                    dt = datetime.fromisoformat(times[i])
                    p = precipitation[i]
                    result.append({
                        "dt": int(dt.timestamp()),
                        "time": dt.strftime("%H:%M"),
                        "precipitation": p if p is not None else 0
                    })

                hourly = data.get("hourly", {})
                hourly_times = hourly.get("time", [])
                hourly_start_idx = None
                for i, t in enumerate(hourly_times):
                    if t >= now_iso:
                        hourly_start_idx = i
                        break

                hourly_result = []
                if hourly_start_idx is not None:
                    precip_probs = hourly.get("precipitation_probability", [])
                    weather_codes = hourly.get("weathercode", [])
                    for i in range(hourly_start_idx, min(hourly_start_idx + 8, len(hourly_times))):
                        dt = datetime.fromisoformat(hourly_times[i])
                        hourly_result.append({
                            "dt": int(dt.timestamp()),
                            "time": dt.strftime("%H:%M"),
                            "precip_prob": precip_probs[i] if i < len(precip_probs) else None,
                            "weather_code": weather_codes[i] if i < len(weather_codes) else None
                        })

                return {
                    "minutely_15": result,
                    "hourly": hourly_result,
                }
            else:
                print(f"[降雨预报] API错误: {response.status_code}")
                return None
    except Exception as e:
        print(f"[降雨预报] 请求失败: {type(e).__name__}: {e}")
        return None


# ==================== 降雨预报模块 ====================

@precip_cmd.handle()
async def handle_precipitation(event, args: Message = CommandArg()):
    now = datetime.now()
    cache_hour_key = now.strftime("%Y%m%d%H")

    locations_data = {}
    all_cached = True
    need_fetch_keys = []

    for loc_name, (lat, lon) in SYSU_CAMPUSES.items():
        cache_key = f"{lat:.4f}_{lon:.4f}"
        cached_data = _PRECIP_CACHE.get(cache_key)
        if cached_data and cached_data[1] == cache_hour_key:
            locations_data[loc_name] = cached_data[0]
            continue

        all_cached = False
        need_fetch_keys.append((loc_name, lat, lon, cache_key))

    if not all_cached:
        await precip_cmd.send("正在获取降雨预报...")

    for loc_name, lat, lon, cache_key in need_fetch_keys:
        data = await _get_precipitation_forecast(lat, lon)
        if data:
            _PRECIP_CACHE[cache_key] = (data, cache_hour_key)
            locations_data[loc_name] = data
        await asyncio.sleep(0.3)

    if not locations_data:
        await precip_cmd.finish("获取数据失败")

    img_bytes = _generate_precip_image(locations_data)

    await precip_cmd.finish(MessageSegment.image(img_bytes))


def _is_heavy_rain(minutely_15: list) -> bool:
    for item in minutely_15:
        precip = item.get("precipitation", 0)
        if precip is not None and precip >= HEAVY_RAIN_THRESHOLD:
            return True
    return False


def _is_first_heavy_rain(campus_name: str) -> bool:
    last_time = CAMPUS_HEAVY_RAIN_LAST.get(campus_name)
    if last_time is None:
        return True
    if datetime.now() - last_time > timedelta(hours=2):
        return True
    return False


async def _check_and_alert_heavy_rain():
    print(f"[大雨预警] 开始检查各校区降水情况...")
    for campus_name, (lat, lon) in SYSU_CAMPUSES.items():
        data = await _get_precipitation_forecast(lat, lon)
        if not data:
            continue

        minutely_15 = data.get("minutely_15", [])
        if not minutely_15:
            continue

        has_heavy_rain = _is_heavy_rain(minutely_15)
        print(f"[大雨预警] {campus_name}: {'有大雨' if has_heavy_rain else '无大雨'}")

        if has_heavy_rain and _is_first_heavy_rain(campus_name):
            rain_periods = []
            for item in minutely_15:
                precip = item.get("precipitation", 0)
                if precip is not None and precip >= HEAVY_RAIN_THRESHOLD:
                    rain_periods.append(f"{item['time']} {precip:.1f}mm/h")

            alert_msg = (
                f"⚠️ 大雨预警\n"
                f"校区：{campus_name}\n"
                f"未来1小时首次检测到大雨（≥{HEAVY_RAIN_THRESHOLD}mm/h）：\n"
                f"{' | '.join(rain_periods)}\n"
                f"请注意防范！"
            )
            print(f"[大雨预警] 发送预警：{alert_msg}")
            await send_group_msg(RAIN_ALERT_GROUP, alert_msg)
            CAMPUS_HEAVY_RAIN_LAST[campus_name] = datetime.now()
        elif not has_heavy_rain:
            CAMPUS_HEAVY_RAIN_LAST.pop(campus_name, None)


def _generate_precip_image(locations_data: Dict[str, dict]) -> bytes:
    cell_w = 90
    cell_h = 36
    header_h = 38
    margin = 20
    label_w = 80

    try:
        font = _FONT
        font_bold = _FONT_BOLD
        font_small = _FONT_SMALL
        font_title = _FONT_TITLE
    except:
        font = ImageFont.load_default()
        font_bold = font
        font_small = font
        font_title = font

    seen_times = set()
    time_entries = []
    for data in locations_data.values():
        hourly = data.get("hourly", [])
        for item in hourly[:6]:
            time_str = item.get("time", "")
            dt_val = item.get("dt")
            key = (time_str, dt_val)
            if time_str and dt_val and key not in seen_times:
                seen_times.add(key)
                time_entries.append(key)

    time_entries.sort(key=lambda x: x[1])
    times = [t[0] for t in time_entries[:6]]

    loc_names = list(locations_data.keys())
    rows = len(loc_names)
    cols = len(times)

    table_w = label_w + cols * cell_w + margin * 2
    table_h = header_h + rows * cell_h

    rain_campuses = []
    for loc_name in loc_names:
        data = locations_data[loc_name]
        for item in data.get("minutely_15", []):
            if item.get("precipitation", 0) > 0:
                rain_campuses.append(loc_name)
                break

    chart_w = table_w - margin * 2
    chart_h_per = 140
    chart_gap = 15
    chart_area_h = len(rain_campuses) * (chart_h_per + chart_gap) + 35 if rain_campuses else 0

    total_h = 30 + table_h + 20 + chart_area_h + margin * 2

    img_w = max(table_w, 600)
    img = Image.new('RGB', (img_w, total_h), '#FAFAFA')
    draw = ImageDraw.Draw(img)

    y = margin

    draw.text((margin, y), "降雨预报 · 未来6小时", font=font_title, fill='#333')
    y += 28

    x0 = margin

    draw.rectangle([x0, y, x0 + label_w, y + header_h], fill='#4A6FA5', outline='#3A5F95', width=1)
    draw.text((x0 + 8, y + 10), "校区", font=font, fill='white')

    for i, t in enumerate(times):
        xc = x0 + label_w + i * cell_w
        draw.rectangle([xc, y, xc + cell_w, y + header_h], fill='#6B8DBF', outline='#5B7DAF', width=1)
        tw = draw.textlength(t, font=font)
        tx = xc + (cell_w - tw) / 2
        draw.text((tx, y + 10), t, font=font, fill='white')

    y += header_h

    for row_idx, loc_name in enumerate(loc_names):
        yr = y + row_idx * cell_h

        bg_color = '#FFFFFF' if row_idx % 2 == 0 else '#F0F2F5'
        draw.rectangle([x0, yr, x0 + label_w, yr + cell_h], fill='#E8ECF1', outline='#D0D5DD', width=1)
        draw.text((x0 + 6, yr + 10), loc_name, font=font, fill='#333')

        data = locations_data[loc_name]
        hourly = data.get("hourly", [])
        hourly_dict = {item.get("time", ""): item for item in hourly}

        for col_idx, t in enumerate(times):
            xc = x0 + label_w + col_idx * cell_w
            item = hourly_dict.get(t, {})
            prob = item.get("precip_prob", 0) or 0

            if prob >= 80:
                fill_color = '#E57373'
                text_color = 'white'
            elif prob >= 50:
                fill_color = '#FFB74D'
                text_color = 'white'
            elif prob >= 20:
                fill_color = '#90CAF9'
                text_color = '#1a3050'
            else:
                fill_color = '#EEEEEE'
                text_color = '#888'

            draw.rectangle([xc, yr, xc + cell_w, yr + cell_h], fill=fill_color, outline='#CCC', width=1)

            prob_text = f"{prob}%"
            pw = draw.textlength(prob_text, font=font_bold)
            px = xc + (cell_w - pw) / 2
            draw.text((px, yr + 10), prob_text, font=font_bold, fill=text_color)

    y = y + rows * cell_h + 18

    if rain_campuses:
        draw.text((margin, y), "未来6小时降雨量 (mm/h)", font=font_title, fill='#333')
        y += 28

        for loc_name in rain_campuses:
            data = locations_data[loc_name]
            minutely_15 = data.get("minutely_15", [])

            precip_items = minutely_15
            precip_values = [item.get("precipitation", 0) or 0 for item in precip_items]
            time_labels = [item.get("time", "") for item in precip_items]

            max_p = max(precip_values) if any(p > 0 for p in precip_values) else 1.0
            max_p = max(max_p, 1.0)

            cx0 = margin
            cy0 = y
            cy1 = y + chart_h_per
            cw = chart_w
            ch = chart_h_per - 35

            draw.text((cx0, cy0), loc_name, font=font_bold, fill='#333')

            plot_y0 = cy0 + 25
            plot_x0 = cx0 + 40
            plot_x1 = cx0 + cw - 10
            plot_y1 = plot_y0 + ch

            draw.rectangle([plot_x0, plot_y0, plot_x1, plot_y1], fill='#FFF', outline='#DDD', width=1)

            grid_lines = 4
            for gi in range(grid_lines + 1):
                gy = plot_y0 + (ch * gi / grid_lines)
                val = max_p * (grid_lines - gi) / grid_lines
                draw.line([(plot_x0, gy), (plot_x1, gy)], fill='#EEE', width=1)
                label = f"{val:.1f}"
                lw = draw.textlength(label, font=font_small)
                lx = plot_x0 - lw - 4
                ly = gy - 6
                if ly >= plot_y0:
                    draw.text((lx, ly), label, font=font_small, fill='#888')

            plot_w = plot_x1 - plot_x0
            n_points = len(precip_values)
            if n_points >= 1 and max_p > 0:
                bar_width = plot_w / n_points
                bar_gap = min(2, bar_width * 0.2)
                actual_bar_width = bar_width - bar_gap
                
                for i, p in enumerate(precip_values):
                    if p <= 0:
                        continue
                    
                    bar_x = plot_x0 + i * bar_width + bar_gap / 2
                    bar_h = (p / max_p) * ch
                    bar_y = plot_y1 - bar_h
                    
                    bar_left = bar_x
                    bar_top = bar_y
                    bar_right = bar_x + actual_bar_width
                    bar_bottom = plot_y1
                    
                    draw.rectangle([bar_left, bar_top, bar_right, bar_bottom], fill='#4A90D9')

            for i, tl in enumerate(time_labels):
                n_pts = len(time_labels)
                label_interval = max(1, n_pts // 8)
                if i % label_interval != 0 and i != n_pts - 1:
                    continue
                step_x = plot_w / (n_pts - 1) if n_pts > 1 else plot_w
                tx = plot_x0 + i * step_x
                tw = draw.textlength(tl, font=font_small)
                tx_centered = tx - tw / 2
                tx_clamped = max(plot_x0, min(tx_centered, plot_x1 - tw))
                draw.text((tx_clamped, plot_y1 + 3), tl, font=font_small, fill='#666')

            y += chart_h_per + chart_gap

    output = BytesIO()
    img.save(output, format='PNG', quality=95)
    return output.getvalue()


def _clean_radar_cache():
    now = datetime.now()
    cleaned = 0
    
    for f in os.listdir(CACHE_DIR):
        fpath = os.path.join(CACHE_DIR, f)
        if os.path.isdir(fpath):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if f.endswith('.png'):
                if now - mtime > timedelta(hours=1):
                    os.remove(fpath)
                    cleaned += 1
            elif f.endswith('.gif'):
                if now - mtime > timedelta(minutes=30):
                    os.remove(fpath)
                    cleaned += 1
            elif f.endswith('.jpg'):
                if now - mtime > timedelta(minutes=10):
                    os.remove(fpath)
                    cleaned += 1
        except Exception:
            pass
    
    for f in os.listdir(GIF_CACHE_DIR):
        if f.endswith('.gif'):
            fpath = os.path.join(GIF_CACHE_DIR, f)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if now - mtime > timedelta(minutes=30):
                    os.remove(fpath)
                    cleaned += 1
            except Exception:
                pass
    
    if cleaned > 0:
        print(f"[缓存清理] 已清理 {cleaned} 个过期文件")


if scheduler:
    @scheduler.scheduled_job('interval', minutes=30, misfire_grace_time=60)
    async def rain_check_task():
        await _check_and_alert_heavy_rain()

    @scheduler.scheduled_job('interval', hours=1, misfire_grace_time=300)
    def clean_cache_task():
        _clean_radar_cache()