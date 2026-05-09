#!/bin/bash
# SSL/TLS Diagnostic and Fix Script

echo "=========================================="
echo "SSL/TLS Diagnostic Report"
echo "=========================================="
echo ""

# Check if Caddy is running
echo "[1] Caddy Status:"
if systemctl is-active --quiet caddy; then
    echo "  ✓ Caddy is running"
else
    echo "  ✗ Caddy is NOT running"
    echo "  → Starting Caddy..."
    sudo systemctl start caddy
fi
echo ""

# Check Caddy logs
echo "[2] Recent Caddy Errors:"
sudo journalctl -u caddy -n 20 --no-pager | tail -10
echo ""

# Check certificate status
echo "[3] Certificate Status:"
sudo /usr/local/bin/caddy list-certs 2>/dev/null || echo "  → Caddy will auto-provision certs on first request"
echo ""

# Check backend connectivity
echo "[4] Backend Connectivity:"
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "  ✓ Backend HTTP responding at localhost:8080"
    curl -s http://localhost:8080/api/health | head -c 100
    echo ""
else
    echo "  ✗ Backend not responding"
    docker ps | grep leasesight-api
fi
echo ""

# Test HTTPS directly (may fail due to cert, but shows connectivity)
echo "[5] HTTPS Connectivity Test:"
curl -kv https://api.leasesights.tech/api/health 2>&1 | grep -E "HTTP|certificate|SSL" | head -5
echo ""

# Check DNS
echo "[6] DNS Resolution:"
nslookup api.leasesights.tech 2>/dev/null | grep -A 1 "api.leasesights.tech" || echo "  ✗ DNS not resolving"
echo ""

# Check if port 443 is open
echo "[7] Port 443 Status:"
ss -tulpn | grep ":443" || netstat -tulpn | grep ":443" || echo "  ✗ Port 443 not listening"
echo ""

# Reload Caddy to ensure latest config
echo "[8] Reloading Caddy..."
sudo systemctl reload caddy
sleep 2

# Final test
echo "[9] Final HTTPS Test:"
echo "  Attempting: curl https://api.leasesights.tech/api/health"
curl -s https://api.leasesights.tech/api/health -m 5 || echo "  Still failing - see above for details"
echo ""
echo "=========================================="
