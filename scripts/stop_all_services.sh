#!/bin/bash
# -*- coding: utf-8 -*-
#
# @Author: xycdaimi
# @Email: xycdaimi@gmail.com
# @Date: 2025-11-20
# @Description: Stop all AIFlow services on Ubuntu/Linux

# Get script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========================================"
echo "   AIFlow - Stop All Services"
echo "========================================"
echo ""
echo "Project Root: $(pwd)"
echo ""

echo "Finding and stopping all AIFlow services..."
echo ""

# PID directory
PID_DIR="logs/pids"

# Function to stop a service gracefully
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    echo "[$2/4] Stopping $3..."
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        # Check if process is running
        if ps -p $pid > /dev/null 2>&1; then
            echo "  Sending SIGTERM to PID $pid..."
            kill -TERM $pid 2>/dev/null
            
            # Wait for graceful shutdown (max 10 seconds)
            local count=0
            while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo "  Process still running, sending SIGKILL..."
                kill -9 $pid 2>/dev/null
                sleep 1
            fi
            
            # Verify stopped
            if ! ps -p $pid > /dev/null 2>&1; then
                echo "  [OK] $3 stopped"
                rm -f "$pid_file"
            else
                echo "  [ERROR] Failed to stop $3"
            fi
        else
            echo "  [WARNING] Process not running (PID $pid not found)"
            rm -f "$pid_file"
        fi
    else
        echo "  [WARNING] PID file not found, trying to find process by name..."
        
        # Try to find and kill by process name
        local pids=$(pgrep -f "services.${service_name}.main")
        if [ -n "$pids" ]; then
            echo "  Found process(es): $pids"
            for pid in $pids; do
                echo "  Killing PID $pid..."
                kill -TERM $pid 2>/dev/null
                sleep 2
                if ps -p $pid > /dev/null 2>&1; then
                    kill -9 $pid 2>/dev/null
                fi
            done
            echo "  [OK] $3 stopped"
        else
            echo "  [WARNING] $3 not running"
        fi
    fi
}

# Stop services in reverse order
stop_service "api_gateway" "1" "API Gateway"
stop_service "task_scheduler" "2" "Task Scheduler"
stop_service "model_forwarder" "3" "Model Forwarder"
stop_service "log_service" "4" "Log Service"

echo ""
echo "========================================"
echo "   All Services Stopped"
echo "========================================"
echo ""
echo "Tip: Check logs in logs/ directory for any errors"
echo ""

