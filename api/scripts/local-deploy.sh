#!/bin/bash
# Local automated deployment script - mimics GitHub Actions workflow locally

set -e

echo "🚀 Starting local deployment simulation..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if in correct directory
if [ ! -f "grace_api.py" ]; then
  echo -e "${RED}❌ Error: Must run from project root${NC}"
  exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
  cp .env.example .env
  echo -e "${YELLOW}⚠️  Please edit .env with your database credentials${NC}"
  exit 1
fi

# Build frontend
echo -e "${GREEN}📦 Building frontend...${NC}"
cd frontend
npm ci --silent
npm run build
cd ..

# Stop existing services
echo -e "${GREEN}🛑 Stopping existing services...${NC}"
pkill -f grace_api.py || true
pkill -f "vite" || true
sleep 2

# Start backend
echo -e "${GREEN}🔧 Starting backend...${NC}"
source .env
python3 grace_api.py > /tmp/backend-local.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Check backend health
if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"
else
  echo -e "${RED}❌ Backend failed to start${NC}"
  echo "Recent logs:"
  tail -20 /tmp/backend-local.log
  exit 1
fi

# Start frontend dev server
echo -e "${GREEN}🌐 Starting frontend dev server...${NC}"
cd frontend
npm run dev > /tmp/frontend-local.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 2

echo -e "${GREEN}✅ Local deployment complete!${NC}"
echo ""
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8001"
echo ""
echo "Backend PID:  $BACKEND_PID (logs: /tmp/backend-local.log)"
echo "Frontend PID: $FRONTEND_PID (logs: /tmp/frontend-local.log)"
echo ""
echo "To stop: pkill -f grace_api.py && pkill -f vite"
