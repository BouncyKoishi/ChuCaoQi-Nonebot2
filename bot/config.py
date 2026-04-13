"""
生草系统 Bot - NoneBot2 配置模块
"""

from typing import Set
from pydantic import BaseModel, Field
from nonebot import get_driver
from nonebot.config import Config as NoneBotConfig


class Config(BaseModel):
    """Bot 配置类"""
    
    # 命令前缀
    command_start: Set[str] = Field(default={"!"})
    
    # 超级管理员
    superusers: Set[str] = Field(default=set())
    
    # 插件配置路径
    plugin_config_path: str = Field(default="config/plugin_config.yaml")
    
    # 数据库路径
    database_path: str = Field(default="database/chuchu.sqlite")


# 全局配置对象
driver = get_driver()

# 从 driver.config 中提取我们需要的配置项
raw_config = {
    "command_start": getattr(driver.config, "command_start", {"!"}),
    "superusers": getattr(driver.config, "superusers", set()),
    "plugin_config_path": getattr(driver.config, "plugin_config_path", "config/plugin_config.yaml"),
    "database_path": getattr(driver.config, "database_path", "database/chuchu.sqlite"),
}

config = Config.model_validate(raw_config)
