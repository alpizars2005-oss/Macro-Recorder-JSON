@echo off
setlocal
cd /d "%~dp0"
title Macro Recorder JSON

set "PYTHON_CMD="
py -3.12 --version >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
    py -3.11 --version >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo ERROR: Python 3.11 or 3.12 was not found.
    echo Install it with:
    echo winget install --exact --id Python.Python.3.12
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" macro_recorder.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo The application stopped with an error.
echo Run run_debug.bat and send the displayed error.
pause
exit /b 1
