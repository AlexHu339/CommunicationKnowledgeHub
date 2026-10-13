@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist runtime\python\Scripts\python.exe goto not_installed
set CKH_ROOT=%CD%
set PYTHONPATH=%CD%\program\backend
set PADDLE_PDX_CACHE_HOME=%CD%\runtime\ocr_models
set PLAYWRIGHT_BROWSERS_PATH=%CD%\runtime\browsers
start "CKH" /min cmd /d /c "runtime\python\Scripts\python.exe program\scripts\launcher.py 1^>userdata\logs\server.log 2^>userdata\logs\server-error.log"
ping 127.0.0.1 -n 4 >nul
if exist runtime\app-state.json type runtime\app-state.json
exit /b 0

:not_installed
echo Setup is required. Run setup.bat first.
pause
exit /b 1
