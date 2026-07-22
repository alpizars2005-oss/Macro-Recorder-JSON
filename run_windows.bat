@echo off
setlocal
cd /d "%~dp0"
title Macro Recorder JSON

set "PYTHON_CMD="
py -3.13 --version >nul 2>&1 && set "PYTHON_CMD=py -3.13"
if not defined PYTHON_CMD py -3.12 --version >nul 2>&1 && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD py -3.11 --version >nul 2>&1 && set "PYTHON_CMD=py -3.11"
if not defined PYTHON_CMD python --version >nul 2>&1 && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    echo ERROR: Python 3.11, 3.12, or 3.13 was not found.
    echo Install Python 3.12 with:
    echo winget install --exact --id Python.Python.3.12
    echo Then close and reopen PowerShell.
    pause
    exit /b 1
)

%PYTHON_CMD% bootstrap.py %*
if errorlevel 1 (
    echo.
    echo The launcher stopped with an error.
    echo Try: .\run.bat --repair
    pause
    exit /b 1
)
endlocal
