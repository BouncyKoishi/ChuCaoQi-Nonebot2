@echo off
echo Activating virtual environment...
call "%~dp0venv\Scripts\activate.bat"

echo.
echo Installing Python dependencies (this may take a few minutes)...
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo ERROR: Python dependency install failed.
    pause
    exit /b 1
)

echo.
echo Installing backend Node dependencies...
if not exist "%~dp0backend\node_modules" (
    cd /d %~dp0backend && call npm install
    if %errorlevel% neq 0 (
        echo ERROR: backend Node dependency install failed.
        pause
        exit /b 1
    )
) else (
    echo backend Node dependencies already exist, skipping.
)

echo.
echo Installing frontend Node dependencies...
if not exist "%~dp0frontend\node_modules" (
    cd /d %~dp0frontend && call npm install
    if %errorlevel% neq 0 (
        echo ERROR: frontend dependency install failed.
        pause
        exit /b 1
    )
) else (
    echo frontend dependencies already exist, skipping.
)

echo.
echo Installation completed!
echo To run bot: cd bot ^&^& python bot.py
pause
