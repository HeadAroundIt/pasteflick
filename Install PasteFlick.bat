@echo off
title PasteFlick Setup
cd /d "%~dp0"
echo.
echo  PasteFlick Setup
echo  Brave / Chrome / Edge / Chromium - same extension.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\install.ps1"
if errorlevel 1 (
  echo.
  echo Setup hit a problem.
  pause
)
