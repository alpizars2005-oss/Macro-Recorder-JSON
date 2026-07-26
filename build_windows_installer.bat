@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/6] Checking Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 was not found.
    echo Install it with: winget install --exact --id Python.Python.3.12
    exit /b 1
)

echo [2/6] Preparing the build environment...
if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv .venv-build
    if errorlevel 1 exit /b 1
)

call ".venv-build\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -r requirements.txt -r requirements-build.txt
if errorlevel 1 exit /b 1
python -m pip check
if errorlevel 1 exit /b 1

echo [3/6] Running tests...
set PYNPUT_BACKEND=dummy
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
set PYNPUT_BACKEND=

echo [4/6] Building the standalone application...
pyinstaller --clean --noconfirm build\windows\MacroRecorderJSON.spec
if errorlevel 1 exit /b 1

echo [5/6] Locating NSIS...
set "MAKENSIS="
for %%I in (makensis.exe) do set "MAKENSIS=%%~$PATH:I"
if not defined MAKENSIS if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not defined MAKENSIS (
    echo NSIS was not found.
    echo Install it with: winget install --exact --id NSIS.NSIS
    exit /b 1
)

echo [6/6] Building the one-click installer...
pushd installer
"%MAKENSIS%" MacroRecorderJSON.nsi
set "BUILD_EXIT=%ERRORLEVEL%"
popd
if not "%BUILD_EXIT%"=="0" exit /b %BUILD_EXIT%

echo.
echo Build completed successfully.
echo Installer location:
for %%F in ("dist\Macro-Recorder-JSON-Setup-*.exe") do echo   %%~fF
exit /b 0
