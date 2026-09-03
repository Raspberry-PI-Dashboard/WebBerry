#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-berryboard.service}"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "$SERVICE_NAME is running; stopping it..."
    sudo systemctl stop "$SERVICE_NAME"
else
    echo "$SERVICE_NAME is not running."
fi

echo "Starting $SERVICE_NAME..."
sudo systemctl start "$SERVICE_NAME"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "$SERVICE_NAME restarted successfully."
else
    echo "Failed to start $SERVICE_NAME."
    sudo systemctl status "$SERVICE_NAME" --no-pager
    exit 1
fi