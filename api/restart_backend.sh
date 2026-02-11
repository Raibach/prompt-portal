#!/bin/bash
# Backend Restart Script for SiteGround
# Run this after deployment to restart the backend service

set -e

echo "🔄 Restarting Prompt Portal Backend..."

# Go to backend directory
cd "$(dirname "$0")"

# Kill existing backend
echo "Stopping existing backend process..."
pkill -f grace_api.py || echo "No existing process found"
sleep 2

# Start backend
echo "Starting backend..."
nohup python3 grace_api.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
sleep 3

# Health check
if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
  echo "✅ Backend started successfully"
  echo "✅ Health check passed"
  echo ""
  echo "Backend is running at http://localhost:8001"
  echo "Proxied via: https://api.prompt-portal-prod.raibach.net"
else
  echo "⚠️ Backend started but health check failed (may still be initializing)"
  echo "   Check logs: tail -f /tmp/backend.log"
  exit 1
fi
