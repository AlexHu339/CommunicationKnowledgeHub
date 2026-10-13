@echo off
setlocal EnableExtensions
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if exist runtime\python\Scripts\python.exe goto bundled_python
python program\scripts\diagnose.py
goto done

:bundled_python
runtime\python\Scripts\python.exe program\scripts\diagnose.py

:done
pause
exit /b %ERRORLEVEL%
