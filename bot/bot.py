#!/usr/bin/env python3
"""
生草系统 Bot - NoneBot2 入口文件
支持 OneBot V11 和 QQ 官方 Bot 协议
"""

import sys
import os

# 确保工作目录正确
bot_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(bot_dir)
sys.path.insert(0, bot_dir)

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

# 尝试导入QQ适配器，如果已安装
try:
    from nonebot.adapters.qq import Adapter as QQAdapter
    QQ_ADAPTER_AVAILABLE = True
    print("[OK] QQ adapter available")
except ImportError:
    QQ_ADAPTER_AVAILABLE = False
    print("[WARN] QQ adapter not installed, OneBot V11 only")

# 初始化 NoneBot，设置命令前缀
nonebot.init(command_start={"/", "!"})

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 注册QQ适配器（如果可用）- 添加错误处理
if QQ_ADAPTER_AVAILABLE:
    try:
        driver.register_adapter(QQAdapter)
        print("[OK] QQ adapter registered")
    except Exception as e:
        print(f"[WARN] QQ adapter registration failed: {e}")
        QQ_ADAPTER_AVAILABLE = False

# 在 NoneBot 启动时初始化数据库（在同一个事件循环中）
@driver.on_startup
async def init_database():
    """初始化数据库"""
    import dbConnection.db as base_db
    await base_db.init_db()
    print("--- Database initialized on startup ---")

# 添加全局错误处理，防止连接错误导致 Bot 退出
@driver.on_startup
async def setup_error_handling():
    """设置全局错误处理"""
    import asyncio
    import logging
    
    logger = logging.getLogger("nonebot")
    
    # 获取当前事件循环
    loop = asyncio.get_event_loop()
    
    # 设置全局异常处理器
    def global_exception_handler(loop, context):
        exception = context.get("exception")
        message = context.get("message", "")
        
        # 检查是否是连接错误
        if exception:
            import httpx
            if isinstance(exception, httpx.ConnectError):
                logger.warning(f"网络连接错误（可能是VPN问题）: {message}")
                logger.warning("Bot 将继续运行，稍后会自动重试连接...")
                return
            elif isinstance(exception, ConnectionError):
                logger.warning(f"连接错误: {message}")
                logger.warning("Bot 将继续运行，稍后会自动重试连接...")
                return
            elif "ConnectError" in str(type(exception)):
                logger.warning(f"网络连接错误: {message}")
                logger.warning("Bot 将继续运行，稍后会自动重试连接...")
                return
        
        # 其他异常正常处理
        logger.error(f"未处理的异常: {context}")
        if exception:
            logger.exception(exception)
    
    loop.set_exception_handler(global_exception_handler)
    print("[OK] Global exception handler configured")

# 加载插件
nonebot.load_plugins("plugins")

# 运行 Bot
if __name__ == "__main__":
    nonebot.run()
