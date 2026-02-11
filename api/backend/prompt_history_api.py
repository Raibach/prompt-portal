"""
Prompt History API - Handles audit log and version history for prompts
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
from backend.database_pool import DatabasePool


class PromptHistoryAPI:
    """API for managing prompt history and audit logs"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def log_action(
        self,
        conversation_id: str,
        user_id: str,
        action: str,
        changes: Optional[Dict] = None
    ) -> str:
        """
        Log an action to prompt history
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID performing action
            action: Action type (e.g., 'created', 'updated', 'published', 'archived')
            changes: Optional dictionary of changes
        
        Returns:
            str: History entry ID
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                INSERT INTO prompt_history (
                    conversation_id, user_id, action, changes
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                conversation_id,
                user_id,
                action,
                json.dumps(changes) if changes else None
            ))
            
            history_id = cursor.fetchone()['id']
            conn.commit()
            return str(history_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_prompt_history(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get history for a prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID (for RLS)
            limit: Maximum number of history entries
        
        Returns:
            List of history dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    ph.id,
                    ph.action,
                    ph.user_id,
                    ph.changes,
                    ph.timestamp,
                    u.email as user_email
                FROM prompt_history ph
                LEFT JOIN users u ON ph.user_id = u.id
                WHERE ph.conversation_id = %s
                ORDER BY ph.timestamp DESC
                LIMIT %s
            """, (conversation_id, limit))
            
            history_items = cursor.fetchall()
            
            result = []
            for item in history_items:
                history_dict = dict(item)
                # Parse changes JSONB
                if history_dict.get('changes') and isinstance(history_dict['changes'], str):
                    try:
                        history_dict['changes'] = json.loads(history_dict['changes'])
                    except:
                        pass
                result.append(history_dict)
            
            return result
        finally:
            cursor.close()
            conn.close()

