@echo off
echo ========================================
echo    Kusa System Web Startup Script
echo ========================================
echo.

echo [1/3] Checking environment...
if not exist "%~dp0venv\Scripts\python.exe" (
    echo ERROR: venv not found. Run install_deps.bat first.
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 16+.
    pause
    exit /b 1
)

echo Environment OK!
echo.

echo [2/3] Installing dependencies...
echo Installing Python dependencies (venv)...
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo ERROR: Python dependency install failed.
    pause
    exit /b 1
)

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

echo Dependencies installed!
echo.

echo [3/3] Starting services...
echo Starting scheduler service (cron jobs)...
start "kusa-scheduler" cmd /k "cd /d %~dp0 && call %~dp0venv\Scripts\activate && python -m scheduler.main"

echo Starting backend service (port 8000)...
start "kusa-backend" cmd /k "cd /d %~dp0backend && call %~dp0venv\Scripts\activate && npm run dev"

timeout /t 3 /nobreak >nul

echo Starting frontend service (port 3000)...
start "kusa-frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo    All services started!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend:    http://localhost:3000
echo API docs:    http://localhost:8000/docs
echo.
echo Press any key to close this window (services keep running)...
pause >nul
