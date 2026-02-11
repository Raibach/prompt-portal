#!/usr/bin/env python3
"""
Development server wrapper for Grace API
Enables auto-reload on file changes using Flask's debug mode
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from grace_api import app

if __name__ == '__main__':
    print("🚀 Grace AI API Server (Development Mode)")
    print("📡 Auto-reload enabled - server will restart on file changes")
    print("🎯 Server running on http://localhost:5001")
    print("")
    print("💡 Press Ctrl+C to stop")
    print("")
    
    # Run with debug mode and reloader enabled for development
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,  # Enable debug mode
        use_reloader=True,  # Enable auto-reload on file changes
        use_debugger=True,  # Enable debugger
        extra_files=None,  # Flask will watch all Python files automatically
    )

