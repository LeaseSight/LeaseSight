#!/bin/bash
# Complete LeaseSight CORS Fix Deployment Script
# Run this on Azure server to fix all CORS issues permanently

set -e

echo "=========================================="
echo "LeaseSight Production Deployment (v1.3.5)"
echo "=========================================="
echo ""

# Step 1: Update Caddy configuration
echo "[1/5] Updating Caddy configuration..."
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
echo "[2/5] Pulling latest code from git..."
cd /home/azureuser/LeaseSight
git fetch origin main
git reset --hard origin/main
echo "  ✓ Code updated"
echo ""

# Step 3: Rebuild Docker image
echo "[3/5] Rebuilding Docker image..."
docker build --no-cache -t leasesight-backend:latest .
echo "  ✓ Docker image built"
echo ""

# Step 4: Restart container
echo "[4/5] Restarting backend container..."
docker stop leasesight-api 2>/dev/null || true
docker rm leasesight-api 2>/dev/null || true
docker run -d \
  --name leasesight-api \
  -p 8080:8080 \
  --env-file /home/azureuser/LeaseSight/.env \
  -v /home/azureuser/LeaseSight/data:/app/data \
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

echo "[5/5] Building and syncing frontend UI layout..."
cd /home/azureuser/LeaseSight/leasesight-ui
if [ -f .env.local ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
elif [ -f ../.env ]; then
  set -a
  # shellcheck disable=SC1091
  source ../.env
  set +a
fi
if [ -z "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]; then
  echo "  ✗ NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is required for frontend build"
  exit 1
fi
npm ci
npm run build
sudo rm -rf /var/www/leasesight-ui/*
sudo cp -r out/* /var/www/leasesight-ui/
echo "Frontend sync complete! Restarting Caddy server..."
sudo systemctl restart caddy

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
echo "Frontend:"
echo "  • Next.js static export built and synced to /var/www/leasesight-ui"
echo ""
echo "Test: Open https://www.leasesights.tech and hard-refresh (Ctrl+Shift+R)"
