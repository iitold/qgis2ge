@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo          qgis2ge - Release & Publish Launcher
echo ==========================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Release script finished with errors (code %ERRORLEVEL%).
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Done!
pause
