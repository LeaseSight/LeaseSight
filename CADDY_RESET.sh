#!/bin/bash
# Nuclear Caddy Reset - Complete reinitalization

set -e

echo "=========================================="
echo "NUCLEAR CADDY RESET"
echo "=========================================="
echo ""

# Step 1: Stop Caddy
echo "[1/6] Stopping Caddy..."
sudo systemctl stop caddy 2>/dev/null || true
sleep 2
echo "  ✓ Stopped"
echo ""

# Step 2: Clear old certs
echo "[2/6] Clearing cached certificates..."
sudo rm -rf /root/.local/share/caddy 2>/dev/null || true
sudo rm -rf /var/lib/caddy/.local/share/caddy 2>/dev/null || true
echo "  ✓ Cleared"
echo ""

# Step 3: Write fresh Caddyfile
echo "[3/6] Writing fresh Caddyfile..."
sudo tee /etc/caddy/Caddyfile > /dev/null << 'CADDYFILE'
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
CADDYFILE
echo "  ✓ Written"
echo ""

# Step 4: Validate config
echo "[4/6] Validating Caddy config..."
sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile
echo "  ✓ Valid"
echo ""

# Step 5: Start Caddy
echo "[5/6] Starting Caddy..."
sudo systemctl start caddy
sleep 3
echo "  ✓ Started"
echo ""

# Step 6: Test
echo "[6/6] Testing..."
echo "  Testing HTTP (backend):"
curl -s http://localhost:8080/api/health | head -c 50
echo ""
echo ""
echo "  Testing HTTPS (browser path):"
curl -s https://api.leasesights.tech/api/health 2>&1 | head -c 80 || echo "  (SSL still initializing, try again in 10 seconds)"
echo ""
echo ""

echo "=========================================="
echo "✓ CADDY RESET COMPLETE"
echo "=========================================="
echo ""
echo "If still getting SSL error:"
echo "  1. Wait 10-15 seconds for certificate provisioning"
echo "  2. Hard refresh browser (Ctrl+Shift+R)"
echo "  3. Check: sudo journalctl -u caddy -f"
echo ""
