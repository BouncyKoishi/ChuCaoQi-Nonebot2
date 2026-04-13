@echo off
echo Activating virtual environment...
call "%~dp0venv\Scripts\activate.bat"

echo.
echo Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt

echo.
echo Installation completed!
echo To run bot: python bot.py
pause
