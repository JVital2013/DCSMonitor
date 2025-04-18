#!/bin/bash

# Exit on error
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/dcs"
SERVICE_NAME="dcs-watcher"

echo "Installing DCS Watcher Service..."

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy files to installation directory
echo "Copying files to $INSTALL_DIR"
cp DCSWatcher.py DCSCommon.py config.ini "$INSTALL_DIR/"

# Install service file
echo "Installing service file"
cp dcs-watcher.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd"
systemctl daemon-reload

# Enable and start service
echo "Enabling and starting service"
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Check service status
echo "Checking service status..."
systemctl status "$SERVICE_NAME"

echo "Installation complete!"
echo "To view logs: journalctl -u $SERVICE_NAME"
echo "To stop service: systemctl stop $SERVICE_NAME"
echo "To start service: systemctl start $SERVICE_NAME"
echo "To check status: systemctl status $SERVICE_NAME" 