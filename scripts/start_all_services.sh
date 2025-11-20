#!/bin/bash
# -*- coding: utf-8 -*-
#
# @Author: xycdaimi
# @Email: xycdaimi@gmail.com
# @Date: 2025-11-20
# @Description: Start all AIFlow services on Ubuntu/Linux

# Get script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========================================"
echo "   AIFlow - Start All Services"
echo "========================================"
echo ""
echo "Project Root: $(pwd)"
echo ""

# Check if in project root directory
if [ ! -d "services" ]; then
    echo "[ERROR] Cannot find services directory!"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found, please install Python 3.8+"
    exit 1
fi

echo "[OK] Python is installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found"
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "[OK] .env file created"
        echo ""
        echo "IMPORTANT: Please configure the following in .env file:"
        echo "  - Redis connection"
        echo "  - RabbitMQ connection"
        echo "  - PostgreSQL connection"
        echo "  - Consul connection"
        echo "  - MinIO connection"
        echo ""
        echo "Press Enter to continue with default configuration..."
        read -r
    else
        echo "[ERROR] .env.example not found, cannot create .env"
        exit 1
    fi
fi

echo "[OK] Configuration file ready"
echo ""

# Create log directories
mkdir -p logs/backup

echo "========================================"
echo "   Startup Order:"
echo "   1. Log Service      (Port 8002)"
echo "   2. Model Forwarder  (Port 8001)"
echo "   3. Task Scheduler   (Background)"
echo "   4. API Gateway      (Port 8000)"
echo "========================================"
echo ""

echo "Note: Each service will run in background"
echo "Use scripts/stop_all_services.sh to stop all services"
echo ""
echo "Press Enter to continue..."
read -r

# Create PID directory
mkdir -p logs/pids

# 1. Start Log Service
echo ""
echo "[1/4] Starting Log Service..."
nohup python3 -m services.log_service.main > logs/log_service.log 2>&1 &
LOG_SERVICE_PID=$!
echo $LOG_SERVICE_PID > logs/pids/log_service.pid
sleep 3
if ps -p $LOG_SERVICE_PID > /dev/null; then
    echo "[OK] Log Service started (PID: $LOG_SERVICE_PID, Port 8002)"
else
    echo "[ERROR] Log Service failed to start"
    exit 1
fi

# 2. Start Model Forwarder
echo ""
echo "[2/4] Starting Model Forwarder..."
nohup python3 -m services.model_forwarder.main > logs/model_forwarder.log 2>&1 &
MODEL_FORWARDER_PID=$!
echo $MODEL_FORWARDER_PID > logs/pids/model_forwarder.pid
sleep 3
if ps -p $MODEL_FORWARDER_PID > /dev/null; then
    echo "[OK] Model Forwarder started (PID: $MODEL_FORWARDER_PID, Port 8001)"
else
    echo "[ERROR] Model Forwarder failed to start"
    exit 1
fi

# 3. Start Task Scheduler
echo ""
echo "[3/4] Starting Task Scheduler..."
nohup python3 -m services.task_scheduler.main > logs/task_scheduler.log 2>&1 &
TASK_SCHEDULER_PID=$!
echo $TASK_SCHEDULER_PID > logs/pids/task_scheduler.pid
sleep 3
if ps -p $TASK_SCHEDULER_PID > /dev/null; then
    echo "[OK] Task Scheduler started (PID: $TASK_SCHEDULER_PID)"
else
    echo "[ERROR] Task Scheduler failed to start"
    exit 1
fi

# 4. Start API Gateway
echo ""
echo "[4/4] Starting API Gateway..."
nohup python3 -m services.api_gateway.main > logs/api_gateway.log 2>&1 &
API_GATEWAY_PID=$!
echo $API_GATEWAY_PID > logs/pids/api_gateway.pid
sleep 3
if ps -p $API_GATEWAY_PID > /dev/null; then
    echo "[OK] API Gateway started (PID: $API_GATEWAY_PID, Port 8000)"
else
    echo "[ERROR] API Gateway failed to start"
    exit 1
fi

echo ""
echo "========================================"
echo "   All Services Started Successfully!"
echo "========================================"
echo ""
echo "Service URLs:"
echo "  - API Gateway:      http://localhost:8000"
echo "  - API Docs:         http://localhost:8000/docs"
echo "  - Model Forwarder:  http://localhost:8001"
echo "  - Log Service:      http://localhost:8002"
echo ""
echo "Health Check:"
echo "  - API Gateway:      http://localhost:8000/health"
echo "  - Model Forwarder:  http://localhost:8001/health"
echo "  - Log Service:      http://localhost:8002/health"
echo ""
echo "Process IDs saved in logs/pids/"
echo "Log files saved in logs/"
echo ""
echo "Tips:"
echo "  - View logs: tail -f logs/<service_name>.log"
echo "  - Stop all services: ./scripts/stop_all_services.sh"
echo ""

