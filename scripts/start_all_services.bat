@echo off
setlocal enabledelayedexpansion

REM Get script directory and change to project root
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo ========================================
echo    AI Router - Start All Services
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

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo [OK] .env file created
        echo.
        echo IMPORTANT: Please configure the following in .env file:
        echo   - Redis connection
        echo   - RabbitMQ connection
        echo   - PostgreSQL connection
        echo   - Consul connection
        echo   - MinIO connection
        echo.
        echo Press any key to continue with default configuration...
        pause >nul
    ) else (
        echo [ERROR] .env.example not found, cannot create .env
        pause
        exit /b 1
    )
)

echo [OK] Configuration file ready
echo.

REM Create log directories
if not exist "logs" mkdir logs
if not exist "logs\backup" mkdir logs\backup

echo ========================================
echo    Startup Order:
echo    1. Log Service      (Port 8002)
echo    2. Model Forwarder  (Port 8001)
echo    3. Task Scheduler   (Background)
echo    4. API Gateway      (Port 8000)
echo ========================================
echo.

echo Note: Each service will start in a new window
echo Close window or press Ctrl+C to stop service
echo.
pause

REM 1. Start Log Service
echo.
echo [1/4] Starting Log Service...
start "AI Router - Log Service" cmd /k "python -m services.log_service.main"
timeout /t 3 /nobreak >nul
echo [OK] Log Service started (Port 8002)

REM 2. Start Model Forwarder
echo.
echo [2/4] Starting Model Forwarder...
start "AI Router - Model Forwarder" cmd /k "python -m services.model_forwarder.main"
timeout /t 3 /nobreak >nul
echo [OK] Model Forwarder started (Port 8001)

REM 3. Start Task Scheduler
echo.
echo [3/4] Starting Task Scheduler...
start "AI Router - Task Scheduler" cmd /k "python -m services.task_scheduler.main"
timeout /t 3 /nobreak >nul
echo [OK] Task Scheduler started

REM 4. Start API Gateway
echo.
echo [4/4] Starting API Gateway...
start "AI Router - API Gateway" cmd /k "python -m services.api_gateway.main"
timeout /t 3 /nobreak >nul
echo [OK] API Gateway started (Port 8000)

echo.
echo ========================================
echo    All Services Started Successfully!
echo ========================================
echo.
echo Service URLs:
echo   - API Gateway:      http://localhost:8000
echo   - API Docs:         http://localhost:8000/docs
echo   - Model Forwarder:  http://localhost:8001
echo   - Log Service:      http://localhost:8002
echo.
echo Health Check:
echo   - API Gateway:      http://localhost:8000/health
echo   - Model Forwarder:  http://localhost:8001/health
echo   - Log Service:      http://localhost:8002/health
echo.
echo Tips:
echo   - Close service windows to stop services
echo   - Or run scripts\stop_all_services.bat to stop all
echo.
pause

