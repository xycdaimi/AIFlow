#!/bin/bash
# -*- coding: utf-8 -*-
#
# @Author: xycdaimi
# @Email: xycdaimi@gmail.com
# @Date: 2025-11-20
# @Description: Setup execute permissions for all shell scripts

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "   AIFlow - Setup Script Permissions"
echo "========================================"
echo ""

# Add execute permissions to all .sh files
echo "Adding execute permissions to shell scripts..."
chmod +x "$SCRIPT_DIR"/*.sh

echo ""
echo "✓ start_all_services.sh"
echo "✓ stop_all_services.sh"
echo "✓ restart_all_services.sh"
echo "✓ setup_permissions.sh"

echo ""
echo "========================================"
echo "   Permissions Setup Complete!"
echo "========================================"
echo ""
echo "You can now run:"
echo "  ./scripts/start_all_services.sh"
echo "  ./scripts/stop_all_services.sh"
echo "  ./scripts/restart_all_services.sh"
echo ""

