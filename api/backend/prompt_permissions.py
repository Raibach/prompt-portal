"""
Prompt Permissions - Permission checking logic for prompts
"""

from typing import Optional, List
from backend.database_pool import DatabasePool


class PromptPermissions:
    """Permission checking logic for prompts"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def get_user_prompt_role(self, user_id: str) -> str:
        """
        Get user's prompt role
        
        Args:
            user_id: User ID
        
        Returns:
            str: Role (contributor, curator, viewer, admin)
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT prompt_role FROM users WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            return result['prompt_role'] if result else 'viewer'
        finally:
            cursor.close()
            conn.close()
    
    def can_create_prompt(self, user_id: str) -> bool:
        """Check if user can create prompts"""
        role = self.get_user_prompt_role(user_id)
        return role in ('contributor', 'curator', 'admin')
    
    def can_edit_prompt(self, user_id: str, conversation_id: str) -> bool:
        """Check if user can edit a prompt"""
        role = self.get_user_prompt_role(user_id)
        
        # Admin and curator can always edit
        if role in ('curator', 'admin'):
            return True
        
        # Contributor can edit their own prompts
        if role == 'contributor':
            conn = self.get_db()
            cursor = conn.cursor()
            self.set_user_context(cursor, user_id)
            
            try:
                cursor.execute("""
                    SELECT user_id FROM conversations WHERE id = %s
                """, (conversation_id,))
                
                result = cursor.fetchone()
                if result and result['user_id'] == user_id:
                    return True
            finally:
                cursor.close()
                conn.close()
        
        return False
    
    def can_review_prompt(self, user_id: str) -> bool:
        """Check if user can review prompts"""
        role = self.get_user_prompt_role(user_id)
        return role in ('curator', 'admin')
    
    def can_publish_prompt(self, user_id: str) -> bool:
        """Check if user can publish prompts"""
        role = self.get_user_prompt_role(user_id)
        return role in ('curator', 'admin')
    
    def can_view_prompt(self, user_id: str, conversation_id: str) -> bool:
        """Check if user can view a prompt"""
        # All authenticated users can view published prompts
        # Owners, curators, and admins can view any status
        role = self.get_user_prompt_role(user_id)
        
        if role in ('curator', 'admin'):
            return True
        
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT user_id, prompt_status FROM conversations WHERE id = %s
            """, (conversation_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            # Owner can always view
            if result['user_id'] == user_id:
                return True
            
            # Published prompts are viewable by all
            if result['prompt_status'] == 'published':
                return True
            
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_prompt_permission(self, user_id: str, conversation_id: str) -> Optional[str]:
        """
        Get specific permission for a prompt
        
        Args:
            user_id: User ID
            conversation_id: Prompt ID
        
        Returns:
            Optional[str]: Permission level (read, write, admin) or None
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            # Check explicit permissions
            cursor.execute("""
                SELECT permission FROM prompt_permissions
                WHERE conversation_id = %s AND user_id = %s
            """, (conversation_id, user_id))
            
            result = cursor.fetchone()
            if result:
                return result['permission']
            
            # Check ownership
            cursor.execute("""
                SELECT user_id FROM conversations WHERE id = %s
            """, (conversation_id,))
            
            owner_result = cursor.fetchone()
            if owner_result and owner_result['user_id'] == user_id:
                return 'admin'
            
            # Check role-based default
            role = self.get_user_prompt_role(user_id)
            if role == 'admin':
                return 'admin'
            elif role == 'curator':
                return 'write'
            elif role == 'contributor':
                # Check if they own it
                if owner_result and owner_result['user_id'] == user_id:
                    return 'write'
                return 'read'
            else:
                return 'read'
        finally:
            cursor.close()
            conn.close()

