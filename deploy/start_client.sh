#!/bin/bash
# SuperPersonal - Start Client (connected via SSH tunnel)
# Run this on your local Windows/WSL machine.
#
# Prerequisites:
#   1. SSH tunnel must be running: ./deploy/ssh_tunnel.sh -bg
#   2. Local venv must be set up
#
# Usage:
#   ./deploy/start_client.sh          # start client (connects to tunnel)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# The tunnel forwards VM:8000 -> localhost:8000
export SERVER_URL="${SUPERPERSONAL_SERVER_URL:-http://localhost:8000/api/v1}"

echo "=== SuperPersonal Client ==="
echo "Server URL: $SERVER_URL"
echo ""

cd "$PROJECT_DIR"
source venv/bin/activate
python -m src.client.client
