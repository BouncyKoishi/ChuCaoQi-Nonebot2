@echo off
echo Stopping kusa system services...
echo.

rem Window title matching: each service runs under a cmd console, so kill
rem the titled cmd window with /t to take down its whole child tree.
taskkill /f /t /im cmd.exe /fi "WINDOWTITLE eq kusa-scheduler*" >nul 2>&1
taskkill /f /t /im cmd.exe /fi "WINDOWTITLE eq kusa-backend*" >nul 2>&1
taskkill /f /t /im cmd.exe /fi "WINDOWTITLE eq kusa-frontend*" >nul 2>&1
taskkill /f /t /im cmd.exe /fi "WINDOWTITLE eq kusa-bot*" >nul 2>&1

echo Services stopped.
pause
