#!/bin/bash
# Complete SSL Fix for ~/LeaseSight setup

set -e

echo "=========================================="
echo "COMPLETE SSL & SERVICE FIX"
echo "=========================================="
echo ""

# Step 1: Verify backend is running
echo "[1/6] Checking backend..."
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "  ✓ Backend is running"
else
    echo "  ✗ Backend not running, starting..."
    docker rm -f leasesight-api 2>/dev/null || true
    docker run -d \
      --name leasesight-api \
      -p 8080:8080 \
      --env-file ~/.leasesight/.env \
      --restart unless-stopped \
      leasesight-backend:latest
    sleep 3
    if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
        echo "  ✓ Backend started"
    else
        echo "  ✗ Backend failed to start"
        docker logs leasesight-api | tail -20
        exit 1
    fi
fi
echo ""

# Step 2: Check Caddyfile exists
echo "[2/6] Checking Caddyfile..."
if [ ! -f /etc/caddy/Caddyfile ]; then
    echo "  ✗ Caddyfile missing, creating..."
    sudo mkdir -p /etc/caddy
else
    echo "  ✓ Caddyfile exists"
fi
echo ""

# Step 3: Update Caddyfile with correct config
echo "[3/6] Writing correct Caddyfile..."
sudo tee /etc/caddy/Caddyfile > /dev/null << 'CADDY_CONFIG'
{
    email admin@leasesights.tech
    agree_tos true
}

api.leasesights.tech {
    reverse_proxy localhost:8080 {
        header_down -Access-Control-Allow-Origin
        header_down -Access-Control-Allow-Methods
        header_down -Access-Control-Allow-Headers
        header_down -Access-Control-Allow-Credentials
        header_down -Access-Control-Allow-Expose-Headers
    }

    @allowed_origin {
        header Origin https://www.leasesights.tech
        header Origin http://localhost:3000
        header Origin http://127.0.0.1:3000
    }
    header @allowed_origin Access-Control-Allow-Origin "{http.request.header.Origin}"
    header Vary "Origin"
    header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE, PATCH"
    header Access-Control-Allow-Headers "Content-Type, Authorization, X-OpenAI-Key, X-API-Key, x-api-key, X-Pinecone-Key, X-Azure-Key, X-Azure-Endpoint, X-User-ID, x-user-id"
    header Access-Control-Allow-Credentials "true"

    @options {
        method OPTIONS
    }
    respond @options 204
}

www.leasesights.tech {
    root * /var/www/leasesight-ui
    file_server
    try_files {path} /index.html
}
CADDY_CONFIG
echo "  ✓ Caddyfile updated"
echo ""

# Step 4: Validate Caddy config
echo "[4/6] Validating Caddy config..."
if sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile > /dev/null 2>&1; then
    echo "  ✓ Config is valid"
else
    echo "  ✗ Config validation failed:"
    sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile
    exit 1
fi
echo ""

# Step 5: Restart Caddy
echo "[5/6] Restarting Caddy..."
sudo systemctl daemon-reload
sudo systemctl restart caddy
sleep 5

if sudo systemctl is-active --quiet caddy; then
    echo "  ✓ Caddy restarted and running"
else
    echo "  ✗ Caddy failed to start"
    sudo journalctl -u caddy -n 10 --no-pager
    exit 1
fi
echo ""

# Step 6: Test everything
echo "[6/6] Testing connectivity..."
echo ""

# Test backend
echo "  Backend (HTTP):"
BACKEND_RESPONSE=$(curl -s http://localhost:8080/api/health 2>&1)
if echo "$BACKEND_RESPONSE" | grep -q "ULTRA_HEALTHY\|status"; then
    echo "    ✓ Responding"
else
    echo "    ✗ Not responding properly: $BACKEND_RESPONSE"
fi

# Test frontend HTTPS (will take time for cert provisioning)
echo "  Frontend (HTTPS):"
sleep 2
HTTPS_RESPONSE=$(curl -s https://api.leasesights.tech/api/health 2>&1 || echo "TIMEOUT")
if echo "$HTTPS_RESPONSE" | grep -q "ULTRA_HEALTHY\|status"; then
    echo "    ✓ HTTPS working!"
elif echo "$HTTPS_RESPONSE" | grep -q "certificate"; then
    echo "    ⏳ Certificate still provisioning (wait 20 seconds, then refresh browser)"
else
    echo "    ℹ Response: $HTTPS_RESPONSE"
fi

echo ""
echo "=========================================="
echo "✓ FIX COMPLETE"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Open: https://www.leasesights.tech"
echo "2. Hard refresh: Ctrl+Shift+R (not just F5)"
echo "3. Check browser console (F12) - should be clean"
echo "4. If SSL error persists, wait 20 more seconds and refresh"
echo ""
echo "Logs to monitor:"
echo "  sudo journalctl -u caddy -f  # Caddy logs in real-time"
echo "  docker logs leasesight-api   # Backend logs"
echo ""
