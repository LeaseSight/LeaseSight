#!/bin/bash
# Complete LeaseSight CORS Fix Deployment Script
# Run this on Azure server to fix all CORS issues permanently

set -e

echo "=========================================="
echo "LeaseSight Production Deployment (v1.3.4)"
echo "=========================================="
echo ""

# Step 1: Update Caddy configuration
echo "[1/4] Updating Caddy configuration..."
sudo tee /etc/caddy/Caddyfile > /dev/null << 'EOF'
api.leasesights.tech {
    # STRIP all incoming CORS headers from backend (to remove wildcard)
    # Then set ONLY the correct ones
    reverse_proxy localhost:8080 {
        header_down -Access-Control-Allow-Origin
        header_down -Access-Control-Allow-Methods
        header_down -Access-Control-Allow-Headers
        header_down -Access-Control-Allow-Credentials
        header_down -Access-Control-Expose-Headers
    }

    # NOW set fresh CORS headers - single source of truth
    header Access-Control-Allow-Origin "https://www.leasesights.tech"
    header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE, PATCH"
    header Access-Control-Allow-Headers "Content-Type, Authorization, X-OpenAI-Key, X-Pinecone-Key"
    header Access-Control-Allow-Credentials "true"
    header Access-Control-Expose-Headers "Content-Type, Content-Disposition"

    # Handle preflight OPTIONS directly - 204 No Content
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
EOF

# Validate and reload Caddy
echo "  → Validating Caddy config..."
sudo caddy validate --config /etc/caddy/Caddyfile
echo "  → Reloading Caddy..."
sudo systemctl reload caddy
echo "  ✓ Caddy updated and reloaded"
echo ""

# Step 2: Update application code
echo "[2/4] Pulling latest code from git..."
cd /opt/leasesight
git fetch origin main
git reset --hard origin/main
echo "  ✓ Code updated"
echo ""

# Step 3: Rebuild Docker image
echo "[3/4] Rebuilding Docker image..."
docker build --no-cache -t leasesight-backend:latest .
echo "  ✓ Docker image built"
echo ""

# Step 4: Restart container
echo "[4/4] Restarting backend container..."
docker stop leasesight-api 2>/dev/null || true
docker rm leasesight-api 2>/dev/null || true
docker run -d \
  --name leasesight-api \
  -p 8080:8080 \
  --env-file /opt/leasesight/.env \
  --restart unless-stopped \
  leasesight-backend:latest
echo "  ✓ Backend restarted"
echo ""

# Wait for container to be ready
echo "Waiting for backend to start..."
sleep 3

# Test health endpoint
echo "Testing health endpoint..."
if curl -s http://localhost:8080/api/health > /dev/null; then
    echo "  ✓ Backend is healthy"
else
    echo "  ✗ Backend health check failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "CORS is now permanently fixed:"
echo "  • Caddy strips old CORS headers from backend"
echo "  • Caddy sets correct specific-origin headers"
echo "  • FastAPI middleware removes any CORS headers it tries to send"
echo "  • Result: Single, clean CORS header sent to browser"
echo ""
echo "Test: Open https://www.leasesights.tech and check console for CORS errors"
