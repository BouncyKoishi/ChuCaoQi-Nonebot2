"""
图片归档服务模块

提供图片审核、分类、删除等业务逻辑（bot 与 web 共用）
从 bot/plugins/pic_archive.py 提取，消除两端代码重复
"""

import os
import glob
import shutil
import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import urlretrieve
from typing import Dict, Any, List, Optional, Tuple, Set

import sys

from core.config import plugin_config, DATA_DIR


# ==================== 路径与分类定义 ====================

def get_base_pic_path() -> str:
    """图片归档根路径"""
    return os.path.join(DATA_DIR, 'picArchive')


def get_save_path() -> str:
    """私藏目录路径"""
    return os.path.join(get_base_pic_path(), '私藏')


def get_examine_path() -> str:
    """待分类目录路径"""
    return os.path.join(get_base_pic_path(), '待分类')


# 分类定义（仅含元数据，onlineFilePaths 运行时缓存由 bot 插件维护）
ARCHIVE_INFO: Dict[str, Dict[str, str]] = {
    "jun": {"onlinePath": os.path.join(get_base_pic_path(), 'jun', 'online'), "displayName": "罗俊"},
    "junOrigin": {"onlinePath": os.path.join(get_base_pic_path(), 'jun', 'origin'), "displayName": "纯净罗俊"},
    "xhb": {"onlinePath": os.path.join(get_base_pic_path(), 'xhb'), "displayName": "xhb"},
    "tudou": {"onlinePath": os.path.join(get_base_pic_path(), '土豆泥'), "displayName": "土豆"},
    "zundamon": {"onlinePath": os.path.join(get_base_pic_path(), '豆包2.0'), "displayName": "俊达萌"},
    "zundamon2": {"onlinePath": os.path.join(get_base_pic_path(), '豆包'), "displayName": "俊达萌美图"},
    "pusheen": {"onlinePath": os.path.join(get_base_pic_path(), 'libmmc'), "displayName": "猫猫虫"},
    "cat": {"onlinePath": os.path.join(get_base_pic_path(), 'cat'), "displayName": "怪猫"},
    "251": {"onlinePath": os.path.join(get_base_pic_path(), '251图库'), "displayName": "251"},
    "xiba": {"onlinePath": os.path.join(get_base_pic_path(), '西八兔子图库'), "displayName": "西八兔"},
    "nczw": {"onlinePath": os.path.join(get_base_pic_path(), '鸟澄珠乌'), "displayName": "鸟澄珠乌"},
    "fumo": {"onlinePath": os.path.join(get_base_pic_path(), 'Fumo Emoji'), "displayName": "Fumo Emoji"},
}


def get_archive_list() -> List[Dict[str, str]]:
    """获取分类列表（供前端渲染分类按钮）"""
    return [
        {'key': k, 'name': v['displayName']}
        for k, v in ARCHIVE_INFO.items()
    ]


# ==================== 文件名解析 ====================

def parse_pic_filename(filename: str) -> Dict[str, Any]:
    """从文件名解析上传者信息

    文件命名规则: {user_id}-{timestamp}-{pic_{i}}{ext}
    其中 user_id 在 OneBot V11 平台即为 QQ 号
    """
    base = os.path.splitext(filename)[0]
    parts = base.split('-', 2)
    if len(parts) >= 1 and parts[0].isdigit():
        return {'uploaderQQ': parts[0]}
    return {'uploaderQQ': None}


# ==================== 待审核图片查询 ====================

def get_pending_pics() -> List[Dict[str, Any]]:
    """获取待审核图片列表（从 pic_archive.py getExamineFiles 提取）"""
    examine_path = get_examine_path()
    if not os.path.exists(examine_path):
        return []

    result = []
    for file_path in glob.glob(os.path.join(examine_path, '*')):
        if not os.path.isfile(file_path):
            continue
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        info = parse_pic_filename(filename)
        result.append({
            'filename': filename,
            'size': size,
            'sizeStr': _format_size(size),
            'uploaderQQ': info['uploaderQQ'],
        })
    return result


def _format_size(size: int) -> str:
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size / 1024 / 1024:.2f} MB'


def _safe_examine_path(filename: str) -> Optional[str]:
    """安全解析待审核图片路径，防止路径穿越

    通过 basename 清洗 + realpath 起始校验双重保险，
    确保解析后的绝对路径仍位于待分类目录内。
    """
    examine_real = os.path.realpath(get_examine_path())
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in ('.', '..'):
        return None
    resolved = os.path.realpath(os.path.join(examine_real, safe_name))
    if not (resolved == examine_real or resolved.startswith(examine_real + os.sep)):
        return None
    return resolved


def get_pic_abs_path(filename: str) -> Optional[str]:
    """获取待审核图片的绝对路径（用于 FileResponse）"""
    path = _safe_examine_path(filename)
    if path and os.path.isfile(path):
        return path
    return None


# ==================== 图片操作（分类/删除/私藏） ====================

def classify_pic(filename: str, category_key: str) -> Dict[str, Any]:
    """将待审核图片移动到指定分类目录

    从 pic_archive.py examinepic 指令的数字分支提取
    """
    if category_key not in ARCHIVE_INFO:
        return {'success': False, 'error': '无效的分类'}

    src_path = _safe_examine_path(filename)
    if not src_path or not os.path.isfile(src_path):
        return {'success': False, 'error': '文件不存在'}

    safe_name = os.path.basename(src_path)
    target_dir = ARCHIVE_INFO[category_key]['onlinePath']
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, safe_name)
    shutil.move(src_path, target_path)

    return {
        'success': True,
        'message': f'已分类到 {ARCHIVE_INFO[category_key]["displayName"]}',
        'category': category_key,
        'displayName': ARCHIVE_INFO[category_key]['displayName']
    }


def delete_pic(filename: str) -> Dict[str, Any]:
    """删除待审核图片

    从 pic_archive.py examinepic 指令的 'd' 分支提取
    """
    src_path = _safe_examine_path(filename)
    if not src_path or not os.path.isfile(src_path):
        return {'success': False, 'error': '文件不存在'}

    os.remove(src_path)
    return {'success': True, 'message': '已删除'}


def save_pic(filename: str) -> Dict[str, Any]:
    """将待审核图片移动到私藏目录

    从 pic_archive.py examinepic 指令的 's' 分支提取
    """
    src_path = _safe_examine_path(filename)
    if not src_path or not os.path.isfile(src_path):
        return {'success': False, 'error': '文件不存在'}

    safe_name = os.path.basename(src_path)
    save_dir = get_save_path()
    os.makedirs(save_dir, exist_ok=True)
    target_path = os.path.join(save_dir, safe_name)
    shutil.move(src_path, target_path)

    return {'success': True, 'message': '已移到私藏'}


def skip_pic(filename: str) -> Dict[str, Any]:
    """跳过图片（不做任何操作，仅返回确认）"""
    src_path = _safe_examine_path(filename)
    if not src_path or not os.path.isfile(src_path):
        return {'success': False, 'error': '文件不存在'}
    return {'success': True, 'message': '已跳过'}


# ==================== MD5 索引（bot 端 commitpic 用于查重） ====================

def compute_md5(file_path: str) -> str:
    """计算文件 MD5"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def build_md5_index() -> Tuple[Set[str], int]:
    """构建全图库 MD5 索引

    返回 (md5_set, total_count)
    bot 端启动时调用，用于 commitpic 查重
    """
    md5_set: Set[str] = set()
    all_dirs = [get_examine_path(), get_save_path()] + [v['onlinePath'] for v in ARCHIVE_INFO.values()]
    total = 0
    for dir_path in all_dirs:
        if not os.path.exists(dir_path):
            continue
        for file_path in glob.glob(os.path.join(dir_path, '*')):
            if not os.path.isfile(file_path):
                continue
            try:
                md5_set.add(compute_md5(file_path))
                total += 1
            except Exception:
                pass
    return md5_set, total


# ==================== 图片下载与查重（bot 端 commitpic 用） ====================

def _extract_ext_from_url(url: str) -> str:
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5 and ext.lstrip('.').isalnum():
        return ext
    return '.jpg'


def download_and_check_dup(img_urls: List[str], user_id: int, md5_set: Set[str]) -> Tuple[int, int, Set[str]]:
    """下载图片到待分类目录并查重（带 MD5 查重）

    从 pic_archive.py _download_and_check_dup 提取
    bot 端 commitpic 指令调用，传入 bot 维护的 md5_set

    Returns:
        (success_count, duplicate_count, updated_md5_set)
    """
    examine_path = get_examine_path()
    os.makedirs(examine_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    success_count = 0
    duplicate_count = 0

    for i, url in enumerate(img_urls):
        ext = _extract_ext_from_url(url)
        safe_filename = re.sub(r'[^\w\.-]', '_', f"pic_{i}") + ext
        new_filename = f'{user_id}-{timestamp}-{safe_filename}'
        file_path = os.path.join(examine_path, new_filename)
        try:
            urlretrieve(url, file_path)
            file_md5 = compute_md5(file_path)
            if file_md5 in md5_set:
                os.remove(file_path)
                duplicate_count += 1
            else:
                md5_set.add(file_md5)
                success_count += 1
        except Exception:
            pass
    return success_count, duplicate_count, md5_set
