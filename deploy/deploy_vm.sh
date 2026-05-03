#!/bin/bash
# SuperPersonal - Google VM Server Deployment
# First-time setup or update of the server on the remote VM.
#
# Prerequisites:
#   1. SSH config entry 'personal' in ~/.ssh/config
#   2. The VM must have Python 3.12+, git, and venv support
#
# Usage:
#   ./deploy/deploy_vm.sh            # first-time deploy
#   ./deploy/deploy_vm.sh --update   # pull + restart (no reinstall)

set -euo pipefail

PROFILE="${SUPERPERSONAL_SSH_PROFILE:-personal}"
REMOTE_DIR="${SUPERPERSONAL_REMOTE_DIR:-~/SuperPersonal}"
REMOTE_PORT="${SUPERPERSONAL_REMOTE_PORT:-8000}"

echo "=== SuperPersonal VM Deploy ==="
echo "Target: $PROFILE:$REMOTE_DIR"
echo ""

# Step 1: Sync code to VM
echo "[1/5] Syncing code to VM..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude 'venv_test' \
    --exclude '.hermes' \
    --exclude '.claude' \
    ./ "$PROFILE:$REMOTE_DIR/"

# Step 2: Setup venv and install deps
if [ "${1:-}" != "--update" ]; then
    echo "[2/5] Setting up virtual environment..."
    ssh "$PROFILE" "cd $REMOTE_DIR && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

    echo "[3/5] Running migrations..."
    ssh "$PROFILE" "cd $REMOTE_DIR && source venv/bin/activate && cd src/server && python manage.py migrate"
else
    echo "[2/5] Skipping venv setup (--update mode)"
    echo "[3/5] Running migrations..."
    ssh "$PROFILE" "cd $REMOTE_DIR && source venv/bin/activate && cd src/server && python manage.py migrate"
fi

# Step 4: Run tests on VM
echo "[4/5] Running tests on VM..."
ssh "$PROFILE" "cd $REMOTE_DIR && source venv/bin/activate && cd src/server && python -m pytest tests/ -q"

# Step 5: Restart server
echo "[5/5] Restarting server..."
ssh "$PROFILE" "pkill -f 'daphne.*$REMOTE_PORT' 2>/dev/null || true"
ssh "$PROFILE" "cd $REMOTE_DIR && source venv/bin/activate && cd src/server && nohup daphne -b 0.0.0.0 -p $REMOTE_PORT super_personal.asgi:application > /tmp/superpersonal-server.log 2>&1 &"

echo ""
echo "=== Deploy Complete ==="
echo "Server: http://34.182.12.121:$REMOTE_PORT"
echo "Or via SSH tunnel: http://localhost:8000"
echo "Logs: $PROFILE:/tmp/superpersonal-server.log"
