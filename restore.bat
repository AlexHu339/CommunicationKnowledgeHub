@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if "%~1"=="" goto usage
set CKH_ROOT=%CD%
set PYTHONPATH=%CD%\program\backend
runtime\python\Scripts\python.exe program\scripts\restore_backup.py "%~1"
pause
exit /b %ERRORLEVEL%

:usage
echo Pass a backup ZIP path to restore.bat.
pause
exit /b 1
