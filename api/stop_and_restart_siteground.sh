#!/bin/bash
# SiteGround Backend Force Stop and Restart
# This script forcefully kills ALL backend processes and restarts cleanly
# Works without lsof (not available on SiteGround)

echo "🔥 FORCE STOP AND RESTART - SiteGround Backend"
echo "================================================"

# Go to backend directory
cd "$(dirname "$0")"
if [ -d ~/www/prompt-portal-prod.raibach.net/api ]; then
  cd ~/www/prompt-portal-prod.raibach.net/api
elif [ -d ~/prompt-portal-prod.raibach.net/api ]; then
  cd ~/prompt-portal-prod.raibach.net/api
fi

echo "📍 Working directory: $(pwd)"
echo ""

# First - check what's ACTUALLY using the port before we start killing
echo "🔍 PRE-CLEANUP DIAGNOSTIC - What's using port 8003?"
if netstat -tlnp 2>/dev/null | grep -q ":8003 "; then
  netstat -tlnp 2>/dev/null | grep ":8003 "
  echo "   Finding and killing specific PIDs..."
  netstat -tlnp 2>/dev/null | grep ":8003 " | awk '{print $7}' | cut -d'/' -f1 | while read pid; do
    if [ "$pid" != "-" ] && [ -n "$pid" ] && [ "$pid" != "0" ]; then
      echo "   Killing PID $pid specifically..."
      kill -9 $pid 2>/dev/null || true
    fi
  done
else
  echo "   ✅ Port 8003 not in use"
fi

echo ""
echo "🔍 All Python/gunicorn/Flask processes running:"
ps aux 2>/dev/null | grep -E "[p]ython|[g]unicorn|[F]lask|[g]race" | head -20 || echo "   None found"

echo ""
echo "🔍 All ports 8001-8004 in use:"
netstat -tln 2>/dev/null | grep -E ":800[1234] " || echo "   None in use"

echo ""
echo "🔍 Checking for cron jobs:"
crontab -l 2>/dev/null | grep -E "grace|python|restart" || echo "   No relevant cron jobs"
echo ""

# CRITICAL: Use flock for atomic locking (prevents ANY parallel execution)
LOCKFILE="/tmp/backend_deploy.lock"
echo "🔒 Acquiring exclusive deployment lock..."
exec 200>"$LOCKFILE"
if ! flock -n 200; then
  echo "❌ Another deployment is ACTIVELY running! Waiting up to 60 seconds..."
  if flock -w 60 200; then
    echo "✅ Lock acquired after wait"
  else
    echo "❌ Could not acquire lock after 60 seconds. Forcing cleanup..."
    # Nuclear option: remove lock and try again
    rm -f "$LOCKFILE"
    exec 200>"$LOCKFILE"
    flock -n 200 || {
      echo "❌ FATAL: Cannot acquire deployment lock"
      exit 1
    }
  fi
fi
echo "✅ Exclusive deployment lock acquired (PID: $$)"

# Lock will be automatically released when script exits (fd 200 closes)

# ULTRA-AGGRESSIVE CLEANUP: Kill everything by all methods
echo "💣 ULTRA-AGGRESSIVE CLEANUP..."

# Method 1: Kill by process name
echo "   Method 1: Kill by process name..."
pkill -9 -f "grace_api.py" 2>/dev/null || true
pkill -9 -f "gunicorn" 2>/dev/null || true
pkill -9 -f "python.*grace_api" 2>/dev/null || true

# Method 2: Kill by port using fuser (FIRST - before netstat)
echo "   Method 2: Kill by port using fuser..."
for port in 8001 8002 8003 8004 8005; do
  fuser -k -9 $port/tcp 2>/dev/null || true
done

# Method 3: Kill by finding PIDs from netstat
echo "   Method 3: Kill PIDs found by netstat..."
for port in 8001 8002 8003 8004 8005; do
  netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | while read pid; do
    if [ "$pid" != "-" ] && [ -n "$pid" ] && [ "$pid" != "0" ]; then
      kill -9 $pid 2>/dev/null || true
    fi
  done
done

# Method 4: Find and kill ANY process with grace_api or gunicorn in command line
echo "   Method 4: Kill by command line pattern..."
ps aux 2>/dev/null | grep -E "[g]race_api|[g]unicorn.*grace" | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

# CRITICAL: Linux TIME_WAIT state can last 60 seconds. We MUST wait this long.
echo "⏳ Waiting FULL 60 seconds for kernel TIME_WAIT sockets to clear..."
echo "   (This is required - Linux holds sockets for up to 60 seconds after close)"
sleep 60

# Verify ports are free
echo "🔍 Checking if ports are free..."
for port in 8001 8002 8003 8004; do
  if netstat -tln 2>/dev/null | grep -q ":$port "; then
    echo "   ⚠️  Port $port still in use (will retry)"
    fuser -k -9 $port/tcp 2>/dev/null || true
  else
    echo "   ✅ Port $port is free"
  fi
done

sleep 5

echo ""
echo "✅ All ports cleared!"
echo ""

# Clear old logs to avoid confusion
echo "🧹 Clearing old log files..."
> /tmp/backend.log
> /tmp/backend_access.log  
> /tmp/backend_gunicorn.log

# Start backend on PORT 8004 (avoiding stuck port 8003)
echo "🚀 Starting backend with gunicorn on port 8004 (skipping stuck port 8003)..."
nohup gunicorn \
  --bind 127.0.0.1:8004 \
  --workers 1 \
  --timeout 300 \
  --access-logfile /tmp/backend_access.log \
  --error-logfile /tmp/backend.log \
  --log-level info \
  grace_api:app > /tmp/backend_gunicorn.log 2>&1 &
BACKEND_PID=$!
echo "   Started with PID: $BACKEND_PID"

sleep 10

# Check if it's running
if kill -0 $BACKEND_PID 2>/dev/null; then
  echo "✅ Backend process is alive!"
  
  # Health check
  echo "🏥 Running health check..."
  sleep 2
  if curl -s http://localhost:8004/api/health > /dev/null 2>&1; then
    echo "✅ Health check PASSED!"
    echo ""
    echo "🎉 SUCCESS! Backend is running at:"
    echo "   Internal: http://localhost:8004"
    echo "   Public:   https://prompt-portal-prod.raibach.net"
    echo ""
    echo "View logs: tail -f /tmp/backend.log"
  else
    echo "⚠️  Health check failed (may still be initializing)"
    echo "   Wait 10 seconds and try: curl http://localhost:8004/api/health"
    echo "   Logs: tail -f /tmp/backend.log"
  fi
else
  echo "❌ Backend died immediately!"
  echo ""
  echo "🔍 DIAGNOSIS - What's using port 8004 RIGHT NOW:"
  netstat -tlnp 2>/dev/null | grep ":8004 " || echo "Nothing on netstat"
  ss -tlnp 2>/dev/null | grep ":8004 " || echo "Nothing on ss"
  echo ""
  echo "🔍 All running Python/gunicorn processes:"
  ps aux 2>/dev/null | grep -E "[p]ython|[g]unicorn" | head -20 || echo "None found"
  echo ""
  echo "📋 Last 40 lines of gunicorn logs:"
  tail -40 /tmp/backend.log
  exit 1
fi
