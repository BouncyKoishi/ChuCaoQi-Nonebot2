"""
共享核心域 - 统一配置加载模块
供 bot、backend、scheduler 三进程共用
"""

import yaml
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 阶段1：配置文件仍在 bot/config/；阶段2将迁移到 config/
_config_path = os.path.join(PROJECT_ROOT, 'bot', 'config', 'plugin_config.yaml')
if not os.path.exists(_config_path):
    _config_path = os.path.join(PROJECT_ROOT, 'config', 'plugin_config.yaml')

with open(_config_path, 'r', encoding='utf-8') as f:
    plugin_config: dict = yaml.safe_load(f)
