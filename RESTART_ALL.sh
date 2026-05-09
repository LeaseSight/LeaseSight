#!/bin/bash
# Complete Backend + Caddy Restart

set -e

echo "=========================================="
echo "COMPLETE SERVICE RESTART"
echo "=========================================="
echo ""

# Stop everything
echo "[1/5] Stopping services..."
sudo systemctl stop caddy 2>/dev/null || true
docker stop leasesight-api 2>/dev/null || true
sleep 2
echo "  ✓ Stopped"
echo ""

# Start backend
echo "[2/5] Starting backend..."
cd /opt/leasesight
docker rm leasesight-api 2>/dev/null || true
docker run -d \
  --name leasesight-api \
  -p 8080:8080 \
  --env-file .env \
  --restart unless-stopped \
  leasesight-backend:latest

sleep 3
if curl -s http://localhost:8080/api/health > /dev/null; then
    echo "  ✓ Backend started and healthy"
else
    echo "  ✗ Backend failed - checking logs..."
    docker logs leasesight-api | tail -20
    exit 1
fi
echo ""

# Start Caddy
echo "[3/5] Starting Caddy..."
sudo systemctl start caddy
sleep 3
echo "  ✓ Caddy started"
echo ""

# Check logs
echo "[4/5] Checking logs..."
echo "  Caddy:"
sudo journalctl -u caddy -n 5 --no-pager | grep -v "exited" | head -3
echo ""
echo "  Backend:"
docker logs leasesight-api | tail -3
echo ""

# Final test
echo "[5/5] Testing endpoints..."
echo "  HTTP (internal): $(curl -s http://localhost:8080/api/health | jq -r .status 2>/dev/null || echo 'FAIL')"
echo "  HTTPS (browser): $(curl -s https://api.leasesights.tech/api/health 2>&1 | head -c 30)..."
echo ""

echo "=========================================="
echo "✓ COMPLETE RESTART DONE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Open https://www.leasesights.tech in browser"
echo "  2. Hard refresh (Ctrl+Shift+R)"
echo "  3. Check browser console for errors"
echo "  4. If SSL error persists, Caddy is still provisioning cert (wait 15s)"
echo ""
