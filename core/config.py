"""
共享核心域 - 统一配置加载模块
供 bot、backend、scheduler 三进程共用
"""

import yaml
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

with open(os.path.join(CONFIG_DIR, 'plugin_config.yaml'), 'r', encoding='utf-8') as f:
    plugin_config: dict = yaml.safe_load(f)
