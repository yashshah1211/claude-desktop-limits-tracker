@echo off
title Claude.ai Limits Tracker - Windows
cd /d "%~dp0"

echo ===================================================
echo   ✦ Claude.ai Limits Tracker for Windows ✦
echo ===================================================
echo [1] Launch Native Windows Desktop GUI (Recommended)
echo [2] Launch Web Dashboard (Browser)
echo [3] Launch Terminal CLI Dashboard (Live Watch)
echo ===================================================
set /p choice="Select mode [1, 2, or 3, default is 1]: "

if "%choice%"=="2" goto run_web
if "%choice%"=="3" goto run_cli
goto run_gui

:run_gui
echo Starting Native Windows GUI...
python gui.py
goto end

:run_web
echo Starting Web Dashboard...
python web_server.py
goto end

:run_cli
echo Starting Terminal CLI...
python cli.py --watch 30
goto end

:end
pause
