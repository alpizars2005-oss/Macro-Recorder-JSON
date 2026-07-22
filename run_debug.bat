@echo off
setlocal
cd /d "%~dp0"
title Macro Recorder JSON - Diagnostics

echo ===== SYSTEM =====
ver
echo.
echo ===== PYTHON COMMANDS =====
where py
where python
py --list
echo.
echo ===== BOOTSTRAP CHECK =====
call "%~dp0run_windows.bat" --check-only
echo.
pause
