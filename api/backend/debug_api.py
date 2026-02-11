"""
Debug API Endpoints

Provides endpoints to view logs, debug information, and system status.
"""

import os
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from backend.debug_logger import debug_logger, ERROR_LOG, DEBUG_LOG, REQUEST_LOG, DATABASE_LOG
from backend.deployment_logger import deployment_logger, DEPLOYMENT_LOG
from pathlib import Path

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/api/debug/logs', methods=['GET'])
def get_logs():
    """Get recent logs"""
    level = request.args.get('level')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    limit = int(request.args.get('limit', 100))
    since_hours = int(request.args.get('since_hours', 24))
    
    since = datetime.now() - timedelta(hours=since_hours) if since_hours > 0 else None
    
    logs = debug_logger.get_logs(level=level, limit=limit, since=since)
    
    return jsonify({
        "logs": logs,
        "count": len(logs),
        "filters": {
            "level": level,
            "limit": limit,
            "since_hours": since_hours
        }
    })

@debug_bp.route('/api/debug/errors', methods=['GET'])
def get_errors():
    """Get recent errors"""
    limit = int(request.args.get('limit', 50))
    errors = debug_logger.get_recent_errors(limit=limit)
    
    return jsonify({
        "errors": errors,
        "count": len(errors)
    })

@debug_bp.route('/api/debug/status', methods=['GET'])
def get_status():
    """Get system status and debug information"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "database_url_set": bool(os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')),
            "database_public_url_set": bool(os.getenv('DATABASE_PUBLIC_URL')),
            "api_keys_set": bool(os.getenv('GRACE_API_KEYS')),
        },
        "log_files": {
            "debug_log": {
                "path": str(DEBUG_LOG),
                "exists": DEBUG_LOG.exists(),
                "size_bytes": DEBUG_LOG.stat().st_size if DEBUG_LOG.exists() else 0
            },
            "error_log": {
                "path": str(ERROR_LOG),
                "exists": ERROR_LOG.exists(),
                "size_bytes": ERROR_LOG.stat().st_size if ERROR_LOG.exists() else 0
            },
            "request_log": {
                "path": str(REQUEST_LOG),
                "exists": REQUEST_LOG.exists(),
                "size_bytes": REQUEST_LOG.stat().st_size if REQUEST_LOG.exists() else 0
            },
            "database_log": {
                "path": str(DATABASE_LOG),
                "exists": DATABASE_LOG.exists(),
                "size_bytes": DATABASE_LOG.stat().st_size if DATABASE_LOG.exists() else 0
            },
            "deployment_log": {
                "path": str(DEPLOYMENT_LOG),
                "exists": DEPLOYMENT_LOG.exists(),
                "size_bytes": DEPLOYMENT_LOG.stat().st_size if DEPLOYMENT_LOG.exists() else 0
            }
        },
        "recent_errors_count": len(debug_logger.get_recent_errors(limit=10))
    }
    
    return jsonify(status)

@debug_bp.route('/api/debug/logs/file', methods=['GET'])
def get_log_file():
    """Get raw log file content"""
    log_type = request.args.get('type', 'error')  # error, debug, request, database
    
    log_files = {
        'error': ERROR_LOG,
        'debug': DEBUG_LOG,
        'request': REQUEST_LOG,
        'database': DATABASE_LOG
    }
    
    if log_type not in log_files:
        return jsonify({"error": f"Invalid log type: {log_type}"}), 400
    
    log_file = log_files[log_type]
    
    if not log_file.exists():
        return jsonify({"error": f"Log file not found: {log_file}"}), 404
    
    try:
        # Read last N lines
        lines = int(request.args.get('lines', 100))
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            "log_type": log_type,
            "log_file": str(log_file),
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "lines": [line.strip() for line in recent_lines]
        })
    except Exception as e:
        return jsonify({"error": f"Error reading log file: {str(e)}"}), 500

@debug_bp.route('/api/debug/test', methods=['POST'])
def test_logging():
    """Test logging system"""
    test_message = request.json.get('message', 'Test log message')
    level = request.json.get('level', 'INFO')
    
    log_method = getattr(debug_logger, level.lower(), debug_logger.info)
    log_method(test_message, context={"test": True})
    
    return jsonify({
        "success": True,
        "message": f"Logged {level} message: {test_message}"
    })

# ============================================================================
# COMMAND CENTER - Single endpoint for complete system status
# ============================================================================

@debug_bp.route('/api/debug/command-center', methods=['GET'])
def get_command_center():
    """
    Command Center - Complete system status in one API call.
    Designed for AI agents, monitoring systems, and autonomous models.
    """
    
    # Get deployment status
    current_deployment = deployment_logger.get_current_status()
    deployment_history = deployment_logger.get_recent(limit=10)
    success_rate = deployment_logger.get_success_rate(hours=24)
    last_success = deployment_logger.get_last_success()
    
    # Calculate system health score
    health_score = 1.0
    issues = []
    
    if current_deployment.get('status') == 'failed':
        health_score -= 0.3
        issues.append('deployment_failing')
    
    # Check SSH configuration
    ssh_configured = all([
        os.getenv('SSH_HOST'),
        os.getenv('SSH_PORT'),
        os.getenv('SSH_USERNAME'),
        os.getenv('SSH_PASSWORD')
    ])
    
    if not ssh_configured:
        health_score -= 0.2
        issues.append('ssh_not_configured')
    
    # Check database
    database_connected = bool(os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL'))
    if not database_connected:
        health_score -= 0.3
        issues.append('database_not_configured')
    
    # Get environment status
    missing_secrets = []
    if not os.getenv('SSH_HOST'):
        missing_secrets.append('SSH_HOST')
    if not os.getenv('SSH_PORT'):
        missing_secrets.append('SSH_PORT')
    if not os.getenv('SSH_USERNAME'):
        missing_secrets.append('SSH_USERNAME')
    if not os.getenv('SSH_PASSWORD'):
        missing_secrets.append('SSH_PASSWORD')
    
    # Generate action items
    actions_required = []
    if missing_secrets:
        actions_required.append({
            "priority": "high",
            "action": "add_github_secrets",
            "description": f"Add SSH secrets to GitHub: {', '.join(missing_secrets)}",
            "automated": False,
            "details": {
                "SSH_HOST": "ssh.raibach.net",
                "SSH_PORT": "18765",
                "SSH_USERNAME": "u2819-gkhlcvpg4gjm",
                "SSH_PASSWORD": "470659ICg$"
            }
        })
    
    # Get recent errors
    recent_errors = debug_logger.get_recent_errors(limit=10)
    
    # Determine overall system status
    if health_score >= 0.8:
        system_status = "healthy"
    elif health_score >= 0.5:
        system_status = "degraded"
    else:
        system_status = "unhealthy"
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "version": "1.0",
        "system": {
            "status": system_status,
            "health_score": round(health_score, 2),
            "issues": issues
        },
        "deployment": {
            "current": current_deployment,
            "history": deployment_history,
            "success_rate_24h": round(success_rate, 2),
            "last_successful_deploy": last_success
        },
        "environment": {
            "ssh_configured": ssh_configured,
            "missing_secrets": missing_secrets,
            "database_connected": database_connected,
            "backend_healthy": True,  # Can add actual health check later
            "frontend_deployed": True  # Can add actual check later
        },
        "actions_required": actions_required,
        "recent_errors": recent_errors,
        "logs": {
            "deployment": "/api/debug/logs/deployment",
            "errors": "/api/debug/errors",
            "database": "/api/debug/logs/file?type=database"
        }
    })

@debug_bp.route('/api/debug/deployment/webhook', methods=['POST'])
def deployment_webhook():
    """
    Webhook receiver for GitHub Actions deployments.
    GitHub Actions POSTs deployment status and logs here.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Log the deployment
        deployment_logger.log_deployment(
            run_id=data.get('run_id', 'unknown'),
            commit=data.get('commit', 'unknown'),
            status=data.get('status', 'unknown'),
            logs=data.get('logs'),
            error=data.get('error'),
            failed_step=data.get('failed_step'),
            duration_seconds=data.get('duration_seconds'),
            started_at=data.get('started_at')
        )
        
        return jsonify({
            "success": True,
            "message": "Deployment logged successfully"
        })
        
    except Exception as e:
        debug_logger.error("Failed to process deployment webhook", e)
        return jsonify({"error": str(e)}), 500

@debug_bp.route('/api/debug/logs/deployment', methods=['GET'])
def get_deployment_logs():
    """Get deployment logs"""
    limit = int(request.args.get('limit', 10))
    
    return jsonify({
        "deployments": deployment_logger.get_recent(limit=limit),
        "count": len(deployment_logger.get_recent(limit=limit))
    })

