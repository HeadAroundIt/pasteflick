@echo off
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" testbed\verify.py
) else (
  python testbed\verify.py
)
echo.
pause
