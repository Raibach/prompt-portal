"""
Prompt Comments API - Handles threaded comments for prompts
"""

from typing import List, Dict, Optional
from datetime import datetime
from backend.database_pool import DatabasePool


class PromptCommentsAPI:
    """API for managing prompt comments"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def add_comment(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Add a comment to a prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID adding comment
            content: Comment content
            parent_id: Optional parent comment ID for threading
        
        Returns:
            str: Comment ID
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                INSERT INTO prompt_comments (
                    conversation_id, user_id, parent_id, content
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (conversation_id, user_id, parent_id, content))
            
            comment_id = cursor.fetchone()['id']
            conn.commit()
            return str(comment_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_comments_for_prompt(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get all comments for a prompt (with threading)
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID (for RLS)
            limit: Maximum number of comments
        
        Returns:
            List of comment dictionaries with nested replies
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    pc.id,
                    pc.user_id,
                    pc.parent_id,
                    pc.content,
                    pc.created_at,
                    pc.updated_at,
                    u.email as user_email
                FROM prompt_comments pc
                LEFT JOIN users u ON pc.user_id = u.id
                WHERE pc.conversation_id = %s
                ORDER BY pc.created_at ASC
                LIMIT %s
            """, (conversation_id, limit))
            
            comments = cursor.fetchall()
            
            # Build threaded structure
            comment_dict = {}
            root_comments = []
            
            for comment in comments:
                comment_dict[comment['id']] = {
                    **dict(comment),
                    'replies': []
                }
            
            for comment in comments:
                comment_obj = comment_dict[comment['id']]
                if comment['parent_id']:
                    parent = comment_dict.get(comment['parent_id'])
                    if parent:
                        parent['replies'].append(comment_obj)
                else:
                    root_comments.append(comment_obj)
            
            return root_comments
        finally:
            cursor.close()
            conn.close()
    
    def update_comment(
        self,
        comment_id: str,
        user_id: str,
        content: str
    ) -> bool:
        """
        Update a comment
        
        Args:
            comment_id: Comment ID
            user_id: User ID (must own the comment)
            content: New content
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                UPDATE prompt_comments
                SET content = %s,
                    updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """, (content, comment_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def delete_comment(
        self,
        comment_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a comment (and its replies)
        
        Args:
            comment_id: Comment ID
            user_id: User ID (must own the comment)
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            # Delete comment and all replies (cascade)
            cursor.execute("""
                DELETE FROM prompt_comments
                WHERE id = %s AND user_id = %s
            """, (comment_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

