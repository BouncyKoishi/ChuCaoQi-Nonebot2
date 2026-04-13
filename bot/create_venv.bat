@echo off
chcp 65001 >nul
echo 创建虚拟环境...

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 删除旧环境（如果存在）
if exist venv (
    echo 删除旧虚拟环境...
    rmdir /s /q venv
)

:: 创建新虚拟环境
echo 创建新虚拟环境...
python -m venv venv

if errorlevel 1 (
    echo 错误: 创建虚拟环境失败
    pause
    exit /b 1
)

echo 虚拟环境创建成功！
echo.
echo 使用方法:
echo   1. 激活环境: venv\Scripts\activate
echo   2. 安装依赖: pip install -r requirements.txt
echo   3. 运行 Bot: python bot.py
pause
