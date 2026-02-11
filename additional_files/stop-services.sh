#!/bin/bash

# Grace Editor - Stop All Services Script

echo "🛑 Stopping all services..."

# Kill any processes on ports 8001 (backend), 5173 (frontend), 8080 (llama-server), and 4040 (ngrok)
lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:8080 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:4040 2>/dev/null | xargs kill -9 2>/dev/null || true

# Kill any existing processes
pkill -f "grace_api.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "llama-server" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true

echo "✅ All services stopped"

