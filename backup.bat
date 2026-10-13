@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set CKH_ROOT=%CD%
set PYTHONPATH=%CD%\program\backend
runtime\python\Scripts\python.exe program\scripts\backup_cli.py
pause
exit /b %ERRORLEVEL%
