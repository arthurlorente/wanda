@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 -m wanda
) else (
  python -m wanda
)
if errorlevel 1 pause
