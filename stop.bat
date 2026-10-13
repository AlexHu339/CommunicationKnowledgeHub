@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if exist runtime\python\Scripts\python.exe goto bundled_python
python program\scripts\stop_server.py
exit /b %ERRORLEVEL%

:bundled_python
runtime\python\Scripts\python.exe program\scripts\stop_server.py
exit /b %ERRORLEVEL%
