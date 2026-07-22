@echo off
setlocal
cd /d "%~dp0"
title Macro Recorder JSON - Debug
echo ===== SYSTEM =====
ver
echo.
echo ===== PYTHON =====
where py
where python
py --list
python --version
echo.
echo ===== APP =====
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" macro_recorder.py
) else (
    echo Virtual environment not found. Run run.bat first.
)
echo.
pause
