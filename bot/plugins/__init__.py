"""
生草系统 Bot 插件包 - NoneBot2 版本
"""

from nonebot import require

# 加载定时任务插件
try:
    require("nonebot_plugin_apscheduler")
    from nonebot_plugin_apscheduler import scheduler
except Exception as e:
    print(f"加载定时任务插件失败: {e}")
    scheduler = None
