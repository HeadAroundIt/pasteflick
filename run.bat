@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  PasteFlick — copy a selection or thread to the clipboard
echo  Uses port 8768 so it can sit beside ScrollMark (8766) and Hush (8765).
echo.

set PYTHONUTF8=1

set "PYLAUNCH="
py -3.12 -c "import sys" 2>nul && set "PYLAUNCH=py -3.12"
if not defined PYLAUNCH py -3.11 -c "import sys" 2>nul && set "PYLAUNCH=py -3.11"
if not defined PYLAUNCH python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" 2>nul && set "PYLAUNCH=python"
if not defined PYLAUNCH (
  echo Needs Python 3.12 ^(3.11 also works^).
  echo Install from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtualenv...
  %PYLAUNCH% -m venv .venv
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, webview" 2>nul
if errorlevel 1 (
  echo Installing packages...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist "ui\dist\index.html" (
  echo Building React UI...
  where npm >nul 2>nul
  if errorlevel 1 (
    echo UI is missing and Node.js/npm was not found.
    echo Install Node LTS from https://nodejs.org/ then run this again.
    pause
    exit /b 1
  )
  pushd ui
  call npm install
  call npm run build
  popd
)

echo Starting PasteFlick...
".venv\Scripts\python.exe" -m app
