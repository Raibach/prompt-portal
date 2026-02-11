"""
Deployment Logger - Centralized logging for GitHub Actions deployments

Captures deployment status, errors, and logs in a structured format.
Integrates with existing logging infrastructure.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Deployment log file
DEPLOYMENT_LOG = LOG_DIR / "deployment.log"

class DeploymentLogger:
    """Centralized deployment logging system"""
    
    @staticmethod
    def _write_log(entry: Dict[str, Any]):
        """Write log entry to file"""
        try:
            with open(DEPLOYMENT_LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️ Failed to write to {DEPLOYMENT_LOG}: {e}")
    
    @staticmethod
    def log_deployment(
        run_id: str,
        commit: str,
        status: str,
        logs: Optional[str] = None,
        error: Optional[str] = None,
        failed_step: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        started_at: Optional[str] = None
    ):
        """Log deployment attempt"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "deployment",
            "run_id": run_id,
            "commit": commit,
            "status": status,  # "success", "failed", "in_progress"
            "failed_step": failed_step,
            "error": error,
            "duration_seconds": duration_seconds,
            "started_at": started_at,
            "logs": logs[:10000] if logs else None  # Truncate very long logs
        }
        
        DeploymentLogger._write_log(entry)
        
        # Print to console
        status_emoji = "✅" if status == "success" else "❌" if status == "failed" else "🔄"
        print(f"{status_emoji} Deployment {run_id}: {status}")
        if error:
            print(f"   Error: {error}")
    
    @staticmethod
    def get_current_status() -> Dict[str, Any]:
        """Get current deployment status"""
        try:
            if not DEPLOYMENT_LOG.exists():
                return {
                    "status": "unknown",
                    "message": "No deployments logged yet"
                }
            
            # Read last deployment
            with open(DEPLOYMENT_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    return {"status": "unknown", "message": "No deployments"}
                
                last_entry = json.loads(lines[-1].strip())
                return {
                    "status": last_entry.get("status", "unknown"),
                    "run_id": last_entry.get("run_id"),
                    "commit": last_entry.get("commit"),
                    "started_at": last_entry.get("started_at"),
                    "duration_seconds": last_entry.get("duration_seconds"),
                    "failed_step": last_entry.get("failed_step"),
                    "error": last_entry.get("error"),
                    "logs": last_entry.get("logs"),
                    "timestamp": last_entry.get("timestamp")
                }
        except Exception as e:
            print(f"⚠️ Error getting current status: {e}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def get_recent(limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent deployment attempts"""
        deployments = []
        try:
            if DEPLOYMENT_LOG.exists():
                with open(DEPLOYMENT_LOG, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        try:
                            entry = json.loads(line.strip())
                            # Don't include full logs in list view
                            if 'logs' in entry:
                                entry['logs'] = f"{len(entry['logs'])} chars" if entry['logs'] else None
                            deployments.append(entry)
                        except:
                            pass
        except Exception as e:
            print(f"⚠️ Error reading deployment history: {e}")
        
        return deployments[-limit:]  # Return most recent
    
    @staticmethod
    def get_success_rate(hours: int = 24) -> float:
        """Calculate deployment success rate for last N hours"""
        try:
            if not DEPLOYMENT_LOG.exists():
                return 0.0
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(DEPLOYMENT_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            recent_deployments = []
            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(entry.get('timestamp', ''))
                    if timestamp >= cutoff_time:
                        recent_deployments.append(entry)
                except:
                    pass
            
            if not recent_deployments:
                return 0.0
            
            successful = sum(1 for d in recent_deployments if d.get('status') == 'success')
            return successful / len(recent_deployments)
            
        except Exception as e:
            print(f"⚠️ Error calculating success rate: {e}")
            return 0.0
    
    @staticmethod
    def get_last_success() -> Optional[str]:
        """Get timestamp of last successful deployment"""
        try:
            if not DEPLOYMENT_LOG.exists():
                return None
            
            with open(DEPLOYMENT_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Search backwards for last success
            for line in reversed(lines):
                try:
                    entry = json.loads(line.strip())
                    if entry.get('status') == 'success':
                        return entry.get('timestamp')
                except:
                    pass
            
            return None
        except Exception as e:
            print(f"⚠️ Error finding last success: {e}")
            return None

# Global instance
deployment_logger = DeploymentLogger()
