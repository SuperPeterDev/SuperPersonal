#!/bin/bash
set -euo pipefail

echo "=== 1. Stop old daphne ==="
pkill -f daphne 2>/dev/null || true
sleep 1

echo "=== 2. Git setup and pull ==="
cd ~/SuperPersonal
if [ ! -d .git ]; then
    git init
    git remote add origin https://github.com/SuperPeterDev/SuperPersonal.git
fi
git fetch origin fix-ci-config-v2
git checkout -f origin/fix-ci-config-v2 -B fix-ci-config-v2

echo "=== 3. Install deps ==="
source venv/bin/activate
pip install -r requirements.txt -q

echo "=== 4. Migrations ==="
cd src/server
python manage.py migrate --noinput

echo "=== 5. Run tests ==="
python -m pytest tests/ -q

echo "=== 6. Create superuser ==="
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin123 DJANGO_SUPERUSER_EMAIL=admin@superpersonal.local python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser may already exist"

echo "=== 7. Start daphne ==="
nohup daphne -b 0.0.0.0 -p 8000 super_personal.asgi:application > /tmp/superpersonal-server.log 2>&1 &
echo "Daphne PID: $!"
sleep 3

echo "=== 8. Verify server ==="
curl -s http://localhost:8000/ | head -3
echo ""
echo "=== 9. Verify API ==="
curl -s http://localhost:8000/api/v1/devices/
