#!/usr/bin/env python3
"""
生草系统 Bot - NoneBot2 入口文件
支持 OneBot V11 和 QQ 官方 Bot 协议
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os

# 确保工作目录正确
bot_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(bot_dir)
sys.path.insert(0, bot_dir)
sys.path.insert(0, os.path.dirname(bot_dir))

# 显式加载 .env 文件（确保配置生效）
from dotenv import load_dotenv
env_path = os.path.join(bot_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print("[OK] dotenv loaded")

# 设置 NO_PROXY 环境变量，排除 QQ 官方 API 的代理
# 这样即使开了 VPN 也能正常连接 QQ 官方 API
qq_api_domains = [
    "api.sgroup.qq.com",
    "sandbox.api.sgroup.qq.com",
    "bot.q.qq.com",
    "q.qq.com",
    "qq.com"
]
existing_no_proxy = os.environ.get("NO_PROXY", "")
if existing_no_proxy:
    os.environ["NO_PROXY"] = existing_no_proxy + "," + ",".join(qq_api_domains)
else:
    os.environ["NO_PROXY"] = ",".join(qq_api_domains)
print(f"[OK] NO_PROXY set: {os.environ['NO_PROXY']}")

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.qq import Adapter as QQAdapter

# 初始化 NoneBot，设置命令前缀
nonebot.init(command_start={"!"})

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 注册QQ适配器
driver.register_adapter(QQAdapter)
print("[OK] QQ adapter registered")

# QQ 官方新增事件类型的兼容处理（GROUP_MESSAGE_CREATE 等），详见 platform_compat
from platform_compat import install_qq_adapter_compat

install_qq_adapter_compat()

# 在 NoneBot 启动时初始化数据库（在同一个事件循环中）
@driver.on_startup
async def init_database():
    """初始化数据库"""
    import core.db.db as base_db
    await base_db.init_db()
    from core.services import identity_service
    await identity_service.load_group_mappings()
    print("--- Database initialized on startup ---")

# 从 pyproject.toml 加载插件配置
nonebot.load_from_toml("pyproject.toml")

# 运行 Bot
if __name__ == "__main__":
    nonebot.run()
