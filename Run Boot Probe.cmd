@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run-boot-probe.ps1"
set "probeResult=%ERRORLEVEL%"
echo.
pause
exit /b %probeResult%
