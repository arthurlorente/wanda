@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 -m wanda --configure-voice
) else (
  python -m wanda --configure-voice
)
pause
