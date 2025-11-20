#!/bin/bash
# -*- coding: utf-8 -*-
#
# @Author: xycdaimi
# @Email: xycdaimi@gmail.com
# @Date: 2025-11-20
# @Description: Restart all AIFlow services on Ubuntu/Linux

# Get script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========================================"
echo "   AIFlow - Restart All Services"
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

echo "Step 1: Stopping all services..."
echo ""
bash "$SCRIPT_DIR/stop_all_services.sh"

echo ""
echo "Waiting 3 seconds before restart..."
sleep 3

echo ""
echo "Step 2: Starting all services..."
echo ""
bash "$SCRIPT_DIR/start_all_services.sh"

