@echo off
title PasteFlick Setup
cd /d "%~dp0"

echo.
echo  PasteFlick Setup
echo  Works with Brave, Chrome, Edge, and Chromium (one package).
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Setup hit a problem.
  pause
)
