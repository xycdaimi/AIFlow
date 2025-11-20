@echo off
setlocal enabledelayedexpansion

REM Get script directory and change to project root
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo ========================================
echo    AI Router - Stop All Services
echo ========================================
echo.
echo Project Root: %CD%
echo.

echo Finding and stopping all AI Router services...
echo.

REM Stop services by sending Ctrl+C (graceful shutdown)
REM First try graceful shutdown, then force kill if needed

REM Stop API Gateway
echo [1/4] Stopping API Gateway...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq AI Router - API Gateway*" /FO LIST ^| find "PID:"') do (
    echo   Sending Ctrl+C to PID %%a...
    taskkill /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
    tasklist /FI "PID eq %%a" 2>nul | find "%%a" >nul
    if not errorlevel 1 (
        echo   Process still running, force killing...
        taskkill /F /PID %%a >nul 2>&1
    )
    REM Close the window
    taskkill /FI "WINDOWTITLE eq AI Router - API Gateway*" /F >nul 2>&1
    echo   [OK] API Gateway stopped
    goto :stop_scheduler
)
echo   [WARNING] API Gateway not running
:stop_scheduler

REM Stop Task Scheduler
echo [2/4] Stopping Task Scheduler...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq AI Router - Task Scheduler*" /FO LIST ^| find "PID:"') do (
    echo   Sending Ctrl+C to PID %%a...
    taskkill /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
    tasklist /FI "PID eq %%a" 2>nul | find "%%a" >nul
    if not errorlevel 1 (
        echo   Process still running, force killing...
        taskkill /F /PID %%a >nul 2>&1
    )
    REM Close the window
    taskkill /FI "WINDOWTITLE eq AI Router - Task Scheduler*" /F >nul 2>&1
    echo   [OK] Task Scheduler stopped
    goto :stop_forwarder
)
echo   [WARNING] Task Scheduler not running
:stop_forwarder

REM Stop Model Forwarder
echo [3/4] Stopping Model Forwarder...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq AI Router - Model Forwarder*" /FO LIST ^| find "PID:"') do (
    echo   Sending Ctrl+C to PID %%a...
    taskkill /PID %%a >nul 2>&1
    timeout /t 20 /nobreak >nul
    tasklist /FI "PID eq %%a" 2>nul | find "%%a" >nul
    if not errorlevel 1 (
        echo   Process still running, force killing...
        taskkill /F /PID %%a >nul 2>&1
    )
    REM Close the window
    taskkill /FI "WINDOWTITLE eq AI Router - Model Forwarder*" /F >nul 2>&1
    echo   [OK] Model Forwarder stopped
    goto :stop_log
)
echo   [WARNING] Model Forwarder not running
:stop_log

REM Stop Log Service
echo [4/4] Stopping Log Service...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq AI Router - Log Service*" /FO LIST ^| find "PID:"') do (
    echo   Sending Ctrl+C to PID %%a...
    taskkill /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
    tasklist /FI "PID eq %%a" 2>nul | find "%%a" >nul
    if not errorlevel 1 (
        echo   Process still running, force killing...
        taskkill /F /PID %%a >nul 2>&1
    )
    REM Close the window
    taskkill /FI "WINDOWTITLE eq AI Router - Log Service*" /F >nul 2>&1
    echo   [OK] Log Service stopped
    goto :done
)
echo   [WARNING] Log Service not running
:done

echo.
echo ========================================
echo    All Services Stopped
echo ========================================
echo.
pause

