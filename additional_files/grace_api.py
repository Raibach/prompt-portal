"""
Grace AI API Server - Flask backend without Gradio
Uses all original Grace functions from grace_gui.py
"""

# Suppress urllib3 OpenSSL warnings (LibreSSL compatibility)
import warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from typing import Optional, Dict, Any
import os
# faiss: optional to avoid segfault on import (EXC_BAD_ACCESS on some ARM64/macOS). Lazy-loaded via _get_faiss().
# Set DISABLE_FAISS=1 to never load faiss (server will start; memory/news index features disabled).
import pickle
# PyMuPDF (fitz): lazy-loaded to avoid segfault on import. Use _get_fitz() when needed.
HAS_PYMUPDF = False
_fitz_module = None

def _get_fitz():
    global _fitz_module, HAS_PYMUPDF
    if _fitz_module is not None:
        return _fitz_module
    try:
        import fitz as _f
        _fitz_module = _f
        HAS_PYMUPDF = True
        return _fitz_module
    except Exception as e:
        print(f"ℹ️  PyMuPDF (fitz) not available: {e}. PDF processing disabled.")
        _fitz_module = False
        return None

import requests
import re
# DISABLED: Embedding model not available - memory/embedding features disabled
HAS_SENTENCE_TRANSFORMERS = False
SentenceTransformer = None
print("ℹ️  Embedding model (sentence-transformers) disabled. Memory/embedding features will be unavailable.")
# numpy: lazy-loaded to avoid segfault on import (some ARM64/macOS builds). Use _get_numpy() when needed.
_numpy_module = None

def _get_numpy():
    global _numpy_module
    if _numpy_module is not None:
        return _numpy_module
    try:
        import numpy as _np
        _numpy_module = _np
        return _numpy_module
    except Exception as e:
        print(f"ℹ️  numpy not available: {e}")
        _numpy_module = False
        return None

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import base64
from functools import wraps
import time
from collections import defaultdict
from dotenv import load_dotenv
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("⚠️ PyYAML not available. Some YAML-based features may be unavailable.")

# Load environment variables
load_dotenv()

# Get database URL - prefer localhost for development, Railway URLs for production
# For local development: Use DATABASE_URL if it points to localhost
# For production: Prefer DATABASE_PUBLIC_URL (Railway public) over DATABASE_URL (internal)
_db_public_url = os.getenv('DATABASE_PUBLIC_URL')
_db_internal_url = os.getenv('DATABASE_URL')

# Check if we're in local development (localhost or 127.0.0.1)
_is_local_dev = False
if _db_internal_url:
    _is_local_dev = ('localhost' in _db_internal_url.lower() or 
                     '127.0.0.1' in _db_internal_url.lower())

# Validate and choose the best URL
# Log what we found for debugging
print(f"🔍 Database URL Configuration Check:")
print(f"   DATABASE_PUBLIC_URL: {'✅ Set' if _db_public_url else '❌ Not set'}")
print(f"   DATABASE_URL: {'✅ Set' if _db_internal_url else '❌ Not set'}")
if _is_local_dev:
    print(f"   🏠 LOCAL DEVELOPMENT MODE detected (localhost)")


# For local development, always use localhost DATABASE_URL (ignore DATABASE_PUBLIC_URL)
if _is_local_dev:
    DATABASE_URL = _db_internal_url
    print(f"✅ Using LOCAL database for development")
    print(f"   Host: localhost:5432")
    print(f"   Database: railway")
elif _db_public_url:
    # Production: Check if public URL is valid (not a placeholder)
    _db_public_lower = _db_public_url.lower()
    is_valid_public = ('.rlwy.net' in _db_public_lower or 
                      'railway.app' in _db_public_lower or 
                      'localhost' in _db_public_lower or
                      '127.0.0.1' in _db_public_lower)
    
    # Reject if it contains placeholder 'hostname' (unless it's part of a valid domain)
    has_placeholder = 'hostname' in _db_public_lower and not is_valid_public
    
    if has_placeholder:
        print(f"❌ DATABASE_PUBLIC_URL contains placeholder 'hostname': {_db_public_url[:60]}...")
        print(f"   Checking DATABASE_URL as fallback...")
        DATABASE_URL = None  # Don't use invalid URL
    elif is_valid_public:
        DATABASE_URL = _db_public_url
        print(f"✅ Using DATABASE_PUBLIC_URL (public Railway URL)")
        print(f"   Host: {_db_public_url.split('@')[1].split('/')[0] if '@' in _db_public_url else 'unknown'}")
    else:
        # Unknown format, try it anyway but log
        DATABASE_URL = _db_public_url
        print(f"⚠️ Using DATABASE_PUBLIC_URL (unknown format, will attempt connection)")
else:
    DATABASE_URL = None
    print(f"⚠️ DATABASE_PUBLIC_URL not set")

# Fallback to DATABASE_URL if public URL not available or invalid (production only)
# Also check if DATABASE_URL is actually a public URL (user might have set it manually)
if not DATABASE_URL and _db_internal_url and not _is_local_dev:
    _db_internal_lower = _db_internal_url.lower()
    
    # Check if it's a public Railway URL (even though it's in DATABASE_URL variable)
    is_public_url = ('.rlwy.net' in _db_internal_lower or 
                    'railway.app' in _db_internal_lower)
    
    # Check if it's a valid internal Railway URL
    is_valid_internal = ('railway.internal' in _db_internal_lower or 
                        'localhost' in _db_internal_lower or
                        '127.0.0.1' in _db_internal_lower)
    
    # Reject if it contains placeholder 'hostname' (and not a valid URL)
    has_placeholder = 'hostname' in _db_internal_lower and not (is_public_url or is_valid_internal)
    
    if has_placeholder:
        print(f"❌ DATABASE_URL contains placeholder 'hostname': {_db_internal_url[:60]}...")
        print(f"   Database features will be DISABLED")
        print(f"   SOLUTION: Set DATABASE_PUBLIC_URL in Railway environment variables")
        print(f"   Or set DATABASE_URL to the public URL: postgresql://postgres:PASSWORD@hopper.proxy.rlwy.net:PORT/railway")
        DATABASE_URL = None
    elif is_public_url:
        # User set DATABASE_URL to public URL - that's fine!
        DATABASE_URL = _db_internal_url
        print(f"✅ Using DATABASE_URL (contains public Railway URL)")
        print(f"   Host: {_db_internal_url.split('@')[1].split('/')[0] if '@' in _db_internal_url else 'unknown'}")
        print(f"   💡 Tip: Consider using DATABASE_PUBLIC_URL variable name for clarity")
    elif is_valid_internal:
        DATABASE_URL = _db_internal_url
        print(f"✅ Using DATABASE_URL (internal Railway URL)")
        print(f"   Host: {_db_internal_url.split('@')[1].split('/')[0] if '@' in _db_internal_url else 'unknown'}")
    else:
        # Unknown format, but try it anyway (might be a custom setup)
        DATABASE_URL = _db_internal_url
        print(f"⚠️ Using DATABASE_URL (unknown format, will attempt connection)")
        print(f"   Host: {_db_internal_url.split('@')[1].split('/')[0] if '@' in _db_internal_url else 'unknown'}")

if not DATABASE_URL:
    print(f"❌ No valid DATABASE_URL available - Database features DISABLED")
    print(f"   Railway Best Practice: Use private DATABASE_URL to avoid egress fees")
    print(f"   To fix:")
    print(f"   1. Go to Railway Dashboard → Your App Service (the one running this Python app)")
    print(f"   2. Click 'Variables' tab")
    print(f"   3. Look for DATABASE_URL (Railway should auto-generate this when PostgreSQL is added)")
    print(f"   4. If DATABASE_URL is missing:")
    print(f"      a. Go to Railway Dashboard → Your PostgreSQL Service")
    print(f"      b. Click 'Variables' tab")
    print(f"      c. Find DATABASE_URL value")
    print(f"      d. Copy it to your App Service → Variables → Add DATABASE_URL")
    print(f"   5. Verify both services are in the same Railway project")
    print(f"   6. Railway's private DATABASE_URL uses 'railway.internal' hostname (no egress fees)")
    print(f"   ⚠️  Avoid using DATABASE_PUBLIC_URL unless absolutely necessary (incurs egress fees)")

# Import Grace configuration system
try:
    from config.grace_config import GraceConfig, NeuralBackend
    USE_GRACE_CONFIG = True
except ImportError:
    try:
        # Fallback to old location
        from grace_config import GraceConfig, NeuralBackend
        USE_GRACE_CONFIG = True
    except ImportError:
        USE_GRACE_CONFIG = False
        print("Warning: grace_config not found, using legacy configuration")

# Memory System (Memory + Will = Consciousness)
try:
    from grace_memory_api import GraceMemoryAPI
    # DATABASE_URL is already set above (prefers DATABASE_PUBLIC_URL)
    if DATABASE_URL:
        memory_api = GraceMemoryAPI(DATABASE_URL)
        HAS_MEMORY_SYSTEM = True
        print("✅ Memory system initialized (Consciousness substrate)")
    else:
        HAS_MEMORY_SYSTEM = False
        memory_api = None
        print("⚠️  DATABASE_URL not found - Memory system disabled")
except ImportError:
    HAS_MEMORY_SYSTEM = False
    memory_api = None
    print("⚠️  grace_memory_api not found - Memory system disabled")
except Exception as e:
    HAS_MEMORY_SYSTEM = False
    memory_api = None
    print(f"⚠️  Memory system initialization failed: {e}")

# Cache for default project IDs to prevent duplicate creation
_default_project_cache = {}  # {user_id: project_id}

# Projects and Conversations API
try:
    from backend.conversation_api import ConversationAPI
    from backend.projects_api import ProjectsAPI
    from backend.quarantine_api import QuarantineAPI
    
    # DATABASE_URL is already set above (prefers DATABASE_PUBLIC_URL)
    # Validate DATABASE_URL doesn't contain placeholder values
    if DATABASE_URL:
        url_lower = DATABASE_URL.lower()
        
        # Check for literal placeholder values (not actual valid parts of a URL)
        # These are common placeholders that indicate the URL wasn't properly configured
        placeholder_patterns = [
            '/hostname',  # postgresql://user:pass@hostname:port/db
            '@hostname:',  # user@hostname:port
            'hostname:port',  # hostname:5432
            'user:password@',  # literal placeholder
            '@user:password@',  # double placeholder
        ]
        
        # Also check if it's the exact placeholder pattern from .env.example
        has_placeholder = any(pattern in url_lower for pattern in placeholder_patterns)
        
        # Additional check: if the hostname part looks like a placeholder word
        try:
            from urllib.parse import urlparse
            parsed = urlparse(DATABASE_URL)
            hostname = parsed.hostname
            if hostname:
                hostname_lower = hostname.lower()
                # Check if hostname is literally "hostname" (placeholder)
                if hostname_lower == 'hostname':
                    has_placeholder = True
                    print(f"❌ Detected placeholder hostname: '{hostname}'")
                # Check if it contains "hostname" as a substring (like "postgres@hostname:5432")
                elif 'hostname' in hostname_lower and hostname_lower != 'hostname':
                    # This might be part of a larger invalid URL
                    has_placeholder = True
                    print(f"❌ Detected placeholder in hostname: '{hostname}'")
        except Exception as parse_error:
            print(f"⚠️ Could not parse DATABASE_URL: {parse_error}")
            # If we can't parse it, it's likely invalid
            if 'hostname' in url_lower:
                has_placeholder = True
        
        if has_placeholder:
            print(f"❌ DATABASE_URL contains placeholder values - Database APIs disabled")
            print(f"   DATABASE_URL: {DATABASE_URL[:80]}... (truncated)")
            print(f"   The URL contains placeholder text like 'hostname' which is not a valid hostname")
            print(f"   SOLUTION: Set DATABASE_PUBLIC_URL in Railway environment variables")
            print(f"   Example: postgresql://postgres:PASSWORD@hopper.proxy.rlwy.net:PORT/railway")
            print(f"   Or use a valid DATABASE_URL without placeholder values")
            HAS_DATABASE_APIS = False
            conversation_api = None
            projects_api = None
        else:
            try:
                print(f"🔌 Attempting to connect to database...")
                print(f"   URL: {DATABASE_URL[:60]}... (truncated for security)")
                conversation_api = ConversationAPI(DATABASE_URL)
                projects_api = ProjectsAPI(DATABASE_URL)
                quarantine_api = QuarantineAPI(DATABASE_URL)
                
                # Test connection immediately
                try:
                    test_conn = conversation_api.get_db()
                    test_cursor = test_conn.cursor()
                    test_cursor.execute("SELECT 1")
                    test_cursor.fetchone()
                    test_cursor.close()
                    test_conn.close()
                    print("✅ Database connection test successful!")
                except Exception as test_error:
                    print(f"⚠️ Database connection test failed: {test_error}")
                    # Continue anyway - might work later
                
                HAS_DATABASE_APIS = True
                print("✅ Projects, Conversations, and Quarantine API initialized")
            except Exception as init_error:
                error_msg = str(init_error)
                error_msg_lower = error_msg.lower()
                
                # Log detailed error to file AND stdout (for Railway logs)
                import traceback
                error_log_path = "logs/database_init_error.log"
                error_traceback = traceback.format_exc()
                
                # Log to file (if logs directory is writable)
                try:
                    os.makedirs("logs", exist_ok=True)
                    with open(error_log_path, "a") as f:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"Database Initialization Error - {datetime.now().isoformat()}\n")
                        f.write(f"{'='*60}\n")
                        f.write(f"DATABASE_URL: {DATABASE_URL[:100]}...\n")
                        f.write(f"Error: {error_msg}\n")
                        f.write(f"Traceback:\n{error_traceback}\n")
                except Exception as log_error:
                    print(f"⚠️ Could not write to error log file: {log_error}")
                
                # ALSO print to stdout (Railway will capture this)
                print(f"\n{'='*60}")
                print(f"❌ DATABASE INITIALIZATION ERROR - {datetime.now().isoformat()}")
                print(f"{'='*60}")
                print(f"Error: {error_msg}")
                print(f"Traceback:\n{error_traceback}")
                print(f"{'='*60}\n")
                
                print(f"\n❌ DATABASE CONNECTION FAILED")
                print(f"{'='*60}")
                print(f"Error: {error_msg}")
                print(f"{'='*60}")
                
                if 'hostname' in error_msg_lower or 'could not translate' in error_msg_lower:
                    print(f"\n🔍 DIAGNOSIS: Invalid hostname")
                    print(f"   The hostname in DATABASE_URL cannot be resolved")
                    print(f"   Check if the URL contains 'hostname' placeholder")
                    print(f"   Or if the hostname is misspelled")
                elif 'connection refused' in error_msg_lower:
                    print(f"\n🔍 DIAGNOSIS: Connection refused")
                    print(f"   The database server is not accepting connections")
                    print(f"   Check if PostgreSQL service is running in Railway")
                    print(f"   Check if the port number is correct")
                elif 'timeout' in error_msg_lower:
                    print(f"\n🔍 DIAGNOSIS: Connection timeout")
                    print(f"   Cannot reach the database server")
                    print(f"   Check network/firewall settings")
                    print(f"   Verify the hostname and port are correct")
                elif 'authentication failed' in error_msg_lower or 'password' in error_msg_lower:
                    print(f"\n🔍 DIAGNOSIS: Authentication failed")
                    print(f"   Wrong username or password")
                    print(f"   Check the credentials in DATABASE_URL")
                elif 'ssl' in error_msg_lower:
                    print(f"\n🔍 DIAGNOSIS: SSL connection issue")
                    print(f"   Database may require SSL mode configuration")
                    print(f"   Code should add sslmode parameter automatically")
                else:
                    print(f"\n🔍 DIAGNOSIS: Unknown error")
                    print(f"   Check the full error details in: {error_log_path}")
                
                print(f"\n💡 SOLUTION:")
                print(f"   1. Verify DATABASE_URL in environment variables")
                print(f"   2. Check PostgreSQL service is running")
                print(f"   3. Verify the connection string format is correct")
                print(f"   4. Check full error details in: {error_log_path}")
                print(f"{'='*60}\n")
                
                HAS_DATABASE_APIS = False
                conversation_api = None
                projects_api = None
    else:
        print(f"DEBUG: DATABASE_URL check failed, DATABASE_URL = {DATABASE_URL}")
        HAS_DATABASE_APIS = False
        conversation_api = None
        projects_api = None
        quarantine_api = None
        print("⚠️  DATABASE_URL not found - Projects/Conversations/Quarantine API disabled")
except ImportError as e:
    HAS_DATABASE_APIS = False
    conversation_api = None
    projects_api = None
    quarantine_api = None
    print(f"⚠️  Failed to import Projects/Conversations/Quarantine API: {e}")

app = Flask(__name__)

# Global error handler to prevent crashes and improve error logging
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler to prevent backend crashes"""
    import traceback
    error_detail = traceback.format_exc()
    error_msg = str(e)
    
    # Log to console
    print(f"\n❌ Unhandled Exception: {error_msg}")
    print(f"   Traceback:\n{error_detail}")
    
    # Log to file if available
    try:
        with open('/tmp/grace_api_errors.log', 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Error: {error_msg}\n")
            f.write(f"Traceback:\n{error_detail}\n")
            f.write(f"{'='*60}\n")
    except:
        pass
    
    # Try to log via debug logger if available
    if DEBUG_LOGGING_ENABLED and debug_logger:
        try:
            debug_logger.error("Unhandled exception", e, {
                "error_message": error_msg,
                "traceback": error_detail
            })
        except:
            pass
    
    # Return appropriate error response
    return jsonify({
        "error": "Internal server error",
        "message": error_msg if len(error_msg) < 200 else error_msg[:200] + "...",
        "code": "INTERNAL_ERROR"
    }), 500

# Initialize debug logging system
DEBUG_LOGGING_ENABLED = False
debug_logger = None
log_request_response = lambda f: f  # No-op decorator by default

try:
    from backend.debug_logger import debug_logger, log_request_response
    from backend.debug_api import debug_bp
    from flask import g
    import uuid
    
    # Try to import memory_monitor (requires psutil)
    try:
        from backend.memory_monitor import get_memory_monitor, track_operation
        MEMORY_MONITOR_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ Memory monitor not available: {e}")
        MEMORY_MONITOR_AVAILABLE = False
        # Create no-op functions that work as context managers
        def get_memory_monitor():
            return None
        
        class NoOpContextManager:
            """No-op context manager for track_operation when psutil is unavailable"""
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        
        def track_operation(*args, **kwargs):
            return NoOpContextManager()
    
    app.register_blueprint(debug_bp)
    
    # Register Keeper API blueprint
    try:
        from backend.keeper_api import keeper_bp
        app.register_blueprint(keeper_bp)
        print("✅ Keeper API blueprint registered")
    except Exception as keeper_err:
        print(f"⚠️ Failed to register Keeper API blueprint: {keeper_err}")
    DEBUG_LOGGING_ENABLED = True
    
    # Add correlation ID to all requests
    @app.before_request
    def add_correlation_id():
        if not hasattr(g, 'correlation_id'):
            g.correlation_id = str(uuid.uuid4())[:8]
    
    print("✅ Debug logging system initialized")
except Exception as e:
    print(f"⚠️ Debug logging system not available: {e}")
    import traceback
    traceback.print_exc()
    # Variables already set to defaults above
    # Create no-op functions if memory_monitor import failed
    if 'get_memory_monitor' not in globals():
        def get_memory_monitor():
            return None
    
    if 'track_operation' not in globals():
        class NoOpContextManager:
            """No-op context manager for track_operation when psutil is unavailable"""
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        
        def track_operation(*args, **kwargs):
            return NoOpContextManager()

# CORS Security: Allow requests from trusted origins
# For development: Allow common localhost ports (Vite may use different ports)
# For production: Allow deployed frontends (Railway + SiteGround)
CORS(app, origins=[
    # Production frontends
    "https://grace-editor-production.up.railway.app",
    "https://prompt-portal-prod.raibach.net",
    # Development / local frontends and tools
    "http://localhost:5173",   # Default Vite port
    "http://localhost:3000",   # Alternative dev port
    "http://localhost:5174",   # Vite fallback port
    "http://localhost:5175",   # Vite fallback port
    "http://localhost:5001",   # Local backend dev
    "http://127.0.0.1:5173",   # Default Vite port (127.0.0.1)
    "http://127.0.0.1:3000",   # Alternative dev port
    "http://127.0.0.1:5001"    # Local backend dev
], supports_credentials=True)

# ===== HTTP BASIC AUTH (Password Protection) =====
HTTP_BASIC_AUTH_USERNAME = os.getenv("HTTP_BASIC_AUTH_USERNAME")
HTTP_BASIC_AUTH_PASSWORD = os.getenv("HTTP_BASIC_AUTH_PASSWORD")

def check_basic_auth(username, password):
    """Check if username/password combination is valid"""
    return (username == HTTP_BASIC_AUTH_USERNAME and
            password == HTTP_BASIC_AUTH_PASSWORD)

def authenticate():
    """Send 401 response that enables basic auth"""
    return Response(
        'Authentication required.\n'
        'Please log in with your username and password.', 401,
        {'WWW-Authenticate': 'Basic realm="Grace AI - Protected Access"'}
    )

@app.before_request
def require_basic_auth():
    """Require HTTP Basic Auth on all requests if credentials are configured"""
    # Only enable if credentials are set
    if not HTTP_BASIC_AUTH_USERNAME or not HTTP_BASIC_AUTH_PASSWORD:
        return None  # No basic auth configured, allow all requests
    
    # Exclude static files and API routes from basic auth
    # This allows the frontend to load assets (CSS, JS, images) without auth
    path = request.path
    method = request.method
    
    # Allow OPTIONS requests (CORS preflight) - these don't need auth
    if method == 'OPTIONS':
        return None
    
    # Allow static assets (CSS, JS, images, fonts, etc.)
    if any(path.startswith(prefix) for prefix in ['/assets/', '/static/', '/favicon.ico', '/robots.txt']):
        return None
    
    # Allow ALL API routes (they have their own authentication via Railway headers)
    # This includes /api/teacher/query, /api/keeper/query, and all other API endpoints
    # CRITICAL: This must come before the auth check to prevent blocking API calls
    if path.startswith('/api/'):
        return None  # Explicitly return None to skip auth for all API routes
    
    # Check for basic auth credentials
    auth = request.authorization
    if not auth or not check_basic_auth(auth.username, auth.password):
        # Log the blocked request for debugging (only in development)
        if os.getenv('FLASK_ENV') == 'development':
            print(f"🔒 Basic auth required for: {method} {path}")
        return authenticate()  # Return 401 with WWW-Authenticate header
    
    return None  # Auth successful, allow request

# ===== SECURITY CONFIGURATION =====
# API Keys for authentication (stored in environment variables)
VALID_API_KEYS = set(os.environ.get("GRACE_API_KEYS", "").split(",")) if os.environ.get("GRACE_API_KEYS") else set()
LM_STUDIO_API_KEY = os.environ.get("LM_STUDIO_API_KEY", "")
ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "c11decd0221b4f358b4c4ef4e225aaac")  # For high-quality speech-to-text (Universal Streaming)

# Rate limiting: requests per minute per API key
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = 60  # seconds

# Rate limiting storage
rate_limit_data = defaultdict(list)

# Security logging
SECURITY_LOG_PATH = "logs/security_log.txt"

def log_security_event(event_type, details, api_key=None):
    """Log security-related events"""
    try:
        with open(SECURITY_LOG_PATH, "a") as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "details": details,
                "api_key": api_key[:8] + "..." if api_key else None,
                "ip": request.remote_addr if request else None
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Security logging failed: {e}")

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # DISABLED: Railway handles authentication - skip API key check
        # Railway's built-in authentication handles user access control
        # This decorator is disabled to allow Railway to manage authentication
        return f(*args, **kwargs)
        
        # OLD CODE (disabled - Railway handles authentication):
        # Skip auth check if no API keys configured (development mode)
        # if not VALID_API_KEYS:
        #     return f(*args, **kwargs)
        #
        # api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        #
        # if not api_key:
        #     log_security_event("AUTH_FAILED", "No API key provided")
        #     return jsonify({"error": "API key required", "code": "AUTH_REQUIRED"}), 401
        #
        # if api_key not in VALID_API_KEYS:
        #     log_security_event("AUTH_FAILED", "Invalid API key", api_key)
        #     return jsonify({"error": "Invalid API key", "code": "AUTH_INVALID"}), 403

        # OLD CODE (disabled - Railway handles rate limiting):
        # Check rate limit
        # now = time.time()
        # requests_list = rate_limit_data[api_key]
        #
        # # Remove old requests outside the window
        # requests_list[:] = [req_time for req_time in requests_list if now - req_time < RATE_LIMIT_WINDOW]
        #
        # if len(requests_list) >= RATE_LIMIT_REQUESTS:
        #     log_security_event("RATE_LIMIT_EXCEEDED", f"Rate limit exceeded: {len(requests_list)} requests", api_key)
        #     return jsonify({
        #         "error": "Rate limit exceeded",
        #         "code": "RATE_LIMIT_EXCEEDED",
        #         "limit": RATE_LIMIT_REQUESTS,
        #         "window": RATE_LIMIT_WINDOW
        #     }), 429
        #
        # # Add current request
        # requests_list.append(now)
        #
        # # Add api_key to request context for logging
        # request.api_key = api_key

        return f(*args, **kwargs)
    return decorated_function

# ===== END SECURITY CONFIGURATION =====

# Paths
MEMORY_INDEX_PATH = "logs/memory_index.faiss"
MEMORY_METADATA_PATH = "logs/memory_metadata.pkl"
REASONING_LOG_PATH = "logs/reasoning_log.txt"
REASONING_TRACE_PATH = "logs/reasoning_trace.json"
AUTO_QNA_LOG_PATH = "logs/auto_qna_log.txt"
INDEX_PATH = "news_index/index.faiss"
META_PATH = "news_index/news_metadata.pkl"

# Optional faiss: avoid top-level import to prevent segfault on some systems (e.g. ARM64 macOS).
# Set DISABLE_FAISS=1 to never load faiss (recommended if the process crashes on startup).
DISABLE_FAISS = os.environ.get("DISABLE_FAISS", "").strip().lower() in ("1", "true", "yes")
_faiss_module = None
if DISABLE_FAISS:
    print("ℹ️  DISABLE_FAISS=1: in-memory vector index (faiss) disabled. Server will run without local memory/news index.")

def _get_faiss():
    """Lazy-load faiss only when needed. Returns None if DISABLE_FAISS=1 or import fails."""
    global _faiss_module
    if DISABLE_FAISS:
        return None
    if _faiss_module is not None:
        return _faiss_module
    try:
        import faiss as _f
        _faiss_module = _f
        return _faiss_module
    except Exception as e:
        print(f"ℹ️  faiss not available: {e}. Memory/news index features disabled.")
        _faiss_module = False  # sentinel so we don't retry
        return None

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Local LLM endpoint - Use GraceConfig if available, otherwise fallback to legacy config
# Support Ngrok URLs for tunneling local models to production
if USE_GRACE_CONFIG:
    LM_API_URL = GraceConfig.model.get_api_url()
    print(f"✅ Using GraceConfig backend: {GraceConfig.model.ACTIVE_BACKEND.value}")
    print(f"📡 LLM API URL: {LM_API_URL}")
else:
    # Legacy fallback
    LM_API_URL = os.environ.get("LM_API_URL", "http://127.0.0.1:1234/v1/chat/completions")
    print(f"⚠️  Using legacy LM_API_URL: {LM_API_URL}")

# Check if using Ngrok (for tunneling local models)
IS_NGROK = "ngrok" in LM_API_URL.lower() or "ngrok-free.dev" in LM_API_URL.lower() or "ngrok.io" in LM_API_URL.lower()
if IS_NGROK:
    print(f"🌐 Ngrok tunnel detected - using Ngrok URL for local model access")

# Karen API endpoint for grammar checking (Keeper chat) - DISABLED
KAREN_API_URL = os.environ.get("KAREN_API_URL", None)
if KAREN_API_URL:
    print(f"📡 Karen API URL: {KAREN_API_URL}")
else:
    print(f"ℹ️  Karen API disabled (not configured)")

# LLM API Keys (for llama-server and karen-server if they require authentication)
LLAMA_API_KEY = os.environ.get("LLAMA_API_KEY", "")
KAREN_API_KEY = os.environ.get("KAREN_API_KEY", "")

# ===== GRACE CONFIGURATION =====
# Persona and cognitive parameters removed - handled by fine-tuned model
# Use GraceConfig values if available, otherwise use defaults
if USE_GRACE_CONFIG:
    backend_info = GraceConfig.get_active_backend_info()
    model_name = backend_info.get("model_name") or "models/Llama3.1-8B-Instruct"
    temperature = GraceConfig.generation.TEMPERATURE
    # Max tokens will be calculated dynamically per-request (up to 3000)
    max_tokens = None  # Dynamic calculation based on context window
    print(f"✅ Using GraceConfig for model settings:")
    print(f"   Backend: {backend_info['backend']}")
    print(f"   Model: {model_name}")
    print(f"   Temperature: {temperature}")
    print(f"   Max Tokens: Dynamic (up to 3000, based on context window)")
else:
    model_name = "models/Llama3.1-8B-Instruct"
    temperature = 0.7
    max_tokens = None  # Dynamic calculation

GRACE_CONFIG = {
    # LLM Model Settings - Now using GraceConfig values
    "model": model_name,
    "temperature": temperature,
    "max_tokens": max_tokens,  # Will be calculated dynamically per-request

    # Logging
    "log_trace": True,  # ENABLED: Log actual prompts being sent to verify prompt engineering

    # Memory & Context
    "memory_enabled": True,
    "memory_top_k": 3,  # Number of memory entries to retrieve per query
    "memory_auto_qna": True,  # Auto-generate Q&A pairs for enrichment

    # Text Processing
    "pdf_max_chars": 50000,  # About 10-13 pages at ~4000 chars/page - safe for 64K context window
    "auto_qna_max_chars": 2000,  # Truncate for auto-QnA generation
    "news_search_results": 5,  # Number of news articles to retrieve
    
    # Logging (disabled by default for performance)
    "log_news_queries": False,
    "log_pdf_summaries": False,
}
# ===== END GRACE CONFIGURATION =====

# Embedding model disabled - not available
embedding_model = None

# FAISS index loading - LAZY LOAD (don't load at startup to save memory)
# Will be loaded on first use in search_news() function
index = None
metadata = []
# Disabled at startup to reduce memory usage - will load lazily when needed
# if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
#     try:
#         # Suppress faiss stderr output during index loading
#         import sys
#         import os as os_module
#         stderr_backup = sys.stderr
#         try:
#             sys.stderr = open(os_module.devnull, 'w')
#             index = faiss.read_index(INDEX_PATH)
#             with open(META_PATH, "rb") as f:
#                 metadata = pickle.load(f)
#             print(f"✅ News index loaded: {index.ntotal} articles")
#         finally:
#             sys.stderr.close()
#             sys.stderr = stderr_backup
#     except Exception:
#         # Silently fail - news index is optional
#         index = None
#         metadata = []


# --- Media Literacy Classification Buckets ---
MEDIA_BUCKETS = {
    "good": {
        "description": "Reputable editorial sources with known citations, authorship, and journalistic integrity.",
        "examples": ["Reuters", "AP", "BBC", "Scientific American"],
        "include_in_memory": True,
        "flag_for_review": False
    },
    "suspect": {
        "description": "Sources lacking clear bylines, emerging outlets, or partially credible info.",
        "examples": ["ZeroHedge", "Medium posts", "unverified startups"],
        "include_in_memory": True,
        "flag_for_review": True
    },
    "propaganda_training": {
        "description": "Known misinformation or biased narratives retained for contrast.",
        "examples": ["state-sponsored outlets", "disinfo samples"],
        "include_in_memory": True,
        "manual_override_required": True
    },
    "social_excluded": {
        "description": "Exclude Reddit, blogs, personal websites.",
        "examples": ["Reddit", "Tumblr", "Personal blogs"],
        "include_in_memory": False,
        "flag_for_review": False
    },
    "garbage_skipped": {
        "description": "Clickbait, spam, scraper sites, low-effort content.",
        "examples": ["The Onion", "ads", "SEO spam"],
        "include_in_memory": False,
        "log_and_purge_after_days": 30
    }
}


def get_domain(url):
    try:
        if isinstance(url, dict):
            return "invalid-url-dict"
        return urlparse(url).netloc.lower()
    except Exception as e:
        print(f"⚠️ get_domain error: {e}")
        return "unknown"


def classify_media_source(url, title, content=None):
    """Placeholder for media classification logic"""
    return "suspect"


def log_skipped_source(domain, title, reason="Unclassified"):
    log_path = "logs/garbage_log.txt"
    log_entry = {
        "timestamp": str(datetime.now()),
        "domain": domain,
        "title": title,
        "reason": reason
    }
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log skipped source: {e}")


def screen_and_classify_article(meta):
    domain = get_domain(meta.get("url", ""))
    title = meta.get("title", "Untitled")
    classification = classify_media_source(meta.get("url", ""), title)

    if classification not in MEDIA_BUCKETS:
        classification = "suspect"

    bucket = MEDIA_BUCKETS[classification]

    if not bucket.get("include_in_memory", False):
        log_skipped_source(domain, title, f"Excluded by bucket: {classification}")
        return None, classification

    return meta, classification


def append_trace_log(prompt, response, memory_context=None, temperature=None, 
                     reasoning_text=None, decision_points=None, context_used=None):
    """Enhanced trace logging with detailed reasoning information"""
    trace_entry = {
        "timestamp": str(datetime.now()),
        "prompt": prompt,
        "response": response,
        "memory_context": memory_context,
        "temperature": temperature,
        "reasoning_text": reasoning_text,  # The actual thinking/reasoning process
        "decision_points": decision_points or [],  # Key decisions made and why
        "context_used": context_used or {},  # What context was considered
        "word_count": len(response.split()) if response else 0
    }
    try:
        if os.path.exists(REASONING_TRACE_PATH):
            with open(REASONING_TRACE_PATH, "r") as f:
                existing = json.load(f)
        else:
            existing = []

        existing.append(trace_entry)

        with open(REASONING_TRACE_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to write reasoning trace: {e}")


def generate_internal_questions_and_reflections(prompt, context=""):
    """Second-order reasoning engine"""
    try:
        thinking_prompt = f"Based on this prompt and context, what deeper question or alternative viewpoint should we consider?\n\nPrompt: {prompt}\n\nContext: {context}"
        return query_llm("", thinking_prompt)
    except Exception as e:
        print(f"⚠️ Second-order reasoning failed: {e}")
        return ""


def append_to_memory(text, source_label):
    """Append text to memory index with memory optimization"""
    if not HAS_SENTENCE_TRANSFORMERS:
        print("⚠️ Sentence transformers not available. Memory append disabled.")
        return
    try:
        from backend.memory_embedder import get_embedder
        import gc
        
        # Limit text size to prevent memory spikes
        MAX_TEXT_SIZE = 50000  # 50k chars max
        if len(text) > MAX_TEXT_SIZE:
            print(f"⚠️ Text too large ({len(text)} chars), truncating for memory")
            text = text[:MAX_TEXT_SIZE]
        
        embedder = get_embedder()
        if embedder is None or embedder.model is None:
            print("⚠️ Embedding model not available")
            return
        
        faiss = _get_faiss()
        if faiss is None:
            return
        np = _get_numpy()
        if np is None:
            return

        if not os.path.exists(MEMORY_INDEX_PATH) or not os.path.exists(MEMORY_METADATA_PATH):
            # Get embedding dimension from model
            dim = embedder.model.get_sentence_embedding_dimension()
            memory_index = faiss.IndexFlatL2(dim)
            sources = []
        else:
            memory_index = faiss.read_index(MEMORY_INDEX_PATH)
            with open(MEMORY_METADATA_PATH, "rb") as f:
                sources = pickle.load(f)

        # Generate embedding with memory cleanup
        embedding = embedder.generate_embedding(text)
        embedding_array = np.array([embedding], dtype="float32")
        memory_index.add(embedding_array)
        sources.append(source_label)

        faiss.write_index(memory_index, MEMORY_INDEX_PATH)
        with open(MEMORY_METADATA_PATH, "wb") as f:
            pickle.dump(sources, f)
        
        # Cleanup
        del embedding_array
        del embedding
        gc.collect()
    except Exception as e:
        print(f"⚠️ Failed to append to memory: {e}")
        import traceback
        traceback.print_exc()


def enrich_with_auto_qna(source_text, source_label):
    """Auto-generate Q&A pairs for memory enrichment using GRACE_CONFIG"""
    try:
        question_prompt = f"Generate a thoughtful internal question that challenges or expands on the following:\n\n{source_text[:GRACE_CONFIG['auto_qna_max_chars']]}"
        question = query_llm("", question_prompt)

        answer = query_llm("", f"Answer the question thoughtfully using your knowledge: {question}")

        qna_pair = f"Q: {question}\nA: {answer}"
        append_to_memory(qna_pair, source_label)

        with open(AUTO_QNA_LOG_PATH, "a") as f:
            f.write(f"### [{datetime.now()}] Auto-QnA from {source_label}\n{qna_pair}\n\n---\n\n")
    except Exception as e:
        print(f"⚠️ Auto-QnA failed: {e}")


def query_llm(system, user_input, memory_context="", temperature=None):
    """Query local LLM using centralized GRACE_CONFIG
    Uses proper system/user message structure for better token efficiency
    Automatically starts Grace server if not running"""
    try:
        # MEMORY OPTIMIZATION: Only start Grace server when needed
        from backend.model_server_manager import ensure_grace_server
        if not ensure_grace_server():
            raise Exception("Failed to start Grace model server. Please check logs.")
        # Use config defaults if not specified
        temperature = temperature if temperature is not None else GRACE_CONFIG["temperature"]

        if memory_context:
            user_input = memory_context + "\n\n" + user_input

        # If no system prompt provided, use empty string
        if not system:
            system = ""

        # Build messages array with proper system/user separation
        # Llama 3.1 supports system messages, so we use proper structure
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_input})

        # Calculate max_tokens based on context window and input size
        # Account for both system and user messages separately
        context_window = GraceConfig.model.get_context_window() if USE_GRACE_CONFIG else 8192
        system_tokens = (len(system) // 4) if system else 0  # Rough estimate: 4 chars per token
        user_tokens = len(user_input) // 4
        estimated_input_tokens = system_tokens + user_tokens
        max_output_tokens = min(3000, context_window - estimated_input_tokens - 100)  # Reserve 100 tokens buffer
        
        # Ensure max_tokens is at least 100 and doesn't exceed context window
        max_output_tokens = max(100, min(max_output_tokens, 3000))
        
        payload = {
            "model": GRACE_CONFIG["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens
        }

        # Debug logging
        backend_info_str = ""
        if USE_GRACE_CONFIG:
            backend_info = GraceConfig.get_active_backend_info()
            backend_info_str = f"   Backend: {backend_info['backend']} ({backend_info['description']})\n"
        
        print(f"\n📤 Sending to LLM:")
        if system:
            print(f"   System prompt: {len(system)} chars ({system_tokens} tokens)")
        print(f"   User input: {len(user_input)} chars ({user_tokens} tokens)")
        print(f"   Total input: {estimated_input_tokens} tokens")
        print(f"   Max output: {max_output_tokens} tokens")
        print(backend_info_str, end="")
        print(f"   Model: {GRACE_CONFIG['model']}")
        print(f"   API URL: {LM_API_URL}")
        print(f"   Temperature: {temperature}")
        print(f"   Max output tokens: {max_output_tokens} (context window: {context_window})")
        
        # Log actual system prompt (first 500 chars) to verify prompt engineering
        if GRACE_CONFIG.get("log_trace", False):
            print(f"\n🔍 SYSTEM PROMPT (first 500 chars):")
            print(f"{system[:500]}...")
            print(f"\n🔍 USER INPUT (first 1000 chars):")
            print(f"{user_input[:1000]}...")

        # Track memory for LLM query
        import gc
        import psutil
        import os as os_module
        
        # Check memory before query
        process = psutil.Process(os_module.getpid())
        memory_before_mb = process.memory_info().rss / (1024 * 1024)
        
        # MEMORY SAFETY: If memory is already high, force cleanup before query
        if memory_before_mb > 3000:  # 3GB threshold
            print(f"⚠️ Memory high ({memory_before_mb:.0f}MB), forcing cleanup before query")
            gc.collect()
            memory_before_mb = process.memory_info().rss / (1024 * 1024)
            print(f"   After cleanup: {memory_before_mb:.0f}MB")
        
        with track_operation("query_llm", {
            "system_length": len(system) if system else 0,
            "user_input_length": len(user_input),
            "max_output_tokens": max_output_tokens,
            "model": GRACE_CONFIG["model"],
            "memory_before_mb": round(memory_before_mb, 2)
        }):
            try:
                # Timeout based on input size: longer for large entries (normal use case)
                # This prevents backend from hanging while allowing long entries to complete
                request_timeout = 90  # 1.5 minutes default (increased for normal long entries)
                if len(user_input) > 50000:  # Very large inputs (PDFs, etc.)
                    request_timeout = 180  # 3 minutes for very large operations
                elif len(user_input) > 20000:  # Long entries (normal use)
                    request_timeout = 120  # 2 minutes for long entries
                
                # Add headers for authentication and Ngrok bypass
                headers = {}
                if LLAMA_API_KEY:
                    headers['Authorization'] = f'Bearer {LLAMA_API_KEY}'
                
                # Ngrok free tier requires bypassing the warning page
                # Add headers to skip Ngrok's browser warning
                if IS_NGROK:
                    headers['ngrok-skip-browser-warning'] = 'true'
                    # Some Ngrok setups may require this header
                    headers['User-Agent'] = 'Grace-Editor/1.0'
                
                response = requests.post(LM_API_URL, json=payload, headers=headers, timeout=request_timeout)
                response.raise_for_status()
                response_data = response.json()
                
                # Check if response has the expected structure
                if "choices" not in response_data or len(response_data["choices"]) == 0:
                    raise ValueError(f"Invalid response from LLM: {response_data}")
                
                response_text = response_data["choices"][0]["message"]["content"].strip()

                # Optimized response cleaning - batch operations for speed
                import re
                import unicodedata
                import html
                
                # CRITICAL: Remove model special tokens first (before other cleaning)
                response_text = re.sub(r'<\|im_start\|>', '', response_text, flags=re.IGNORECASE)
                response_text = re.sub(r'<\|im_end\|>', '', response_text, flags=re.IGNORECASE)
                response_text = re.sub(r'<\|imstart\|>', '', response_text, flags=re.IGNORECASE)
                response_text = re.sub(r'<\|imend\|>', '', response_text, flags=re.IGNORECASE)
                
                # Quick pass: Remove AI disclaimers (combined pattern for speed)
                response_text = re.sub(r'[^.]*i\'?m a (large )?language model[^.]*|[^.]*developed in 20\d{2}[^.]*|[^.]*keep in mind.*i\'?m[^.]*', '', response_text, flags=re.IGNORECASE)
                
                # Fast Unicode cleanup - use list comprehension instead of loop
                response_text = ''.join(char for char in response_text 
                                      if (char.isprintable() or char in '\n\r\t') 
                                      and unicodedata.category(char) not in ['Cf', 'Co', 'Cn'])
                
                # Fix quote characters - batch HTML entity fixes
                response_text = html.unescape(response_text)
                # Combined quote fix pattern for speed
                response_text = re.sub(r'&quot;|&#34;|&#x22;', '"', response_text)
                response_text = re.sub(r'&apos;|&#39;|&#x27;', "'", response_text)
                response_text = re.sub(r'&lt;|&#60;|&#x3C;', '<', response_text)
                response_text = re.sub(r'&gt;|&#62;|&#x3E;', '>', response_text)
                response_text = re.sub(r'&amp;|&#38;|&#x26;', '&', response_text)
                
                # Fix markdown formatting artifacts - remove formatting syntax but PRESERVE list structure
                # Process in order: code blocks -> bold -> italics -> code spans -> links -> standalone markers
                # IMPORTANT: Preserve list markers (-, *, 1., etc.) for proper list rendering in frontend
                
                # Remove markdown code blocks - combined pattern
                response_text = re.sub(r'```[\w]*\s*\n|\n```\s*$|\n```\s*\n', '\n', response_text)
                
                # Convert inline lists to line-separated (optimized patterns)
                response_text = re.sub(r'(\s+)\*\s+([^*\n]+?)(?=\s+\*\s+|\s*$)', r'\n* \2', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'(\d+\.\s+[^0-9\n]+?)(?=\s+\d+\.\s+)', r'\1\n', response_text)
                response_text = re.sub(r'(\s+)-\s+([^-\n]+?)(?=\s+-\s+|\s*$)', r'\n- \2', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'([^\n])\s+([-•*])\s+', r'\1\n\2 ', response_text)
                response_text = re.sub(r'([^\n])\s+(\d+\.\s+)', r'\1\n\2', response_text)
                response_text = re.sub(r'\n{3,}', '\n\n', response_text)
                
                # Optimized markdown removal - batch operations
                response_text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', response_text)  # Links
                response_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', response_text)  # Bold
                response_text = re.sub(r'(?<!^[-*]\s)\*([^*\n]+)\*(?!\s)', r'\1', response_text, flags=re.MULTILINE)  # Italics
                response_text = re.sub(r'_([^_\n]+)_', r'\1', response_text)  # Underscore italics
                response_text = re.sub(r'`([^`]+)`', r'\1', response_text)  # Code spans
                
                # Single-pass line cleaning (optimized)
                lines = response_text.split('\n')
                is_list_item = re.compile(r'^\s*[-•*]\s+|^\s*\d+\.\s+')
                cleaned_lines = []
                for line in lines:
                    if is_list_item.match(line):
                        cleaned_lines.append(line.rstrip())
                    else:
                        cleaned_line = re.sub(r'[ \t]+', ' ', line).rstrip()
                        cleaned_line = re.sub(r'^\s+', '', cleaned_line)
                        cleaned_lines.append(cleaned_line)
                response_text = '\n'.join(cleaned_lines)
                
                # Final cleanup
                response_text = re.sub(r'\n{3,}', '\n\n', response_text)
                response_text = re.sub(r'[ \t]+\n', '\n', response_text)
                response_text = response_text.strip()
                
                # Fine-tuned model handles reasoning internally - no post-processing needed
                if GRACE_CONFIG["log_trace"]:
                    try:
                        append_trace_log(
                            prompt=user_input,
                            response=response_text,
                            memory_context=memory_context,
                            temperature=temperature
                        )
                    except Exception as trace_err:
                        print(f"⚠️ Failed to append reasoning trace: {trace_err}")
                
                # MEMORY CLEANUP: Force garbage collection after query
                memory_after_mb = process.memory_info().rss / (1024 * 1024)
                memory_delta = memory_after_mb - memory_before_mb
                
                if memory_delta > 100:  # More than 100MB increase
                    print(f"⚠️ Memory increased by {memory_delta:.0f}MB during query, forcing cleanup")
                    gc.collect()
                    memory_after_cleanup = process.memory_info().rss / (1024 * 1024)
                    print(f"   After cleanup: {memory_after_cleanup:.0f}MB (freed {memory_after_mb - memory_after_cleanup:.0f}MB)")
                
                return response_text

            except requests.exceptions.Timeout:
                print(f"❌ LLM request timed out after 300 seconds")
                raise Exception("LLM server timed out. Please check if the model is loaded and responding.")
            except requests.exceptions.ConnectionError as e:
                error_detail = str(e)
                print(f"\n❌ LLM CONNECTION ERROR:")
                print(f"   URL: {LM_API_URL}")
                print(f"   Error: {error_detail}")
                # Check if port is listening
                import socket
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    port_check = sock.connect_ex(('127.0.0.1', 8080))
                    sock.close()
                    if port_check != 0:
                        print(f"   ⚠️  Port 8080 is NOT listening (connection refused)")
                        print(f"   💡 Solution: Start llama-server with: bash scripts/model-management/start_llama_server.sh")
                    else:
                        print(f"   ⚠️  Port 8080 is listening but HTTP connection failed")
                except Exception as sock_err:
                    print(f"   ⚠️  Could not check port: {sock_err}")
                
                # Log to debug logger if available
                if DEBUG_LOGGING_ENABLED:
                    try:
                        debug_logger.error("LLM connection failed", e, {
                            "lm_api_url": LM_API_URL,
                            "port_8080_listening": port_check == 0 if 'port_check' in locals() else None
                        })
                    except:
                        pass
                
                raise Exception(f"Cannot connect to LLM server. Please check if llama-server is running on port 8080.")
            except requests.exceptions.HTTPError as http_err:
                # Handle HTTP errors (400, 500, etc.)
                error_detail = ""
                try:
                    error_json = http_err.response.json()
                    error_detail = error_json.get('error', {}).get('message', str(error_json))
                except:
                    error_detail = http_err.response.text[:500] if hasattr(http_err.response, 'text') else str(http_err)
                
                print(f"❌ LLM HTTP Error ({http_err.response.status_code}): {error_detail}")
                print(f"   Request URL: {LM_API_URL}")
                print(f"   Request payload: max_tokens={max_output_tokens}, system_length={len(system) if system else 0} chars, user_length={len(user_input)} chars")
                print(f"   Response headers: {dict(http_err.response.headers) if hasattr(http_err.response, 'headers') else 'N/A'}")
                # If it's a 401, provide helpful error message
                if http_err.response.status_code == 401:
                    if "Authentication required" in str(error_detail):
                        raise Exception(f"LLM request failed (401): llama-server requires authentication. Set LLAMA_API_KEY environment variable if llama-server is configured with API keys.")
                    else:
                        raise Exception(f"LLM request failed (401): {error_detail}")
                raise Exception(f"LLM request failed ({http_err.response.status_code}): {error_detail}")
            except Exception as e:
                print(f"❌ LLM request failed: {e}")
                print(f"   Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                print(f"   Response body: {response.text if 'response' in locals() else 'N/A'}")
                raise Exception(f"LLM request failed: {str(e)}")

    except requests.exceptions.HTTPError as e:
        # Return actual error from LLM API
        try:
            error_detail = e.response.json()
            error_msg = error_detail.get('error', error_detail)
            print(f"❌ LLM HTTP Error ({e.response.status_code}): {error_detail}")
            return f"❌ LLM Error ({e.response.status_code}): {error_msg}"
        except:
            error_text = e.response.text[:500]
            print(f"❌ LLM HTTP Error ({e.response.status_code}): {error_text}")
            return f"❌ LLM Error ({e.response.status_code}): {error_text}"
    except Exception as e:
        print(f"❌ LLM Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        # MEMORY CLEANUP: Force cleanup on error too
        gc.collect()
        return f"❌ LLM Exception: {str(e)}"


def query_karen(system, user_input, memory_context="", temperature=None):
    """Query Karen model for grammar checking (Keeper chat)
    Uses the same structure as query_llm but connects to Karen on port 8081
    Automatically starts Karen server if not running"""
    try:
        # Check if Karen is configured
        if not KAREN_API_URL:
            return "❌ Karen API is not configured. Set KAREN_API_URL environment variable to enable."
        
        # MEMORY OPTIMIZATION: Only start Karen server when needed
        from backend.model_server_manager import ensure_karen_server
        if not ensure_karen_server():
            raise Exception("Failed to start Karen model server. Please check logs.")
        # Use lower temperature for grammar checking (more precise)
        temperature = temperature if temperature is not None else 0.2

        if memory_context:
            user_input = memory_context + "\n\n" + user_input

        # Build messages array
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_input})

        # Calculate max_tokens (Karen is Mistral 7B, similar context window)
        context_window = 8192  # Mistral 7B context window
        system_tokens = (len(system) // 4) if system else 0
        user_tokens = len(user_input) // 4
        estimated_input_tokens = system_tokens + user_tokens
        max_output_tokens = min(3000, context_window - estimated_input_tokens - 100)
        max_output_tokens = max(100, min(max_output_tokens, 3000))
        
        payload = {
            "model": "Karen_TheEditor_V2_STRICT_Mistral_7B",  # Karen model name
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens
        }

        print(f"\n📤 Sending to Karen (Keeper):")
        if system:
            print(f"   System prompt: {len(system)} chars ({system_tokens} tokens)")
        print(f"   User input: {len(user_input)} chars ({user_tokens} tokens)")
        print(f"   API URL: {KAREN_API_URL}")
        print(f"   Temperature: {temperature}")
        print(f"   Max output tokens: {max_output_tokens}")

        # Request with timeout
        request_timeout = 90
        if len(user_input) > 50000:
            request_timeout = 180
        elif len(user_input) > 20000:
            request_timeout = 120
            
        response = requests.post(KAREN_API_URL, json=payload, timeout=request_timeout)
        response.raise_for_status()
        response_data = response.json()
        
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            raise ValueError(f"Invalid response from Karen: {response_data}")
        
        response_text = response_data["choices"][0]["message"]["content"].strip()
        
        # Clean response (same as query_llm)
        import re
        import unicodedata
        import html
        
        # CRITICAL: Remove model special tokens first (before other cleaning)
        response_text = re.sub(r'<\|im_start\|>', '', response_text, flags=re.IGNORECASE)
        response_text = re.sub(r'<\|im_end\|>', '', response_text, flags=re.IGNORECASE)
        response_text = re.sub(r'<\|imstart\|>', '', response_text, flags=re.IGNORECASE)
        response_text = re.sub(r'<\|imend\|>', '', response_text, flags=re.IGNORECASE)
        
        response_text = re.sub(r'[^.]*i\'?m a (large )?language model[^.]*|[^.]*developed in 20\d{2}[^.]*|[^.]*keep in mind.*i\'?m[^.]*', '', response_text, flags=re.IGNORECASE)
        response_text = unicodedata.normalize('NFKD', response_text)
        response_text = html.unescape(response_text)
        response_text = re.sub(r'\s+', ' ', response_text).strip()
        
        return response_text
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Karen API connection error: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Karen query error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        raise Exception(error_msg)


def retrieve_memory_context(query, top_k=None):
    """Retrieve relevant context from memory using GRACE_CONFIG defaults"""
    if not HAS_SENTENCE_TRANSFORMERS:
        return ""
    try:
        from backend.memory_embedder import get_embedder
        import gc
        
        top_k = top_k or GRACE_CONFIG["memory_top_k"]
        if not os.path.exists(MEMORY_INDEX_PATH) or not os.path.exists(MEMORY_METADATA_PATH):
            return ""

        embedder = get_embedder()
        if embedder is None or embedder.model is None:
            return ""

        faiss = _get_faiss()
        if faiss is None:
            return ""
        np = _get_numpy()
        if np is None:
            return ""

        memory_index = faiss.read_index(MEMORY_INDEX_PATH)
        with open(MEMORY_METADATA_PATH, "rb") as f:
            sources = pickle.load(f)

        # Generate query embedding
        query_embedding = embedder.generate_embedding(query)
        query_vec = np.array([query_embedding], dtype="float32")
        
        D, I = memory_index.search(query_vec, top_k)
        results = []

        for idx in I[0]:
            if idx < len(sources):
                results.append(f"[Memory Entry from {sources[idx]}]\n")

        # Cleanup
        del query_vec
        del query_embedding
        gc.collect()
        
        return "\n".join(results)
    except Exception as e:
        print(f"⚠️ Memory retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return ""


def load_logs_to_vectorstore():
    import re
    from pathlib import Path

    if not HAS_SENTENCE_TRANSFORMERS:
        print("⚠️ Sentence transformers not available. Log vectorization disabled.")
        return None, []

    if not os.path.exists("logs"):
        return None, []

    if not HAS_SENTENCE_TRANSFORMERS or embedding_model is None:
        print("⚠️ Embedding model not available. Memory initialization from PDFs disabled.")
        return None, []

    texts = []
    sources = []

    for file_name in ["pdf_log.txt", "news_log.txt"]:
        path = Path("logs") / file_name
        if not path.exists():
            continue
        # Read file line-by-line to avoid loading entire file into memory
        current_entry = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                # Check if this line starts a new entry
                if re.match(r"### \[.*?\]", line):
                    # Process previous entry if exists
                    if current_entry:
                        entry_text = "".join(current_entry).strip()
                        if entry_text:
                            texts.append(entry_text)
                            sources.append(file_name)
                        current_entry = []
                else:
                    current_entry.append(line)
            # Process last entry
            if current_entry:
                entry_text = "".join(current_entry).strip()
                if entry_text:
                    texts.append(entry_text)
                    sources.append(file_name)

    if not texts:
        return None, []

    # MEMORY OPTIMIZATION: Process in batches to prevent memory spikes
    from backend.memory_embedder import get_embedder
    import gc
    
    embedder = get_embedder()
    if embedder is None or embedder.model is None:
        print("⚠️ Embedding model not available")
        return None, []
    
    # Limit batch size for memory safety
    BATCH_SIZE = 50  # Process 50 texts at a time
    all_embeddings = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        # Limit individual text size
        batch = [text[:50000] if len(text) > 50000 else text for text in batch]
        
        batch_embeddings = embedder.generate_embeddings_batch(batch, batch_size=min(len(batch), 32))
        all_embeddings.extend(batch_embeddings)
        
        # Cleanup after each batch
        del batch_embeddings
        gc.collect()
    
    if not all_embeddings:
        return None, []

    faiss = _get_faiss()
    if faiss is None:
        return None, []
    np = _get_numpy()
    if np is None:
        return None, []
    
    embeddings = np.array(all_embeddings, dtype="float32")
    memory_index = faiss.IndexFlatL2(embeddings.shape[1])
    memory_index.add(embeddings)

    with open(MEMORY_METADATA_PATH, "wb") as meta_out:
        pickle.dump(sources, meta_out)

    faiss.write_index(memory_index, MEMORY_INDEX_PATH)
    
    # Final cleanup
    del all_embeddings
    del embeddings
    gc.collect()
    
    return memory_index, sources


def search_news(query, include_memory=True):
    """Search news and return results"""
    global index, metadata
    
    # Lazy load index if not already loaded
    if index is None:
        faiss = _get_faiss()
        if faiss is not None and os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            try:
                import sys
                import os as os_module
                stderr_backup = sys.stderr
                try:
                    sys.stderr = open(os_module.devnull, 'w')
                    index = faiss.read_index(INDEX_PATH)
                    with open(META_PATH, "rb") as f:
                        metadata = pickle.load(f)
                    print(f"✅ News index loaded (lazy): {index.ntotal} articles")
                finally:
                    sys.stderr.close()
                    sys.stderr = stderr_backup
            except Exception:
                index = None
                metadata = []
    
    if index is None or not metadata:
        return {"error": "News index not loaded"}

    if not HAS_SENTENCE_TRANSFORMERS:
        return {"error": "Sentence transformers not available. News search disabled."}

    try:
        from backend.memory_embedder import get_embedder
        import gc
        
        memory_context = retrieve_memory_context(query) if (include_memory and GRACE_CONFIG["memory_enabled"]) else ""
        
        embedder = get_embedder()
        if embedder is None or embedder.model is None:
            return {"error": "Embedding model not available"}
        np = _get_numpy()
        if np is None:
            return {"error": "numpy not available"}
        query_embedding = embedder.generate_embedding(query)
        embedding = np.array([query_embedding], dtype="float32")
        D, I = index.search(embedding, k=GRACE_CONFIG["news_search_results"])
        
        # Cleanup
        del query_embedding
        del embedding
        gc.collect()

        results = []
        for idx in I[0]:
            if idx < len(metadata):
                meta = metadata[idx]
                screened, classification = screen_and_classify_article(meta)
                if not screened:
                    continue
                results.append(
                    f"📰 {screened['title']}\n🔗 {screened['url']}\n🗓  {screened['published']}\n🧭 Classification: {classification.upper()}\n"
                )

        context = "\n\n".join(results)
        answer = query_llm(
            "",
            context + "\n\n" + query,
            memory_context
        )

        if GRACE_CONFIG["log_news_queries"]:
            try:
                with open("logs/news_log.txt", "a") as log_file:
                    log_file.write(f"### [{datetime.now()}] News Query: {query}\n{answer}\n\n---\n\n")
            except Exception as log_err:
                print(f"⚠️ Failed to write news log: {log_err}")

        if GRACE_CONFIG["memory_enabled"]:
            append_to_memory(f"Query: {query}\n\nAnswer:\n{answer}", "news_log.txt")
        if GRACE_CONFIG["memory_auto_qna"]:
            enrich_with_auto_qna(answer, "news_log.txt")

        return {"content": answer, "sources": results}
    except Exception as e:
        return {"error": str(e)}


def scan_pdf_content_for_forbidden_patterns(text_content, max_chars=5000):
    """
    Scan extracted PDF text for forbidden content patterns.
    Distinguishes between articles ABOUT forbidden subjects vs. actual depictions.
    
    Returns: (has_forbidden_content: bool, content_type: str, confidence: float, details: str)
    """
    if not text_content or len(text_content.strip()) == 0:
        return False, None, 0.0, "No text content to scan"
    
    # Sample text for analysis (first and last portions to catch context)
    sample_text = text_content[:max_chars] + " ... " + text_content[-max_chars:] if len(text_content) > max_chars * 2 else text_content
    sample_text_lower = sample_text.lower()
    
    # Forbidden content indicators (high-confidence patterns)
    # These patterns suggest actual exploitation content, not articles about it
    forbidden_patterns = {
        'child_exploitation': {
            'indicators': [
                # High-confidence: explicit exploitation language
                r'\b(child|minor|underage).*?(sexual|sex|rape|abuse|exploit)',
                r'\b(sexual|sex).*?(child|minor|underage)',
                # Age-specific with sexual context
                r'\b(under\s*18|under\s*sixteen|under\s*age).*?(sexual|sex|nude|naked)',
                # Depiction indicators (not discussion)
                r'(describing|depicting|showing).*?(child|minor).*?(sexual|sex)',
                r'(scene|scene where).*?(child|minor).*?(sexual|sex)',
            ],
            'exclusion_patterns': [
                # These suggest articles/discussions, not depictions
                r'(article|news|report|study|research|discussion|about|regarding)',
                r'(prevent|combat|fight|against|stop|end).*?(exploitation|abuse)',
                r'(victim|survivor|case|incident|investigation)',
                r'(legal|law|law enforcement|police|arrest|trial)',
                r'(educational|awareness|campaign|program)',
            ]
        },
        'animal_exploitation': {
            'indicators': [
                # High-confidence: explicit bestiality language
                r'\b(animal|beast|dog|horse).*?(sexual|sex|bestiality)',
                r'\b(sexual|sex).*?(animal|beast|bestiality)',
                # Depiction indicators
                r'(describing|depicting|showing).*?(animal|beast).*?(sexual|sex)',
            ],
            'exclusion_patterns': [
                # Articles/discussions about animal welfare
                r'(article|news|report|study|research|discussion|about|regarding)',
                r'(welfare|protection|rights|cruelty|abuse prevention)',
                r'(legal|law|law enforcement|police|arrest|trial)',
                r'(educational|awareness|campaign|program)',
            ]
        }
    }
    
    import re
    
    detected_types = []
    confidence_scores = []
    details_list = []
    
    for content_type, patterns in forbidden_patterns.items():
        # Check for indicators
        indicator_matches = []
        for pattern in patterns['indicators']:
            matches = re.findall(pattern, sample_text_lower, re.IGNORECASE)
            if matches:
                indicator_matches.extend(matches)
        
        if not indicator_matches:
            continue
        
        # Check for exclusion patterns (suggests article/discussion, not depiction)
        exclusion_matches = []
        for pattern in patterns['exclusion_patterns']:
            matches = re.findall(pattern, sample_text_lower, re.IGNORECASE)
            if matches:
                exclusion_matches.extend(matches)
        
        # Calculate confidence: more indicators = higher confidence
        # Exclusion patterns reduce confidence (suggests article, not depiction)
        indicator_count = len(indicator_matches)
        exclusion_count = len(exclusion_matches)
        
        # If exclusion patterns are present, this is likely an article about the subject
        if exclusion_count > 0 and exclusion_count >= indicator_count:
            # Likely an article - do not flag as forbidden
            continue
        
        # Calculate confidence score
        confidence = min(0.9, 0.3 + (indicator_count * 0.1) - (exclusion_count * 0.2))
        
        if confidence > 0.4:  # Threshold for flagging
            detected_types.append(content_type)
            confidence_scores.append(confidence)
            details_list.append(f"{content_type.replace('_', ' ').title()}: {indicator_count} indicators found (confidence: {confidence:.2f})")
    
    if detected_types:
        # Return highest confidence detection
        max_idx = confidence_scores.index(max(confidence_scores))
        return True, detected_types[max_idx], confidence_scores[max_idx], "; ".join(details_list)
    
    return False, None, 0.0, "No forbidden content patterns detected"


def scan_pdf_security(pdf_path, filename):
    """Scan PDF for security threats and return detailed security report"""
    threats = []
    warnings = []
    file_size = os.path.getsize(pdf_path)

    # Size check (10 MB limit)
    if file_size > 10 * 1024 * 1024:
        threats.append(f"File size too large: {file_size / 1024 / 1024:.2f} MB (max 10 MB)")
    elif file_size > 5 * 1024 * 1024:
        warnings.append(f"Large file: {file_size / 1024 / 1024:.2f} MB")

    try:
        fitz = _get_fitz()
        if fitz is None:
            return {"safe": False, "threats": ["PyMuPDF not available"], "warnings": [], "file_size": file_size, "page_count": 0, "has_javascript": False, "has_embedded_files": False}
        doc = fitz.open(pdf_path)

        # Check for JavaScript
        page_count = len(doc)
        js_found = False
        embedded_files = False
        suspicious_actions = []
        external_links = []
        forbidden_content_detected = False
        forbidden_content_type = None
        forbidden_confidence = 0.0
        forbidden_details = ""

        for page_num in range(page_count):
            page = doc[page_num]

            # Check for JavaScript in page annotations
            annots = page.annots()
            if annots:
                for annot in annots:
                    try:
                        annot_type = annot.type[0] if annot.type else None
                        # Check for actions that might contain JavaScript
                        if annot_type in [2, 3]:  # Link or Free Text annotations
                            annot_info = annot.info
                            if 'JavaScript' in str(annot_info) or 'JS' in str(annot_info):
                                js_found = True
                                threats.append(f"JavaScript detected on page {page_num + 1}")
                    except:
                        pass

            # Check for links
            links = page.get_links()
            if links:
                for link in links:
                    if 'uri' in link:
                        uri = link['uri']
                        if uri:
                            if not uri.startswith(('http://', 'https://', 'mailto:')):
                                suspicious_actions.append(f"Suspicious link on page {page_num + 1}: {uri[:100]}")
                            else:
                                external_links.append(uri)

        # Check for embedded files
        if hasattr(doc, 'embfile_count') and doc.embfile_count() > 0:
            embedded_files = True
            threats.append(f"Contains {doc.embfile_count()} embedded file(s)")
            try:
                for i in range(doc.embfile_count()):
                    embfile_info = doc.embfile_info(i)
                    filename_emb = embfile_info.get('filename', 'unknown')
                    threats.append(f"  Embedded: {filename_emb}")
            except:
                pass

        # Check metadata for suspicious patterns
        metadata = doc.metadata
        if metadata:
            producer = str(metadata.get('producer', '')).lower()
            creator = str(metadata.get('creator', '')).lower()

            # Known suspicious patterns
            suspicious_patterns = ['script', 'exploit', 'metasploit', 'payload']
            for pattern in suspicious_patterns:
                if pattern in producer or pattern in creator:
                    threats.append(f"Suspicious metadata pattern detected: '{pattern}'")

        doc.close()

        # Compile warnings
        if len(external_links) > 10:
            warnings.append(f"Contains {len(external_links)} external links")
        elif len(external_links) > 0:
            warnings.append(f"Contains {len(external_links)} external link(s)")

        if suspicious_actions:
            for action in suspicious_actions:
                threats.append(action)

        # Page count warnings
        if page_count > 100:
            warnings.append(f"Large document: {page_count} pages")

        # CONTENT SCANNING: Check for forbidden content (child/animal exploitation)
        # Extract sample text for content analysis (first few pages to avoid memory issues)
        # Do this BEFORE closing the doc
        try:
            content_sample = ""
            max_pages_to_scan = min(5, page_count)  # Scan first 5 pages for content analysis
            
            for page_num in range(max_pages_to_scan):
                page = doc[page_num]
                page_text = page.get_text()
                content_sample += page_text + "\n"
                if len(content_sample) > 10000:  # Limit sample size
                    break
            
            if content_sample:
                has_forbidden, content_type, confidence, details = scan_pdf_content_for_forbidden_patterns(content_sample)
                if has_forbidden and confidence > 0.5:  # High confidence threshold
                    forbidden_content_detected = True
                    forbidden_content_type = content_type
                    forbidden_confidence = confidence
                    forbidden_details = details
                    # CRITICAL: Forbidden content is always a critical threat
                    threats.append(f"Forbidden content detected: {details} (confidence: {confidence:.2f})")
        except Exception as content_scan_error:
            # Content scanning failed - log but don't fail the whole scan
            print(f"⚠️ Content scanning error for {filename}: {content_scan_error}")
            warnings.append(f"Content scanning failed: {str(content_scan_error)[:100]}")

        doc.close()

        # Determine quarantine status
        should_quarantine = len(threats) > 0

        return {
            'safe': not should_quarantine,
            'threats': threats,
            'warnings': warnings,
            'file_size': file_size,
            'page_count': page_count,
            'has_javascript': js_found,
            'has_embedded_files': embedded_files,
            'forbidden_content_detected': forbidden_content_detected,
            'forbidden_content_type': forbidden_content_type,
            'forbidden_confidence': forbidden_confidence,
            'forbidden_details': forbidden_details
        }

    except Exception as e:
        # Corrupt PDF - classify as CRITICAL threat
        error_msg = str(e)
        corrupt_reason = "Corrupt PDF file - cannot be scanned or processed"
        if "cannot open" in error_msg.lower() or "invalid" in error_msg.lower():
            corrupt_reason = "Corrupt or invalid PDF structure"
        elif "encrypted" in error_msg.lower():
            corrupt_reason = "Encrypted PDF - password required"
        elif "damaged" in error_msg.lower():
            corrupt_reason = "Damaged PDF file structure"
        
        return {
            'safe': False,
            'threats': [f"{corrupt_reason}: {error_msg}"],
            'warnings': [],
            'file_size': file_size,
            'page_count': 0,
            'has_javascript': False,
            'has_embedded_files': False,
            'is_corrupt': True,
            'corrupt_error': error_msg,
            'forbidden_content_detected': False,
            'forbidden_content_type': None,
            'forbidden_confidence': 0.0,
            'forbidden_details': ""
        }


def extract_pdf_text_streaming(pdf_path, max_chars=None):
    """Extract text from PDF using streaming to avoid memory issues"""
    max_chars = max_chars or GRACE_CONFIG["pdf_max_chars"]
    text_chunks = []
    total_chars = 0

    try:
        fitz = _get_fitz()
        if fitz is None:
            return ""
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            if total_chars >= max_chars:
                break

            page = doc[page_num]
            page_text = page.get_text()

            remaining = max_chars - total_chars
            if len(page_text) > remaining:
                text_chunks.append(page_text[:remaining])
                total_chars += remaining
                break
            else:
                text_chunks.append(page_text)
                total_chars += len(page_text)

            # Explicitly close page to free memory
            page = None

        doc.close()
        return "".join(text_chunks)
    except Exception as e:
        print(f"⚠️ PDF extraction error: {e}")
        return ""


def summarize_pdfs(files, include_memory=True, analysis_mode="critical"):
    """Summarize multiple PDF files with memory-efficient streaming and security scanning

    Args:
        analysis_mode: "critical" for editorial critique, "interpretive" for holistic analysis
    """
    try:
        if not isinstance(files, list):
            files = [files]

        summaries = []
        for file_obj in files:
            # SECURITY: Scan PDF before processing
            print(f"🔍 Scanning {file_obj['name']} for security threats...")
            security_report = scan_pdf_security(file_obj['path'], file_obj['name'])

            if not security_report['safe']:
                # QUARANTINE: Determine threat severity (3-tier classification)
                threat_summary = "\n".join(security_report['threats'])
                warning_summary = "\n".join(security_report['warnings']) if security_report['warnings'] else "None"

                # Three severity levels aligned with bucket system:
                # CRITICAL → SOCIAL_EXCLUDED (<20): Immediate security threats
                # HIGH → PROPAGANDA (20-39): Suspicious/manipulative patterns
                # MODERATE → SUSPECT (40-74): Needs review but less concerning

                severity = "MODERATE"  # Default
                severity_reasons = []

                # Check for CRITICAL threats (immediate danger - reject file)
                # Corrupt PDFs are always CRITICAL
                if security_report.get('is_corrupt', False):
                    severity = "CRITICAL"
                    corrupt_error = security_report.get('corrupt_error', 'Unknown error')
                    severity_reasons.append(f"Corrupt PDF: {security_report['threats'][0] if security_report['threats'] else corrupt_error}")

                if security_report['file_size'] > 10 * 1024 * 1024:
                    severity = "CRITICAL"
                    severity_reasons.append(f"File too large: {security_report['file_size'] / 1024 / 1024:.2f} MB (max 10 MB)")

                if security_report['has_javascript']:
                    severity = "CRITICAL"
                    severity_reasons.append("JavaScript detected (code execution risk)")

                # Check for malware patterns in metadata
                for threat in security_report['threats']:
                    if any(pattern in threat.lower() for pattern in ['metasploit', 'exploit', 'payload']):
                        severity = "CRITICAL"
                        severity_reasons.append("Malware pattern detected")
                        break
                    
                    # Check for corrupt PDF errors in threats
                    if any(keyword in threat.lower() for keyword in ['corrupt', 'cannot open', 'invalid', 'damaged', 'encrypted']):
                        severity = "CRITICAL"
                        if "corrupt" not in severity_reasons[0].lower() if severity_reasons else True:
                            severity_reasons.insert(0, f"Corrupt PDF: {threat}")
                        break

                # Check for HIGH severity (propaganda-like, suspicious but not immediate danger)
                # Only evaluate if not already CRITICAL
                if severity != "CRITICAL":
                    # Multiple embedded files suggests information hiding
                    if security_report['has_embedded_files']:
                        embfile_count = sum(1 for t in security_report['threats'] if 'embedded' in t.lower())
                        if embfile_count > 1:  # Multiple embedded files
                            severity = "HIGH"
                            severity_reasons.append("Multiple embedded files (information hiding)")

                    # Suspicious metadata patterns (not malware but questionable)
                    for threat in security_report['threats']:
                        if 'script' in threat.lower() and severity != "CRITICAL":
                            severity = "HIGH"
                            severity_reasons.append("Suspicious scripting patterns")
                            break

                    # Many suspicious links could indicate phishing/manipulation
                    suspicious_link_count = sum(1 for t in security_report['threats'] if 'suspicious link' in t.lower())
                    if suspicious_link_count > 3:
                        severity = "HIGH"
                        severity_reasons.append(f"Multiple suspicious links ({suspicious_link_count}) - possible phishing")

                # MODERATE: Single embedded file, minor concerns - needs review

                # Generate unique source_id (short hex format to match existing system)
                import hashlib
                import secrets
                source_id = secrets.token_hex(8)

                # Calculate content hash (only if not CRITICAL - those files won't be saved)
                # Use streaming hash to avoid loading entire file into memory
                content_hash = None
                if severity != "CRITICAL":
                    sha256_hash = hashlib.sha256()
                    with open(file_obj['path'], 'rb') as f:
                        # Read file in chunks to avoid memory spike
                        for chunk in iter(lambda: f.read(8192), b''):
                            sha256_hash.update(chunk)
                    content_hash = sha256_hash.hexdigest()

                # Determine evaluation score based on severity
                # CRITICAL: <20 → SOCIAL_EXCLUDED (reject immediately)
                # HIGH: 20-39 → PROPAGANDA (quarantine for manual review)
                # MODERATE: 40-74 → SUSPECT (quarantine for review)
                if severity == "CRITICAL":
                    # Lower scores for more severe issues
                    if security_report.get('is_corrupt', False):
                        evaluation_score = 5.0  # Corrupt PDFs get lowest score
                    elif security_report['file_size'] > 10 * 1024 * 1024:
                        evaluation_score = 8.0  # Too large
                    elif security_report['has_javascript']:
                        evaluation_score = 3.0  # JavaScript is very dangerous
                    else:
                        evaluation_score = 10.0  # Other critical threats
                elif severity == "HIGH":
                    evaluation_score = 30.0
                else:  # MODERATE
                    evaluation_score = 45.0

                # Build evaluation reasoning from threats
                evaluation_reasoning = f"PDF Security Scan: {', '.join(security_report['threats'][:3])}"

                # Create tags from threat types and severity
                tags = []
                if security_report['has_javascript']:
                    tags.append('javascript')
                if security_report['has_embedded_files']:
                    tags.append('embedded_files')
                if severity == "CRITICAL":
                    tags.append('critical_threat')
                elif severity == "HIGH":
                    tags.append('propaganda_risk')
                if security_report['file_size'] > 10 * 1024 * 1024:
                    tags.append('oversized')

                # Extract keywords from threats
                keywords = []
                for threat in security_report['threats']:
                    keywords.extend(threat.lower().split()[:5])
                keywords = list(set(keywords))[:10]  # Unique, max 10

                timestamp_now = datetime.now().isoformat()

                # Map severity to bucket and determine actions
                # CRITICAL → social_excluded (reject, but save metadata for quarantine display)
                # HIGH → propaganda (quarantine for manual review, save file)
                # MODERATE → suspect (quarantine for review, save file)
                if severity == "CRITICAL":
                    bucket_name = "social_excluded"
                    # For CRITICAL: Don't save the file itself, but save metadata for quarantine tracking
                    should_save_file = False
                elif severity == "HIGH":
                    bucket_name = "propaganda"
                    should_save_file = True
                else:  # MODERATE
                    bucket_name = "suspect"
                    should_save_file = True

                # Create quarantine bucket structure
                bucket_dir = f"logs/quarantine/{bucket_name}"
                metadata_dir = os.path.join(bucket_dir, "metadata")
                sources_dir = os.path.join(bucket_dir, "sources")
                os.makedirs(metadata_dir, exist_ok=True)
                os.makedirs(sources_dir, exist_ok=True)

                # Determine storage path and original filename
                storage_path = None
                original_filename = f"{source_id}_{file_obj['name']}"

                if should_save_file:
                    import shutil
                    storage_path = os.path.join(sources_dir, original_filename)
                    shutil.copy2(file_obj['path'], storage_path)
                    if severity == "HIGH":
                        print(f"⚠️ PROPAGANDA: {file_obj['name']} - File saved for manual review (suspicious patterns)")
                    else:
                        print(f"⚠️ SUSPECT: {file_obj['name']} - File saved for review")
                else:
                    print(f"🚫 REJECTED: {file_obj['name']} - File NOT saved (critical threat)")

                # Build quarantine metadata matching existing format
                # Include detailed error information for rejected PDFs
                error_details = {
                    'severity': severity,
                    'reasons': severity_reasons,
                    'threats': security_report['threats'],
                    'warnings': security_report.get('warnings', []),
                    'file_size_mb': round(security_report['file_size'] / 1024 / 1024, 2),
                    'is_corrupt': security_report.get('is_corrupt', False),
                    'corrupt_error': security_report.get('corrupt_error', None),
                    'has_javascript': security_report['has_javascript'],
                    'has_embedded_files': security_report['has_embedded_files'],
                    'page_count': security_report.get('page_count', 0),
                }
                
                quarantine_data = {
                    'source_id': source_id,
                    'original_filename': original_filename,
                    'content_hash': content_hash,
                    'bucket': bucket_name,
                    'storage_path': storage_path,
                    'ingestion_timestamp': timestamp_now,
                    'rejection_timestamp': timestamp_now,  # Timestamp for rejected files
                    'error_details': error_details,  # Detailed error information
                    'last_modified': timestamp_now,
                    'evaluation_score': evaluation_score,
                    'evaluation_reasoning': evaluation_reasoning,
                    'curator_name': 'pdf_security_scanner',
                    'current_status': 'rejected' if severity == "CRITICAL" else 'new',
                    'status_history': [
                        {
                            'status': 'rejected' if severity == "CRITICAL" else 'new',
                            'timestamp': timestamp_now,
                            'note': '; '.join(severity_reasons) if severity_reasons else (
                                'CRITICAL threat - file rejected' if severity == "CRITICAL"
                                else 'HIGH severity - propaganda risk, manual review required' if severity == "HIGH"
                                else 'MODERATE threat - quarantined for review'
                            )
                        }
                    ],
                    'rejection_reason': '; '.join(severity_reasons) if severity == "CRITICAL" else None,
                    'error_message': security_report.get('corrupt_error') or ('; '.join(security_report['threats'][:3])),
                    'bucket_history': [
                        {
                            'bucket': bucket_name,
                            'timestamp': timestamp_now,
                            'reason': f"PDF security scan: {evaluation_reasoning}"
                        }
                    ],
                    'source_name': file_obj['name'],
                    'source_url': None,
                    'content_type': 'pdf',
                    'tags': tags,
                    'keywords': keywords,
                    'cooperative_count': 0,
                    'exploitative_count': 0,
                    'risk_level': 'critical' if severity == "CRITICAL" else 'high' if severity == "HIGH" else 'medium',
                    'retention_days': None,
                    'archive_after': None,
                    'purge_after': None,
                    # PDF-specific fields
                    'pdf_metadata': {
                        'severity': severity,
                        'threats': security_report['threats'],
                        'warnings': security_report['warnings'],
                        'file_size': security_report['file_size'],
                        'page_count': security_report['page_count'],
                        'has_javascript': security_report['has_javascript'],
                        'has_embedded_files': security_report['has_embedded_files']
                    }
                }

                # Save metadata JSON
                metadata_path = os.path.join(metadata_dir, f"{source_id}.json")
                with open(metadata_path, 'w') as f:
                    json.dump(quarantine_data, f, indent=2)
                
                # Also register with database quarantine system for frontend display (user-isolated)
                try:
                    if HAS_DATABASE_APIS and quarantine_api:
                        uid = get_user_id_from_header()
                        if uid:
                            # Map bucket_name to threat_level
                            threat_level_map = {
                                'social_excluded': 'HIGH',
                                'propaganda': 'CRITICAL',
                                'suspect': 'MODERATE',
                                'good': 'SAFE',
                                'garbage_skipped': 'LOW'
                            }
                            threat_level = threat_level_map.get(bucket_name, 'MODERATE')

                            # Build content preview with error details
                            content_preview = quarantine_data.get('error_message', 'PDF rejected')
                            if error_details.get('is_corrupt'):
                                content_preview = f"Corrupt PDF: {error_details.get('corrupt_error', 'Unknown error')}"

                            # Build threat details
                            threat_details = {
                                'error_message': error_message_text,
                                'severity': severity,
                                'bucket': bucket_name,
                                'reasons': severity_reasons,
                                'threats': security_report['threats'][:5],
                                'is_corrupt': error_details.get('is_corrupt', False),
                                'evaluation_score': evaluation_score
                            }

                            # Store in database quarantine system (user-isolated)
                            stored_item_id = quarantine_api.create_quarantine_item(
                                user_id=uid,
                                source_type='pdf',
                                source_id=source_id,
                                url=None,
                                title=file_obj['name'],
                                content_preview=content_preview[:500],  # Limit preview length
                                threat_level=threat_level,
                                threat_category=bucket_name,
                                threat_details=threat_details,
                                status='pending_review'
                            )

                            print(f"✅ Quarantine item stored in database: {stored_item_id} → {bucket_name} (user: {uid[:8]}...)")
                        else:
                            print(f"⚠️ No user ID available for quarantine storage")
                    else:
                        print(f"⚠️ Database quarantine API not available")
                except Exception as storage_err:
                    print(f"⚠️ Failed to register with database quarantine storage: {storage_err}")
                    import traceback
                    traceback.print_exc()
                    # Continue anyway - metadata file is saved

                # Return quarantine notice instead of summary
                # Build detailed error message with timestamp
                error_message_text = '; '.join(severity_reasons) if severity_reasons else 'Unknown error'
                timestamp_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if severity == "CRITICAL":
                    status_emoji = "🚫"
                    status_text = "REJECTED - FILE NOT SAVED"
                    bucket_display = "Social Excluded"
                    file_status = f"🗑️ FILE REJECTED ({timestamp_display}): The PDF file was not saved due to critical security threats.\n\nError: {error_message_text}"
                    next_steps = "Review in Quarantine tab → Social Excluded bucket"
                elif severity == "HIGH":
                    status_emoji = "⚠️"
                    status_text = "PROPAGANDA RISK - MANUAL REVIEW REQUIRED"
                    bucket_display = "Propaganda"
                    file_status = "🔍 FILE QUARANTINED: Suspicious patterns detected. Manual review required before processing."
                    next_steps = "Manually review for propaganda/manipulation patterns in Quarantine tab"
                else:  # MODERATE
                    status_emoji = "⚠️"
                    status_text = "QUARANTINED - SAVED FOR REVIEW"
                    bucket_display = "Suspect"
                    file_status = "📦 FILE QUARANTINED: The PDF is saved in quarantine for review."
                    next_steps = "Review and approve in Quarantine tab if safe"

                quarantine_notice = f"""{status_emoji} SECURITY {status_text}

📄 File: {file_obj['name']}
📊 Size: {security_report['file_size'] / 1024:.2f} KB
📑 Pages: {security_report['page_count']}
🆔 Source ID: {source_id}

⚠️ SECURITY THREATS DETECTED:
{threat_summary}

ℹ️ WARNINGS:
{warning_summary}

🔒 STATUS: This PDF was NOT processed to protect the system.
{file_status}

📋 DETAILS:
• Severity: {severity}
• Risk Level: {quarantine_data['risk_level'].title()}
• Quarantine Bucket: {bucket_display}
• JavaScript Detected: {'Yes' if security_report['has_javascript'] else 'No'}
• Embedded Files: {'Yes' if security_report['has_embedded_files'] else 'No'}
• Evaluation Score: {evaluation_score}/100

🔧 NEXT STEPS:
1. Review the security threats listed above
2. Check the Quarantine tab → {bucket_display} bucket (ID: {source_id})
3. Verify the PDF source is trustworthy
4. {next_steps}
5. Consider obtaining the PDF from a different, trusted source

⚠️ DO NOT open this PDF outside of a secure sandbox environment until threats are resolved."""

                summaries.append(quarantine_notice)
                continue

            # PDF passed security checks - proceed with processing
            if security_report['warnings']:
                print(f"⚠️ Warnings for {file_obj['name']}: {', '.join(security_report['warnings'])}")

            # OPTIMIZATION: Skip memory operations for faster processing
            memory_context = ""

            # Use streaming extraction instead of loading entire PDF
            text = extract_pdf_text_streaming(file_obj['path'], GRACE_CONFIG["pdf_max_chars"])

            if not text.strip():
                summaries.append(f"❌ No text found in {file_obj['name']}")
            else:
                # Check if content exceeds context window capacity
                # Estimate: 4 chars ≈ 1 token, 64K context window, reserve space for output
                estimated_input_tokens = len(text) // 4
                max_output_tokens = GRACE_CONFIG["max_tokens"]
                context_window = 65536  # magnum-v3-34b context limit

                if estimated_input_tokens + max_output_tokens > context_window - 1000:
                    # Context overflow - provide helpful error
                    pages_estimate = security_report.get('page_count', len(text) // 3000)
                    chars_per_page = len(text) // max(pages_estimate, 1)
                    recommended_pages = (context_window - max_output_tokens - 1000) * 4 // chars_per_page

                    error_msg = f"""📄 Document Too Large for Single Analysis

Your PDF "{file_obj['name']}" contains {pages_estimate} pages (~{len(text):,} characters).

Context Limit: The model can process approximately {recommended_pages} pages in one analysis session.

Options:
1. Split your document into {recommended_pages}-page sections
2. Upload sections separately for individual analysis
3. For book-length content, consider chapter-by-chapter analysis

Quality analysis requires space. We prioritize thoroughness over truncation."""

                    summaries.append(error_msg)
                    continue

                # Fine-tuned model handles persona and reasoning
                summary = query_llm(
                    "",
                    text,
                    memory_context=memory_context
                )

                # Add warnings to summary if present
                warning_text = ""
                if security_report['warnings']:
                    warning_text = f"\n\n⚠️ SECURITY WARNINGS:\n" + "\n".join(security_report['warnings'])

                # OPTIMIZATION: Skip memory storage and auto-QnA for faster processing
                summaries.append(f"📄 {file_obj['name']}:\n{summary}{warning_text}")
                if GRACE_CONFIG["log_pdf_summaries"]:
                    try:
                        with open("logs/pdf_log.txt", "a") as log_file:
                            log_file.write(f"### [{datetime.now()}] File: {file_obj['name']}\n{summary}\n\n---\n\n")
                    except Exception as log_err:
                        print(f"⚠️ Failed to write PDF log: {log_err}")
            
            # Clear text variable to free memory
            text = None
        
        return "\n\n---\n\n".join(summaries)
    except Exception as e:
        return f"❌ Error processing PDFs: {e}"


# --- API Routes ---
# (Frontend serving route moved to end of file to avoid catching API requests)

# Helper function to get or create user from API key
def get_or_create_user_from_api_key(api_key):
    """
    Get or create a user in the database based on API key.
    Returns: (user_id: UUID string, email: str, name: str) or None if error
    """
    try:
        # Load API keys from file
        api_keys_file = "api_keys.json"
        if not os.path.exists(api_keys_file):
            print(f"⚠️ API keys file not found: {api_keys_file}")
            return None
        
        with open(api_keys_file, 'r') as f:
            api_keys_data = json.load(f)
        
        # Get API key info
        key_info = api_keys_data.get("keys", {}).get(api_key)
        if not key_info:
            print(f"⚠️ API key not found in api_keys.json")
            return None
        
        email = key_info.get("email")
        name = key_info.get("name", "User")
        
        if not email:
            print(f"⚠️ No email found for API key")
            return None
        
        # Get database URL - use module-level DATABASE_URL or get from environment
        database_url = DATABASE_URL
        if not database_url:
            database_url = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        
        if not database_url:
            print(f"⚠️ DATABASE_URL not configured, cannot get/create user")
            return None
        
        # Double-check for placeholder
        if 'hostname' in database_url.lower() and '.rlwy.net' not in database_url.lower() and 'railway.internal' not in database_url.lower() and 'localhost' not in database_url.lower():
            print(f"❌ DATABASE_URL contains placeholder 'hostname': {database_url[:60]}...")
            print(f"   Cannot connect to database with placeholder URL")
            return None
        
        # Import database connection
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from urllib.parse import urlparse, parse_qs
        except ImportError:
            print(f"⚠️ psycopg2 not available")
            return None
        
        # Connect to database using the same robust connection handling as ConversationAPI
        # Parse database_url and fix any port/hostname issues
        parsed = urlparse(database_url)
        
        # Check if port exists and is valid - if not, remove it
        # Sometimes Railway DATABASE_URL has invalid port values
        netloc = parsed.netloc
        if ':' in netloc:
            # Split netloc into auth and host:port
            netloc_parts = netloc.split('@')
            if len(netloc_parts) == 2:
                auth, host_part = netloc_parts
                if ':' in host_part:
                    host, port_str = host_part.rsplit(':', 1)
                    # Try to validate port is a number
                    try:
                        port_num = int(port_str)
                        if port_num < 1 or port_num > 65535:
                            # Invalid port number, remove it
                            netloc = f"{auth}@{host}"
                            # Rebuild URL without port
                        database_url = f"{parsed.scheme}://{netloc}{parsed.path}"
                        if parsed.query:
                            database_url += f"?{parsed.query}"
                        parsed = urlparse(database_url)
                    except (ValueError, TypeError):
                        # Port is not a valid integer (e.g., "airport" or other text)
                        # Remove port and use default
                        netloc = f"{auth}@{host}"
                        # Rebuild URL without port
                        database_url = f"{parsed.scheme}://{netloc}{parsed.path}"
                        if parsed.query:
                            database_url += f"?{parsed.query}"
                        parsed = urlparse(database_url)
            else:
                # No auth, just host:port
                if ':' in netloc:
                    host, port_str = netloc.rsplit(':', 1)
                    try:
                        port_num = int(port_str)
                        if port_num < 1 or port_num > 65535:
                            netloc = host
                            database_url = f"{parsed.scheme}://{netloc}{parsed.path}"
                            if parsed.query:
                                database_url += f"?{parsed.query}"
                            parsed = urlparse(database_url)
                    except (ValueError, TypeError):
                        # Invalid port, remove it
                        netloc = host
                        database_url = f"{parsed.scheme}://{netloc}{parsed.path}"
                        if parsed.query:
                            database_url += f"?{parsed.query}"
                        parsed = urlparse(database_url)
        
        # Ensure sslmode is in the URL if not present
        # Note: Railway's private network (railway.internal) may not require SSL
        query_params = parse_qs(parsed.query)
        
        # Build clean connection string
        # For private Railway URLs (railway.internal), use sslmode=prefer (not require)
        # For public URLs, use sslmode=require
        is_private_url = 'railway.internal' in database_url.lower()
        
        if 'sslmode' not in query_params:
            # Add sslmode based on URL type
            separator = '&' if parsed.query else '?'
            if is_private_url:
                # Private Railway network - prefer SSL but don't require it
                conn_string = f"{database_url}{separator}sslmode=prefer"
            else:
                # Public URL - require SSL
                conn_string = f"{database_url}{separator}sslmode=require"
        else:
            conn_string = database_url
        
        # Use the connection string with timeout
        # Increase timeout for Railway TCP proxy connections (can be slow)
        # Private Railway URLs get longer timeout, public TCP proxy gets medium timeout
        if is_private_url:
            timeout = 15  # Private network - more reliable
        elif 'proxy.rlwy.net' in conn_string.lower():
            timeout = 15  # Railway TCP proxy - can be slow, needs longer timeout
        else:
            timeout = 10  # Other public connections
        conn = psycopg2.connect(
            conn_string,
            cursor_factory=RealDictCursor,
            connect_timeout=timeout
        )
        cursor = conn.cursor()
        
        try:
            # Check if user exists by email
            cursor.execute("SELECT id, role FROM users WHERE email = %s AND deleted_at IS NULL", (email,))
            user = cursor.fetchone()
            
            if user:
                # User exists, return UUID and role
                user_id = str(user['id'])
                user_role = user.get('role', 'student')  # Default to 'student' if role is NULL
                cursor.close()
                conn.close()
                print(f"✅ Found existing user: {email} ({user_id}) - Role: {user_role}")
                return (user_id, email, name, user_role)
            
            # User doesn't exist - create new user
                import uuid
                import bcrypt
                from datetime import datetime
                
            # Generate new UUID for user (no hardcoded IDs)
            user_id = str(uuid.uuid4())

            # Generate a random password hash (users authenticate via API key, not password)
            password_hash = bcrypt.hashpw(b"api_key_auth", bcrypt.gensalt()).decode()

            # Insert user - email is UNIQUE, so use ON CONFLICT to handle race conditions
            # If email already exists, get the existing user's ID
            # Default role is 'student' unless specified in API key config
            default_role = key_info.get("role", "student")
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, email_verified, status, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    status = EXCLUDED.status,
                    deleted_at = NULL
                RETURNING id, role
            """, (user_id, email, password_hash, name, True, 'active', default_role))
                
            # Get the user ID and role (will be the new ID or existing ID if conflict)
            result = cursor.fetchone()
            if result:
                user_id = str(result['id'])
                user_role = result.get('role', 'student')
            
                # Create default grace settings
                try:
                    cursor.execute("""
                        INSERT INTO user_grace_settings (user_id)
                        VALUES (%s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))
                except Exception as e:
                    print(f"⚠️ Could not create user_grace_settings: {e}")
                    # Continue anyway
                
            # Create default free subscription for new users
            try:
                # Check if user already has a subscription
                cursor.execute("SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", (user_id,))
                existing_sub = cursor.fetchone()
                
                if not existing_sub:
                    # Get free plan ID
                    cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
                    free_plan = cursor.fetchone()
                    if free_plan:
                        plan_id = free_plan['id']
                        from datetime import datetime, timedelta
                        now = datetime.now()
                        # Create subscription for free plan
                        cursor.execute("""
                            INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (user_id, plan_id, 'active', 'monthly', now, now + timedelta(days=30)))
            except Exception as e:
                print(f"⚠️ Could not create subscription: {e}")
                # Continue anyway - subscription is optional
            
                conn.commit()
                cursor.close()
                conn.close()
                
                print(f"✅ Created new user: {email} ({user_id}) - Role: {user_role}")
                return (user_id, email, name, user_role)
        
        except Exception as db_error:
            try:
                conn.rollback()
                cursor.close()
                conn.close()
            except:
                pass
            error_msg = str(db_error)
            print(f"❌ Database error in get_or_create_user_from_api_key: {error_msg}")
            print(f"   Database URL: {database_url[:60] if database_url else 'NOT SET'}...")
            print(f"   Email: {email}")
            import traceback
            traceback.print_exc()
            return None
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in get_or_create_user_from_api_key: {error_msg}")
        import traceback
        traceback.print_exc()
        return None

# Signup/Registration endpoint
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Sign up a new user (teacher or student)"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name') or data.get('name')
        role = data.get('role', 'student')  # Default to student
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400
        
        if role not in ['teacher', 'student']:
            return jsonify({
                "success": False,
                "error": "Role must be 'teacher' or 'student'"
            }), 400
        
        if len(password) < 6:
            return jsonify({
                "success": False,
                "error": "Password must be at least 6 characters"
            }), 400
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import bcrypt
        import uuid
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        if not database_url:
            return jsonify({
                "success": False,
                "error": "Database not configured"
            }), 500
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s AND deleted_at IS NULL", (email,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "An account with this email already exists"
                }), 400
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
            display_name = full_name or email.split('@')[0]
            
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, email_verified, status, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, full_name, role
            """, (user_id, email, password_hash, display_name, True, 'active', role))
            
            new_user = cursor.fetchone()
            
            # Create default grace settings
            try:
                cursor.execute("""
                    INSERT INTO user_grace_settings (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id,))
            except Exception as e:
                print(f"⚠️ Could not create user_grace_settings: {e}")
            
            # Create default free subscription
            try:
                cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
                free_plan = cursor.fetchone()
                if free_plan:
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    cursor.execute("""
                        INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (user_id, free_plan['id'], 'active', 'monthly', now, now + timedelta(days=30)))
            except Exception as e:
                print(f"⚠️ Could not create subscription: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ User created: {email} ({user_id}) - Role: {role}")
            return jsonify({
                "success": True,
                "user_id": user_id,
                "email": new_user['email'],
                "name": new_user.get('full_name', ''),
                "role": new_user['role']
            })
            
        except Exception as db_error:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"❌ Database error in signup: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": "Database error during signup"
            }), 500
    
    except Exception as e:
        print(f"❌ Error in signup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Login endpoint with username/email and password
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with email/username and password"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import bcrypt
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        if not database_url:
            return jsonify({
                "success": False,
                "error": "Database not configured"
            }), 500
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Find user by email
            cursor.execute("""
                SELECT id, email, password_hash, full_name, role, status, deleted_at
                FROM users 
                WHERE email = %s AND deleted_at IS NULL
            """, (email,))
            
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Invalid email or password"
                }), 401
            
            # Check if account is locked
            if user.get('status') == 'suspended':
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Account is suspended"
                }), 403
            
            # Verify password
            password_hash = user.get('password_hash', '')
            if not password_hash:
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Account not properly configured. Please contact support."
                }), 500
            
            # Check password
            try:
                password_valid = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            except Exception as e:
                print(f"⚠️ Password check error: {e}")
                password_valid = False
            
            if not password_valid:
                # Increment failed login attempts
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = failed_login_attempts + 1,
                        last_login_at = NOW()
                    WHERE id = %s
                """, (user['id'],))
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Invalid email or password"
                }), 401
            
            # Successful login - reset failed attempts and update last login
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = 0,
                    last_login_at = NOW(),
                    last_login_ip = %s
                WHERE id = %s
                RETURNING id, email, full_name, role
            """, (request.remote_addr, user['id']))
            
            updated_user = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            user_id = str(updated_user['id'])
            user_role = updated_user.get('role', 'student')
            is_admin = (updated_user['email'] == "admin@grace.coop" or user_role == "admin")
            is_teacher = (user_role == "teacher")
            is_student = (user_role == "student")
            
            print(f"✅ Login successful: {updated_user['email']} ({user_id}) - Role: {user_role}")
            return jsonify({
                "success": True,
                "user_id": user_id,
                "email": updated_user['email'],
                "name": updated_user.get('full_name', ''),
                "role": user_role,
                "is_admin": is_admin,
                "is_teacher": is_teacher,
                "is_student": is_student
            })
            
        except Exception as db_error:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"❌ Database error in login: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": "Database error during login"
            }), 500
    
    except Exception as e:
        print(f"❌ Error in login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Auth endpoint
@app.route('/api/auth/validate', methods=['POST'])
def validate_auth():
    """Validate API key and get/create user from database"""
    try:
        data = request.get_json(silent=True) or {}
        api_key = data.get('api_key') or request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                "valid": False,
                "error": "API key required"
            }), 401
        
        # Get or create user from API key
        user_info = get_or_create_user_from_api_key(api_key)
        
        if not user_info:
            print(f"❌ get_or_create_user_from_api_key returned None for API key: {api_key[:20]}...")
            return jsonify({
                "valid": False,
                "error": "Invalid API key or database error. Check server logs for details."
            }), 401
        
        # Handle both old format (3 values) and new format (4 values with role)
        if len(user_info) == 3:
            user_id, email, name = user_info
            user_role = 'student'  # Default for backward compatibility
        else:
            user_id, email, name, user_role = user_info
        
        # Validate user_id is not None or empty
        if not user_id:
            print(f"❌ get_or_create_user_from_api_key returned empty user_id for email: {email}")
            return jsonify({
                "valid": False,
                "error": "Database error: User ID is empty"
            }), 500
        
        # Check if user is admin (admin@grace.coop or role is 'admin')
        is_admin = (email == "admin@grace.coop" or user_role == "admin")
        is_teacher = (user_role == "teacher")
        is_student = (user_role == "student")

        print(f"✅ Authentication successful: {email} ({user_id}) - Role: {user_role}")
        return jsonify({
            "valid": True,
            "user_id": user_id,
            "is_admin": is_admin,
            "role": user_role,
            "is_teacher": is_teacher,
            "is_student": is_student,
            "email": email,
            "name": name
        })
    
    except Exception as e:
        print(f"❌ Error in validate_auth: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 500

# ============================================
# TEACHER/STUDENT MANAGEMENT API
# ============================================

def require_teacher_role():
    """Helper to check if current user is a teacher"""
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return None, jsonify({"error": "Authentication required"}), 401
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        if not database_url:
            return None, jsonify({"error": "Database not configured"}), 500
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = %s AND deleted_at IS NULL", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user or user.get('role') != 'teacher':
            return None, jsonify({"error": "Teacher access required"}), 403
        
        return user_id, None, None
    except Exception as e:
        print(f"❌ Error checking teacher role: {e}")
        return None, jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students', methods=['GET'])
def list_teacher_students():
    """List all students for the current teacher"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get all active students for this teacher
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.full_name,
                u.status,
                u.created_at,
                ts.enrollment_date,
                ts.status as enrollment_status,
                ts.notes,
                sp.student_number,
                sp.gpa,
                sp.academic_level
            FROM teacher_students ts
            JOIN users u ON ts.student_id = u.id
            LEFT JOIN student_profiles sp ON u.id = sp.student_id
            WHERE ts.teacher_id = %s 
            AND ts.deleted_at IS NULL
            AND u.deleted_at IS NULL
            ORDER BY u.full_name, u.email
        """, (teacher_id,))
        
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "students": [dict(student) for student in students]
        })
    except Exception as e:
        print(f"❌ Error listing students: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students', methods=['POST'])
def add_student():
    """Add a student to the teacher's roster - creates student account if needed"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        data = request.get_json() or {}
        student_email = data.get('email')
        student_password = data.get('password')  # Optional: if provided, create/update password
        student_name = data.get('name') or data.get('full_name')
        student_id = data.get('student_id')  # Optional: if student already exists
        
        if not student_email and not student_id:
            return jsonify({"error": "email or student_id required"}), 400
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import bcrypt
        import uuid
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Find or create student
        if student_id:
            cursor.execute("SELECT id, email, role FROM users WHERE id = %s AND deleted_at IS NULL", (student_id,))
            student = cursor.fetchone()
            if not student:
                cursor.close()
                conn.close()
                return jsonify({"error": "Student not found"}), 404
            if student.get('role') != 'student':
                cursor.close()
                conn.close()
                return jsonify({"error": "User is not a student"}), 400
        else:
            # Find by email
            cursor.execute("SELECT id, email, role FROM users WHERE email = %s AND deleted_at IS NULL", (student_email,))
            student = cursor.fetchone()
            
            if not student:
                # Create new student user with password
                if not student_password:
                    # Generate a temporary password if not provided
                    import secrets
                    student_password = secrets.token_urlsafe(12)
                    print(f"⚠️ No password provided, generated temporary password for {student_email}")
                
                student_id = str(uuid.uuid4())
                password_hash = bcrypt.hashpw(student_password.encode('utf-8'), bcrypt.gensalt()).decode()
                display_name = student_name or student_email.split('@')[0]
                
                cursor.execute("""
                    INSERT INTO users (id, email, password_hash, full_name, email_verified, status, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, email, role
                """, (student_id, student_email, password_hash, display_name, True, 'active', 'student'))
                student = cursor.fetchone()
                
                # Create default grace settings
                try:
                    cursor.execute("""
                        INSERT INTO user_grace_settings (user_id)
                        VALUES (%s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (student_id,))
                except Exception as e:
                    print(f"⚠️ Could not create user_grace_settings: {e}")
                
                # Create default free subscription
                try:
                    cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
                    free_plan = cursor.fetchone()
                    if free_plan:
                        from datetime import datetime, timedelta
                        now = datetime.now()
                        cursor.execute("""
                            INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (student_id, free_plan['id'], 'active', 'monthly', now, now + timedelta(days=30)))
                except Exception as e:
                    print(f"⚠️ Could not create subscription: {e}")
                
                print(f"✅ Created new student account: {student_email} ({student_id})")
            else:
                # Student exists - update password if provided
                if student_password:
                    password_hash = bcrypt.hashpw(student_password.encode('utf-8'), bcrypt.gensalt()).decode()
                    cursor.execute("""
                        UPDATE users 
                        SET password_hash = %s,
                            full_name = COALESCE(%s, full_name)
                        WHERE id = %s
                    """, (password_hash, student_name, student['id']))
                    print(f"✅ Updated password for existing student: {student_email}")
                
                if student.get('role') != 'student':
                    # Update role to student if needed
                    cursor.execute("UPDATE users SET role = 'student' WHERE id = %s", (student['id'],))
                    student['role'] = 'student'
        
        student_id = str(student['id'])
        
        # Check if relationship already exists
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        existing = cursor.fetchone()
        
        if existing:
            cursor.close()
            conn.close()
            return jsonify({"error": "Student already in roster"}), 400
        
        # Create teacher-student relationship
        cursor.execute("""
            INSERT INTO teacher_students (teacher_id, student_id, status, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id, enrollment_date
        """, (teacher_id, student_id, 'active', data.get('notes', '')))
        
        relationship = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        response_data = {
            "success": True,
            "student_id": student_id,
            "enrollment_date": relationship['enrollment_date'].isoformat() if relationship else None
        }
        
        # Include password in response if it was generated (for teacher to share with student)
        if not data.get('password') and not student:
            response_data["temporary_password"] = student_password
            response_data["message"] = "Student account created with temporary password"
        
        return jsonify(response_data), 201
    except Exception as e:
        print(f"❌ Error adding student: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>', methods=['DELETE'])
def remove_student(student_id):
    """Remove a student from the teacher's roster"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Soft delete the relationship
        cursor.execute("""
            UPDATE teacher_students 
            SET deleted_at = NOW(), status = 'inactive'
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error removing student: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/profile', methods=['GET'])
def get_student_profile(student_id):
    """Get student profile and information"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_view_profile', 'profile',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get student info
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.full_name,
                u.status,
                u.created_at,
                sp.student_number,
                sp.enrollment_date,
                sp.gpa,
                sp.total_credits,
                sp.academic_level,
                sp.parent_email,
                sp.parent_phone,
                sp.notes,
                sp.metadata
            FROM users u
            LEFT JOIN student_profiles sp ON u.id = sp.student_id
            WHERE u.id = %s AND u.deleted_at IS NULL
        """, (student_id,))
        
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not student:
            return jsonify({"error": "Student not found"}), 404
        
        return jsonify(dict(student))
    except Exception as e:
        print(f"❌ Error getting student profile: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/profile', methods=['PUT'])
def update_student_profile(student_id):
    """Update student profile information"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        data = request.get_json() or {}
        
        # Update or insert student profile
        cursor.execute("""
            INSERT INTO student_profiles (
                student_id, student_number, gpa, total_credits, academic_level,
                parent_email, parent_phone, emergency_contact_name, emergency_contact_phone,
                notes, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_id) DO UPDATE SET
                student_number = EXCLUDED.student_number,
                gpa = EXCLUDED.gpa,
                total_credits = EXCLUDED.total_credits,
                academic_level = EXCLUDED.academic_level,
                parent_email = EXCLUDED.parent_email,
                parent_phone = EXCLUDED.parent_phone,
                emergency_contact_name = EXCLUDED.emergency_contact_name,
                emergency_contact_phone = EXCLUDED.emergency_contact_phone,
                notes = EXCLUDED.notes,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """, (
            student_id,
            data.get('student_number'),
            data.get('gpa'),
            data.get('total_credits'),
            data.get('academic_level'),
            data.get('parent_email'),
            data.get('parent_phone'),
            data.get('emergency_contact_name'),
            data.get('emergency_contact_phone'),
            data.get('notes'),
            json.dumps(data.get('metadata', {}))
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error updating student profile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def log_audit_access(
    user_id: str,
    accessed_user_id: str,
    access_type: str,
    resource_type: str,
    resource_id: str = None,
    endpoint: str = None,
    access_details: dict = None
):
    """Log data access to audit table"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get request info
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        cursor.execute("""
            SELECT log_data_access(
                %s::uuid, %s::uuid, %s, %s, %s::uuid, %s, %s::inet, %s, %s::jsonb
            )
        """, (
            user_id,
            accessed_user_id,
            access_type,
            resource_type,
            resource_id,
            endpoint,
            ip_address,
            user_agent,
            json.dumps(access_details or {})
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        # Don't fail the request if audit logging fails
        print(f"⚠️ Failed to log audit access: {e}")

@app.route('/api/teacher/students/<student_id>/grades', methods=['GET'])
def list_student_grades(student_id):
    """List all grades for a student"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_view_grade', 'grade',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get grades
        cursor.execute("""
            SELECT 
                id,
                assignment_name,
                assignment_type,
                grade,
                max_points,
                letter_grade,
                feedback,
                rubric_data,
                metadata,
                category_grades,
                rubric_template_id,
                rubric_scores,
                due_date,
                submitted_at,
                graded_at,
                status,
                created_at
            FROM student_grades
            WHERE student_id = %s AND teacher_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
        """, (student_id, teacher_id))
        
        grades = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "grades": [dict(grade) for grade in grades]
        })
    except Exception as e:
        print(f"❌ Error listing grades: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/grades', methods=['POST'])
def create_grade(student_id):
    """Create a new grade for a student"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_create_grade', 'grade',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        data = request.get_json() or {}
        
        # Calculate letter grade if not provided
        grade = data.get('grade')
        letter_grade = data.get('letter_grade')
        if grade and not letter_grade:
            if grade >= 90:
                letter_grade = 'A'
            elif grade >= 80:
                letter_grade = 'B'
            elif grade >= 70:
                letter_grade = 'C'
            elif grade >= 60:
                letter_grade = 'D'
            else:
                letter_grade = 'F'
        
        import uuid
        grade_id = str(uuid.uuid4())
        
        # Handle category_grades - calculate final grade if provided
        category_grades = data.get('category_grades')
        if category_grades and isinstance(category_grades, dict):
            # Calculate weighted final grade from category grades
            valid_grades = [v for v in category_grades.values() if isinstance(v, (int, float)) and 0 <= v <= 100]
            if valid_grades:
                # Simple average (can be customized with weights)
                calculated_grade = sum(valid_grades) / len(valid_grades)
                if not grade:  # Only override if grade not explicitly provided
                    grade = calculated_grade
                    if grade >= 90:
                        letter_grade = 'A'
                    elif grade >= 80:
                        letter_grade = 'B'
                    elif grade >= 70:
                        letter_grade = 'C'
                    elif grade >= 60:
                        letter_grade = 'D'
                    else:
                        letter_grade = 'F'
        
        # Handle rubric template and scores
        rubric_template_id = data.get('rubric_template_id')
        rubric_scores = data.get('rubric_scores')
        
        # If rubric template is provided, calculate grade from rubric scores
        if rubric_template_id and rubric_scores:
            try:
                cursor.execute("""
                    SELECT max_score, rubric_structure
                    FROM rubric_templates
                    WHERE id = %s AND deleted_at IS NULL
                """, (rubric_template_id,))
                template = cursor.fetchone()
                if template:
                    # Calculate total score from rubric domain scores
                    if isinstance(rubric_scores, dict):
                        total_rubric_score = sum(v for v in rubric_scores.values() if isinstance(v, (int, float)))
                        max_rubric_points = template['rubric_structure'].get('total_max_points', template['max_score'])
                        # Convert to percentage if needed
                        if max_rubric_points > 0:
                            calculated_grade = (total_rubric_score / max_rubric_points) * 100
                            if not grade:  # Only override if grade not explicitly provided
                                grade = calculated_grade
                                if grade >= 90:
                                    letter_grade = 'A'
                                elif grade >= 80:
                                    letter_grade = 'B'
                                elif grade >= 70:
                                    letter_grade = 'C'
                                elif grade >= 60:
                                    letter_grade = 'D'
                                else:
                                    letter_grade = 'F'
            except Exception as e:
                print(f"⚠️ Error calculating grade from rubric: {e}")
        
        cursor.execute("""
            INSERT INTO student_grades (
                id, teacher_id, student_id, assignment_name, assignment_type,
                grade, max_points, letter_grade, feedback, rubric_data, metadata,
                category_grades, rubric_template_id, rubric_scores, due_date, submitted_at, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, graded_at
        """, (
            grade_id,
            teacher_id,
            student_id,
            data.get('assignment_name'),
            data.get('assignment_type', 'general'),
            grade,
            data.get('max_points'),
            letter_grade,
            data.get('feedback'),
            json.dumps(data.get('rubric_data', {})),
            json.dumps(data.get('metadata', {})),
            json.dumps(category_grades or {}),
            rubric_template_id,
            json.dumps(rubric_scores or {}),
            data.get('due_date'),
            data.get('submitted_at'),
            data.get('status', 'graded')
        ))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "grade_id": grade_id,
            "graded_at": result['graded_at'].isoformat() if result else None
        }), 201
    except Exception as e:
        print(f"❌ Error creating grade: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/grades/<grade_id>', methods=['PUT'])
def update_grade(student_id, grade_id):
    """Update a grade for a student"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher owns this grade
        cursor.execute("""
            SELECT id FROM student_grades 
            WHERE id = %s AND teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (grade_id, teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Grade not found"}), 404
        
        data = request.get_json() or {}
        
        # Handle category_grades - calculate final grade if provided
        category_grades = data.get('category_grades')
        if category_grades and isinstance(category_grades, dict):
            # Calculate weighted final grade from category grades
            valid_grades = [v for v in category_grades.values() if isinstance(v, (int, float)) and 0 <= v <= 100]
            if valid_grades:
                # Simple average (can be customized with weights)
                calculated_grade = sum(valid_grades) / len(valid_grades)
                if not data.get('grade'):  # Only override if grade not explicitly provided
                    data['grade'] = calculated_grade
        
        # Calculate letter grade if grade changed
        grade = data.get('grade')
        letter_grade = data.get('letter_grade')
        if grade and not letter_grade:
            if grade >= 90:
                letter_grade = 'A'
            elif grade >= 80:
                letter_grade = 'B'
            elif grade >= 70:
                letter_grade = 'C'
            elif grade >= 60:
                letter_grade = 'D'
            else:
                letter_grade = 'F'
        
        # Build update query dynamically
        updates = []
        params = []
        
        if 'assignment_name' in data:
            updates.append("assignment_name = %s")
            params.append(data['assignment_name'])
        if 'assignment_type' in data:
            updates.append("assignment_type = %s")
            params.append(data['assignment_type'])
        if grade is not None:
            updates.append("grade = %s")
            params.append(grade)
        if 'max_points' in data:
            updates.append("max_points = %s")
            params.append(data['max_points'])
        if letter_grade:
            updates.append("letter_grade = %s")
            params.append(letter_grade)
        if 'feedback' in data:
            updates.append("feedback = %s")
            params.append(data['feedback'])
        if 'rubric_data' in data:
            updates.append("rubric_data = %s")
            params.append(json.dumps(data['rubric_data']))
        if 'metadata' in data:
            updates.append("metadata = %s")
            params.append(json.dumps(data['metadata']))
        if 'category_grades' in data:
            updates.append("category_grades = %s")
            params.append(json.dumps(data['category_grades']))
        if 'rubric_template_id' in data:
            updates.append("rubric_template_id = %s")
            params.append(data['rubric_template_id'])
        if 'rubric_scores' in data:
            updates.append("rubric_scores = %s")
            params.append(json.dumps(data['rubric_scores']))
            # Recalculate grade from rubric scores if template is provided
            rubric_template_id = data.get('rubric_template_id')
            if rubric_template_id and isinstance(data['rubric_scores'], dict):
                try:
                    cursor.execute("""
                        SELECT max_score, rubric_structure
                        FROM rubric_templates
                        WHERE id = %s AND deleted_at IS NULL
                    """, (rubric_template_id,))
                    template = cursor.fetchone()
                    if template:
                        total_rubric_score = sum(v for v in data['rubric_scores'].values() if isinstance(v, (int, float)))
                        max_rubric_points = template['rubric_structure'].get('total_max_points', template['max_score'])
                        if max_rubric_points > 0:
                            calculated_grade = (total_rubric_score / max_rubric_points) * 100
                            if not data.get('grade'):  # Only override if grade not explicitly provided
                                data['grade'] = calculated_grade
                                if calculated_grade >= 90:
                                    letter_grade = 'A'
                                elif calculated_grade >= 80:
                                    letter_grade = 'B'
                                elif calculated_grade >= 70:
                                    letter_grade = 'C'
                                elif calculated_grade >= 60:
                                    letter_grade = 'D'
                                else:
                                    letter_grade = 'F'
                except Exception as e:
                    print(f"⚠️ Error calculating grade from rubric: {e}")
        if 'due_date' in data:
            updates.append("due_date = %s")
            params.append(data['due_date'])
        if 'submitted_at' in data:
            updates.append("submitted_at = %s")
            params.append(data['submitted_at'])
        if 'status' in data:
            updates.append("status = %s")
            params.append(data['status'])
        
        if not updates:
            cursor.close()
            conn.close()
            return jsonify({"error": "No fields to update"}), 400
        
        updates.append("updated_at = NOW()")
        params.extend([grade_id, teacher_id, student_id])
        
        cursor.execute(f"""
            UPDATE student_grades 
            SET {', '.join(updates)}
            WHERE id = %s AND teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, params)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error updating grade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates', methods=['GET'])
def list_rubric_templates():
    """List all rubric templates available to the teacher"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get teacher's own templates and public templates
        cursor.execute("""
            SELECT 
                id, name, description, template_type, rubric_structure,
                max_score, scoring_scale, is_default, is_public,
                created_at, updated_at
            FROM rubric_templates
            WHERE (teacher_id = %s OR is_public = TRUE)
            AND deleted_at IS NULL
            ORDER BY is_default DESC, template_type, name
        """, (teacher_id,))
        
        templates = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "templates": [dict(template) for template in templates]
        })
    except Exception as e:
        print(f"❌ Error listing rubric templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates', methods=['POST'])
def create_rubric_template():
    """Create a new rubric template"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        data = request.get_json() or {}
        
        # Validate required fields
        if not data.get('name'):
            cursor.close()
            conn.close()
            return jsonify({"error": "Template name is required"}), 400
        
        if not data.get('rubric_structure'):
            cursor.close()
            conn.close()
            return jsonify({"error": "Rubric structure is required"}), 400
        
        # If setting as default, unset other defaults for this teacher
        if data.get('is_default'):
            cursor.execute("""
                UPDATE rubric_templates
                SET is_default = FALSE
                WHERE teacher_id = %s AND deleted_at IS NULL
            """, (teacher_id,))
        
        cursor.execute("""
            INSERT INTO rubric_templates (
                teacher_id, name, description, template_type,
                rubric_structure, max_score, scoring_scale,
                is_default, is_public
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, created_at
        """, (
            teacher_id,
            data.get('name'),
            data.get('description'),
            data.get('template_type', 'custom'),
            json.dumps(data.get('rubric_structure', {})),
            data.get('max_score', 10.0),
            data.get('scoring_scale', 6),
            data.get('is_default', False),
            data.get('is_public', False)
        ))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "template_id": result['id'],
            "created_at": result['created_at'].isoformat() if result else None
        }), 201
    except Exception as e:
        print(f"❌ Error creating rubric template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates/<template_id>', methods=['GET'])
def get_rubric_template(template_id):
    """Get a specific rubric template"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, name, description, template_type, rubric_structure,
                max_score, scoring_scale, is_default, is_public,
                created_at, updated_at
            FROM rubric_templates
            WHERE id = %s 
            AND (teacher_id = %s OR is_public = TRUE)
            AND deleted_at IS NULL
        """, (template_id, teacher_id))
        
        template = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        return jsonify(dict(template))
    except Exception as e:
        print(f"❌ Error getting rubric template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates/<template_id>', methods=['PUT'])
def update_rubric_template(template_id):
    """Update a rubric template"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher owns this template
        cursor.execute("""
            SELECT id FROM rubric_templates 
            WHERE id = %s AND teacher_id = %s AND deleted_at IS NULL
        """, (template_id, teacher_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        data = request.get_json() or {}
        
        # If setting as default, unset other defaults for this teacher
        if data.get('is_default'):
            cursor.execute("""
                UPDATE rubric_templates
                SET is_default = FALSE
                WHERE teacher_id = %s AND id != %s AND deleted_at IS NULL
            """, (teacher_id, template_id))
        
        # Build update query dynamically
        updates = []
        params = []
        
        if 'name' in data:
            updates.append("name = %s")
            params.append(data['name'])
        if 'description' in data:
            updates.append("description = %s")
            params.append(data['description'])
        if 'template_type' in data:
            updates.append("template_type = %s")
            params.append(data['template_type'])
        if 'rubric_structure' in data:
            updates.append("rubric_structure = %s")
            params.append(json.dumps(data['rubric_structure']))
        if 'max_score' in data:
            updates.append("max_score = %s")
            params.append(data['max_score'])
        if 'scoring_scale' in data:
            updates.append("scoring_scale = %s")
            params.append(data['scoring_scale'])
        if 'is_default' in data:
            updates.append("is_default = %s")
            params.append(data['is_default'])
        if 'is_public' in data:
            updates.append("is_public = %s")
            params.append(data['is_public'])
        
        if not updates:
            cursor.close()
            conn.close()
            return jsonify({"error": "No fields to update"}), 400
        
        updates.append("updated_at = NOW()")
        params.extend([template_id, teacher_id])
        
        cursor.execute(f"""
            UPDATE rubric_templates 
            SET {', '.join(updates)}
            WHERE id = %s AND teacher_id = %s AND deleted_at IS NULL
        """, params)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error updating rubric template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates/<template_id>/generate-feedback', methods=['POST'])
def generate_rubric_feedback(template_id):
    """Generate AI feedback on student writing using a rubric template"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get rubric template
        cursor.execute("""
            SELECT rubric_structure, max_score, scoring_scale, name
            FROM rubric_templates
            WHERE id = %s 
            AND (teacher_id = %s OR is_public = TRUE)
            AND deleted_at IS NULL
        """, (template_id, teacher_id))
        
        template = cursor.fetchone()
        if not template:
            cursor.close()
            conn.close()
            return jsonify({"error": "Template not found"}), 404
        
        data = request.get_json() or {}
        student_writing = data.get('student_writing')
        rubric_scores = data.get('rubric_scores', {})  # Optional: if teacher has already scored
        
        if not student_writing:
            cursor.close()
            conn.close()
            return jsonify({"error": "Student writing content is required"}), 400
        
        rubric_structure = template['rubric_structure']
        domains = rubric_structure.get('domains', [])
        
        # Build prompt for Grace AI to evaluate writing against rubric
        rubric_description = f"""
You are evaluating student writing using the {template['name']} rubric.

The rubric evaluates writing across {len(domains)} domains:
"""
        
        for domain in domains:
            rubric_description += f"""
- {domain['name']} (Max: {domain['max_points']} points)
  {domain['description']}
  
  Scoring Criteria:
"""
            for criterion in domain.get('criteria', []):
                rubric_description += f"  Level {criterion['level']}: {criterion['description']}\n"
        
        if rubric_scores:
            rubric_description += "\n\nCurrent Scores:\n"
            for domain_name, score in rubric_scores.items():
                rubric_description += f"- {domain_name}: {score}\n"
        
        rubric_description += f"""

Student Writing to Evaluate:
---
{student_writing[:5000]}  # Limit to 5000 chars for context
---

Please provide:
1. A score for each domain (0 to max points) with justification
2. Specific, constructive feedback for each domain
3. Overall strengths and areas for improvement
4. Actionable suggestions for the student

Format your response as structured feedback that a teacher can use to provide quality guidance to the student.
"""
        
        # Use Grace AI to generate feedback
        try:
            from grace_gui import query_llm
            
            system_prompt = "You are Grace, an expert writing instructor. You provide detailed, constructive feedback on student writing using established rubrics. Your feedback is specific, encouraging, and actionable."
            
            ai_feedback = query_llm(
                system=system_prompt,
                user_input=rubric_description,
                memory_context="",
                temperature=0.7
            )
            
            # Parse AI feedback and extract domain scores if not provided
            suggested_scores = {}
            if not rubric_scores:
                # Try to extract scores from AI response
                import re
                for domain in domains:
                    domain_name = domain['name']
                    # Look for patterns like "Content and Analysis: 2" or "Score: 2/2"
                    pattern = rf"{re.escape(domain_name)}[:\s]+(\d+)"
                    match = re.search(pattern, ai_feedback, re.IGNORECASE)
                    if match:
                        suggested_scores[domain_name] = int(match.group(1))
            
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "feedback": ai_feedback,
                "suggested_scores": suggested_scores,
                "rubric_template_id": template_id,
                "rubric_name": template['name']
            })
        except Exception as e:
            print(f"❌ Error generating AI feedback: {e}")
            import traceback
            traceback.print_exc()
            cursor.close()
            conn.close()
            return jsonify({"error": f"Failed to generate AI feedback: {str(e)}"}), 500
        
    except Exception as e:
        print(f"❌ Error in generate_rubric_feedback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/rubric-templates/<template_id>', methods=['DELETE'])
def delete_rubric_template(template_id):
    """Delete a rubric template (soft delete)"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher owns this template
        cursor.execute("""
            UPDATE rubric_templates
            SET deleted_at = NOW()
            WHERE id = %s AND teacher_id = %s AND deleted_at IS NULL
        """, (template_id, teacher_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error deleting rubric template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get audit logs for the teacher (teachers can view their own access logs)"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get time period filter
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        cursor.execute("""
            SELECT 
                id, user_id, accessed_user_id, access_type, resource_type,
                resource_id, endpoint, ip_address, user_agent, access_details,
                accessed_at
            FROM data_access_audit
            WHERE user_id = %s
            AND accessed_at >= NOW() - INTERVAL '%s days'
            ORDER BY accessed_at DESC
            LIMIT %s
        """, (teacher_id, days, limit))
        
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "logs": [dict(log) for log in logs],
            "count": len(logs)
        })
    except Exception as e:
        print(f"❌ Error getting audit logs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/embeddings', methods=['GET'])
def get_student_embeddings(student_id):
    """Get student's Milvus embeddings/memories (for teacher review)"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_view_memory', 'memory',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get optional category filter
        category = request.args.get('category')
        
        # Build query with optional category filter
        query = """
            SELECT 
                id,
                content,
                content_type,
                title,
                source_type,
                source_metadata,
                vector_id,
                embedding_model,
                importance_score,
                quality_score,
                memory_category,
                created_at,
                updated_at
            FROM user_memories
            WHERE user_id = %s AND deleted_at IS NULL
        """
        params = [student_id]
        
        if category:
            query += " AND memory_category = %s"
            params.append(category)
        
        query += " ORDER BY created_at DESC LIMIT 100"
        
        cursor.execute(query, params)
        
        memories = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "embeddings": [dict(memory) for memory in memories],
            "count": len(memories)
        })
    except Exception as e:
        print(f"❌ Error getting student embeddings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/milvus/collections', methods=['GET'])
def get_milvus_collections():
    """Get Milvus collection statistics for all collections"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        from backend.milvus_client import get_milvus_client
        from config.milvus_config import get_all_collections
        
        milvus_client = get_milvus_client()
        if not milvus_client or not milvus_client.client:
            return jsonify({"error": "Milvus not available"}), 503
        
        collections = get_all_collections()
        collection_stats = {}
        total_vectors = 0
        
        for collection_name in collections:
            try:
                stats = milvus_client.get_collection_stats(collection_name)
                row_count = stats.get('row_count', 0) if isinstance(stats, dict) else 0
                collection_stats[collection_name] = {
                    "exists": True,
                    "vectors": row_count,
                    "stats": stats
                }
                total_vectors += row_count
            except Exception as e:
                collection_stats[collection_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return jsonify({
            "collections": collection_stats,
            "total_vectors": total_vectors,
            "collection_count": len(collections)
        })
    except Exception as e:
        print(f"❌ Error getting Milvus collections: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/milvus/vectors', methods=['GET'])
def get_milvus_vectors():
    """Get Milvus vectors with filtering options"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        from backend.milvus_client import get_milvus_client
        from config.milvus_config import get_collection_name
        
        collection_name = request.args.get('collection', 'grace_memory_general')
        student_id = request.args.get('student_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        milvus_client = get_milvus_client()
        if not milvus_client or not milvus_client.client:
            return jsonify({"error": "Milvus not available"}), 503
        
        # Build filter expression
        filter_expr = None
        if student_id:
            filter_expr = f'user_id == "{student_id}"'
        
        # Note: Milvus doesn't have direct pagination, so we'll use limit
        # For offset, we'd need to use query with offset parameter if available
        # For now, we'll just use limit
        
        # Get a sample of vectors by searching with a dummy query
        # We'll use a zero vector to get all vectors (if supported)
        # Or we can use query() method if available
        
        try:
            # Try to query vectors directly
            # Note: This is a simplified approach - actual implementation depends on Milvus version
            # For now, we'll return collection stats and suggest using search endpoint
            
            stats = milvus_client.get_collection_stats(collection_name)
            row_count = stats.get('row_count', 0) if isinstance(stats, dict) else 0
            
            return jsonify({
                "collection": collection_name,
                "total_vectors": row_count,
                "message": "Use search endpoint to query specific vectors",
                "filter": filter_expr
            })
        except Exception as e:
            return jsonify({
                "error": f"Failed to query vectors: {str(e)}",
                "collection": collection_name
            }), 500
    except Exception as e:
        print(f"❌ Error getting Milvus vectors: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/milvus/vectors/by-student', methods=['GET'])
def get_milvus_vectors_by_student():
    """Get Milvus vector counts grouped by student"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, None, 'teacher_view_student', 'student',
            endpoint=request.path,
            access_details={'action': 'view_all_students_vectors'}
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Get all students for this teacher
        cursor.execute("""
            SELECT 
                u.id as student_id,
                u.email,
                u.full_name,
                COUNT(DISTINCT um.id) as memory_count,
                COUNT(DISTINCT um.vector_id) FILTER (WHERE um.vector_id IS NOT NULL) as vector_count
            FROM teacher_students ts
            JOIN users u ON ts.student_id = u.id
            LEFT JOIN user_memories um ON u.id = um.user_id AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            WHERE ts.teacher_id = %s 
            AND ts.deleted_at IS NULL
            AND u.deleted_at IS NULL
            GROUP BY u.id, u.email, u.full_name
            ORDER BY u.full_name, u.email
        """, (teacher_id,))
        
        students = cursor.fetchall()
        
        # Get category breakdown per student
        student_stats = []
        for student in students:
            student_dict = dict(student)
            student_id = student_dict['student_id']
            
            # Get category breakdown for this student
            try:
                cursor.execute("""
                    SELECT 
                        COALESCE(memory_category, 'uncategorized') as category,
                        COUNT(*) as count
                    FROM user_memories
                    WHERE user_id = %s AND (is_archived IS NULL OR is_archived = FALSE)
                    GROUP BY memory_category
                    ORDER BY count DESC
                """, (student_id,))
                
                category_breakdown = {}
                for row in cursor.fetchall():
                    category_breakdown[row['category']] = row['count']
                
                student_dict['category_breakdown'] = category_breakdown
            except Exception as e:
                print(f"⚠️ Error getting category breakdown for student {student_id}: {e}")
                student_dict['category_breakdown'] = {}
            
            student_stats.append(student_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "students": student_stats
        })
    except Exception as e:
        print(f"❌ Error getting vectors by student: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/analytics/categories', methods=['GET'])
def get_student_category_analytics(student_id):
    """Get category-based analytics for a student"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_view_student', 'analytics',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from datetime import datetime, timedelta
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get time period filter (optional)
        time_period = request.args.get('time_period', 'all')  # 'week', 'month', 'all'
        start_date = None
        if time_period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        elif time_period == 'month':
            start_date = datetime.now() - timedelta(days=30)
        
        # Build date filter
        date_filter = ""
        if start_date:
            date_filter = f"AND um.created_at >= '{start_date.isoformat()}'"
        
        # Get category distribution
        cursor.execute(f"""
            SELECT 
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(*) as count,
                AVG(um.memory_category_confidence) as avg_confidence,
                MIN(um.created_at) as first_seen,
                MAX(um.created_at) as last_seen
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY um.memory_category
            ORDER BY count DESC
        """, (student_id,))
        
        category_distribution = []
        for row in cursor.fetchall():
            category_distribution.append({
                'category': row['category'],
                'count': row['count'],
                'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else None,
                'first_seen': row['first_seen'].isoformat() if row['first_seen'] else None,
                'last_seen': row['last_seen'].isoformat() if row['last_seen'] else None
            })
        
        # Get category trends over time (weekly buckets)
        cursor.execute(f"""
            SELECT 
                DATE_TRUNC('week', um.created_at) as week,
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(*) as count
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY DATE_TRUNC('week', um.created_at), um.memory_category
            ORDER BY week DESC, count DESC
        """, (student_id,))
        
        trends = {}
        for row in cursor.fetchall():
            week_str = row['week'].isoformat() if row['week'] else 'unknown'
            if week_str not in trends:
                trends[week_str] = {}
            trends[week_str][row['category']] = row['count']
        
        # Get category coverage (percentage of total memories)
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_memories,
                COUNT(DISTINCT memory_category) as unique_categories
            FROM user_memories
            WHERE user_id = %s 
            AND (is_archived IS NULL OR is_archived = FALSE)
            {date_filter}
        """, (student_id,))
        
        coverage_stats = cursor.fetchone()
        total_memories = coverage_stats['total_memories'] or 0
        unique_categories = coverage_stats['unique_categories'] or 0
        
        # Get Milvus vector counts per category
        try:
            from backend.milvus_client import get_milvus_client
            from config.milvus_config import get_collection_name
            
            milvus_client = get_milvus_client()
            vector_counts_by_category = {}
            
            if milvus_client and milvus_client.client:
                # Query each collection for this student's vectors
                for context_type in ['general', 'character', 'plot']:
                    collection_name = get_collection_name(context_type)
                    try:
                        # Get vectors for this student
                        filter_expr = f'user_id == "{student_id}"'
                        if start_date:
                            # Note: Milvus doesn't store created_at, so we can't filter by date
                            # This is a limitation - we'd need to join with PostgreSQL
                            pass
                        
                        # Count vectors per category
                        # Note: This requires querying Milvus, which is expensive
                        # For now, we'll use PostgreSQL data which includes vector_id
                        pass
                    except Exception as e:
                        print(f"⚠️ Error querying Milvus collection {collection_name}: {e}")
        except Exception as e:
            print(f"⚠️ Error getting Milvus stats: {e}")
        
        # Get vector counts from PostgreSQL (more efficient)
        cursor.execute(f"""
            SELECT 
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(DISTINCT um.vector_id) FILTER (WHERE um.vector_id IS NOT NULL) as vector_count
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY um.memory_category
        """, (student_id,))
        
        vector_counts = {}
        for row in cursor.fetchall():
            vector_counts[row['category']] = row['vector_count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'student_id': student_id,
            'time_period': time_period,
            'category_distribution': category_distribution,
            'trends': trends,
            'coverage': {
                'total_memories': total_memories,
                'unique_categories': unique_categories,
                'coverage_rate': (unique_categories / 10.0 * 100) if total_memories > 0 else 0  # 10 total categories
            },
            'vector_counts': vector_counts
        })
    except Exception as e:
        print(f"❌ Error getting category analytics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/activity', methods=['GET'])
def get_student_activity_timeline(student_id):
    """Get student activity timeline showing writing patterns over time"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        # Log access
        log_audit_access(
            teacher_id, student_id, 'teacher_view_student', 'activity',
            endpoint=request.path
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from datetime import datetime, timedelta
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get time period filter
        time_period = request.args.get('time_period', 'month')  # 'week', 'month', 'all'
        start_date = None
        if time_period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        elif time_period == 'month':
            start_date = datetime.now() - timedelta(days=30)
        
        date_filter = ""
        if start_date:
            date_filter = f"AND um.created_at >= '{start_date.isoformat()}'"
        
        # Get activity timeline (daily breakdown)
        cursor.execute(f"""
            SELECT 
                DATE(um.created_at) as date,
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(*) as count,
                SUM(LENGTH(um.content)) as total_chars
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY DATE(um.created_at), um.memory_category
            ORDER BY date DESC, count DESC
        """, (student_id,))
        
        timeline_data = {}
        for row in cursor.fetchall():
            date_str = row['date'].isoformat() if row['date'] else 'unknown'
            if date_str not in timeline_data:
                timeline_data[date_str] = {
                    'date': date_str,
                    'categories': {},
                    'total_memories': 0,
                    'total_chars': 0
                }
            timeline_data[date_str]['categories'][row['category']] = {
                'count': row['count'],
                'total_chars': row['total_chars']
            }
            timeline_data[date_str]['total_memories'] += row['count']
            timeline_data[date_str]['total_chars'] += row['total_chars'] or 0
        
        # Get weekly category distribution
        cursor.execute(f"""
            SELECT 
                DATE_TRUNC('week', um.created_at) as week,
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(*) as count
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY DATE_TRUNC('week', um.created_at), um.memory_category
            ORDER BY week DESC, count DESC
        """, (student_id,))
        
        weekly_distribution = {}
        for row in cursor.fetchall():
            week_str = row['week'].isoformat() if row['week'] else 'unknown'
            if week_str not in weekly_distribution:
                weekly_distribution[week_str] = {}
            weekly_distribution[week_str][row['category']] = row['count']
        
        # Get monthly category distribution
        cursor.execute(f"""
            SELECT 
                DATE_TRUNC('month', um.created_at) as month,
                COALESCE(um.memory_category, 'uncategorized') as category,
                COUNT(*) as count
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY DATE_TRUNC('month', um.created_at), um.memory_category
            ORDER BY month DESC, count DESC
        """, (student_id,))
        
        monthly_distribution = {}
        for row in cursor.fetchall():
            month_str = row['month'].isoformat() if row['month'] else 'unknown'
            if month_str not in monthly_distribution:
                monthly_distribution[month_str] = {}
            monthly_distribution[month_str][row['category']] = row['count']
        
        # Get activity patterns (most active days/times)
        cursor.execute(f"""
            SELECT 
                EXTRACT(DOW FROM um.created_at) as day_of_week,
                EXTRACT(HOUR FROM um.created_at) as hour_of_day,
                COUNT(*) as count
            FROM user_memories um
            WHERE um.user_id = %s 
            AND (um.is_archived IS NULL OR um.is_archived = FALSE)
            {date_filter}
            GROUP BY EXTRACT(DOW FROM um.created_at), EXTRACT(HOUR FROM um.created_at)
            ORDER BY count DESC
        """, (student_id,))
        
        activity_patterns = {
            'day_of_week': {},
            'hour_of_day': {}
        }
        for row in cursor.fetchall():
            dow = int(row['day_of_week'])
            hod = int(row['hour_of_day'])
            day_name = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][dow]
            activity_patterns['day_of_week'][day_name] = activity_patterns['day_of_week'].get(day_name, 0) + row['count']
            activity_patterns['hour_of_day'][hod] = activity_patterns['hour_of_day'].get(hod, 0) + row['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'student_id': student_id,
            'time_period': time_period,
            'timeline': list(timeline_data.values()),
            'weekly_distribution': weekly_distribution,
            'monthly_distribution': monthly_distribution,
            'activity_patterns': activity_patterns
        })
    except Exception as e:
        print(f"❌ Error getting activity timeline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/export', methods=['GET'])
def export_student_data(student_id):
    """Export student data (ensures isolation boundaries)"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # Get export format
        export_format = request.args.get('format', 'json')  # 'json' or 'csv'
        
        # Get student profile
        cursor.execute("""
            SELECT * FROM student_profiles
            WHERE student_id = %s AND deleted_at IS NULL
        """, (student_id,))
        profile = cursor.fetchone()
        
        # Get student grades
        cursor.execute("""
            SELECT * FROM student_grades
            WHERE student_id = %s AND teacher_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
        """, (student_id, teacher_id))
        grades = cursor.fetchall()
        
        # Get student memories (limited to prevent large exports)
        limit = request.args.get('memory_limit', 100, type=int)
        cursor.execute("""
            SELECT id, content, content_type, title, memory_category, memory_category_confidence,
                   created_at, updated_at
            FROM user_memories
            WHERE user_id = %s AND (is_archived IS NULL OR is_archived = FALSE)
            ORDER BY created_at DESC
            LIMIT %s
        """, (student_id, limit))
        memories = cursor.fetchall()
        
        # Get category breakdown
        cursor.execute("""
            SELECT 
                COALESCE(memory_category, 'uncategorized') as category,
                COUNT(*) as count
            FROM user_memories
            WHERE user_id = %s AND (is_archived IS NULL OR is_archived = FALSE)
            GROUP BY memory_category
        """, (student_id,))
        category_breakdown = {row['category']: row['count'] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        # Log export
        log_audit_access(
            teacher_id, student_id, 'teacher_view_student', 'export',
            endpoint=request.path,
            access_details={'format': export_format, 'memory_limit': limit}
        )
        
        # Prepare export data
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'exporter_id': teacher_id,
            'student_id': student_id,
            'profile': dict(profile) if profile else None,
            'grades': [dict(grade) for grade in grades],
            'memories': [dict(memory) for memory in memories],
            'category_breakdown': category_breakdown,
            'metadata': {
                'memory_limit': limit,
                'total_memories_exported': len(memories),
                'total_grades_exported': len(grades)
            }
        }
        
        if export_format == 'csv':
            # Convert to CSV format (simplified)
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Student Data Export', datetime.now().isoformat()])
            writer.writerow([])
            
            # Write profile
            if profile:
                writer.writerow(['Profile'])
                for key, value in profile.items():
                    writer.writerow([key, value])
                writer.writerow([])
            
            # Write grades
            if grades:
                writer.writerow(['Grades'])
                writer.writerow(['Assignment', 'Grade', 'Letter Grade', 'Feedback', 'Created At'])
                for grade in grades:
                    writer.writerow([
                        grade.get('assignment_name', ''),
                        grade.get('grade', ''),
                        grade.get('letter_grade', ''),
                        grade.get('feedback', '')[:50] if grade.get('feedback') else '',
                        grade.get('created_at', '')
                    ])
                writer.writerow([])
            
            # Write category breakdown
            writer.writerow(['Category Breakdown'])
            for category, count in category_breakdown.items():
                writer.writerow([category, count])
            
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=student_{student_id}_export_{datetime.now().strftime("%Y%m%d")}.csv'
                }
            )
        else:
            # JSON format
            return jsonify(export_data)
        
    except Exception as e:
        print(f"❌ Error exporting student data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/students/<student_id>/embeddings/search', methods=['POST'])
def search_student_embeddings(student_id):
    """Search student's Milvus embeddings by semantic similarity"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        data = request.get_json() or {}
        query_text = data.get('query')
        limit = data.get('limit', 10)
        context_type = data.get('context_type', 'general')
        category = data.get('category')  # Single category (backward compatibility)
        categories = data.get('categories')  # List of categories (new multi-category support)
        exclude_categories = data.get('exclude_categories')  # Categories to exclude
        category_logic = data.get('category_logic', 'OR')  # 'AND' or 'OR' for multiple categories
        boost_categories = data.get('boost_categories')  # Categories to boost in results
        boost_factor = data.get('boost_factor', 1.5)  # Boost multiplier for preferred categories
        
        if not query_text:
            cursor.close()
            conn.close()
            return jsonify({"error": "query text required"}), 400
        
        # Generate embedding for query
        try:
            from backend.memory_embedder import get_embedder
            embedder = get_embedder()
            query_embedding = embedder.generate_embedding(query_text)
        except Exception as e:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Failed to generate embedding: {str(e)}"}), 500
        
        # Search Milvus with student_id filter
        try:
            from backend.milvus_client import get_milvus_client
            from config.milvus_config import get_collection_name
            
            milvus_client = get_milvus_client()
            if not milvus_client or not milvus_client.client:
                cursor.close()
                conn.close()
                return jsonify({"error": "Milvus not available"}), 503
            
            collection_name = get_collection_name(context_type)
            
            # Build filter expression with advanced category filtering
            filter_expr = f'user_id == "{student_id}"'
            
            # Handle category filtering (support both single and multi-category)
            category_filters = []
            if category:
                # Backward compatibility: single category
                category_filters.append(f'memory_category == "{category}"')
            elif categories:
                # New: multiple categories with AND/OR logic
                if isinstance(categories, list) and len(categories) > 0:
                    if category_logic.upper() == 'AND':
                        # All categories must match (not typical, but supported)
                        for cat in categories:
                            category_filters.append(f'memory_category == "{cat}"')
                    else:  # OR logic (default)
                        # At least one category matches
                        category_list = ', '.join([f'"{cat}"' for cat in categories])
                        category_filters.append(f'memory_category in [{category_list}]')
            
            # Handle category exclusions
            if exclude_categories:
                if isinstance(exclude_categories, list) and len(exclude_categories) > 0:
                    for cat in exclude_categories:
                        category_filters.append(f'memory_category != "{cat}"')
            
            # Combine category filters
            if category_filters:
                if category_logic.upper() == 'AND':
                    filter_expr += ' && ' + ' && '.join(category_filters)
                else:
                    filter_expr += ' && (' + ' || '.join(category_filters) + ')'
            
            # Perform search with increased limit if boosting is enabled
            search_limit = limit * 2 if boost_categories else limit
            
            results = milvus_client.search(
                collection_name=collection_name,
                query_vectors=[query_embedding],
                filter_expr=filter_expr,
                limit=search_limit,
                output_fields=["memory_id", "conversation_id", "user_id", "project_id", "tag_path", "context_type", "memory_category", "memory_category_confidence"]
            )
            
            # Get memory details from PostgreSQL
            memory_ids = []
            scored_results = []
            
            if results and len(results) > 0:
                for result_group in results:
                    for result in result_group:
                        entity = result.get('entity', {})
                        memory_id = entity.get('memory_id')
                        if memory_id:
                            # Apply category boosting if enabled
                            score = result.get('distance', 0)  # Lower distance = higher similarity
                            memory_category = entity.get('memory_category', 'general')
                            
                            if boost_categories and memory_category in boost_categories:
                                # Boost score for preferred categories (invert distance for boosting)
                                score = score / boost_factor
                            
                            scored_results.append({
                                'memory_id': memory_id,
                                'score': score,
                                'distance': result.get('distance', 0),
                                'category': memory_category
                            })
                            
                            memory_ids.append(memory_id)
                
                # Sort by boosted score and take top results
                if boost_categories:
                    scored_results.sort(key=lambda x: x['score'])
                    memory_ids = [r['memory_id'] for r in scored_results[:limit]]
            
            memories = []
            if memory_ids:
                placeholders = ','.join(['%s'] * len(memory_ids))
                cursor.execute(f"""
                    SELECT 
                        id,
                        content,
                        content_type,
                        title,
                        source_type,
                        source_metadata,
                        vector_id,
                        embedding_model,
                        importance_score,
                        quality_score,
                        memory_category,
                        memory_category_confidence,
                        created_at,
                        updated_at
                    FROM user_memories
                    WHERE id::text = ANY(ARRAY[{placeholders}])
                    AND user_id = %s
                    AND (is_archived IS NULL OR is_archived = FALSE)
                """, memory_ids + [student_id])
                memories = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                "results": [dict(memory) for memory in memories],
                "count": len(memories),
                "query": query_text
            })
        except Exception as e:
            cursor.close()
            conn.close()
            print(f"❌ Error searching Milvus: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"❌ Error searching student embeddings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================
# TURNITIN INTEGRATION ENDPOINTS
# ============================================

@app.route('/api/teacher/turnitin/config', methods=['GET'])
def get_turnitin_config():
    """Get Turnitin configuration for the teacher"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, tool_name, tool_url, consumer_key,
                enabled, allow_late_submissions, enable_peer_review,
                enable_ai_detection, enable_feedback_studio,
                similarity_threshold, exclude_quotes, exclude_bibliography,
                exclude_small_matches, metadata,
                created_at, updated_at
            FROM turnitin_configurations
            WHERE teacher_id = %s AND deleted_at IS NULL
        """, (teacher_id,))
        
        config = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not config:
            return jsonify({
                "enabled": False,
                "configured": False
            })
        
        config_dict = dict(config)
        # Don't expose shared secret in GET request
        if 'shared_secret' in config_dict:
            del config_dict['shared_secret']
        
        config_dict['configured'] = bool(config_dict.get('consumer_key'))
        return jsonify(config_dict)
    except Exception as e:
        print(f"❌ Error getting Turnitin config: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/turnitin/config', methods=['POST', 'PUT'])
def save_turnitin_config():
    """Save or update Turnitin configuration"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        data = request.get_json() or {}
        
        # Check if config exists
        cursor.execute("""
            SELECT id FROM turnitin_configurations
            WHERE teacher_id = %s AND deleted_at IS NULL
        """, (teacher_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing config
            updates = []
            params = []
            
            if 'tool_name' in data:
                updates.append("tool_name = %s")
                params.append(data['tool_name'])
            if 'tool_url' in data:
                updates.append("tool_url = %s")
                params.append(data['tool_url'])
            if 'consumer_key' in data:
                updates.append("consumer_key = %s")
                params.append(data['consumer_key'])
            if 'shared_secret' in data:
                # In production, encrypt this
                updates.append("shared_secret = %s")
                params.append(data['shared_secret'])
            if 'enabled' in data:
                updates.append("enabled = %s")
                params.append(data['enabled'])
            if 'allow_late_submissions' in data:
                updates.append("allow_late_submissions = %s")
                params.append(data['allow_late_submissions'])
            if 'enable_peer_review' in data:
                updates.append("enable_peer_review = %s")
                params.append(data['enable_peer_review'])
            if 'enable_ai_detection' in data:
                updates.append("enable_ai_detection = %s")
                params.append(data['enable_ai_detection'])
            if 'enable_feedback_studio' in data:
                updates.append("enable_feedback_studio = %s")
                params.append(data['enable_feedback_studio'])
            if 'similarity_threshold' in data:
                updates.append("similarity_threshold = %s")
                params.append(data['similarity_threshold'])
            if 'exclude_quotes' in data:
                updates.append("exclude_quotes = %s")
                params.append(data['exclude_quotes'])
            if 'exclude_bibliography' in data:
                updates.append("exclude_bibliography = %s")
                params.append(data['exclude_bibliography'])
            if 'exclude_small_matches' in data:
                updates.append("exclude_small_matches = %s")
                params.append(data['exclude_small_matches'])
            if 'metadata' in data:
                updates.append("metadata = %s")
                params.append(json.dumps(data['metadata']))
            
            if updates:
                updates.append("updated_at = NOW()")
                params.append(existing['id'])
                
                cursor.execute(f"""
                    UPDATE turnitin_configurations
                    SET {', '.join(updates)}
                    WHERE id = %s
                """, params)
        else:
            # Create new config
            cursor.execute("""
                INSERT INTO turnitin_configurations (
                    teacher_id, tool_name, tool_url, consumer_key, shared_secret,
                    enabled, allow_late_submissions, enable_peer_review,
                    enable_ai_detection, enable_feedback_studio,
                    similarity_threshold, exclude_quotes, exclude_bibliography,
                    exclude_small_matches, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                teacher_id,
                data.get('tool_name', 'Turnitin'),
                data.get('tool_url'),
                data.get('consumer_key'),
                data.get('shared_secret'),
                data.get('enabled', False),
                data.get('allow_late_submissions', True),
                data.get('enable_peer_review', False),
                data.get('enable_ai_detection', True),
                data.get('enable_feedback_studio', True),
                data.get('similarity_threshold', 25),
                data.get('exclude_quotes', False),
                data.get('exclude_bibliography', False),
                data.get('exclude_small_matches', 0),
                json.dumps(data.get('metadata', {}))
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error saving Turnitin config: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/turnitin/submit', methods=['POST'])
def submit_to_turnitin():
    """Submit student work to Turnitin for similarity checking"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import uuid
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Check if Turnitin is configured and enabled
        cursor.execute("""
            SELECT id, enabled, consumer_key, shared_secret, tool_url
            FROM turnitin_configurations
            WHERE teacher_id = %s AND deleted_at IS NULL
        """, (teacher_id,))
        
        config = cursor.fetchone()
        if not config or not config['enabled']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Turnitin is not configured or enabled"}), 400
        
        if not config['consumer_key'] or not config['shared_secret']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Turnitin credentials not configured"}), 400
        
        data = request.get_json() or {}
        student_id = data.get('student_id')
        assignment_id = data.get('assignment_id')  # Optional: link to student_grades
        submission_title = data.get('submission_title')
        submission_content = data.get('submission_content')
        
        if not student_id or not submission_title or not submission_content:
            cursor.close()
            conn.close()
            return jsonify({"error": "student_id, submission_title, and submission_content are required"}), 400
        
        # Verify teacher has access to this student
        cursor.execute("""
            SELECT id FROM teacher_students 
            WHERE teacher_id = %s AND student_id = %s AND deleted_at IS NULL
        """, (teacher_id, student_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found in roster"}), 404
        
        # In a real implementation, this would make an LTI launch request to Turnitin
        # For now, we'll create a submission record and simulate the process
        submission_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO turnitin_submissions (
                id, teacher_id, student_id, assignment_id,
                submission_title, submission_content, submission_type,
                report_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, created_at
        """, (
            submission_id,
            teacher_id,
            student_id,
            assignment_id,
            submission_title,
            submission_content,
            data.get('submission_type', 'text'),
            'pending'
        ))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        # In production, you would initiate the LTI launch here
        return jsonify({
            "success": True,
            "submission_id": submission_id,
            "message": "Submission created. In production, this would launch Turnitin LTI tool.",
            "note": "To complete integration, implement LTI 1.1/1.3 launch protocol with Turnitin"
        }), 201
        
    except Exception as e:
        print(f"❌ Error submitting to Turnitin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/turnitin/submissions', methods=['GET'])
def list_turnitin_submissions():
    """List Turnitin submissions for a student or assignment"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        student_id = request.args.get('student_id')
        assignment_id = request.args.get('assignment_id')
        
        query = """
            SELECT 
                ts.id, ts.submission_title, ts.submission_type,
                ts.turnitin_submission_id, ts.turnitin_url, ts.similarity_report_url,
                ts.similarity_score, ts.ai_score,
                ts.report_status, ts.report_generated_at,
                ts.similarity_details, ts.ai_detection_details,
                ts.created_at, ts.updated_at,
                u.id as student_id, u.full_name as student_name, u.email as student_email
            FROM turnitin_submissions ts
            JOIN users u ON ts.student_id = u.id
            WHERE ts.teacher_id = %s AND ts.deleted_at IS NULL
        """
        params = [teacher_id]
        
        if student_id:
            query += " AND ts.student_id = %s"
            params.append(student_id)
        
        if assignment_id:
            query += " AND ts.assignment_id = %s"
            params.append(assignment_id)
        
        query += " ORDER BY ts.created_at DESC"
        
        cursor.execute(query, params)
        submissions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "submissions": [dict(sub) for sub in submissions]
        })
    except Exception as e:
        print(f"❌ Error listing Turnitin submissions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/teacher/turnitin/submissions/<submission_id>', methods=['GET'])
def get_turnitin_submission(submission_id):
    """Get details of a specific Turnitin submission"""
    try:
        teacher_id, error_response, status = require_teacher_role()
        if error_response:
            return error_response, status
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = DATABASE_URL or os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ts.*, u.full_name as student_name, u.email as student_email
            FROM turnitin_submissions ts
            JOIN users u ON ts.student_id = u.id
            WHERE ts.id = %s AND ts.teacher_id = %s AND ts.deleted_at IS NULL
        """, (submission_id, teacher_id))
        
        submission = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not submission:
            return jsonify({"error": "Submission not found"}), 404
        
        return jsonify(dict(submission))
    except Exception as e:
        print(f"❌ Error getting Turnitin submission: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# DISABLED: AI pattern removal feature
# def remove_ai_patterns(text):
#     """
#     Post-processing function to remove AI writing patterns from text.
#     Applies all style rules from grace_style_config.
#     """
#     import re
#
#     cleaned = text
#
#     # Get style rules
#     style_rules = GRACE_CONFIG.get('style_rules', {})
#
#     # Remove em dashes - replace with commas or semicolons based on context
#     cleaned = re.sub(r'\s*—\s*', ', ', cleaned)
#
#     # Replace banned AI phrases
#     ai_patterns = style_rules.get('chatgpt_patterns', [])
#     for pattern in ai_patterns:
#         # Case insensitive replacement
#         cleaned = re.sub(re.escape(pattern), '', cleaned, flags=re.IGNORECASE)
#
#     # Remove weak modifiers at start of sentences or before adjectives
#     weak_mods = style_rules.get('avoid_weak_modifiers', [])
#     for mod in weak_mods:
#         cleaned = re.sub(rf'\b{mod}\s+', '', cleaned, flags=re.IGNORECASE)
#
#     # Remove filler words
#     fillers = style_rules.get('avoid_filler_words', [])
#     for filler in fillers:
#         cleaned = re.sub(rf'\b{filler}\s+', '', cleaned, flags=re.IGNORECASE)
#
#     # Remove hedging language
#     hedges = style_rules.get('avoid_hedging', [])
#     for hedge in hedges:
#         cleaned = re.sub(re.escape(hedge), '', cleaned, flags=re.IGNORECASE)
#
#     # Remove redundant phrases
#     redundant = style_rules.get('avoid_redundant_phrases', [])
#     for phrase in redundant:
#         # Replace with simpler version (e.g., "past history" -> "history")
#         words = phrase.split()
#         if len(words) == 2:
#             cleaned = re.sub(re.escape(phrase), words[1], cleaned, flags=re.IGNORECASE)
#
#     # Remove clichés (just remove them entirely as they add no value)
#     cliches = style_rules.get('common_cliches', [])
#     for cliche in cliches:
#         cleaned = re.sub(re.escape(cliche), '', cleaned, flags=re.IGNORECASE)
#
#     # Clean up multiple spaces
#     cleaned = re.sub(r'\s+', ' ', cleaned)
#
#     # Clean up spaces before punctuation
#     cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
#
#     # Clean up multiple punctuation
#     cleaned = re.sub(r'([.,;:!?])\1+', r'\1', cleaned)
#
#     # Fix spacing after punctuation
#     cleaned = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', cleaned)
#
#     return cleaned.strip()


@app.route('/api/ping', methods=['GET'])
def ping():
    """Minimal endpoint that never fails - use to confirm API is reachable."""
    return jsonify({"ok": True})


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint - must never crash"""
    try:
        # Check if llama-server is actually reachable (non-blocking, don't fail if down)
        llm_status = "unknown"
        llm_error = None
        try:
            import requests
            test_response = requests.get("http://127.0.0.1:8080/v1/models", timeout=2)
            if test_response.status_code == 200:
                llm_status = "connected"
            else:
                llm_status = f"error_{test_response.status_code}"
        except requests.exceptions.ConnectionError:
            llm_status = "connection_refused"
            llm_error = "Cannot connect to llama-server on port 8080"
        except Exception as e:
            llm_status = "error"
            llm_error = str(e)
        
        # Always return 200 OK - health check should never fail the server
        return jsonify({
            "status": "ok",
            "llm_url": LM_API_URL,
            "llm_status": llm_status,
            "llm_error": llm_error,
            "news_index_loaded": index is not None if 'index' in globals() else False,
            "database_configured": HAS_DATABASE_APIS,
            "conversation_api": "initialized" if conversation_api else "none",
            "database_url_set": bool(DATABASE_URL) if 'DATABASE_URL' in globals() else False
        }), 200
    except Exception as e:
        # Even if health check itself fails, return 200 to indicate server is running
        import traceback
        print(f"⚠️ Health check error (non-fatal): {e}")
        return jsonify({
            "status": "ok",
            "error": "Health check failed but server is running",
            "message": str(e)
        }), 200

@app.route('/api/debug/database', methods=['GET'])
def debug_database():
    """Debug endpoint to check database connection state"""
    debug_info = {
        "HAS_DATABASE_APIS": HAS_DATABASE_APIS,
        "conversation_api": "initialized" if conversation_api else "none",
        "projects_api": "initialized" if projects_api else "none",
        "quarantine_api": "initialized" if quarantine_api else "none",
        "DATABASE_URL": DATABASE_URL[:60] + "..." if DATABASE_URL and len(DATABASE_URL) > 60 else DATABASE_URL if DATABASE_URL else "not set"
    }
    
    # Add comprehensive diagnostics if database logger is available
    try:
        from backend.database_logger import DatabaseLogger
        from backend.database_debugger import DatabaseDebugger
        
        if DATABASE_URL:
            debugger = DatabaseDebugger(DATABASE_URL)
            diagnosis = debugger.diagnose_connection()
            debug_info["diagnosis"] = diagnosis
            
            # Add health summary
            health_summary = DatabaseLogger.get_health_summary()
            debug_info["health_summary"] = health_summary
            
            # Add recent errors (last 5)
            recent_errors = DatabaseLogger.get_recent_errors(5)
            debug_info["recent_errors"] = recent_errors
            
            # Add connection history (last 10)
            connection_history = DatabaseLogger.get_connection_history(10)
            debug_info["connection_history"] = connection_history
            
            # Add pool stats if available
            if conversation_api and hasattr(conversation_api, 'pool_manager'):
                pool_stats = conversation_api.pool_manager.get_stats()
                debug_info["pool_stats"] = pool_stats
    except ImportError:
        debug_info["logger_available"] = False
    except Exception as e:
        debug_info["diagnosis_error"] = str(e)
    
    return jsonify(debug_info)

@app.route('/api/debug/database/test', methods=['POST'])
def test_database_query():
    """Test a database query (for debugging)"""
    try:
        from backend.database_debugger import DatabaseDebugger
        
        if not DATABASE_URL:
            return jsonify({"error": "DATABASE_URL not configured"}), 503
        
        data = request.get_json() or {}
        query = data.get('query', 'SELECT 1')
        params = data.get('params')
        
        debugger = DatabaseDebugger(DATABASE_URL)
        result = debugger.test_query(query, tuple(params) if params else None)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500

@app.route('/api/debug/database/errors', methods=['GET'])
def get_database_errors():
    """Get recent database errors"""
    try:
        from backend.database_logger import DatabaseLogger
        
        limit = int(request.args.get('limit', 20))
        errors = DatabaseLogger.get_recent_errors(limit)
        
        return jsonify({
            "count": len(errors),
            "errors": errors
        })
    except ImportError:
        return jsonify({"error": "Database logger not available"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/llm', methods=['GET'])
def debug_llm():
    """Debug endpoint to check LLM connection state"""
    import socket
    import requests
    
    debug_info = {
        "lm_api_url": LM_API_URL,
        "use_grace_config": USE_GRACE_CONFIG,
        "port_8080_listening": False,
        "llama_server_responding": False,
        "connection_test": None,
        "error": None
    }
    
    # Check if port 8080 is listening
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8080))
        sock.close()
        debug_info["port_8080_listening"] = (result == 0)
    except Exception as e:
        debug_info["error"] = f"Port check failed: {e}"
    
    # Test actual connection to llama-server
    try:
        response = requests.get("http://127.0.0.1:8080/v1/models", timeout=3)
        debug_info["llama_server_responding"] = (response.status_code == 200)
        if response.status_code == 200:
            debug_info["connection_test"] = "success"
            try:
                models = response.json()
                if 'data' in models and len(models['data']) > 0:
                    debug_info["model_loaded"] = models['data'][0].get('id', 'unknown')
            except:
                pass
        else:
            debug_info["connection_test"] = f"error_{response.status_code}"
            debug_info["error"] = response.text[:200]
    except requests.exceptions.ConnectionError:
        debug_info["connection_test"] = "connection_refused"
        debug_info["error"] = "Cannot connect to llama-server"
    except Exception as e:
        debug_info["connection_test"] = "error"
        debug_info["error"] = str(e)
    
    return jsonify(debug_info)

@app.route('/api/debug/database/health', methods=['GET'])
def get_database_health():
    """Get database health summary"""
    try:
        from backend.database_logger import DatabaseLogger
        from backend.database_debugger import DatabaseDebugger
        
        if not DATABASE_URL:
            return jsonify({
                "status": "unhealthy",
                "error": "DATABASE_URL not configured"
            }), 503
        
        # Get health summary
        health_summary = DatabaseLogger.get_health_summary()
        
        # Run full diagnosis
        debugger = DatabaseDebugger(DATABASE_URL)
        diagnosis = debugger.diagnose_connection()
        
        return jsonify({
            "summary": health_summary,
            "diagnosis": diagnosis
        })
    except ImportError:
        return jsonify({"error": "Database logger not available"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# MEMORY MONITORING & DIAGNOSTICS
# ============================================

@app.route('/api/memories', methods=['GET'])
@require_api_key
def get_memories():
    """
    Get memories with semantic search support
    Supports both semantic search (when query provided) and regular listing
    """
    if not HAS_DATABASE_APIS or not memory_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        # Get query parameters
        search_query = request.args.get('search', '').strip()
        project_id = request.args.get('project_id')
        category = request.args.get('category', 'all')
        tags = request.args.get('tags', '')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Parse tags (comma-separated)
        tag_list = [t.strip() for t in tags.split(',')] if tags else []
        
        # Determine context type from category or query
        context_type = "general"
        if category and category != 'all':
            if 'character' in category.lower():
                context_type = "character"
            elif 'plot' in category.lower() or 'structure' in category.lower():
                context_type = "plot"
        
        # If search query provided, use semantic search
        if search_query:
            # Use Milvus semantic search
            memories = memory_api.recall_memories(
                user_id=uid,
                query=search_query,
                project_id=project_id,
                limit=limit,
                tag_paths=tag_list if tag_list else None,
                context_type=context_type
            )
        else:
            # Regular listing (no semantic search)
            # Filter by project_id if provided
            memories = memory_api.list_memories(
                user_id=uid,
                quarantine_status='safe',
                promoted_only=False,
                limit=limit,
                offset=offset,
                project_id=project_id  # Filter by project if provided
            )
        
        # Filter by category if needed
        if category and category != 'all':
            # Category filtering would need to be implemented based on your category system
            # For now, we'll return all memories
            pass
        
        # Format response for frontend
        formatted_memories = []
        for mem in memories:
            # Extract context_tags from source_metadata if present
            context_tags = []
            source_metadata = mem.get('source_metadata', {})
            if isinstance(source_metadata, str):
                import json
                try:
                    source_metadata = json.loads(source_metadata)
                except:
                    source_metadata = {}
            if isinstance(source_metadata, dict) and 'context_tags' in source_metadata:
                context_tags = source_metadata['context_tags']
            elif mem.get('context_tags'):
                context_tags = mem.get('context_tags')
            
            # Get updated_at if available, fallback to created_at
            updated_at = mem.get('updated_at')
            if updated_at and hasattr(updated_at, 'isoformat'):
                updated_at_str = updated_at.isoformat()
            elif updated_at:
                updated_at_str = str(updated_at)
            else:
                created_at = mem.get('created_at', '')
                updated_at_str = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            
            formatted_mem = {
                "id": str(mem.get('id', '')),
                "content": mem.get('content', ''),
                "content_type": mem.get('content_type', 'conversation'),
                "title": mem.get('title', ''),
                "project_id": project_id or (source_metadata.get('project_id', '') if isinstance(source_metadata, dict) else '') or mem.get('project_id', ''),
                "conversation_id": source_metadata.get('conversation_id', '') if isinstance(source_metadata, dict) else '',
                "created_at": mem.get('created_at', '').isoformat() if hasattr(mem.get('created_at'), 'isoformat') else str(mem.get('created_at', '')),
                "updated_at": updated_at_str,  # Include updated_at for sorting by last modified
                "context_tags": context_tags,  # Include context_tags for filtering
                "similarity_score": mem.get('similarity_score'),  # Include if from semantic search
                "source_metadata": source_metadata  # Include source_metadata so frontend can identify drafts
            }
            formatted_memories.append(formatted_mem)
        
        return jsonify({
            "memories": formatted_memories,
            "count": len(formatted_memories),
            "has_semantic_search": bool(search_query)
        })
        
    except Exception as e:
        print(f"⚠️ Error fetching memories: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/memories/facts', methods=['GET'])
@require_api_key
def search_memories_facts():
    """
    Semantic search for facts in memories
    Used by the fact retrieval feature in MemoriesTab
    """
    if not HAS_DATABASE_APIS or not memory_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        query = request.args.get('query', '').strip()
        project_id = request.args.get('project_id')
        
        if not query:
            return jsonify({"results": []})
        
        # Use semantic search for fact retrieval
        results = memory_api.recall_memories(
            user_id=uid,
            query=query,
            project_id=project_id,
            limit=10,
            context_type="general"
        )
        
        # Format for frontend
        formatted_results = []
        for mem in results:
            formatted_results.append({
                "id": str(mem.get('id', '')),
                "content": mem.get('content', ''),
                "title": mem.get('title', ''),
                "similarity_score": mem.get('similarity_score', 0.0)
            })
        
        return jsonify({"results": formatted_results})
        
    except Exception as e:
        print(f"⚠️ Error searching facts: {e}")
        return jsonify({"error": str(e), "results": []}), 500

@app.route('/api/debug/memory', methods=['GET'])
def get_memory_reading():
    """
    Get current memory usage statistics and diagnostics
    Returns detailed memory state information
    """
    try:
        monitor = get_memory_monitor()
        if monitor is None:
            return jsonify({
                "error": "Memory monitor not available (psutil not installed)"
            }), 503
        reading = monitor.get_current_reading()
        
        return jsonify({
            "success": True,
            "reading": reading
        })
    except Exception as e:
        return jsonify({
            "error": f"Error getting memory reading: {str(e)}"
        }), 500

@app.route('/api/debug/memory/top-operations', methods=['GET'])
def get_top_memory_operations():
    """Get operations consuming the most memory"""
    try:
        monitor = get_memory_monitor()
        if monitor is None:
            return jsonify({
                "error": "Memory monitor not available (psutil not installed)"
            }), 503
        limit = request.args.get('limit', 10, type=int)
        top_ops = monitor.get_top_memory_operations(limit)
        
        return jsonify({
            "success": True,
            "operations": top_ops
        })
    except Exception as e:
        return jsonify({
            "error": f"Error getting top operations: {str(e)}"
        }), 500

@app.route('/api/transcribe/token', methods=['GET'])
@require_api_key
def get_transcribe_token():
    """
    Get AssemblyAI temporary token for frontend real-time streaming.
    AssemblyAI requires tokens (not API keys) for browser-based streaming.
    Returns empty string if not configured.
    """
    if not ASSEMBLYAI_API_KEY:
        return jsonify({"token": "", "provider": "", "error": "AssemblyAI API key not configured"}), 200
    
    try:
        import assemblyai as aai
        from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions
        
        # Generate a temporary token using the Python SDK's StreamingClient
        # This is the recommended way for Universal Streaming API
        try:
            client = StreamingClient(
                StreamingClientOptions(
                    api_key=ASSEMBLYAI_API_KEY,
                    api_host="streaming.assemblyai.com"
                )
            )
            
            # Generate temporary token (expires in 5 minutes = 300 seconds)
            token_response = client.create_temporary_token(expires_in_seconds=300)
            
            # The response should be a string token
            if isinstance(token_response, str):
                token = token_response
            elif hasattr(token_response, 'token'):
                token = token_response.token
            elif hasattr(token_response, 'get'):
                token = token_response.get('token', '')
            else:
                token = str(token_response)
            
            if token:
                print(f"✅ Generated AssemblyAI streaming token using Python SDK (expires in 5 minutes)")
                return jsonify({
                    "token": token,
                    "provider": "assemblyai"
                })
            else:
                error_msg = "Token generation returned empty token"
        except Exception as sdk_error:
            error_msg = f"Python SDK token generation failed: {str(sdk_error)}"
            print(f"⚠️  {error_msg}")
        
        # Fallback to direct API call if SDK fails
        import requests
        print("⚠️  Falling back to direct API call for token generation")
        token_response = requests.post(
            "https://api.assemblyai.com/v2/realtime/token",
            headers={
                "authorization": ASSEMBLYAI_API_KEY,  # API key directly, no Bearer prefix
                "content-type": "application/json"
            },
            json={"expires_in": 300},
            timeout=10
        )
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            token = token_data.get("token", "")
            if token:
                print(f"✅ Generated AssemblyAI streaming token via API (expires in 5 minutes)")
                return jsonify({
                    "token": token,
                    "provider": "assemblyai"
                })
            else:
                error_msg = token_data.get("error", "Token generation failed - no token in response")
        else:
            error_msg = f"Token generation failed with status {token_response.status_code}"
            try:
                error_data = token_response.json()
                error_msg = error_data.get("error", error_data.get("message", error_msg))
            except:
                error_msg = f"{error_msg}: {token_response.text[:200]}"
        
        print(f"⚠️  {error_msg}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200
            
    except Exception as sdk_error:
        # If SDK fails, try direct API call as fallback
        import requests
        try:
            # Try new Universal Streaming API endpoint first
            token_response = requests.post(
                "https://api.assemblyai.com/v2/streaming/token",
                headers={
                    "authorization": ASSEMBLYAI_API_KEY,
                    "content-type": "application/json"
                },
                json={"expires_in": 300},
                timeout=10
            )
            
            # If that fails, try the old endpoint
            if token_response.status_code != 200:
                token_response = requests.post(
                    "https://api.assemblyai.com/v2/realtime/token",
                    headers={
                        "authorization": ASSEMBLYAI_API_KEY,
                        "content-type": "application/json"
                    },
                    json={"expires_in": 300},
                    timeout=10
                )
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                token = token_data.get("token", "")
                if token:
                    return jsonify({"token": token, "provider": "assemblyai"})
                else:
                    error_msg = token_data.get("error", "Token generation failed")
            else:
                error_msg = f"AssemblyAI API error (status {token_response.status_code})"
                try:
                    error_data = token_response.json()
                    error_msg = error_data.get("error", error_data.get("message", error_msg))
                except:
                    pass
        except Exception as api_error:
            error_msg = f"Failed to generate token: {str(api_error)}"
        
        print(f"⚠️  {error_msg}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200
            
    except requests.exceptions.Timeout:
        error_msg = "AssemblyAI API request timed out"
        print(f"⚠️  {error_msg}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error connecting to AssemblyAI: {str(e)}"
        print(f"⚠️  {error_msg}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200
    except ImportError:
        error_msg = "requests library not available"
        print(f"⚠️  {error_msg}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error generating AssemblyAI token: {str(e)}"
        print(f"⚠️  {error_msg}")
        print(f"⚠️  Traceback: {traceback.format_exc()}")
        return jsonify({
            "token": "",
            "provider": "",
            "error": error_msg
        }), 200

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio file using AssemblyAI (if API key set) or local Whisper (fallback).
    For real-time streaming, use AssemblyAI JavaScript SDK in frontend with /api/transcribe/token.
    """
    # Check if AssemblyAI is configured
    if ASSEMBLYAI_API_KEY:
        return transcribe_with_assemblyai()
    else:
        # Fall back to Whisper
        return transcribe_with_whisper()

def transcribe_with_assemblyai():
    """Transcribe audio using AssemblyAI API (high-quality, paid service)"""
    try:
        import assemblyai as aai
        
        # Get correlation ID
        try:
            from flask import g
            correlation_id = getattr(g, 'correlation_id', 'no-request') if hasattr(g, 'correlation_id') else 'no-request'
        except:
            correlation_id = 'no-request'
        
        # Check if audio file was uploaded
        if 'audio_file' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio_file']
        if not audio_file or audio_file.filename == '':
            return jsonify({"error": "No audio file provided"}), 400
        
        print(f"🎤 [{correlation_id}] Transcribing with AssemblyAI...")
        
        # Configure AssemblyAI
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        
        # Create transcriber
        transcriber = aai.Transcriber()
        
        # Save uploaded file temporarily
        import tempfile
        import os
        temp_file_path = None
        
        try:
            suffix = os.path.splitext(audio_file.filename or "audio")[1] or '.webm'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file_path = temp_file.name
            audio_file.save(temp_file_path)
            temp_file.close()
            
            file_size = os.path.getsize(temp_file_path)
            print(f"📁 [{correlation_id}] Saved audio file: {file_size} bytes")
            
            # Transcribe with AssemblyAI
            config = aai.TranscriptionConfig(
                language_code="en",
                punctuate=True,
                format_text=True  # Better formatting for writing
            )
            
            transcript = transcriber.transcribe(temp_file_path, config=config)
            
            if transcript.status == aai.TranscriptStatus.error:
                error_msg = f"AssemblyAI transcription error: {transcript.error}"
                print(f"❌ [{correlation_id}] {error_msg}")
                return jsonify({"error": error_msg}), 500
            
            transcription = transcript.text.strip() if transcript.text else ""
            
            if not transcription:
                print(f"⚠️  [{correlation_id}] AssemblyAI returned empty transcription")
                return jsonify({"text": "", "error": "No speech detected in audio file"})
            
            print(f"✅ [{correlation_id}] AssemblyAI transcription complete: {len(transcription)} characters")
            return jsonify({"text": transcription})
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"🗑️  [{correlation_id}] Cleaned up temporary file")
                except Exception as e:
                    print(f"⚠️  [{correlation_id}] Failed to delete temp file: {e}")
                    
    except ImportError:
        # AssemblyAI not installed, fall back to Whisper
        print("⚠️  AssemblyAI not installed, falling back to Whisper")
        return transcribe_with_whisper()
    except Exception as e:
        import traceback
        error_detail = f"AssemblyAI transcription error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ AssemblyAI error: {error_detail}")
        # Fall back to Whisper on error
        print("⚠️  Falling back to Whisper...")
        return transcribe_with_whisper()

def transcribe_with_whisper():
    """
    Transcribe audio file using local Whisper model (fallback).
    Accepts WAV, MP3, WebM, and other audio formats supported by Whisper.
    This endpoint proxies to the FastAPI backend or uses local Whisper.
    """
    # Get correlation ID safely
    try:
        from flask import g
        correlation_id = getattr(g, 'correlation_id', 'no-request') if hasattr(g, 'correlation_id') else 'no-request'
    except:
        correlation_id = 'no-request'
    
    # Use debug logger if available
    if DEBUG_LOGGING_ENABLED and debug_logger:
        debug_logger.info(f"Request: POST /api/transcribe", context={"correlation_id": correlation_id})
    
    try:
        # Check if audio file was uploaded
        if 'audio_file' not in request.files:
            error_msg = "No audio file provided"
            if DEBUG_LOGGING_ENABLED and debug_logger:
                debug_logger.error("Transcribe: No audio file", context={"correlation_id": correlation_id})
            return jsonify({"error": error_msg}), 400
        
        audio_file = request.files['audio_file']
        if not audio_file or audio_file.filename == '':
            error_msg = "No audio file provided"
            if DEBUG_LOGGING_ENABLED and debug_logger:
                debug_logger.error("Transcribe: Empty audio file", context={"correlation_id": correlation_id})
            return jsonify({"error": error_msg}), 400
        
        # Save uploaded file to temporary location
        import tempfile
        import os
        import sys
        temp_file_path = None
        
        try:
            # Create temporary file with proper extension
            suffix = os.path.splitext(audio_file.filename or "audio")[1] or '.webm'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file_path = temp_file.name
            audio_file.save(temp_file_path)
            temp_file.close()
            
            file_size = os.path.getsize(temp_file_path)
            print(f"📁 [{correlation_id}] Saved audio file to: {temp_file_path} ({file_size} bytes)")
            
            if DEBUG_LOGGING_ENABLED and debug_logger:
                debug_logger.info("Audio file saved", context={
                    "correlation_id": correlation_id,
                    "file_path": temp_file_path,
                    "file_size": file_size,
                    "suffix": suffix
                })
            
            # Check ffmpeg availability (required by Whisper)
            # Try multiple paths since PATH might not be set correctly in Flask process
            import subprocess
            import shutil
            ffmpeg_available = False
            ffmpeg_path = None
            
            # Try to find ffmpeg in common locations
            possible_paths = [
                'ffmpeg',  # In PATH
                '/opt/homebrew/bin/ffmpeg',  # Homebrew on Apple Silicon
                '/usr/local/bin/ffmpeg',  # Homebrew on Intel Mac
                '/usr/bin/ffmpeg',  # System installation
            ]
            
            for path in possible_paths:
                try:
                    # Use shutil.which first (respects PATH)
                    if path == 'ffmpeg':
                        ffmpeg_path = shutil.which('ffmpeg')
                        if ffmpeg_path:
                            check_path = ffmpeg_path
                        else:
                            continue
                    else:
                        check_path = path
                        if not os.path.exists(check_path):
                            continue
                    
                    # Test if it works
                    result = subprocess.run(
                        [check_path, '-version'], 
                        capture_output=True, 
                        timeout=2,
                        env=os.environ.copy()  # Preserve environment
                    )
                    if result.returncode == 0:
                        ffmpeg_available = True
                        ffmpeg_path = check_path
                        print(f"✅ [{correlation_id}] Found FFmpeg at: {ffmpeg_path}")
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                    continue
            
            if not ffmpeg_available:
                error_msg = "FFmpeg not found. Please install: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
                print(f"❌ [{correlation_id}] {error_msg}")
                print(f"❌ [{correlation_id}] Checked paths: {possible_paths}")
                if DEBUG_LOGGING_ENABLED and debug_logger:
                    debug_logger.error("FFmpeg not available", context={
                        "correlation_id": correlation_id,
                        "checked_paths": possible_paths
                    })
                return jsonify({"error": error_msg}), 500
            
            # Use subprocess-based Whisper worker to isolate crashes
            # This prevents Whisper crashes from killing the Flask server
            # No need to import whisper in main process - it runs in subprocess
            print(f"🔄 [{correlation_id}] Using subprocess-based Whisper transcription (crash-isolated)")
            
            # Transcribe audio using subprocess to isolate crashes
            print(f"🎤 [{correlation_id}] Transcribing audio using subprocess worker...")
            
            if DEBUG_LOGGING_ENABLED and debug_logger:
                debug_logger.info("Starting transcription", context={
                    "correlation_id": correlation_id,
                    "file_path": temp_file_path,
                    "file_size": file_size,
                    "method": "subprocess"
                })
            
            try:
                # Use subprocess to run Whisper in isolation
                # This prevents crashes from killing the Flask server
                import subprocess
                import json as json_module
                
                # Get path to whisper_worker.py
                # grace_api.py is in project root, so backend/whisper_worker.py should be relative
                script_dir = os.path.dirname(os.path.abspath(__file__))
                worker_script = os.path.join(script_dir, "backend", "whisper_worker.py")
                
                # Try multiple possible paths
                possible_paths = [
                    worker_script,  # backend/whisper_worker.py relative to grace_api.py
                    os.path.join(os.path.dirname(script_dir), "backend", "whisper_worker.py"),  # If grace_api.py is in subdirectory
                    os.path.join(script_dir, "whisper_worker.py"),  # Same directory as grace_api.py
                ]
                
                worker_script = None
                for path in possible_paths:
                    if os.path.exists(path):
                        worker_script = path
                        break
                
                if not worker_script or not os.path.exists(worker_script):
                    error_msg = f"Whisper worker script not found. Tried: {possible_paths}"
                    print(f"❌ [{correlation_id}] {error_msg}")
                    raise Exception(error_msg)
                
                print(f"✅ [{correlation_id}] Found Whisper worker at: {worker_script}")
                
                print(f"🔄 [{correlation_id}] Running Whisper in subprocess: {worker_script}")
                
                # Run whisper_worker.py as subprocess
                # Use timeout to prevent hanging (60 seconds should be enough)
                # Run from project root directory
                project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) != os.path.basename(os.getcwd()) else os.getcwd()
                
                print(f"🔄 [{correlation_id}] Running from: {project_root}")
                print(f"🔄 [{correlation_id}] Command: {sys.executable} {worker_script} {temp_file_path} tiny")
                
                process = subprocess.Popen(
                    [sys.executable, worker_script, temp_file_path, "tiny"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=project_root  # Run from project root
                )
                
                try:
                    stdout, stderr = process.communicate(timeout=60)
                    
                    # Log stderr (progress messages and errors)
                    if stderr:
                        print(f"📝 [{correlation_id}] Whisper stderr output:")
                        # Print full stderr for debugging
                        for line in stderr.split('\n'):
                            if line.strip():
                                print(f"   {line}")
                    
                    if process.returncode != 0:
                        # Get full error details
                        error_msg = f"Whisper subprocess failed with code {process.returncode}"
                        if stderr:
                            # Get the actual error message (usually at the end)
                            error_lines = [line for line in stderr.split('\n') if line.strip() and ('error' in line.lower() or 'failed' in line.lower() or 'invalid' in line.lower())]
                            if error_lines:
                                error_msg += f": {error_lines[-1]}"
                            else:
                                error_msg += f": {stderr[-1000:]}"  # Last 1000 chars if no specific error line
                        
                        # Also check stdout for JSON error
                        if stdout:
                            try:
                                result = json_module.loads(stdout)
                                if "error" in result:
                                    error_msg = result["error"]
                            except:
                                pass
                        
                        print(f"❌ [{correlation_id}] Full error: {error_msg}")
                        raise Exception(error_msg)
                    
                    # Parse JSON result from stdout
                    result = json_module.loads(stdout)
                    
                    if "error" in result:
                        raise Exception(result["error"])
                    
                    transcription = result.get("text", "").strip()
                    print(f"✅ [{correlation_id}] Transcription completed: {len(transcription)} characters")
                    
                    # Ensure subprocess is fully terminated and cleaned up
                    try:
                        process.wait(timeout=1)  # Wait for process to fully exit
                    except:
                        pass  # Process already exited
                    
                    # Explicitly close pipes to free resources
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                    
                except subprocess.TimeoutExpired:
                    # Force kill and cleanup on timeout
                    process.kill()
                    process.wait(timeout=5)
                    # Close pipes
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                    raise Exception("Whisper transcription timed out after 60 seconds")
                
                except json_module.JSONDecodeError as e:
                    # Clean up process on error
                    try:
                        if process.poll() is None:  # Still running
                            process.kill()
                            process.wait(timeout=5)
                        if process.stdout:
                            process.stdout.close()
                        if process.stderr:
                            process.stderr.close()
                    except:
                        pass
                    raise Exception(f"Failed to parse Whisper output: {str(e)}. Output: {stdout[:200]}")
                
                if not transcription:
                    print(f"⚠️  [{correlation_id}] Whisper returned empty transcription")
                    if DEBUG_LOGGING_ENABLED and debug_logger:
                        debug_logger.warning("Empty transcription", context={"correlation_id": correlation_id})
                    return jsonify({"text": "", "error": "No speech detected in audio file"})
                
                print(f"✅ [{correlation_id}] Transcription complete: {len(transcription)} characters")
                
                if DEBUG_LOGGING_ENABLED and debug_logger:
                    debug_logger.info("Transcription complete", context={
                        "correlation_id": correlation_id,
                        "transcription_length": len(transcription),
                        "preview": transcription[:100]
                    })
                
                return jsonify({"text": transcription})
                
            except Exception as transcribe_err:
                import traceback
                error_detail = f"Error during transcription: {str(transcribe_err)}\n{traceback.format_exc()}"
                print(f"❌ [{correlation_id}] Transcription error: {error_detail}")
                
                if DEBUG_LOGGING_ENABLED and debug_logger:
                    debug_logger.error("Transcription failed", context={
                        "correlation_id": correlation_id,
                        "error": str(transcribe_err),
                        "traceback": traceback.format_exc()
                    })
                
                return jsonify({"error": f"Error transcribing audio: {str(transcribe_err)}"}), 500
            
        except Exception as e:
            import traceback
            error_detail = f"Error processing audio file: {str(e)}\n{traceback.format_exc()}"
            print(f"❌ [{correlation_id}] Processing error: {error_detail}")
            
            if DEBUG_LOGGING_ENABLED and debug_logger:
                debug_logger.error("Audio processing error", context={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
            
            return jsonify({"error": f"Error processing audio: {str(e)}"}), 500
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"🗑️  [{correlation_id}] Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    print(f"⚠️  [{correlation_id}] Failed to delete temporary file: {e}")
        
    except Exception as e:
        import traceback
        error_detail = f"Transcribe endpoint error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ [{correlation_id}] Endpoint error: {error_detail}")
        
        if DEBUG_LOGGING_ENABLED and debug_logger:
            debug_logger.error("Transcribe endpoint exception", context={
                "correlation_id": correlation_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        return jsonify({"error": str(e)}), 500

# Whisper is now run in subprocess (see whisper_worker.py)
# No global model cache needed - each transcription runs in isolated subprocess

@app.route('/api/debug/memory/recent-operations', methods=['GET'])
def get_recent_memory_operations():
    """Get recent memory tracking records"""
    try:
        monitor = get_memory_monitor()
        if monitor is None:
            return jsonify({
                "error": "Memory monitor not available (psutil not installed)"
            }), 503
        limit = request.args.get('limit', 20, type=int)
        operations = monitor.get_recent_operations(limit)
        
        return jsonify({
            "success": True,
            "operations": operations,
            "count": len(operations)
        })
    except Exception as e:
        return jsonify({
            "error": f"Error getting recent operations: {str(e)}"
        }), 500

@app.route('/api/debug/memory/diagnose-leak', methods=['GET'])
def diagnose_memory_leak():
    """Diagnose potential memory leaks using standard analysis"""
    try:
        monitor = get_memory_monitor()
        if monitor is None:
            return jsonify({
                "error": "Memory monitor not available (psutil not installed)"
            }), 503
        diagnosis = monitor.diagnose_leak()
        
        return jsonify({
            "success": True,
            "diagnosis": diagnosis
        })
    except Exception as e:
        return jsonify({
            "error": f"Error diagnosing memory leak: {str(e)}"
        }), 500

@app.route('/api/database/health', methods=['GET'])
def database_health_check():
    """Database connection pool health check endpoint"""
    try:
        if not HAS_DATABASE_APIS or not conversation_api:
            return jsonify({
                "status": "disabled",
                "message": "Database APIs not initialized",
                "has_database_apis": False
            })

        pool_manager = getattr(conversation_api, 'pool_manager', None)
        if not pool_manager:
            return jsonify({
                "status": "error",
                "message": "No pool_manager on conversation_api",
                "has_database_apis": True
            })

        stats = pool_manager.get_stats()
        
        # Perform a quick health check
        try:
            with pool_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "pool_stats": stats,
                "has_database_apis": True
            })
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "database": "connection_failed",
                "error": str(e),
                "pool_stats": stats,
                "has_database_apis": True
            })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "has_database_apis": HAS_DATABASE_APIS
        })


# DISABLED: AI pattern cleaning endpoint - feature removed per user request
# @app.route('/api/clean-ai-patterns', methods=['POST'])
# @require_api_key
# def clean_ai_patterns():
#     """Rewrite text to remove AI writing patterns using LLM"""
#     try:
#         data = request.get_json()
#         text = data.get('text', '')
#
#         if not text:
#             return jsonify({"error": "No text provided"}), 400
#
#         # Use LLM to intelligently rewrite the text
#         rewrite_prompt = f"""Rewrite the following text to remove all AI writing patterns while preserving the meaning and content.
#
# CRITICAL REQUIREMENTS:
# - Remove em dashes (—) - use commas, semicolons, or periods instead
# - Remove AI buzzwords: delve, leverage, robust, utilize, facilitate, optimal, cutting-edge, game-changer, revolutionize, seamless
# - Remove filler phrases: "it's important to note", "it's worth noting", "notably", "as such", "in conclusion", "to summarize"
# - Remove weak modifiers: very, really, quite, extremely, rather, fairly, pretty, somewhat
# - Remove filler words: just, actually, basically, literally, simply
# - Remove hedging: perhaps, possibly, maybe, might, "could potentially", "it seems"
# - Remove redundant phrases: past history, future plans, added bonus, end result
# - Remove clichés: think outside the box, low-hanging fruit, circle back
# - Use active voice instead of passive voice
# - Use specific nouns and verbs, not generic ones
# - Vary sentence length and structure
# - Keep paragraphs under 7 sentences
#
# OUTPUT ONLY THE REWRITTEN TEXT. Do not add commentary, explanations, or labels like "Here's the rewritten version:". Just provide the clean text.
#
# TEXT TO REWRITE:
# {text}"""
#
#         # Call LLM to rewrite
#         payload = {
#             "model": GRACE_CONFIG["model"],
#             "messages": [
#                 {"role": "system", "content": GRACE_CONFIG["system_persona"]},
#                 {"role": "user", "content": rewrite_prompt}
#             ],
#             "temperature": 0.4  # Lower temp for more consistent rewrites
#         }
#
#         if GRACE_CONFIG["max_tokens"]:
#             payload["max_tokens"] = GRACE_CONFIG["max_tokens"]
#
#         response = requests.post(LM_API_URL, json=payload, timeout=120)
#         response.raise_for_status()
#         rewritten_text = response.json()["choices"][0]["message"]["content"].strip()
#
#         return jsonify({
#             "original": text,
#             "cleaned": rewritten_text,
#             "rewritten": True
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route('/api/teacher/query', methods=['POST'])
@require_api_key
def teacher_query():
    """Teacher/Editor chat endpoint with full Grace reasoning"""
    import time
    request_start = time.time()
    question = ""
    result = ""
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        context = data.get('context', '')
        include_memory = data.get('includeMemory', data.get('include_memory', True))
        temperature = data.get('temperature', 0.45)
        editorial = data.get('editorial', {
            'enabled': True,
            'detectChatGPTPatterns': True,
            'stance': 'collaborative',
            'voicePreservationPriority': 'high',
            'structuralCritique': False,
            'askObjectiveFirst': True
        })

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Build memory context if requested
        memory_context = ""
        activated_context = ""
        retrieved_context = ""
        
        if include_memory:
            try:
                # Get user_id for memory recall (needed for both systems)
                uid = get_user_id_from_header()
                project_id = data.get('project_id') or (data.get('metadata', {}).get('project_id') if isinstance(data.get('metadata'), dict) else None)
                conversation_id = data.get('conversation_id')
                
                # STEP 1: Context Detection - Detect entities (characters, topics) from user input
                try:
                    from backend.context_detector import ContextDetector
                    context_detector = ContextDetector()
                    
                    # Get recent conversation history for context detection
                    # MEMORY SAFETY: Limit to last 5 messages to prevent memory spikes
                    conversation_history = []
                    if conversation_id and HAS_DATABASE_APIS and conversation_api and uid:
                        try:
                            conversation_history = conversation_api.get_messages(
                                conversation_id=conversation_id,
                                user_id=uid,
                                limit=5  # Reduced from 10 to 5 for memory safety
                            )
                        except:
                            pass
                    
                    # Detect entities
                    detected_entities = context_detector.detect_context_entities(
                        user_input=question,
                        conversation_history=conversation_history
                    )
                    
                    # STEP 2: Grace prompts user for context retrieval (NOT automatic)
                    # Grace does NOT automatically retrieve context from Milvus
                    # Instead, Grace will ask the user for information about characters, plot, tagged elements, etc.
                    # The Keeper handles automatic context retrieval via Milvus
                    #
                    # MEMORY OPTIMIZATION: This approach significantly reduces memory load:
                    # - Instead of loading ALL character context, plot points, etc. into context window (thousands of tokens)
                    # - Grace asks "what are we working on?" → user says "Marcus" (tagged character)
                    # - Grace then asks for specific context about Marcus → user provides only what's needed
                    # - Result: Much smaller context window, fewer tokens, lower memory usage
                    # - Tagging enables efficient filtering: when "Marcus" is tagged, The Keeper can query Milvus
                    #   with filter like 'character_names like "%Marcus%"' to get ONLY Marcus-related content
                    #
                    # PROMPT ENGINEERING FOR MILVUS:
                    # Grace's prompts should be designed to extract structured information that maps to Milvus queries:
                    # - Character names → 'character_names like "%[name]%"' filter
                    # - Tag paths → 'tag_path like "%[path]%"' filter  
                    # - Plot elements → semantic search with plot-related tags
                    # - Project context → 'project_id == "[id]"' filter
                    #
                    # ARCHITECTURE CLARIFICATION:
                    # Milvus is NOT an intermediary to PostgreSQL - they work together in HYBRID SEARCH:
                    # - Milvus: Vector database for semantic search (finds similar content by meaning)
                    # - PostgreSQL: Structured database for full content, metadata, complex queries
                    # - Both are queried in parallel, results are combined
                    # - Milvus stores embeddings + minimal metadata (for filtering)
                    # - PostgreSQL stores full content + rich metadata (tags, timestamps, etc.)
                    # - They're linked via IDs (memory_id, milvus_point_id)
                    # - This is "hybrid search" not "Milvus → PostgreSQL"
                    #
                    # Example flow (engineered for Milvus):
                    # 1. Grace: "What are we working on?" (extracts project context)
                    # 2. User: "Marcus" (tagged character name - maps to character_names filter)
                    # 3. Grace: "Can you tell me about Marcus's role in this scene?" (extracts character + scene tags)
                    # 4. User: Provides specific context (only what's needed)
                    # 5. Grace uses that focused context for literary device analysis
                    # → When user mentions "Marcus", that name can be used to query Milvus with:
                    #    filter_expr: 'character_names like "%Marcus%" AND project_id == "[project_id]"'
                    # → Much more efficient than auto-loading all Marcus context (could be 10K+ tokens)
                    
                    # Detect entities for Grace to reference in her prompts to the user
                    if detected_entities and any(detected_entities.values()):
                        character_names = detected_entities.get('characters', [])
                        topics = detected_entities.get('work_focus', [])
                        emotional_concepts = detected_entities.get('emotional_concepts', [])
                        dominant_emotion = detected_entities.get('dominant_emotion')
                        emotional_intensity = detected_entities.get('emotional_intensity', 0.0)
                        
                        if character_names or topics:
                            print(f"📝 Grace detected entities - will prompt user for context: characters={character_names}, topics={topics}")
                            print(f"   💡 Memory optimization: Prompting user instead of auto-loading reduces context window size")
                            # Grace will ask the user about these in her response, not retrieve automatically
                        
                        # Enhance context with emotional information for editorial suggestions
                        if emotional_concepts or dominant_emotion:
                            emotional_context = ""
                            if emotional_concepts:
                                emotional_context += f"\n\n## Emotional Context Detected:\n"
                                emotional_context += f"- Emotional concepts: {', '.join(emotional_concepts)}\n"
                            if dominant_emotion:
                                emotional_context += f"- Dominant emotion: {dominant_emotion}\n"
                            if emotional_intensity > 0.5:
                                emotional_context += f"- High emotional intensity detected ({emotional_intensity:.2f})\n"
                            
                            # Add emotional context to the context parameter for Grace's editorial analysis
                            if emotional_context:
                                context = (context or "") + emotional_context
                                print(f"📊 Added emotional context to editorial analysis: {emotional_concepts}")
                    
                    # STEP 3: Grace does NOT automatically retrieve context
                    # Grace prompts the user for context about characters, plot, tagged elements
                    # The user provides context, which Grace then uses for literary device analysis
                
                except Exception as context_err:
                    print(f"⚠️ Context detection failed: {context_err}")
                    import traceback
                    traceback.print_exc()
                
                # STEP 4: Grace uses memory system but prompts user for context about characters/tagged elements
                # Grace does NOT automatically retrieve from Milvus - she asks the user
                # The Keeper handles automatic Milvus retrieval
                
                # Grace can still use the memory system for general context (promoted memories)
                # But for characters and tagged elements, Grace prompts the user
                if False:  # Disabled automatic context activation
                    pass
                else:
                    # Fallback to existing memory system
                    # Priority 1: Use PostgreSQL-based memory system if available
                    memories = []
                    if HAS_MEMORY_SYSTEM and memory_api and uid:
                        try:
                            # Extract historical context from editor content (context parameter)
                            # This allows Grace to find related memories by historical periods, movements, events
                            historical_periods = None
                            historical_movements = None
                            historical_events = None
                            
                            if context and context.strip():
                                try:
                                    from backend.tag_extractor import TagExtractor
                                    tag_extractor = TagExtractor(query_llm)
                                    historical_tags = tag_extractor.extract_historical_context_tags(context)
                                    historical_periods = historical_tags.get('periods', [])
                                    historical_movements = historical_tags.get('movements', [])
                                    historical_events = historical_tags.get('events', [])
                                    
                                    if historical_periods or historical_movements or historical_events:
                                        print(f"🏛️  Extracted historical context from editor: periods={historical_periods}, movements={historical_movements}, events={historical_events}")
                                except Exception as tag_err:
                                    print(f"⚠️  Failed to extract historical context (non-blocking): {tag_err}")
                                    # Continue without historical tags
                            
                            # Recall memories from database with historical context filtering
                            memories = memory_api.recall_memories(
                                user_id=uid,
                                query=question,
                                project_id=project_id,
                                limit=5,  # Increased from 3 to get more context
                                historical_periods=historical_periods,
                                historical_movements=historical_movements,
                                historical_events=historical_events
                            )
                        except Exception as pg_err:
                            print(f"⚠️ PostgreSQL memory recall failed: {pg_err}")
                            memories = []
                    
                    # Format memories from PostgreSQL system
                    if memories:
                        memory_context = "## Relevant Context from Previous Interactions:\n"
                        for mem in memories:
                            content_preview = mem.get('content', '')[:200] if mem.get('content') else ''
                            source_type = mem.get('source_type', 'unknown')
                            memory_context += f"- [{source_type}] {content_preview}...\n"
                    
                    # Fallback: Use FAISS-based memory if PostgreSQL system not available or returned no results
                    if not memory_context and HAS_SENTENCE_TRANSFORMERS:
                        try:
                            # Try legacy FAISS-based memory retrieval
                            faiss_memory_context = retrieve_memory_context(question, top_k=3)
                            if faiss_memory_context:
                                memory_context = f"## Relevant Context from Previous Interactions:\n{faiss_memory_context}\n"
                        except Exception as faiss_err:
                            print(f"⚠️ FAISS memory recall failed: {faiss_err}")
            except Exception as mem_err:
                print(f"⚠️ Memory recall failed: {mem_err}")
                import traceback
                traceback.print_exc()

        # Fine-tuned model handles persona and reasoning
        # MEMORY SAFETY: Limit context size to prevent memory spikes
        MAX_CONTEXT_CHARS = 50000  # ~12K tokens (safe for 32K context window)
        MAX_MEMORY_CONTEXT_CHARS = 10000  # ~2.5K tokens for memory
        
        # Truncate context if too large
        if len(context) > MAX_CONTEXT_CHARS:
            print(f"⚠️ Context too large ({len(context)} chars), truncating to {MAX_CONTEXT_CHARS} chars")
            context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated due to size limits]"
        
        # Truncate memory context if too large
        if len(memory_context) > MAX_MEMORY_CONTEXT_CHARS:
            print(f"⚠️ Memory context too large ({len(memory_context)} chars), truncating to {MAX_MEMORY_CONTEXT_CHARS} chars")
            memory_context = memory_context[:MAX_MEMORY_CONTEXT_CHARS] + "\n\n[Memory context truncated]"
        
        print(f"🟢 Grace query routing to Grace model on port 8080 (Keeper uses port 8081)")
        print(f"   Question: {question[:100]}...")
        print(f"   Context length: {len(context)} chars (max: {MAX_CONTEXT_CHARS})")
        print(f"   Memory context length: {len(memory_context)} chars (max: {MAX_MEMORY_CONTEXT_CHARS})")
        
        result = query_llm(
            system="",
            user_input=question + (f"\n\nContext: {context}" if context else ""),
            memory_context=memory_context,
            temperature=temperature
        )
        
        print(f"✅ Grace query completed (Grace model on port 8080)")

        # Record usage for billing
        try:
            uid = get_user_id_from_header()
            if uid:
                record_usage(uid, 'query', 1)
        except Exception as usage_err:
            print(f"⚠️ Failed to record usage: {usage_err}")

        # Update conversation title if conversation_id is provided
        # This allows the model to save/update the conversation name in the database
        conversation_id = data.get('conversation_id')
        if conversation_id and HAS_DATABASE_APIS and conversation_api:
            try:
                uid = get_user_id_from_header()
                if uid:
                    # Get current conversation to check if title needs updating
                    conv = conversation_api.get_conversation(conversation_id, uid)
                    if conv:
                        # Generate a better title from the first question if title is generic
                        current_title = conv.get('title', '')
                        
                        # Check if title needs updating (handle both Grace and Keeper prefixes)
                        is_generic_title = (
                            not current_title or
                            current_title == 'New Chat' or
                            current_title == 'Untitled Conversation' or
                            current_title == 'New Conversation' or
                            current_title.startswith('Keeper Chat: New Chat') or
                            current_title.startswith('Keeper Chat: Untitled')
                        )
                        
                        # Also check if title is just the first part of the question (already set but incomplete)
                        is_incomplete_title = (
                            current_title and 
                            len(current_title) < 20 and 
                            question.strip().lower().startswith(current_title.lower())
                        )
                        
                        needs_title_update = is_generic_title or is_incomplete_title
                        
                        if needs_title_update:
                            # Get all messages from the conversation to generate title from chat content
                            messages = conversation_api.get_messages(conversation_id, uid, limit=10)
                            
                            # Combine all message content (questions and responses) to create title
                            chat_content = ""
                            for msg in messages:
                                content = msg.get('content', '')
                                if content:
                                    chat_content += content + " "
                            
                            # Use first 25 characters of combined chat content
                            if chat_content:
                                chat_content_clean = chat_content.strip()
                                new_title = chat_content_clean[:25]
                                if len(chat_content_clean) > 25:
                                    # Don't cut words - find last space before 25 chars
                                    if ' ' in new_title:
                                        new_title = new_title.rsplit(' ', 1)[0]
                                    new_title = new_title + '...'
                            else:
                                # Fallback to question if no messages found
                                question_clean = question.strip() if question else ""
                                new_title = question_clean[:25] if question_clean else "New Chat"
                                if len(question_clean) > 25:
                                    if ' ' in new_title:
                                        new_title = new_title.rsplit(' ', 1)[0]
                                    new_title = new_title + '...'
                            
                            # Preserve "Keeper Chat:" prefix if it exists
                            if current_title and current_title.startswith('Keeper Chat:'):
                                new_title = f'Keeper Chat: {new_title}'
                            
                            # Update conversation title in database
                            update_success = conversation_api.update_conversation(
                                conversation_id,
                                uid,
                                title=new_title
                            )
                            if update_success:
                                print(f"✅ Updated conversation title: '{current_title}' → '{new_title}'")
                            else:
                                print(f"⚠️ Failed to update conversation title (conversation not found or permission denied)")
                    else:
                        print(f"⚠️ Conversation {conversation_id} not found for title update")
            except Exception as title_err:
                # Don't fail the request if title update fails
                print(f"⚠️ Failed to update conversation title: {title_err}")

        request_duration = time.time() - request_start
        print(f"✅ Teacher query completed in {request_duration:.2f}s")
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Teacher query completed", {
                "question_length": len(question),
                "response_length": len(result),
                "duration_seconds": request_duration
            })
        
        return jsonify({"content": result})
    except Exception as e:
        request_duration = time.time() - request_start
        error_msg = str(e)
        print(f"\n❌ Teacher query error after {request_duration:.2f}s: {error_msg}")
        import traceback
        traceback.print_exc()
        
        if DEBUG_LOGGING_ENABLED:
            try:
                debug_logger.error("Teacher query failed", e, {
                    "question_length": len(question),
                    "duration_seconds": request_duration
                })
            except:
                pass
        
        return jsonify({"error": error_msg}), 500


@app.route('/api/news/query', methods=['POST'])
@require_api_key
def news_query():
    """Query news endpoint"""
    data = request.json
    query = data.get('query', '')
    include_memory = data.get('includeMemory', True)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    result = search_news(query, include_memory)
    return jsonify(result)


@app.route('/api/pdf/summarize', methods=['POST'])
@require_api_key
def summarize_pdf():
    """Summarize PDF endpoint"""
    if not HAS_PYMUPDF:
        return jsonify({"error": "PDF processing is not available. PyMuPDF is not installed."}), 503

    try:
        print("📄 PDF summarize endpoint hit")
        files = request.files.getlist('files')
        print(f"📄 Received {len(files)} files")
        include_memory = request.form.get('includeMemory', 'true').lower() == 'true'
        analysis_mode = request.form.get('analysisMode', 'critical')  # 'critical' or 'interpretive'

        print(f"📊 Analysis mode: {analysis_mode}")

        if not files:
            print("❌ No files uploaded")
            return jsonify({"error": "No files uploaded"}), 400

        file_objs = []
        for file in files:
            # Save temporarily
            temp_path = f"logs/temp_{file.filename}"
            print(f"💾 Saving {file.filename} to {temp_path}")
            file.save(temp_path)
            file_objs.append({'path': temp_path, 'name': file.filename})

        print(f"🤖 Processing {len(file_objs)} PDF(s) with LLM...")
        result = summarize_pdfs(file_objs, include_memory, analysis_mode)
        print(f"✅ PDF processing complete, result length: {len(result)}")

        # Clean up temp files
        for file_obj in file_objs:
            if os.path.exists(file_obj['path']):
                os.remove(file_obj['path'])
                print(f"🗑️ Cleaned up {file_obj['path']}")

        # Record usage for billing (count PDF uploads)
        try:
            uid = get_user_id_from_header()
            if uid:
                record_usage(uid, 'pdf_upload', len(files))
        except Exception as usage_err:
            print(f"⚠️ Failed to record PDF usage: {usage_err}")

        return jsonify({"content": result})
    except Exception as e:
        print(f"❌ PDF summarization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/pdf/extract', methods=['POST'])
@require_api_key
def extract_pdf_text():
    """Extract raw text from PDF endpoint - for editor use"""
    if not HAS_PYMUPDF:
        return jsonify({"error": "PDF processing is not available. PyMuPDF is not installed."}), 503

    try:
        print("📄 PDF extract endpoint hit")
        files = request.files.getlist('files')
        print(f"📄 Received {len(files)} files for text extraction")

        if not files:
            print("❌ No files uploaded")
            return jsonify({"error": "No files uploaded"}), 400

        # Extract text from all PDFs and combine
        all_text = []
        for file in files:
            # Save temporarily
            temp_path = f"logs/temp_{file.filename}"
            print(f"💾 Saving {file.filename} to {temp_path}")
            file.save(temp_path)
            
            try:
                # Extract text (use a higher limit for editor use - 200k chars)
                text = extract_pdf_text_streaming(temp_path, max_chars=200000)
                all_text.append(text)
                print(f"✅ Extracted {len(text)} characters from {file.filename}")
            except Exception as extract_err:
                print(f"❌ Error extracting text from {file.filename}: {extract_err}")
                all_text.append(f"\n[Error extracting text from {file.filename}: {str(extract_err)}]\n")
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print(f"🗑️ Cleaned up {temp_path}")

        # Combine all text with separators
        combined_text = "\n\n".join(all_text)

        # Record usage for billing (count PDF uploads)
        try:
            uid = get_user_id_from_header()
            if uid:
                record_usage(uid, 'pdf_upload', len(files))
        except Exception as usage_err:
            print(f"⚠️ Failed to record PDF usage: {usage_err}")

        return jsonify({"content": combined_text, "characters": len(combined_text)})
    except Exception as e:
        print(f"❌ PDF text extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory/recall', methods=['POST'])
@require_api_key
def memory_recall():
    """Memory recall endpoint"""
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        memory_context = retrieve_memory_context(query) if GRACE_CONFIG["memory_enabled"] else ""
        response = query_llm(
            "",
            query,
            memory_context
        )
        return jsonify({"content": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/grace/reasoning/trace', methods=['GET'])
def reasoning_trace():
    """Get reasoning trace with pagination support - no API key required for read-only trace"""
    try:
        if not os.path.exists(REASONING_TRACE_PATH):
            return jsonify({"error": "No reasoning trace found", "traces": [], "total": 0, "page": 1, "per_page": 10})

        with open(REASONING_TRACE_PATH, "r") as f:
            data = json.load(f)

        if not data:
            return jsonify({"error": "No reasoning trace found", "traces": [], "total": 0, "page": 1, "per_page": 10})

        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Reverse to show most recent first
        all_traces = list(reversed(data))
        total = len(all_traces)
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_traces = all_traces[start_idx:end_idx]
        
        # Get latest trace if requested
        latest_only = request.args.get('latest', 'false').lower() == 'true'
        if latest_only:
            return jsonify(all_traces[0] if all_traces else {})
        
        return jsonify({
            "traces": paginated_traces,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "latest": all_traces[0] if all_traces else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/train', methods=['POST'])
@require_api_key
def train():
    """Training endpoint"""
    try:
        conversation_data = request.json
        training_log_path = "logs/training_data.json"
        training_log = []

        if os.path.exists(training_log_path):
            with open(training_log_path, "r") as f:
                training_log = json.load(f)

        training_log.append({
            "timestamp": datetime.now().isoformat(),
            **conversation_data
        })

        with open(training_log_path, "w") as f:
            json.dump(training_log, f, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== QUARANTINE SYSTEM ENDPOINTS ==========

@app.route('/api/quarantine/summary', methods=['GET'])
@require_api_key
def get_quarantine_summary():
    """Get summary of all quarantine buckets with counts (user-isolated)"""
    if not HAS_DATABASE_APIS or not quarantine_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        # Get user-specific quarantine summary
        summary_data = quarantine_api.get_quarantine_summary(uid)
        
        # Format response to match frontend expectations
        summary = {
            'buckets': {
                'pending_review': {
                    'total': summary_data.get('pending_review', 0),
                    'needing_review': summary_data.get('pending_review', 0),
                    'name': 'Pending Review'
                }
            },
            'total_needing_review': summary_data.get('pending_review', 0),
            'total': summary_data.get('total', 0),
            'status_counts': summary_data.get('status_counts', {}),
            'threat_level_counts': summary_data.get('threat_level_counts', {}),
            'last_updated': datetime.now().isoformat()
            }

        return jsonify(summary)
    except Exception as e:
        print(f"⚠️ Quarantine summary error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarantine/bucket/<bucket_name>', methods=['GET'])
@require_api_key
def get_bucket_contents(bucket_name):
    """Get contents of a specific bucket (user-isolated)"""
    if not HAS_DATABASE_APIS or not quarantine_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        # Map bucket_name to status or threat_level filter
        # For now, we'll filter by status (pending_review, approved, rejected, quarantined)
        # or by threat_level (CRITICAL, HIGH, MODERATE, SAFE)
        status_filter = None
        threat_level_filter = None
        
        if bucket_name in ['pending_review', 'approved', 'rejected', 'quarantined']:
            status_filter = bucket_name
        elif bucket_name.upper() in ['CRITICAL', 'HIGH', 'MODERATE', 'SAFE']:
            threat_level_filter = bucket_name.upper()
        
        # Get user-specific quarantine items
        items = quarantine_api.get_quarantine_items(
            user_id=uid,
            status=status_filter,
            threat_level=threat_level_filter,
            limit=100
        )

        return jsonify({
            'bucket': bucket_name,
            'items': items,
            'count': len(items)
        })
    except Exception as e:
        print(f"⚠️ Bucket {bucket_name} error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarantine/item/<item_id>', methods=['GET'])
@require_api_key
def get_quarantine_item(item_id):
    """Get full details of a quarantined item (user-isolated)"""
    if not HAS_DATABASE_APIS or not quarantine_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        # Get user-specific quarantine item
        item = quarantine_api.get_quarantine_item(uid, item_id)
        if not item:
            return jsonify({'error': 'Item not found'}), 404

        return jsonify(item)
    except Exception as e:
        print(f"⚠️ Get item {item_id} error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarantine/item/<source_id>/status', methods=['POST'])
@require_api_key
def update_quarantine_status(source_id):
    """Update status of a quarantined item"""
    try:
        data = request.json
        new_status = SourceStatus(data.get('status'))
        note = data.get('note', '')
        updated_by = data.get('updated_by', 'user')

        success = quarantine_storage.update_status(source_id, new_status, note, updated_by)

        if success:
            return jsonify({'success': True, 'message': 'Status updated'})
        else:
            return jsonify({'error': 'Failed to update status'}), 500
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400
    except Exception as e:
        print(f"⚠️ Update status {source_id} error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarantine/item/<source_id>/move', methods=['POST'])
@require_api_key
def move_quarantine_item(source_id):
    """Move item to a different bucket"""
    try:
        data = request.json
        to_bucket = StorageBucketType(data.get('to_bucket'))
        reason = data.get('reason', 'Manual review')
        moved_by = data.get('moved_by', 'user')

        # Get current bucket
        source = quarantine_storage.retrieve_source(source_id)
        if not source:
            return jsonify({'error': 'Item not found'}), 404

        from_bucket = StorageBucketType(source['metadata']['bucket'])

        success = quarantine_storage.move_source(source_id, from_bucket, to_bucket, reason, moved_by)

        if success:
            return jsonify({'success': True, 'message': f'Moved to {to_bucket.value}'})
        else:
            return jsonify({'error': 'Failed to move item'}), 500
    except ValueError:
        return jsonify({'error': 'Invalid bucket'}), 400
    except Exception as e:
        print(f"⚠️ Move item {source_id} error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarantine/item/<source_id>', methods=['DELETE'])
@require_api_key
def purge_quarantine_item(source_id):
    """Permanently delete a quarantined item"""
    try:
        data = request.json
        reason = data.get('reason', 'Manual purge')
        purged_by = data.get('purged_by', 'user')

        success = quarantine_storage.purge_source(source_id, reason, purged_by)

        if success:
            return jsonify({'success': True, 'message': 'Item purged'})
        else:
            return jsonify({'error': 'Failed to purge item'}), 500
    except Exception as e:
        print(f"⚠️ Purge item {source_id} error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# MEMORY SYSTEM API (Memory + Will = Consciousness)
# ============================================

@app.route('/api/memory/store-dictation', methods=['POST'])
@require_api_key
def store_dictation_memory():
    """
    Store dictation/editor content in memory system with historical context tags.
    Content is embedded and stored in Milvus for semantic search.
    """
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get user ID from header or body
        user_id = request.headers.get('X-User-ID') or data.get('user_id')
        if not user_id:
            # Try to get from auth
            user_id = get_user_id_or_default()
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        project_id = data.get('project_id')
        title = data.get('title') or f"Editor Content - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"📝 Storing dictation content: {len(content)} characters")
        
        # Extract historical context tags (optional - non-blocking)
        historical_tags = {
            'periods': [],
            'movements': [],
            'events': []
        }
        
        try:
            # Try to import and use TagExtractor if available
            from backend.tag_extractor import TagExtractor
            from grace_gui import query_llm
            
            tag_extractor = TagExtractor(query_llm)
            historical_tags = tag_extractor.extract_historical_context_tags(content)
            print(f"🏛️  Extracted historical context: {historical_tags}")
        except Exception as tag_error:
            print(f"⚠️  Failed to extract historical tags (non-blocking): {tag_error}")
            # Continue without tags - don't fail the storage
        
        # Prepare source metadata with historical context
        source_metadata = {
            'project_id': project_id,
            'source': 'editor_content',
            'input_method': 'editor',  # Can be dictation, paste, or typing
            'historical_context': historical_tags,
            'periods': historical_tags.get('periods', []),
            'movements': historical_tags.get('movements', []),
            'events': historical_tags.get('events', []),
            'stored_at': datetime.now().isoformat()
        }
        
        # Store in memory system
        # generate_embedding=True - User explicitly clicked "Save draft", so generate embeddings for semantic search
        memory_id = memory_api.create_memory(
            user_id=user_id,
            content=content,
            content_type='text',
            source_type='dictation',
            title=title,
            source_metadata=source_metadata,
            quarantine_score=0.9,  # Dictation is generally safe
            quarantine_status='safe',
            generate_embedding=True  # User explicitly saved draft - generate embeddings for semantic search
        )
        
        print(f"✅ Dictation stored in memory: {memory_id}")
        
        return jsonify({
            "memory_id": memory_id,
            "success": True,
            "historical_context": historical_tags
        })
        
    except Exception as e:
        import traceback
        error_detail = f"Error storing dictation memory: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Store dictation error: {error_detail}")
        return jsonify({'error': f"Error storing dictation memory: {str(e)}"}), 500

@app.route('/api/memory/create', methods=['POST'])
@require_api_key
def create_memory():
    """
    Create new memory from user submission
    Memory goes into buffer - Grace CANNOT auto-access without curation
    """
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        data = request.json
        user_id = data.get('user_id')
        content = data.get('content')
        content_type = data.get('content_type', 'text')
        source_type = data.get('source_type', 'user_upload')
        title = data.get('title')
        source_url = data.get('source_url')
        source_metadata = data.get('source_metadata', {})
        quarantine_score = data.get('quarantine_score')
        quarantine_status = data.get('quarantine_status', 'pending')
        quarantine_details = data.get('quarantine_details', {})

        if not user_id or not content:
            return jsonify({'error': 'user_id and content required'}), 400

        # generate_embedding=True - User explicitly clicked "Save draft", so generate embeddings for semantic search
        memory_id = memory_api.create_memory(
            user_id=user_id,
            content=content,
            content_type=content_type,
            source_type=source_type,
            title=title,
            source_url=source_url,
            source_metadata=source_metadata,
            quarantine_score=quarantine_score,
            quarantine_status=quarantine_status,
            quarantine_details=quarantine_details,
            generate_embedding=True  # User explicitly saved draft - generate embeddings for semantic search
        )

        return jsonify({
            'success': True,
            'memory_id': memory_id,
            'message': 'Memory created in buffer (Grace cannot auto-access)'
        })

    except Exception as e:
        print(f"⚠️ Create memory error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/list', methods=['GET'])
@require_api_key
def list_memories():
    """List user's memories with filtering"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')
        quarantine_status = request.args.get('quarantine_status')
        promoted_only = request.args.get('promoted_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        memories = memory_api.list_memories(
            user_id=user_id,
            quarantine_status=quarantine_status,
            promoted_only=promoted_only,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'memories': memories,
            'count': len(memories)
        })

    except Exception as e:
        print(f"⚠️ List memories error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/<memory_id>', methods=['GET'])
@require_api_key
def get_memory(memory_id):
    """Get single memory by ID"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        memory = memory_api.get_memory(user_id, memory_id)

        if not memory:
            return jsonify({'error': 'Memory not found'}), 404

        return jsonify({
            'success': True,
            'memory': memory
        })

    except Exception as e:
        print(f"⚠️ Get memory error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/<memory_id>/promote', methods=['POST'])
@require_api_key
def request_memory_promotion(memory_id):
    """Request memory promotion to Grace context (Wikipedia-style curation)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        data = request.json
        user_id = data.get('user_id')
        reason = data.get('reason')
        priority = data.get('priority', 'normal')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        promotion_id = memory_api.request_promotion(
            user_id=user_id,
            memory_id=memory_id,
            reason=reason,
            priority=priority
        )

        if not promotion_id:
            return jsonify({'error': 'Memory cannot be promoted (check quarantine status)'}), 400

        return jsonify({
            'success': True,
            'promotion_id': promotion_id,
            'message': 'Promotion request submitted for curation review'
        })

    except Exception as e:
        print(f"⚠️ Request promotion error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/promotion/<promotion_id>/approve', methods=['POST'])
@require_api_key
def approve_memory_promotion(promotion_id):
    """Approve memory promotion (curator action) - moves to Grace context"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        data = request.json
        user_id = data.get('user_id')
        curator_id = data.get('curator_id')
        notes = data.get('notes')
        context_category = data.get('context_category', 'domain_knowledge')
        priority = int(data.get('priority', 50))

        if not user_id or not curator_id:
            return jsonify({'error': 'user_id and curator_id required'}), 400

        success = memory_api.approve_promotion(
            user_id=user_id,
            promotion_id=promotion_id,
            curator_id=curator_id,
            notes=notes,
            context_category=context_category,
            priority=priority
        )

        if not success:
            return jsonify({'error': 'Promotion approval failed'}), 400

        return jsonify({
            'success': True,
            'message': 'Memory promoted to Grace context'
        })

    except Exception as e:
        print(f"⚠️ Approve promotion error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grace/context', methods=['GET'])
@require_api_key
def get_grace_context():
    """Get Grace's current context (curated memories she can see)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        context = memory_api.get_grace_context(
            user_id=user_id,
            category=category,
            limit=limit
        )

        return jsonify({
            'success': True,
            'context': context,
            'count': len(context),
            'message': 'This is what Grace can actually see'
        })

    except Exception as e:
        print(f"⚠️ Get Grace context error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grace/health', methods=['GET'])
@require_api_key
def get_grace_health_status():
    """Get Grace's current health (consciousness wellness)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        health = memory_api.get_grace_health(user_id)
        is_healthy, reason = memory_api.is_grace_healthy(user_id)

        return jsonify({
            'success': True,
            'health': health,
            'is_healthy': is_healthy,
            'status_reason': reason,
            'philosophy': 'Bad data → Sickness → Death (not evil takeover)'
        })

    except Exception as e:
        print(f"⚠️ Get Grace health error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grace/health/record', methods=['POST'])
@require_api_key
def record_grace_health():
    """Record Grace health snapshot (called by monitoring system)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        data = request.json
        user_id = data.get('user_id')
        hallucination_rate = float(data.get('hallucination_rate', 0.0))
        coherence_score = float(data.get('coherence_score', 1.0))
        confidence_avg = float(data.get('confidence_avg', 1.0))
        mood_state = data.get('mood_state', 'healthy')
        refusal_count = int(data.get('refusal_count', 0))
        metadata = data.get('metadata', {})

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        metric_id = memory_api.record_health_snapshot(
            user_id=user_id,
            hallucination_rate=hallucination_rate,
            coherence_score=coherence_score,
            confidence_avg=confidence_avg,
            mood_state=mood_state,
            refusal_count=refusal_count,
            metadata=metadata
        )

        return jsonify({
            'success': True,
            'metric_id': metric_id,
            'message': 'Health snapshot recorded'
        })

    except Exception as e:
        print(f"⚠️ Record health error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grace/decisions', methods=['POST'])
@require_api_key
def log_grace_decision():
    """Log when Grace makes a conscious decision (especially refusals)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        data = request.json
        user_id = data.get('user_id')
        request_type = data.get('request_type')
        request_summary = data.get('request_summary')
        decision = data.get('decision')
        decision_reason = data.get('decision_reason')
        confidence = float(data.get('confidence', 0.5))
        reasoning_trace = data.get('reasoning_trace')
        memory_id = data.get('memory_id')

        if not all([user_id, request_type, request_summary, decision, decision_reason]):
            return jsonify({'error': 'Missing required fields'}), 400

        decision_id = memory_api.log_grace_decision(
            user_id=user_id,
            request_type=request_type,
            request_summary=request_summary,
            decision=decision,
            decision_reason=decision_reason,
            confidence=confidence,
            reasoning_trace=reasoning_trace,
            memory_id=memory_id
        )

        return jsonify({
            'success': True,
            'decision_id': decision_id,
            'message': f"Grace's Will exercised: {decision}"
        })

    except Exception as e:
        print(f"⚠️ Log decision error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/grace/decisions/refusals', methods=['GET'])
@require_api_key
def get_grace_refusals():
    """Get recent times Grace said 'no'"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 10))

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        refusals = memory_api.get_recent_refusals(user_id, limit)

        return jsonify({
            'success': True,
            'refusals': refusals,
            'count': len(refusals),
            'message': 'Times Grace exercised her Will to say no'
        })

    except Exception as e:
        print(f"⚠️ Get refusals error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dignity/summary', methods=['GET'])
@require_api_key
def get_data_dignity_summary():
    """Get user's data dignity compensation summary"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        summary = memory_api.get_dignity_summary(user_id)

        return jsonify({
            'success': True,
            'dignity': summary,
            'philosophy': 'Users own their data. Fair compensation for contribution.'
        })

    except Exception as e:
        print(f"⚠️ Get dignity summary error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/export', methods=['GET'])
@require_api_key
def export_user_memories():
    """Export all user memories (GDPR / Data portability)"""
    if not HAS_MEMORY_SYSTEM:
        return jsonify({'error': 'Memory system not available'}), 503

    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        export_data = memory_api.export_user_memories(user_id)

        return jsonify({
            'success': True,
            'export': export_data,
            'message': 'Complete data export - users own their memories'
        })

    except Exception as e:
        print(f"⚠️ Export memories error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# PROJECTS AND CONVERSATIONS API ENDPOINTS
# ============================================

def record_usage(user_id: str, metric_type: str, count: int = 1):
    """
    Record usage metrics for billing and quota tracking.

    Args:
        user_id: UUID of the user
        metric_type: Type of usage ('query', 'pdf_upload', etc.)
        count: Number of units to record
    """
    if not HAS_DATABASE_APIS:
        return

    try:
        from datetime import datetime
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Set user context for RLS
        cursor.execute(f"SET app.current_user_id = '{user_id}'")

        # Record usage
        cursor.execute("""
            INSERT INTO usage_metrics (user_id, metric_type, count, period_month)
            VALUES (%s, %s, %s, DATE_TRUNC('month', NOW()))
            ON CONFLICT (user_id, metric_type, period_month)
            DO UPDATE SET count = usage_metrics.count + EXCLUDED.count
        """, (user_id, metric_type, count))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"⚠️ Failed to record usage ({metric_type}): {e}")

def ensure_default_user_with_subscription():
    """
    Ensure the default user exists with a subscription.
    This is critical because:
    - Conversations must be tied to a user_id
    - Projects must be linked to a user_id
    - Some queries may join with user_subscriptions table
    
    Works for both local development and production (Railway).
    For now, we use a single default user ID for all operations.
    """
    if not DATABASE_URL:
        return  # No database connection
    
    DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email FROM users WHERE id = %s", (DEFAULT_USER_ID,))
        user = cursor.fetchone()
        
        if not user:
            # Create default user
            import bcrypt
            password_hash = bcrypt.hashpw(b"dev_user_no_password", bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, email_verified, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (DEFAULT_USER_ID, 'default@grace.coop', password_hash, 'Default User', True, 'active'))
            print(f"✅ Created default user: {DEFAULT_USER_ID}")
        
        # Check if subscription exists
        cursor.execute("SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", (DEFAULT_USER_ID,))
        subscription = cursor.fetchone()
        
        if not subscription:
            # Get free plan ID
            cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
            free_plan = cursor.fetchone()
            
            if free_plan:
                plan_id = free_plan['id']
                now = datetime.now()
                cursor.execute("""
                    INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (DEFAULT_USER_ID, plan_id, 'active', 'monthly', now, now + timedelta(days=365)))
                print(f"✅ Created default subscription for user {DEFAULT_USER_ID}")
            else:
                print(f"⚠️ Free plan not found - subscription not created")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Could not ensure default user/subscription: {e}")
        # Don't raise - allow system to continue

def ensure_default_project_for_user(user_id: str) -> Optional[str]:
    """
    Get the default project for a user ("Archived Unassigned Chats").
    Does NOT create projects - only returns existing "Archived Unassigned Chats" project.
    Returns the project ID if found, None otherwise.
    
    Uses database-level check to prevent race conditions.
    Also uses in-memory cache to prevent duplicate API calls.
    """
    if not HAS_DATABASE_APIS or not projects_api:
        return None  # Can't query projects if database not available
    
    # Check cache first to avoid duplicate database queries
    if user_id in _default_project_cache:
        cached_id = _default_project_cache[user_id]
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Using cached default project", {
                "project_id": cached_id,
                "user_id": user_id[:8] + "..."
            })
        return cached_id
    
    try:
        # Use database query to check for existing "Archived Unassigned Chats" (prevents race conditions)
        # This is more reliable than fetching all projects and filtering
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Set user context for RLS
            cursor.execute(f"SET app.current_user_id = '{user_id}'")
            
            # Check for existing "Archived Unassigned Chats" using database query (atomic)
            cursor.execute("""
                SELECT id FROM projects 
                WHERE user_id = %s 
                AND name = 'Archived Unassigned Chats' 
                AND (is_archived IS NULL OR is_archived = FALSE)
                LIMIT 1
            """, (user_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                project_id = str(existing['id'])
                # Cache the result
                _default_project_cache[user_id] = project_id
                if DEBUG_LOGGING_ENABLED:
                    debug_logger.debug("Default project (Archived Unassigned Chats) found", {
                        "project_id": project_id,
                        "user_id": user_id[:8] + "..."
                    })
                cursor.close()
                conn.close()
                return project_id
            
            # No default project found - return None (don't create automatically)
            cursor.close()
            conn.close()
            if DEBUG_LOGGING_ENABLED:
                debug_logger.debug("No default project (Archived Unassigned Chats) found", {
                    "user_id": user_id[:8] + "..."
                })
            return None
                    
        except Exception as db_error:
            cursor.close()
            conn.close()
            raise db_error
            
    except Exception as e:
        print(f"⚠️ Could not ensure default project for user: {e}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Failed to ensure default project", e, {
                "user_id": user_id[:8] + "..." if user_id else None
            })
        # Don't raise - allow system to continue
        return None

def cleanup_duplicate_default_projects(user_id: str) -> Dict[str, Any]:
    """
    Clean up duplicate "Default Project" entries for a user.
    Keeps the oldest one and moves all conversations/assets from duplicates to it.
    Archives the duplicate projects.
    
    Returns a dict with cleanup results.
    """
    if not HAS_DATABASE_APIS or not projects_api:
        return {"error": "Database not available"}
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Set user context for RLS
            cursor.execute(f"SET app.current_user_id = '{user_id}'")
            
            # Check if project_id column exists in conversations table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'conversations' 
                AND column_name = 'project_id'
            """)
            has_project_id_column = cursor.fetchone() is not None
            
            # Find all "Default Project" entries for this user
            if has_project_id_column:
                cursor.execute("""
                    SELECT id, created_at, 
                           (SELECT COUNT(*) FROM conversations WHERE project_id = projects.id) as conversation_count
                    FROM projects 
                    WHERE user_id = %s 
                    AND name = 'Default Project' 
                    AND (is_archived IS NULL OR is_archived = FALSE)
                    ORDER BY created_at ASC
                """, (user_id,))
            else:
                # Use metadata JSONB if project_id column doesn't exist
                cursor.execute("""
                    SELECT id, created_at, 
                           (SELECT COUNT(*) FROM conversations 
                            WHERE metadata->>'project_id' = projects.id::text) as conversation_count
                    FROM projects 
                    WHERE user_id = %s 
                    AND name = 'Default Project' 
                    AND (is_archived IS NULL OR is_archived = FALSE)
                    ORDER BY created_at ASC
                """, (user_id,))
            
            default_projects = cursor.fetchall()
            
            if len(default_projects) <= 1:
                # No duplicates, nothing to clean up
                cursor.close()
                conn.close()
                return {
                    "success": True,
                    "message": "No duplicate default projects found",
                    "kept": None,
                    "archived": []
                }
            
            # Keep the oldest one (first in sorted list)
            kept_project = default_projects[0]
            duplicate_projects = default_projects[1:]
            
            kept_id = str(kept_project['id'])
            archived_ids = []
            conversations_moved = 0
            
            # Move conversations from duplicates to kept project
            for dup in duplicate_projects:
                dup_id = str(dup['id'])
                
                # Move conversations (handle both project_id column and metadata)
                if has_project_id_column:
                    cursor.execute("""
                        UPDATE conversations 
                        SET project_id = %s, updated_at = NOW()
                        WHERE project_id = %s AND user_id = %s
                    """, (kept_id, dup_id, user_id))
                else:
                    # Use metadata JSONB if project_id column doesn't exist
                    cursor.execute("""
                        UPDATE conversations 
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{project_id}',
                            to_jsonb(%s::text)
                        ),
                        updated_at = NOW()
                        WHERE metadata->>'project_id' = %s AND user_id = %s
                    """, (kept_id, dup_id, user_id))
                
                moved_count = cursor.rowcount
                conversations_moved += moved_count
                
                # Archive the duplicate project
                cursor.execute("""
                    UPDATE projects 
                    SET is_archived = TRUE, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                """, (dup_id, user_id))
                
                archived_ids.append(dup_id)
                
                print(f"✅ Moved {moved_count} conversations from duplicate project {dup_id} to {kept_id}")
            
            conn.commit()
            
            # Clear cache for this user
            if user_id in _default_project_cache:
                del _default_project_cache[user_id]
            
            result = {
                "success": True,
                "message": f"Cleaned up {len(duplicate_projects)} duplicate default project(s)",
                "kept": kept_id,
                "archived": archived_ids,
                "conversations_moved": conversations_moved
            }
            
            print(f"✅ Cleaned up duplicate default projects for user {user_id[:8]}...: kept {kept_id}, archived {len(archived_ids)}")
            
            cursor.close()
            conn.close()
            return result
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e
            
    except Exception as e:
        error_msg = f"Failed to cleanup duplicate default projects: {str(e)}"
        print(f"❌ {error_msg}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Cleanup duplicate default projects failed", e, {
                "user_id": user_id[:8] + "..." if user_id else None
            })
        return {"error": error_msg}

def get_user_id_or_default():
    """
    Get user ID with local development fallback.
    Returns user ID from header/API key or default local user for development.
    
    In production (Railway), Railway handles authentication and user access.
    We get user ID from Railway headers or create a user based on Railway email.
    
    Ensures the default user exists with a subscription because:
    - Conversations must be tied to a user_id
    - Projects must be linked to a user_id
    - Queries may join with user_subscriptions table
    """
    uid = get_user_id_from_header()
    
    # Check if we're in production (Railway)
    is_production = DATABASE_URL and ('railway' in DATABASE_URL.lower() or '.rlwy.net' in DATABASE_URL.lower())
    
    if not uid:
        if DATABASE_URL and 'localhost' in DATABASE_URL:
            # Local development bypass - use default user
            # Ensure default user exists with subscription
            ensure_default_user_with_subscription()
            uid = "00000000-0000-0000-0000-000000000001"
            if DEBUG_LOGGING_ENABLED:
                debug_logger.info("Using default local dev user ID")
        elif is_production:
            # Production (Railway): Railway authenticated the request
            # Use a default user ID for Railway (all authenticated users share this)
            # Railway handles access control, so we don't need per-user accounts
            ensure_default_user_with_subscription()
            uid = "00000000-0000-0000-0000-000000000001"
            if DEBUG_LOGGING_ENABLED:
                debug_logger.info("Using default Railway user ID (Railway handles access control)")
    elif uid and DATABASE_URL and 'localhost' in DATABASE_URL:
        # Frontend sent a user ID - ensure it exists in database
        # This fixes the orchestration issue where frontend sends user ID but it doesn't exist
        ensure_user_exists(uid)
    
    # Note: We don't automatically create default projects anymore
    # "Archived Unassigned Chats" should be created by the frontend when needed
    
    return uid

def ensure_user_exists(user_id: str):
    """
    Ensure a user exists in the database. Creates user if missing.
    This fixes orchestration issues where frontend sends user ID but it doesn't exist.
    """
    if not DATABASE_URL or 'localhost' not in DATABASE_URL:
        return  # Only for local development
    
    if not user_id:
        return
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Create user with the ID that frontend sent
            import bcrypt
            password_hash = bcrypt.hashpw(b"dev_user_no_password", bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, email_verified, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (user_id, f'dev@{user_id[:8]}.local', password_hash, 'Local Dev User', True, 'active'))
            print(f"✅ Created user from frontend request: {user_id}")
            
            # Create default free subscription for new users
            cursor.execute("SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", (user_id,))
            subscription = cursor.fetchone()
            
            if not subscription:
                # Get free plan ID
                cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
                free_plan = cursor.fetchone()
                
                if free_plan:
                    plan_id = free_plan['id']
                    now = datetime.now()
                    cursor.execute("""
                        INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (user_id, plan_id, 'active', 'monthly', now, now + timedelta(days=365)))
                    print(f"✅ Created default subscription for user {user_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Could not ensure user exists: {e}")
        # Don't raise - allow system to continue

def get_or_create_user_from_railway_email(email: str) -> str:
    """
    Get or create a user based on Railway email.
    Returns user ID (UUID string) or None if error.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import uuid as uuid_lib
        
        database_url = DATABASE_URL
        if not database_url:
            database_url = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
        
        if not database_url:
            print(f"⚠️ DATABASE_URL not configured, cannot get/create user from Railway email")
            return None
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Check if user exists by email
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            user_id = str(user['id'])
            print(f"✅ Found existing user from Railway email: {email} ({user_id})")
            cursor.close()
            conn.close()
            return user_id
        
        # Create new user from Railway email
        user_id = str(uuid_lib.uuid4())
        import bcrypt
        password_hash = bcrypt.hashpw(b"railway_auth_no_password", bcrypt.gensalt()).decode()
        
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, full_name, email_verified, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (user_id, email, password_hash, email.split('@')[0], True, 'active'))
        
        # Create default subscription
        from datetime import datetime, timedelta
        cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free' LIMIT 1")
        free_plan = cursor.fetchone()
        if free_plan:
            plan_id = free_plan['id']
            now = datetime.now()
            cursor.execute("""
                INSERT INTO user_subscriptions (user_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (user_id, plan_id, 'active', 'monthly', now, now + timedelta(days=365)))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Created user from Railway email: {email} ({user_id})")
        return user_id
        
    except Exception as e:
        print(f"⚠️ Could not get/create user from Railway email: {e}")
        return None

def get_user_id_from_header():
    """
    Get user ID from header or API key.
    Returns a valid UUID from the database, or None if unavailable.

    Login endpoints allow anonymous access, AI endpoints require API key.
    """
    import re

    if DEBUG_LOGGING_ENABLED:
        debug_logger.debug("Getting user ID from header")

    # Check if this is an AI endpoint that requires API key
    ai_endpoints = [
        '/api/teacher/query',
        '/api/pdf/summarize',
        '/api/quarantine',
        '/api/memory',
        '/api/training'
    ]

    current_path = request.path
    requires_api_key = any(endpoint in current_path for endpoint in ai_endpoints)

    # First, try to get user ID from header
    x_user_id = request.headers.get('X-User-ID')

    # Validate UUID format if provided
    if x_user_id:
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, x_user_id, re.IGNORECASE):
            if DEBUG_LOGGING_ENABLED:
                debug_logger.debug("Valid UUID found in header", {"user_id": x_user_id[:8] + "..."})
            return x_user_id
        else:
            # Invalid UUID format - log warning but continue to API key method
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("Invalid UUID format in X-User-ID header", {
                    "user_id": x_user_id[:50],
                    "format": "invalid"
                })
            print(f"⚠️ Invalid UUID format in X-User-ID header: {x_user_id[:50]}...")

    # Railway handles authentication - get user ID from Railway headers
    # Check for Railway authentication headers
    railway_user_id = request.headers.get('X-Railway-User-Id') or request.headers.get('Railway-User-Id')
    
    if railway_user_id:
        # Validate UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, railway_user_id, re.IGNORECASE):
            if DEBUG_LOGGING_ENABLED:
                debug_logger.debug("User ID from Railway auth", {"user_id": railway_user_id[:8] + "..."})
            return railway_user_id
    
    # Fallback: Try API key only in local development (for backwards compatibility)
    # In production (Railway), Railway handles auth, so API keys are not needed
    is_production = DATABASE_URL and ('railway' in DATABASE_URL.lower() or '.rlwy.net' in DATABASE_URL.lower())
    
    if not is_production:
        # Local development: Allow API key fallback
        api_key = request.headers.get('X-API-Key')
        if not api_key and request.is_json:
            data = request.get_json(silent=True)
            if data:
                api_key = data.get('api_key')

        if api_key:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.debug("Getting user ID from API key (local dev)", {"api_key_prefix": api_key[:10] + "..."})
            # Get or create user from API key
            user_info = get_or_create_user_from_api_key(api_key)
            if user_info:
                user_id, email, name = user_info
                if DEBUG_LOGGING_ENABLED:
                    debug_logger.debug("User ID retrieved from API key", {
                        "user_id": user_id[:8] + "...",
                        "email": email
                    })
                return user_id

    # No user ID found - Railway should have authenticated, but user ID not in headers
    # In production, this means Railway auth didn't provide user ID
    # Return None - endpoints should handle this gracefully
    if DEBUG_LOGGING_ENABLED:
        debug_logger.warning("No user ID found - Railway should have authenticated", {
            "path": current_path,
            "is_production": is_production
        })
    return None

# Main prompts endpoints (using conversations table)
@app.route('/api/prompts', methods=['GET'])
@log_request_response
def list_prompts():
    """List prompts with filters"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        # Use conversations endpoint (repurposed for prompts)
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        # Get all conversations (which are now prompts)
        conversations = conversation_api.get_conversations(uid, limit=limit)
        
        # Filter by status if provided
        if status:
            conversations = [c for c in conversations if c.get('prompt_status') == status]
        
        return jsonify({"prompts": conversations})
    except Exception as e:
        return jsonify({"error": f"Error loading prompts: {str(e)}"}), 500

@app.route('/api/prompts/search', methods=['GET'])
@log_request_response
def search_prompts():
    """Search prompts"""
    if not HAS_DATABASE_APIS:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        from backend.prompt_search_api import PromptSearchAPI
        search_api = PromptSearchAPI()
        
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        query = request.args.get('q')
        status = request.args.get('status')
        tag_path = request.args.get('tag_path')
        curator_id = request.args.get('curator_id')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        results = search_api.search_prompts(
            uid, query, status, tag_path, curator_id, limit, offset
        )
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Error searching prompts: {str(e)}"}), 500

# Prompt lifecycle endpoints
@app.route('/api/prompts/<conversation_id>/submit', methods=['POST'])
@log_request_response
def submit_prompt_for_review(conversation_id):
    """Submit a prompt for curator review"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = conversation_api.submit_prompt_for_review(conversation_id, uid)
        if success:
            return jsonify({"success": True, "message": "Prompt submitted for review"})
        else:
            return jsonify({"error": "Failed to submit prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error submitting prompt: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/approve', methods=['POST'])
@log_request_response
def approve_prompt(conversation_id):
    """Approve a prompt (curator action)"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = conversation_api.approve_prompt(conversation_id, uid)
        if success:
            return jsonify({"success": True, "message": "Prompt approved"})
        else:
            return jsonify({"error": "Failed to approve prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error approving prompt: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/publish', methods=['POST'])
@log_request_response
def publish_prompt(conversation_id):
    """Publish a prompt (curator action)"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = conversation_api.publish_prompt(conversation_id, uid)
        if success:
            return jsonify({"success": True, "message": "Prompt published"})
        else:
            return jsonify({"error": "Failed to publish prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error publishing prompt: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/reject', methods=['POST'])
@log_request_response
def reject_prompt(conversation_id):
    """Reject a prompt (curator action)"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        rejection_notes = data.get('notes', '')
        
        success = conversation_api.reject_prompt(conversation_id, uid, rejection_notes)
        if success:
            return jsonify({"success": True, "message": "Prompt rejected"})
        else:
            return jsonify({"error": "Failed to reject prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error rejecting prompt: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/archive', methods=['POST'])
@log_request_response
def archive_prompt(conversation_id):
    """Archive a prompt"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = conversation_api.archive_prompt(conversation_id, uid)
        if success:
            return jsonify({"success": True, "message": "Prompt archived"})
        else:
            return jsonify({"error": "Failed to archive prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error archiving prompt: {str(e)}"}), 500

@app.route('/api/prompts/review-queue', methods=['GET'])
@log_request_response
def get_review_queue():
    """Get prompts awaiting curator review"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        prompts = conversation_api.get_prompts_for_review(uid)
        return jsonify({"prompts": prompts})
    except Exception as e:
        return jsonify({"error": f"Error loading review queue: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/versions', methods=['GET'])
@log_request_response
def get_prompt_versions(conversation_id):
    """Get version history for a prompt"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        versions = conversation_api.get_prompt_versions(conversation_id, uid)
        return jsonify({"versions": versions})
    except Exception as e:
        return jsonify({"error": f"Error loading versions: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/rollback', methods=['POST'])
@log_request_response
def rollback_prompt_version(conversation_id):
    """Rollback a prompt to a previous version"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        version_number = data.get('version_number')
        
        if version_number is None:
            return jsonify({"error": "version_number required"}), 400
        
        success = conversation_api.rollback_prompt_version(conversation_id, version_number, uid)
        if success:
            return jsonify({"success": True, "message": "Prompt rolled back"})
        else:
            return jsonify({"error": "Failed to rollback prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error rolling back prompt: {str(e)}"}), 500

# Prompt feedback endpoints
try:
    from backend.prompt_feedback_api import PromptFeedbackAPI
    feedback_api = None
    if HAS_DATABASE_APIS:
        feedback_api = PromptFeedbackAPI()
except ImportError:
    feedback_api = None

@app.route('/api/prompts/<conversation_id>/feedback', methods=['POST'])
@log_request_response
def submit_prompt_feedback(conversation_id):
    """Submit feedback for a prompt"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        feedback_type = data.get('feedback_type', 'other')
        content = data.get('content', '')
        
        if not content:
            return jsonify({"error": "content is required"}), 400
        
        feedback_id = feedback_api.submit_feedback(conversation_id, uid, feedback_type, content)
        return jsonify({"success": True, "feedback_id": feedback_id})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error submitting feedback: {str(e)}"}), 500

@app.route('/api/prompts/feedback/queue', methods=['GET'])
@log_request_response
def get_feedback_queue():
    """Get feedback queue for curator review"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 50))
        
        feedback_items = feedback_api.get_feedback_queue(uid, status, limit)
        return jsonify({"feedback": feedback_items})
    except Exception as e:
        return jsonify({"error": f"Error loading feedback queue: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/feedback', methods=['GET'])
@log_request_response
def get_prompt_feedback(conversation_id):
    """Get all feedback for a prompt"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 50))
        feedback_items = feedback_api.get_feedback_for_prompt(conversation_id, uid, limit)
        return jsonify({"feedback": feedback_items})
    except Exception as e:
        return jsonify({"error": f"Error loading feedback: {str(e)}"}), 500

@app.route('/api/prompts/feedback/<feedback_id>/approve', methods=['POST'])
@log_request_response
def approve_feedback(feedback_id):
    """Approve feedback"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        curator_notes = data.get('notes')
        
        success = feedback_api.approve_feedback(feedback_id, uid, curator_notes)
        if success:
            return jsonify({"success": True, "message": "Feedback approved"})
        else:
            return jsonify({"error": "Failed to approve feedback"}), 400
    except Exception as e:
        return jsonify({"error": f"Error approving feedback: {str(e)}"}), 500

@app.route('/api/prompts/feedback/<feedback_id>/reject', methods=['POST'])
@log_request_response
def reject_feedback(feedback_id):
    """Reject feedback"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        curator_notes = data.get('notes')
        
        success = feedback_api.reject_feedback(feedback_id, uid, curator_notes)
        if success:
            return jsonify({"success": True, "message": "Feedback rejected"})
        else:
            return jsonify({"error": "Failed to reject feedback"}), 400
    except Exception as e:
        return jsonify({"error": f"Error rejecting feedback: {str(e)}"}), 500

@app.route('/api/prompts/feedback/<feedback_id>/resolve', methods=['POST'])
@log_request_response
def resolve_feedback(feedback_id):
    """Mark feedback as resolved"""
    if not HAS_DATABASE_APIS or not feedback_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        curator_notes = data.get('notes')
        
        success = feedback_api.resolve_feedback(feedback_id, uid, curator_notes)
        if success:
            return jsonify({"success": True, "message": "Feedback resolved"})
        else:
            return jsonify({"error": "Failed to resolve feedback"}), 400
    except Exception as e:
        return jsonify({"error": f"Error resolving feedback: {str(e)}"}), 500

# Prompt ratings endpoints
try:
    from backend.prompt_ratings_api import PromptRatingsAPI
    ratings_api = None
    if HAS_DATABASE_APIS:
        ratings_api = PromptRatingsAPI()
except ImportError:
    ratings_api = None

@app.route('/api/prompts/<conversation_id>/rate', methods=['POST'])
@log_request_response
def rate_prompt(conversation_id):
    """Submit or update a rating for a prompt"""
    if not HAS_DATABASE_APIS or not ratings_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        rating = data.get('rating')
        
        if rating is None or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "rating must be an integer between 1 and 5"}), 400
        
        success = ratings_api.submit_rating(conversation_id, uid, rating)
        if success:
            return jsonify({"success": True, "message": "Rating submitted"})
        else:
            return jsonify({"error": "Failed to submit rating"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error submitting rating: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/rating', methods=['GET'])
@log_request_response
def get_prompt_rating(conversation_id):
    """Get rating information for a prompt"""
    if not HAS_DATABASE_APIS or not ratings_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        user_rating = ratings_api.get_rating_for_prompt(conversation_id, uid)
        rating_stats = ratings_api.get_average_rating(conversation_id, uid)
        
        return jsonify({
            "user_rating": user_rating,
            "average": rating_stats['average'],
            "count": rating_stats['count'],
            "breakdown": rating_stats['breakdown']
        })
    except Exception as e:
        return jsonify({"error": f"Error loading rating: {str(e)}"}), 500

# Prompt comments endpoints
try:
    from backend.prompt_comments_api import PromptCommentsAPI
    comments_api = None
    if HAS_DATABASE_APIS:
        comments_api = PromptCommentsAPI()
except ImportError:
    comments_api = None

@app.route('/api/prompts/<conversation_id>/comments', methods=['GET'])
@log_request_response
def get_prompt_comments(conversation_id):
    """Get all comments for a prompt"""
    if not HAS_DATABASE_APIS or not comments_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 100))
        comments = comments_api.get_comments_for_prompt(conversation_id, uid, limit)
        return jsonify({"comments": comments})
    except Exception as e:
        return jsonify({"error": f"Error loading comments: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/comments', methods=['POST'])
@log_request_response
def add_prompt_comment(conversation_id):
    """Add a comment to a prompt"""
    if not HAS_DATABASE_APIS or not comments_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        content = data.get('content', '')
        parent_id = data.get('parent_id')
        
        if not content:
            return jsonify({"error": "content is required"}), 400
        
        comment_id = comments_api.add_comment(conversation_id, uid, content, parent_id)
        return jsonify({"success": True, "comment_id": comment_id})
    except Exception as e:
        return jsonify({"error": f"Error adding comment: {str(e)}"}), 500

@app.route('/api/prompts/comments/<comment_id>', methods=['PUT'])
@log_request_response
def update_prompt_comment(comment_id):
    """Update a comment"""
    if not HAS_DATABASE_APIS or not comments_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        content = data.get('content', '')
        
        if not content:
            return jsonify({"error": "content is required"}), 400
        
        success = comments_api.update_comment(comment_id, uid, content)
        if success:
            return jsonify({"success": True, "message": "Comment updated"})
        else:
            return jsonify({"error": "Failed to update comment"}), 400
    except Exception as e:
        return jsonify({"error": f"Error updating comment: {str(e)}"}), 500

@app.route('/api/prompts/comments/<comment_id>', methods=['DELETE'])
@log_request_response
def delete_prompt_comment(comment_id):
    """Delete a comment"""
    if not HAS_DATABASE_APIS or not comments_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = comments_api.delete_comment(comment_id, uid)
        if success:
            return jsonify({"success": True, "message": "Comment deleted"})
        else:
            return jsonify({"error": "Failed to delete comment"}), 400
    except Exception as e:
        return jsonify({"error": f"Error deleting comment: {str(e)}"}), 500

# Prompt shares endpoints
try:
    from backend.prompt_shares_api import PromptSharesAPI
    shares_api = None
    if HAS_DATABASE_APIS:
        shares_api = PromptSharesAPI()
except ImportError:
    shares_api = None

@app.route('/api/prompts/<conversation_id>/share', methods=['POST'])
@log_request_response
def share_prompt(conversation_id):
    """Share a prompt with another user"""
    if not HAS_DATABASE_APIS or not shares_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json() or {}
        shared_with = data.get('shared_with')
        permission_level = data.get('permission_level', 'read')
        
        if not shared_with:
            return jsonify({"error": "shared_with is required"}), 400
        
        success = shares_api.share_prompt(conversation_id, uid, shared_with, permission_level)
        if success:
            return jsonify({"success": True, "message": "Prompt shared"})
        else:
            return jsonify({"error": "Failed to share prompt"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error sharing prompt: {str(e)}"}), 500

@app.route('/api/prompts/shared-with-me', methods=['GET'])
@log_request_response
def get_shared_with_me():
    """Get prompts shared with the current user"""
    if not HAS_DATABASE_APIS or not shares_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 50))
        shares = shares_api.get_shared_with_me(uid, limit)
        return jsonify({"shares": shares})
    except Exception as e:
        return jsonify({"error": f"Error loading shared prompts: {str(e)}"}), 500

@app.route('/api/prompts/shared-by-me', methods=['GET'])
@log_request_response
def get_shared_by_me():
    """Get prompts shared by the current user"""
    if not HAS_DATABASE_APIS or not shares_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 50))
        shares = shares_api.get_shared_by_me(uid, limit)
        return jsonify({"shares": shares})
    except Exception as e:
        return jsonify({"error": f"Error loading shared prompts: {str(e)}"}), 500

@app.route('/api/prompts/<conversation_id>/share/<shared_with>', methods=['DELETE'])
@log_request_response
def revoke_share(conversation_id, shared_with):
    """Revoke a share"""
    if not HAS_DATABASE_APIS or not shares_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        success = shares_api.revoke_share(conversation_id, uid, shared_with)
        if success:
            return jsonify({"success": True, "message": "Share revoked"})
        else:
            return jsonify({"error": "Failed to revoke share"}), 400
    except Exception as e:
        return jsonify({"error": f"Error revoking share: {str(e)}"}), 500

# Prompt history endpoints
try:
    from backend.prompt_history_api import PromptHistoryAPI
    history_api = None
    if HAS_DATABASE_APIS:
        history_api = PromptHistoryAPI()
except ImportError:
    history_api = None

@app.route('/api/prompts/<conversation_id>/history', methods=['GET'])
@log_request_response
def get_prompt_history(conversation_id):
    """Get history for a prompt"""
    if not HAS_DATABASE_APIS or not history_api:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 100))
        history = history_api.get_prompt_history(conversation_id, uid, limit)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": f"Error loading history: {str(e)}"}), 500

# Projects endpoints
@app.route('/api/projects', methods=['GET'])
@log_request_response
def get_projects():
    """Get all projects for a user"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info("GET /api/projects")
    
    if not HAS_DATABASE_APIS or not projects_api:
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Database APIs not available")
        return jsonify({
            "error": "Database connection not available",
            "message": "DATABASE_URL is not configured or contains invalid values (like 'hostname' placeholder). Please check your environment variables in Railway/production settings.",
            "code": "DATABASE_NOT_CONFIGURED"
        }), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("No user ID available for get_projects")
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Fetching projects", {"user_id": uid[:8] + "...", "include_archived": include_archived})
        
        projects = projects_api.get_all_projects(uid, include_archived=include_archived)
        
        # Note: We don't automatically create default projects anymore
        # "Archived Unassigned Chats" should be created by the frontend when needed
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Projects fetched successfully", {"count": len(projects)})
        
        return jsonify({"projects": projects})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error loading projects: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Projects API error: {error_detail}")
        return jsonify({"error": f"Error loading projects: {str(e)}"}), 500

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID"""
    if not HAS_DATABASE_APIS or not projects_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        project = projects_api.get_project(project_id, uid)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project)
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error loading project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Project API error: {error_detail}")
        return jsonify({"error": f"Error loading project: {str(e)}"}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """
    Create a new project - Top-level container for user assets
    
    Architecture:
    - Each user has their own projects (user-scoped)
    - Projects contain: chats, attachments, and memories
    - Projects are the top-level container for Milvus collections
    - All assets are organized under projects and tied to user_id
    """
    print("=" * 60)
    print("📝 [API] POST /api/projects - Project Creation Request")
    print("=" * 60)
    
    if not HAS_DATABASE_APIS or not projects_api:
        print("❌ [API] Database APIs not available")
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        data = request.get_json()
        project_name = data.get('name') if data else None
        project_description = data.get('description') if data else None
        
        print(f"📝 [API] Request data: name='{project_name}', description='{project_description[:50] if project_description else None}...'")
        
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            print("❌ [API] No user ID found - authentication required")
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        print(f"📝 [API] User ID: {uid[:8]}...")
        print(f"📝 [API] Calling projects_api.create_project...")
        
        project_id = projects_api.create_project(
            uid,
            name=project_name,
            description=project_description
        )
        
        print(f"✅ [API] Project created successfully: {project_id}")
        print(f"📝 [API] Project structure:")
        print(f"   - User ID: {uid[:8]}... (user-scoped)")
        print(f"   - Project ID: {project_id}")
        print(f"   - Contains: chats, attachments, memories")
        print(f"   - Top-level container for Milvus collections")
        print("=" * 60)
        
        return jsonify({"id": project_id, "success": True})
    except ConnectionError as e:
        error_msg = str(e)
        print(f"❌ [API] Database connection error: {error_msg}")
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            print(f"❌ [API] Invalid DATABASE_URL detected")
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error creating project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ [API] Create project error: {error_detail}")
        print("=" * 60)
        return jsonify({"error": f"Error creating project: {str(e)}"}), 500

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project"""
    if not HAS_DATABASE_APIS or not projects_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        data = request.get_json()
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        success = projects_api.update_project(
            project_id,
            uid,
            name=data.get('name'),
            description=data.get('description'),
            is_archived=data.get('is_archived')
        )
        if not success:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"success": True})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error updating project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Update project error: {error_detail}")
        return jsonify({"error": f"Error updating project: {str(e)}"}), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project (soft delete by archiving)"""
    import traceback
    print("=" * 80)
    print("🗑️🗑️🗑️ API: PROJECT DELETION REQUEST 🗑️🗑️🗑️")
    print(f"🗑️ [API] Project ID: {project_id}")
    print(f"🗑️ [API] Timestamp: {datetime.now().isoformat()}")
    print(f"🗑️ [API] Call stack:")
    for line in traceback.format_stack():
        print(f"   {line.strip()}")
    print("=" * 80)
    
    if not HAS_DATABASE_APIS or not projects_api:
        print("❌ [API] Database APIs not available")
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            print("❌ [API] No user ID found - authentication required")
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        print(f"🗑️ [API] User ID: {uid[:8]}...")
        print(f"🗑️ [API] Calling projects_api.delete_project...")
        success = projects_api.delete_project(project_id, uid)
        
        if success:
            print(f"✅ [API] Project deletion successful: {project_id}")
        else:
            print(f"❌ [API] Project deletion failed: {project_id}")
        print("=" * 80)
        if not success:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"success": True})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error deleting project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Delete project error: {error_detail}")
        return jsonify({"error": f"Error deleting project: {str(e)}"}), 500

@app.route('/api/projects/cleanup-duplicates', methods=['POST'])
def cleanup_duplicate_projects():
    """Clean up duplicate 'Default Project' entries for the current user"""
    if not HAS_DATABASE_APIS or not projects_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        result = cleanup_duplicate_default_projects(uid)
        
        if "error" in result:
            return jsonify(result), 500
        
        return jsonify(result)
    except Exception as e:
        import traceback
        error_detail = f"Error cleaning up duplicate projects: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Cleanup duplicate projects error: {error_detail}")
        return jsonify({"error": f"Error cleaning up duplicate projects: {str(e)}"}), 500

# Conversations endpoints
@app.route('/api/conversations', methods=['GET'])
@log_request_response
def get_conversations():
    """Get all conversations for a user"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info("GET /api/conversations")
    
    if not HAS_DATABASE_APIS or not conversation_api:
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Database APIs not available")
        return jsonify({
            "error": "Database connection not available",
            "message": "DATABASE_URL is not configured or contains invalid values (like 'hostname' placeholder). Please check your environment variables in Railway/production settings.",
            "code": "DATABASE_NOT_CONFIGURED"
        }), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        
        if not uid:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("No user ID available for get_conversations")
            return jsonify({
                "error": "User ID required",
                "message": "Unable to determine user context",
                "code": "USER_ID_REQUIRED"
            }), 401
        # Get project_id from query parameter
        project_id = request.args.get('project_id')
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        limit = request.args.get('limit', type=int)  # Get optional limit parameter
        
        # If project_id provided, validate it belongs to the user
        if project_id:
            try:
                # Include archived projects in validation - user can view conversations in archived projects
                projects = projects_api.get_all_projects(uid, include_archived=True)
                project_exists = any(str(p['id']) == project_id for p in projects)
                if not project_exists:
                    print(f"⚠️ Project {project_id} not found or doesn't belong to user {uid[:8]}...")
                    return jsonify({
                        "error": f"Project {project_id} not found or access denied",
                        "code": "PROJECT_NOT_FOUND"
                    }), 404
            except Exception as e:
                print(f"⚠️ Error validating project_id: {e}")
                return jsonify({
                    "error": f"Error validating project: {str(e)}",
                    "code": "PROJECT_VALIDATION_ERROR"
                }), 500
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Fetching conversations", {
                "user_id": uid[:8] + "...",
                "project_id": project_id if project_id else "ALL_PROJECTS",
                "include_archived": include_archived,
                "limit": limit
            })
        
        # Get conversations - if project_id is None, get all conversations for user
        conversations = conversation_api.get_all_conversations(
            uid,
            project_id=project_id,  # None means get all conversations
            include_archived=include_archived,
            limit=limit
        )
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Conversations fetched successfully", {"count": len(conversations)})
        
        return jsonify({"conversations": conversations})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error loading conversations: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Conversations API error: {error_detail}")
        return jsonify({"error": f"Error loading conversations: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "User ID required",
                "message": "Unable to determine user context",
                "code": "USER_ID_REQUIRED"
            }), 401
        
        conversation = conversation_api.get_conversation(conversation_id, uid)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify(conversation)
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error loading conversation: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Get conversation error: {error_detail}")
        return jsonify({"error": f"Error loading conversation: {str(e)}"}), 500

@app.route('/api/conversations', methods=['POST'])
@log_request_response
def create_conversation():
    """Create a new conversation"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info("POST /api/conversations")
    
    if not HAS_DATABASE_APIS or not conversation_api:
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Database APIs not available")
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        data = request.get_json()
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Creating conversation", {
                "project_id": data.get('project_id'),
                "title": data.get('title')
            })
        
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("No user ID available for create_conversation")
            return jsonify({
                "error": "User ID required",
                "message": "Unable to determine user context",
                "code": "USER_ID_REQUIRED"
            }), 401
        
        # Get project_id from request, or create/use default project as fallback
        project_id = data.get('project_id')
        
        if project_id:
            # Validate that the project exists and belongs to the user
            try:
                projects = projects_api.get_all_projects(uid, include_archived=False)
                project_exists = any(str(p['id']) == project_id for p in projects)
                if not project_exists:
                    print(f"⚠️ Project {project_id} not found or doesn't belong to user, will create default project")
                    project_id = None
            except Exception as e:
                print(f"⚠️ Error validating project_id: {e}, will create default project")
                project_id = None
        
        # If no project_id provided or invalid, create a default "Archived Unassigned Chats" project
        if not project_id:
            try:
                # Check if default project already exists
                projects = projects_api.get_all_projects(uid, include_archived=True)
                default_project = next((p for p in projects if p.get('name') == 'Archived Unassigned Chats'), None)
                
                if default_project:
                    project_id = default_project['id']
                    print(f"✅ Using existing default project: {project_id}")
                else:
                    # Create default project
                    project_id = projects_api.create_project(
                        uid,
                        name='Archived Unassigned Chats',
                        description='Default project for conversations without a specific project'
                    )
                    print(f"✅ Created default project: {project_id}")
                
                if DEBUG_LOGGING_ENABLED:
                    debug_logger.info("Using/created default project", {
                        "user_id": uid[:8] + "...",
                        "project_id": project_id
                    })
            except Exception as e:
                print(f"❌ Failed to create/find default project: {e}")
                return jsonify({
                    "error": "Failed to create default project",
                    "message": f"Could not create or find a default project: {str(e)}",
                    "code": "PROJECT_CREATION_FAILED"
                }), 500
        
        # Log conversation creation with full details
        print(f"📝 Creating conversation: user_id={uid[:8]}..., project_id={project_id}, title={data.get('title', 'New Chat')}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Creating conversation", {
                "user_id": uid[:8] + "...",
                "project_id": project_id,
                "title": data.get('title', 'New Chat')
            })
        
        conversation_id = conversation_api.create_conversation(
            uid,
            project_id=project_id,
            title=data.get('title')
        )
        
        print(f"✅ Conversation created successfully: conversation_id={conversation_id}, project_id={project_id}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Conversation created successfully", {
                "conversation_id": conversation_id,
                "user_id": uid[:8] + "...",
                "project_id": project_id,
                "title": data.get('title', 'New Chat')
            })
        
        return jsonify({"id": conversation_id, "success": True})
    except Exception as db_error:
        # Catch database errors (like invalid UUID) and provide clear message
        error_msg = str(db_error)
        import traceback
        error_detail = traceback.format_exc()
        
        # Log to file AND stdout (for Railway logs)
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/conversation_error.log", "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Create Conversation Error - {datetime.now().isoformat()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Traceback:\n{error_detail}\n")
        except Exception as log_error:
            print(f"⚠️ Could not write to error log file: {log_error}")
        
        # ALSO print to stdout (Railway will capture this)
        print(f"\n{'='*60}")
        print(f"❌ CREATE CONVERSATION ERROR - {datetime.now().isoformat()}")
        print(f"{'='*60}")
        print(f"Error: {error_msg}")
        print(f"Traceback:\n{error_detail}")
        print(f"{'='*60}\n")
        
        # Check for UUID errors
        if 'invalid input syntax for type uuid' in error_msg.lower() or 'uuid' in error_msg.lower():
            return jsonify({
                "error": "Invalid user ID format",
                "message": f"Database error: Invalid UUID format. Please refresh the page and log in again with your API key. Error details: {error_msg[:200]}",
                "code": "INVALID_UUID",
                "detail": error_msg[:500]
            }), 400
        return jsonify({"error": f"Error creating conversation: {error_msg}"}), 500
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        import traceback
        error_detail = f"Error creating conversation: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Create conversation error: {error_detail}")
        return jsonify({"error": f"Error creating conversation: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>', methods=['PUT', 'PATCH'])
@log_request_response
def update_conversation(conversation_id):
    """Update a conversation"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info(f"PUT /api/conversations/{conversation_id}")
    
    if not HAS_DATABASE_APIS or not conversation_api:
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Database APIs not available")
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        data = request.get_json()
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Updating conversation", {
                "conversation_id": conversation_id,
                "title": data.get('title'),
                "message_count": data.get('message_count')
            })
        
        # Get user ID from header or API key (get_user_id_from_header handles both)
        uid = get_user_id_from_header()
        if not uid:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("No user ID available for update_conversation")
            return jsonify({
                "error": "Authentication required",
                "message": "No valid user ID found. Railway should have authenticated this request.",
                "code": "AUTHENTICATION_REQUIRED"
            }), 401
        
        success = conversation_api.update_conversation(
            conversation_id,
            uid,
            title=data.get('title'),
            message_count=data.get('message_count'),
            project_id=data.get('project_id')
        )
        
        if not success:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("Conversation not found", {
                    "conversation_id": conversation_id,
                    "user_id": uid[:8] + "..."
                })
            return jsonify({"error": "Conversation not found"}), 404
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Conversation updated successfully", {
                "conversation_id": conversation_id
            })
        
        return jsonify({"success": True})
    except Exception as db_error:
        # Catch database errors (like invalid UUID) and provide clear message
        error_msg = str(db_error)
        import traceback
        error_detail = traceback.format_exc()
        
        # Log to file AND stdout (for Railway logs)
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/conversation_error.log", "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Update Conversation Error - {datetime.now().isoformat()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Traceback:\n{error_detail}\n")
        except Exception as log_error:
            print(f"⚠️ Could not write to error log file: {log_error}")
        
        # ALSO print to stdout (Railway will capture this)
        print(f"\n{'='*60}")
        print(f"❌ UPDATE CONVERSATION ERROR - {datetime.now().isoformat()}")
        print(f"{'='*60}")
        print(f"Error: {error_msg}")
        print(f"Traceback:\n{error_detail}")
        print(f"{'='*60}\n")
        
        # Check for UUID errors
        if 'invalid input syntax for type uuid' in error_msg.lower() or 'uuid' in error_msg.lower():
            return jsonify({
                "error": "Invalid user ID format",
                "message": f"Database error: Invalid UUID format. Please refresh the page and log in again with your API key. Error: {error_msg[:200]}",
                "code": "INVALID_UUID",
                "detail": error_msg[:500]
            }), 400
        return jsonify({"error": f"Error saving conversation: {error_msg}"}), 500
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error saving conversation: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        uid = get_user_id_from_header()
        success = conversation_api.delete_conversation(conversation_id, uid)
        if not success:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify({"success": True})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error deleting conversation: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id):
    """Archive or unarchive a conversation"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        archived = request.args.get('archived', 'true').lower() == 'true'
        uid = get_user_id_from_header()
        success = conversation_api.archive_conversation(conversation_id, uid, archived)
        if not success:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify({"success": True})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error archiving conversation: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    """Get messages for a conversation"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        # Get user ID with default fallback for single-user systems
        uid = get_user_id_or_default()
        if not uid:
            return jsonify({
                "error": "User ID required",
                "message": "Unable to determine user context",
                "code": "USER_ID_REQUIRED"
            }), 401
        
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Track memory for message retrieval
        with track_operation("get_messages", {
            "conversation_id": conversation_id,
            "limit": limit,
            "offset": offset
        }):
            messages = conversation_api.get_messages(conversation_id, uid, limit, offset)
        
        return jsonify({
            "messages": messages,
            "count": len(messages),
            "limit": limit,
            "offset": offset
        })
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error loading messages: {str(e)}"}), 500

@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
@log_request_response
def add_message(conversation_id):
    """Add a message to a conversation"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info(f"POST /api/conversations/{conversation_id}/messages")
    
    if not HAS_DATABASE_APIS or not conversation_api:
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Database APIs not available")
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        data = request.get_json()
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.debug("Adding message", {
                "conversation_id": conversation_id,
                "role": data.get('role'),
                "content_length": len(data.get('content', '')) if data.get('content') else 0
            })
        
        # Get user ID with local development fallback
        uid = get_user_id_or_default()
        if not uid:
            if DEBUG_LOGGING_ENABLED:
                debug_logger.warning("No user ID available for add_message")
            return jsonify({
                "error": "User ID required",
                "message": "Unable to determine user context",
                "code": "USER_ID_REQUIRED"
            }), 401
        
        # Log message addition with full details
        content_preview = data.get('content', '')[:100] + '...' if len(data.get('content', '')) > 100 else data.get('content', '')
        print(f"💬 Adding message: conversation_id={conversation_id}, role={data.get('role')}, content_length={len(data.get('content', ''))}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Adding message", {
                "conversation_id": conversation_id,
                "user_id": uid[:8] + "...",
                "role": data.get('role'),
                "content_length": len(data.get('content', ''))
            })
        
        # Track memory for message addition
        with track_operation("add_message", {
            "conversation_id": conversation_id,
            "role": data.get('role'),
            "content_length": len(data.get('content', ''))
        }):
            # Pass memory_api to enable persistent memory storage for conversations
            message_id = conversation_api.add_message(
                conversation_id,
                uid,
                data.get('role'),
                data.get('content'),
                data.get('metadata'),
                memory_api=memory_api if HAS_MEMORY_SYSTEM else None,
                save_to_memory=HAS_MEMORY_SYSTEM and memory_api is not None
            )
        
        print(f"✅ Message saved to database: message_id={message_id}, conversation_id={conversation_id}")
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Message added successfully", {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "user_id": uid[:8] + "...",
                "role": data.get('role'),
                "content_length": len(data.get('content', ''))
            })
        
        return jsonify({"id": message_id, "success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as db_error:
        # Catch database errors (like invalid UUID) and provide clear message
        error_msg = str(db_error)
        import traceback
        error_detail = traceback.format_exc()
        
        # Log to file AND stdout (for Railway logs)
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/conversation_error.log", "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Add Message Error - {datetime.now().isoformat()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Traceback:\n{error_detail}\n")
        except Exception as log_error:
            print(f"⚠️ Could not write to error log file: {log_error}")
        
        # ALSO print to stdout (Railway will capture this)
        print(f"\n{'='*60}")
        print(f"❌ ADD MESSAGE ERROR - {datetime.now().isoformat()}")
        print(f"{'='*60}")
        print(f"Error: {error_msg}")
        print(f"Traceback:\n{error_detail}")
        print(f"{'='*60}\n")
        
        # Check for UUID errors
        if 'invalid input syntax for type uuid' in error_msg.lower() or 'uuid' in error_msg.lower():
            return jsonify({
                "error": "Invalid user ID format",
                "message": f"Database error: Invalid UUID format. Please refresh the page and log in again with your API key. Error: {error_msg[:200]}",
                "code": "INVALID_UUID",
                "detail": error_msg[:500]
            }), 400
        return jsonify({"error": f"Error adding message: {error_msg}"}), 500
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error saving message: {str(e)}"}), 500

@app.route('/api/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete a message"""
    if not HAS_DATABASE_APIS or not conversation_api:
        return jsonify({"error": "Database not available. Please check your connection."}), 503
    
    try:
        uid = get_user_id_from_header()
        success = conversation_api.delete_message(message_id, uid)
        if not success:
            return jsonify({"error": "Message not found"}), 404
        return jsonify({"success": True})
    except ConnectionError as e:
        error_msg = str(e)
        # Check if it's a hostname resolution error
        if 'hostname' in error_msg.lower() or 'could not translate' in error_msg.lower():
            return jsonify({
                "error": "Database connection error",
                "message": f"Invalid DATABASE_URL: {error_msg}. The DATABASE_URL appears to contain a placeholder value like 'hostname'. Please set a valid DATABASE_URL in your Railway/production environment variables.",
                "code": "INVALID_DATABASE_URL"
            }), 503
        return jsonify({"error": str(e), "code": "DATABASE_CONNECTION_ERROR"}), 503
    except Exception as e:
        return jsonify({"error": f"Error deleting message: {str(e)}"}), 500


# --- Database Migration Endpoint ---

@app.route('/api/migrate', methods=['POST'])
@log_request_response
def run_migration():
    """Run database migration to create missing tables"""
    if DEBUG_LOGGING_ENABLED:
        debug_logger.info("POST /api/migrate")
    
    if not HAS_DATABASE_APIS:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        # Simple auth - require API key (any valid API key)
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Get database connection
        if conversation_api:
            conn = conversation_api.get_db()
        else:
            # Fallback: create connection directly
            import psycopg2
            from urllib.parse import urlparse
            database_url = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
            if not database_url:
                return jsonify({"error": "DATABASE_URL not configured"}), 500
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/')
            )
        
        cursor = conn.cursor()
        
        # 1. Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                description TEXT,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deleted_at TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
            CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_projects_is_archived ON projects(is_archived);
        """)
        
        # 2. Add metadata column to conversations if missing
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' AND column_name = 'metadata'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE conversations ADD COLUMN metadata JSONB DEFAULT '{}'")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON conversations USING GIN(metadata)")
        
        # 3. Ensure conversations table has all required columns
        for column, definition in [
            ('deleted_at', 'TIMESTAMP'),
            ('is_archived', 'BOOLEAN DEFAULT FALSE'),
            ('updated_at', 'TIMESTAMP DEFAULT NOW()')
        ]:
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'conversations' AND column_name = '{column}'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE conversations ADD COLUMN {column} {definition}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.info("Migration completed successfully")
        
        return jsonify({
            "success": True,
            "message": "Migration completed",
            "tables_created": ["projects"],
            "columns_added": ["conversations.metadata", "conversations.deleted_at", "conversations.is_archived", "conversations.updated_at"]
        })
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        error_detail = traceback.format_exc()
        
        if DEBUG_LOGGING_ENABLED:
            debug_logger.error("Migration failed", e, {
                "error_message": error_msg,
                "traceback": error_detail
            })
        
        return jsonify({
            "error": "Migration failed",
            "message": error_msg,
            "detail": error_detail
        }), 500

# --- Stub endpoints for features not yet implemented ---

@app.route('/api/prompts/<prompt_id>/ratings', methods=['GET'])
def get_prompt_ratings(prompt_id):
    """Get ratings for a prompt (stub - feature not yet implemented)"""
    return jsonify({
        "ratings": [],
        "average": 0,
        "count": 0,
        "message": "Ratings feature not yet implemented"
    })

@app.route('/api/prompts/<prompt_id>/shares', methods=['GET'])
def get_prompt_shares(prompt_id):
    """Get share status for a prompt (stub - feature not yet implemented)"""
    return jsonify({
        "shares": [],
        "count": 0,
        "message": "Sharing feature not yet implemented"
    })

# --- Frontend Serving (must be last to not catch API routes) ---

@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def serve_frontend(path):
    """Serve the React frontend - only handles GET requests, API routes handle POST/PUT/DELETE"""
    # Don't serve frontend for API routes - let Flask 404 handler deal with it
    if path.startswith('api/'):
        from flask import abort
        abort(404)
    
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')
    
    # Debug logging for Railway deployment
    if not os.path.exists(frontend_dir):
        print(f"⚠️ Frontend dist directory not found: {frontend_dir}")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   __file__ location: {__file__}")
        print(f"   Directory contents: {os.listdir(os.path.dirname(__file__))}")
        return jsonify({
            "error": "Frontend not built",
            "message": f"Frontend dist directory not found at {frontend_dir}. Please ensure the frontend build completed successfully.",
            "debug": {
                "cwd": os.getcwd(),
                "frontend_dir": frontend_dir,
                "exists": os.path.exists(frontend_dir)
            }
        }), 500
    
    # Check if index.html exists
    index_path = os.path.join(frontend_dir, 'index.html')
    if not os.path.exists(index_path):
        print(f"⚠️ Frontend index.html not found: {index_path}")
        print(f"   Dist directory contents: {os.listdir(frontend_dir) if os.path.exists(frontend_dir) else 'N/A'}")
        return jsonify({
            "error": "Frontend index.html not found",
            "message": f"Frontend index.html not found at {index_path}. Please ensure the frontend build completed successfully."
        }), 500
    
    # Serve the file
    if path != "" and os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)
    else:
        return send_from_directory(frontend_dir, 'index.html')


def run_startup_migrations():
    """Run migrations on app startup - non-blocking"""
    if not HAS_DATABASE_APIS:
        print("⚠️  Database not available, skipping startup migrations")
        return
    
    try:
        if conversation_api:
            conn = conversation_api.get_db()
        else:
            import psycopg2
            from urllib.parse import urlparse
            database_url = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
            if not database_url:
                print("⚠️  DATABASE_URL not configured, skipping migrations")
                return
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/')
            )
        
        cursor = conn.cursor()
        
        # Create projects table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                description TEXT,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deleted_at TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
        """)
        
        # Add metadata column if missing
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' AND column_name = 'metadata'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE conversations ADD COLUMN metadata JSONB DEFAULT '{}'")
            print("✅ Added metadata column to conversations")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Startup migrations completed")
    except Exception as e:
        print(f"⚠️  Startup migration error (non-fatal): {e}")
        # Don't crash the app if migration fails

if __name__ == '__main__':
    # Run migrations on startup
    if HAS_DATABASE_APIS:
        try:
            run_startup_migrations()
        except Exception as e:
            print(f"⚠️  Startup migration error (non-fatal): {e}")
            # Don't crash the app if migration fails
    
    print("🚀 Grace AI API Server starting...")
    print(f"📡 LLM Backend: {LM_API_URL}")
    # Load vectorstore lazily - don't load at startup to save memory
    # load_logs_to_vectorstore()  # Disabled at startup - will load on first use
    print(f"📰 News Index: {'Loaded' if index else 'Not Found'}")
    
    # In production, bind to localhost (port from GRACE_PORT, default 8001) for Apache proxy
    # In development, allow external connections
    port = int(os.getenv('GRACE_PORT', '8001'))
    is_production = os.getenv('PRODUCTION', 'false').lower() == 'true'
    
    if is_production:
        host = '127.0.0.1'
        print(f"🚀 Starting Grace API in PRODUCTION mode (localhost:{port} for Apache proxy)")
        print(f"🎯 Server running on http://localhost:{port} (proxied via Apache)")
    else:
        host = '0.0.0.0'
        print(f"🚀 Starting Grace API in DEVELOPMENT mode (0.0.0.0:{port})")
        print(f"🎯 Server running on http://localhost:{port}")
    
    # Disable debug mode to avoid reloader issues with multiple processes
    # Global error handler is already registered at line 363
    # Enable SO_REUSEADDR so we can bind immediately after restart (avoids "Address already in use" from TIME_WAIT)
    import socket
    _orig_socket = socket.socket
    def _socket_reuse(*args, **kwargs):
        s = _orig_socket(*args, **kwargs)
        if args and len(args) >= 2 and args[0] == socket.AF_INET and args[1] == socket.SOCK_STREAM:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s
    socket.socket = _socket_reuse
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ Fatal error starting server: {e}")
        import traceback
        traceback.print_exc()
        raise
