@echo off
setlocal enabledelayedexpansion

REM Get script directory and change to project root
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo ========================================
echo    AI Router - Restart All Services
echo ========================================
echo.
echo Project Root: %CD%
echo.

REM Check if in project root directory
if not exist "services\" (
    echo [ERROR] Cannot find services directory!
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Step 1: Stopping all services...
echo.
call scripts\stop_all_services.bat

echo.
echo Waiting 3 seconds before restart...
timeout /t 3 /nobreak >nul

echo.
echo Step 2: Starting all services...
echo.
call scripts\start_all_services.bat

