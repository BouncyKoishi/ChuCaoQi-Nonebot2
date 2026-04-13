@echo off
chcp 65001 >nul
echo 正在停止生草系统服务...
echo.

taskkill /f /im python.exe /fi "WINDOWTITLE eq 生草系统后端*" >nul 2>&1
taskkill /f /im node.exe /fi "WINDOWTITLE eq 生草系统前端*" >nul 2>&1

echo 服务已停止
pause
