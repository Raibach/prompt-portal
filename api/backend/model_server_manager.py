"""
Model Server Manager - On-demand startup of model servers
Only starts the model server when it's actually needed
"""

import subprocess
import time
import socket
import os
from typing import Optional
from pathlib import Path

# Model server ports
GRACE_PORT = 8080
KAREN_PORT = 8081

# Timeout for server startup (seconds)
STARTUP_TIMEOUT = 60

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_grace_server() -> bool:
    """Start Grace model server on port 8080 if not running"""
    if check_port(GRACE_PORT):
        print(f"✅ Grace server already running on port {GRACE_PORT}")
        return True
    
    script_path = PROJECT_ROOT / "scripts" / "model-management" / "start_llama_server.sh"
    if not script_path.exists():
        print(f"❌ Grace server script not found: {script_path}")
        return False
    
    print(f"🚀 Starting Grace server (port {GRACE_PORT})...")
    print(f"   This may take 30-60 seconds to load the model...")
    
    try:
        # Start server in background
        log_file = open("/tmp/grace_server.log", "a")
        process = subprocess.Popen(
            ["bash", str(script_path)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT)
        )
        
        # Wait for server to be ready
        print(f"   Waiting for server to start (max {STARTUP_TIMEOUT}s)...")
        for i in range(STARTUP_TIMEOUT):
            if check_port(GRACE_PORT):
                print(f"✅ Grace server started successfully (took {i+1}s)")
                return True
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                print(f"   Still waiting... ({i+1}s)")
        
        print(f"⚠️ Grace server startup timeout after {STARTUP_TIMEOUT}s")
        print(f"   Check logs: tail -f /tmp/grace_server.log")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start Grace server: {e}")
        return False


def start_karen_server() -> bool:
    """Start Karen model server on port 8081 if not running"""
    if check_port(KAREN_PORT):
        print(f"✅ Karen server already running on port {KAREN_PORT}")
        return True
    
    script_path = PROJECT_ROOT / "scripts" / "model-management" / "start_karen_server.sh"
    if not script_path.exists():
        print(f"❌ Karen server script not found: {script_path}")
        return False
    
    print(f"🚀 Starting Karen server (port {KAREN_PORT})...")
    print(f"   This may take 30-60 seconds to load the model...")
    
    try:
        # Start server in background
        log_file = open("/tmp/karen_server.log", "a")
        process = subprocess.Popen(
            ["bash", str(script_path)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT)
        )
        
        # Wait for server to be ready
        print(f"   Waiting for server to start (max {STARTUP_TIMEOUT}s)...")
        for i in range(STARTUP_TIMEOUT):
            if check_port(KAREN_PORT):
                print(f"✅ Karen server started successfully (took {i+1}s)")
                return True
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                print(f"   Still waiting... ({i+1}s)")
        
        print(f"⚠️ Karen server startup timeout after {STARTUP_TIMEOUT}s")
        print(f"   Check logs: tail -f /tmp/karen_server.log")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start Karen server: {e}")
        return False


def ensure_grace_server() -> bool:
    """Ensure Grace server is running, start if needed"""
    if check_port(GRACE_PORT):
        return True
    return start_grace_server()


def ensure_karen_server() -> bool:
    """Ensure Karen server is running, start if needed"""
    if check_port(KAREN_PORT):
        return True
    return start_karen_server()

