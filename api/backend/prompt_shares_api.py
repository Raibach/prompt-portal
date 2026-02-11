"""
Prompt Shares API - Handles sharing prompts with other users
"""

from typing import List, Dict, Optional
from backend.database_pool import DatabasePool


class PromptSharesAPI:
    """API for managing prompt shares"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def share_prompt(
        self,
        conversation_id: str,
        shared_by: str,
        shared_with: str,
        permission_level: str = 'read'
    ) -> bool:
        """
        Share a prompt with another user
        
        Args:
            conversation_id: Prompt ID
            shared_by: User ID sharing the prompt
            shared_with: User ID to share with
            permission_level: Permission level (read, write, admin)
        
        Returns:
            bool: True if successful
        """
        if permission_level not in ('read', 'write', 'admin'):
            raise ValueError("permission_level must be 'read', 'write', or 'admin'")
        
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, shared_by)
        
        try:
            cursor.execute("""
                INSERT INTO prompt_shares (
                    conversation_id, shared_by, shared_with, permission_level
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (conversation_id, shared_with) 
                DO UPDATE SET permission_level = EXCLUDED.permission_level
            """, (conversation_id, shared_by, shared_with, permission_level))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_shared_with_me(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get prompts shared with the user
        
        Args:
            user_id: User ID
            limit: Maximum number of prompts
        
        Returns:
            List of prompt dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    ps.conversation_id,
                    ps.permission_level,
                    ps.created_at,
                    c.title,
                    c.prompt_status,
                    u.email as shared_by_email
                FROM prompt_shares ps
                JOIN conversations c ON ps.conversation_id = c.id
                LEFT JOIN users u ON ps.shared_by = u.id
                WHERE ps.shared_with = %s
                ORDER BY ps.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            shares = cursor.fetchall()
            
            result = []
            for share in shares:
                result.append(dict(share))
            
            return result
        finally:
            cursor.close()
            conn.close()
    
    def get_shared_by_me(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get prompts shared by the user
        
        Args:
            user_id: User ID
            limit: Maximum number of prompts
        
        Returns:
            List of share dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    ps.conversation_id,
                    ps.shared_with,
                    ps.permission_level,
                    ps.created_at,
                    c.title,
                    u.email as shared_with_email
                FROM prompt_shares ps
                JOIN conversations c ON ps.conversation_id = c.id
                LEFT JOIN users u ON ps.shared_with = u.id
                WHERE ps.shared_by = %s
                ORDER BY ps.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            shares = cursor.fetchall()
            
            result = []
            for share in shares:
                result.append(dict(share))
            
            return result
        finally:
            cursor.close()
            conn.close()
    
    def revoke_share(
        self,
        conversation_id: str,
        shared_by: str,
        shared_with: str
    ) -> bool:
        """
        Revoke a share
        
        Args:
            conversation_id: Prompt ID
            shared_by: User ID who shared (must match)
            shared_with: User ID to revoke share from
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, shared_by)
        
        try:
            cursor.execute("""
                DELETE FROM prompt_shares
                WHERE conversation_id = %s 
                  AND shared_by = %s 
                  AND shared_with = %s
            """, (conversation_id, shared_by, shared_with))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

