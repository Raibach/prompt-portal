#!/bin/bash

# Grace Editor - Restart All Services Script
# This script stops and restarts backend, frontend, and llama-server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping all services..."

# Kill any processes on ports 8001 (backend), 5173 (frontend), 8080 (llama-server)
lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:8080 2>/dev/null | xargs kill -9 2>/dev/null || true

# Kill any existing processes
pkill -f "grace_api.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "llama-server" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true

# Wait a moment for processes to fully stop
sleep 2

echo "✅ All services stopped"
echo ""

echo "🚀 Starting llama-server (port 8080)..."
if [[ -f "scripts/model-management/start_llama_server.sh" ]]; then
    bash scripts/model-management/start_llama_server.sh > /tmp/llama_server.log 2>&1 &
    LLAMA_PID=$!
    echo "   llama-server started (PID: $LLAMA_PID)"
    echo "   Logs: tail -f /tmp/llama_server.log"
    sleep 3
else
    echo "   ⚠️  Warning: start_llama_server.sh not found, skipping llama-server"
    LLAMA_PID=""
fi

echo ""
echo "🌐 Starting ngrok tunnel (port 8080)..."
ngrok http 8080 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo "   ngrok started (PID: $NGROK_PID)"
echo "   Waiting for ngrok to initialize..."
sleep 3

# Get ngrok public URL
NGROK_URL=""
if command -v curl &> /dev/null; then
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | grep -o 'https://[^"]*' | head -1)
fi

if [[ -n "$NGROK_URL" ]]; then
    echo "   ✅ ngrok URL: $NGROK_URL"
    echo "   📋 Add this to GitHub secrets as NGROK_MODEL_URL"
else
    echo "   ⚠️  Could not get ngrok URL (may still be starting)"
    echo "   Check: http://localhost:4040 or cat /tmp/ngrok.log"
fi

echo ""
echo "🐘 Checking PostgreSQL database..."
# Try multiple ways to check PostgreSQL
PG_CHECKED=false
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
        echo "   ✅ PostgreSQL is already running"
        PG_CHECKED=true
    fi
elif ps aux | grep -q "[p]ostgres.*5432"; then
    echo "   ✅ PostgreSQL appears to be running (process found)"
    PG_CHECKED=true
fi

if [ "$PG_CHECKED" = false ]; then
    echo "   PostgreSQL not running. Starting..."
    if command -v brew &> /dev/null; then
        brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null || true
        echo "   Waiting for PostgreSQL to be ready (max 10 seconds)..."
        TIMEOUT=10
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ]; do
            if command -v pg_isready &> /dev/null && pg_isready -h localhost -p 5432 -q 2>/dev/null; then
                echo "   ✅ PostgreSQL is ready"
                PG_CHECKED=true
                break
            fi
            sleep 1
            ELAPSED=$((ELAPSED + 1))
        done
        if [ "$PG_CHECKED" = false ]; then
            echo "   ⚠️  PostgreSQL may still be starting (timeout after ${TIMEOUT}s)"
        fi
    else
        echo "   ⚠️  brew not found. Please start PostgreSQL manually."
    fi
fi

echo ""
echo "🚀 Starting backend service (Flask on port 8001)..."
python3 grace_api.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started (PID: $BACKEND_PID)"
echo "   Logs: tail -f /tmp/backend.log"
sleep 2

echo ""
echo "🚀 Starting frontend service (Vite on port 5173)..."
cd frontend
PORT=5173 npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend started (PID: $FRONTEND_PID)"
echo "   Logs: tail -f /tmp/frontend.log"

echo ""
echo "✅ All services restarted!"
echo ""
echo "📊 Service Status:"
if [[ -n "$NGROK_PID" ]] && [[ -n "$NGROK_URL" ]]; then
    echo "   ngrok:        $NGROK_URL (PID: $NGROK_PID)"
    echo "                 Dashboard: http://localhost:4040"
fi
if [[ -n "$LLAMA_PID" ]]; then
    echo "   llama-server: http://localhost:8080 (PID: $LLAMA_PID)"
fi
if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
    echo "   Database:     PostgreSQL on localhost:5432 ✅"
else
    echo "   Database:     PostgreSQL not running ⚠️"
fi
echo "   Backend:      http://localhost:8001 (PID: $BACKEND_PID)"
echo "   Frontend:     http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "To stop all services, run: ./stop-services.sh"
if [[ -n "$NGROK_PID" ]] && [[ -n "$LLAMA_PID" ]]; then
    echo "Or manually: kill $NGROK_PID $LLAMA_PID $BACKEND_PID $FRONTEND_PID"
elif [[ -n "$LLAMA_PID" ]]; then
    echo "Or manually: kill $LLAMA_PID $BACKEND_PID $FRONTEND_PID"
elif [[ -n "$NGROK_PID" ]]; then
    echo "Or manually: kill $NGROK_PID $BACKEND_PID $FRONTEND_PID"
else
    echo "Or manually: kill $BACKEND_PID $FRONTEND_PID"
fi

