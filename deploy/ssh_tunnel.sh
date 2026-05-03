#!/bin/bash
# SuperPersonal - SSH Tunnel Manager
# Establishes a persistent SSH tunnel to the Google VM.
# This forwards port 8000 on localhost to the VM's Django server.
#
# Usage:
#   ./deploy/ssh_tunnel.sh           # start tunnel (foreground)
#   ./deploy/ssh_tunnel.sh -bg        # start tunnel (background)
#   ./deploy/ssh_tunnel.sh -kill      # kill running tunnel

set -euo pipefail

PROFILE="${SUPERPERSONAL_SSH_PROFILE:-personal}"
LOCAL_PORT="${SUPERPERSONAL_LOCAL_PORT:-8000}"
REMOTE_PORT="${SUPERPERSONAL_REMOTE_PORT:-8000}"
PID_FILE="/tmp/superpersonal-tunnel.pid"

kill_tunnel() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Killing tunnel (PID $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "Tunnel stopped."
        else
            echo "Stale PID file — removing."
            rm -f "$PID_FILE"
        fi
    else
        echo "No tunnel PID file found."
    fi
}

case "${1:-}" in
    -kill|--kill)
        kill_tunnel
        exit 0
        ;;
    -bg|--background)
        echo "Starting SSH tunnel to $PROFILE ($LOCAL_PORT -> VM:$REMOTE_PORT) in background..."
        ssh -f -N -L "${LOCAL_PORT}:localhost:${REMOTE_PORT}" "$PROFILE"
        echo "Tunnel started. Use '$0 -kill' to stop."
        exit 0
        ;;
    *)
        echo "Starting SSH tunnel to $PROFILE ($LOCAL_PORT -> VM:$REMOTE_PORT)..."
        echo "Press Ctrl+C to stop."
        ssh -N -L "${LOCAL_PORT}:localhost:${REMOTE_PORT}" "$PROFILE"
        ;;
esac
