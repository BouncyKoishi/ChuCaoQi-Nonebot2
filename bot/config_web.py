"""
生草系统 Web 后端配置模块
独立于 NoneBot 的配置，供 Web 后端使用
"""

from typing import Set, Dict, Any
from pydantic import BaseModel, Field
import yaml
import os


class Config(BaseModel):
    """Web 后端配置类"""
    
    # 命令前缀
    command_start: Set[str] = Field(default={"!"})
    
    # 超级管理员
    superusers: Set[str] = Field(default=set())
    
    # 插件配置路径
    plugin_config_path: str = Field(default="config/plugin_config.yaml")
    
    # 数据库路径
    database_path: str = Field(default="database/chuchu.sqlite")


# 加载插件配置
plugin_config_path = os.path.join(os.path.dirname(__file__), "config", "plugin_config.yaml")
if os.path.exists(plugin_config_path):
    with open(plugin_config_path, 'r', encoding='utf-8') as f:
        plugin_config: Dict[str, Any] = yaml.safe_load(f)
else:
    plugin_config = {}

# Web 后端使用的配置对象
config = Config()
