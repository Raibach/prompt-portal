#!/bin/bash
# Real-time system monitoring for Grace Editor
# Monitors memory, CPU, backend health, and logs for crashes

echo "🔍 Grace Editor System Monitor"
echo "Press Ctrl+C to stop"
echo ""

while true; do
  TIMESTAMP=$(date '+%H:%M:%S')
  echo "=== $TIMESTAMP ==="
  
  # Check processes
  echo "📊 Process Status:"
  ps aux | grep -E "(grace_api|llama-server)" | grep -v grep | awk '{printf "  %-50s %6.1f MB (%5.2f%%) CPU: %5.1f%%\n", $11, $6/1024, $4, $3}'
  
  # Check backend health
  if curl -s -m 2 http://localhost:5001/api/health >/dev/null 2>&1; then
    echo "  ✅ Backend: RESPONDING"
  else
    echo "  ❌ Backend: NOT RESPONDING - CRASH DETECTED!"
  fi
  
  # Check for errors in logs
  if tail -n 5 /tmp/grace_api.log 2>/dev/null | grep -qi -E "(error|exception|traceback|500|failed|timeout)"; then
    echo "  ⚠️  ERROR DETECTED IN LOGS:"
    tail -n 5 /tmp/grace_api.log 2>/dev/null | grep -i -E "(error|exception|traceback|500|failed|timeout)" | tail -3
  else
    echo "  ✅ No recent errors"
  fi
  
  # Check error log file
  if [ -f /tmp/grace_api_errors.log ]; then
    ERROR_COUNT=$(wc -l < /tmp/grace_api_errors.log 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
      echo "  ⚠️  Error log file has $ERROR_COUNT lines"
      tail -n 2 /tmp/grace_api_errors.log 2>/dev/null
    fi
  fi
  
  # Memory spike detection
  BACKEND_MEM=$(ps aux | grep "grace_api" | grep -v grep | awk '{print $4}')
  LLAMA_MEM=$(ps aux | grep "llama-server" | grep -v grep | awk '{print $4}')
  
  if [ ! -z "$BACKEND_MEM" ] && (( $(echo "$BACKEND_MEM > 15.0" | bc -l 2>/dev/null || echo 0) )); then
    echo "  ⚠️  BACKEND MEMORY SPIKE: ${BACKEND_MEM}%"
  fi
  
  if [ ! -z "$LLAMA_MEM" ] && (( $(echo "$LLAMA_MEM > 25.0" | bc -l 2>/dev/null || echo 0) )); then
    echo "  ⚠️  LLAMA-SERVER MEMORY SPIKE: ${LLAMA_MEM}%"
  fi
  
  echo ""
  sleep 2
done

