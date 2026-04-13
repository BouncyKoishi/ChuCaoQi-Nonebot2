@echo off
chcp 65001 >nul
echo ========================================
echo    生草系统 Web 项目启动脚本
echo ========================================
echo.

echo [1/3] 检查环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
)

echo 环境检查通过！
echo.

echo [2/3] 安装依赖...
echo 正在安装后端依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 后端依赖安装失败
    pause
    exit /b 1
)

echo 正在安装前端依赖...
if not exist "node_modules" (
    call npm install
    if %errorlevel% neq 0 (
        echo 错误: 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo 前端依赖已存在，跳过安装
)

echo 依赖安装完成！
echo.

echo [3/3] 启动服务...
echo 正在启动后端服务 (端口 8000)...
start "生草系统后端" cmd /k "cd /d %~dp0backend && npm run dev"

timeout /t 3 /nobreak >nul

echo 正在启动前端服务 (端口 3000)...
start "生草系统前端" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo ========================================
echo    启动完成！
echo ========================================
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:3000
echo API文档: http://localhost:8000/docs
echo.
echo 按任意键关闭此窗口（服务将继续运行）...
pause >nul
