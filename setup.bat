@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 goto no_python
python program\scripts\setup_windows.py
if errorlevel 1 goto failed
echo.
echo Setup completed. Run start.bat to open the site.
pause
exit /b 0
:no_python
echo Python 3.11 or newer was not found.
pause
exit /b 1
:failed
echo.
echo Setup failed. Read the Chinese error above and run diagnose.bat.
pause
exit /b 1
