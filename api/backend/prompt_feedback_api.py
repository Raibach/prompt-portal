"""
Prompt Feedback API - Handles user feedback submission and curator review queue
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
from backend.database_pool import DatabasePool


class PromptFeedbackAPI:
    """API for managing prompt feedback"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def submit_feedback(
        self,
        conversation_id: str,
        user_id: str,
        feedback_type: str,
        content: str
    ) -> str:
        """
        Submit feedback for a prompt
        
        Args:
            conversation_id: Prompt ID (conversation_id repurposed)
            user_id: User ID submitting feedback
            feedback_type: Type of feedback (bug, improvement, question, praise, other)
            content: Feedback content
        
        Returns:
            str: Feedback ID
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            # Validate feedback type
            valid_types = ['bug', 'improvement', 'question', 'praise', 'other']
            if feedback_type not in valid_types:
                raise ValueError(f"Invalid feedback_type. Must be one of: {', '.join(valid_types)}")
            
            cursor.execute("""
                INSERT INTO prompt_feedback (
                    conversation_id, user_id, feedback_type, content, status
                ) VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id
            """, (conversation_id, user_id, feedback_type, content))
            
            feedback_id = cursor.fetchone()['id']
            conn.commit()
            return str(feedback_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_feedback_queue(
        self,
        curator_id: str,
        status: Optional[str] = 'pending',
        limit: int = 50
    ) -> List[Dict]:
        """
        Get feedback queue for curator review
        
        Args:
            curator_id: Curator user ID
            status: Filter by status (default: 'pending')
            limit: Maximum number of feedback items to return
        
        Returns:
            List of feedback dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)
        
        try:
            if status:
                cursor.execute("""
                    SELECT 
                        pf.id,
                        pf.conversation_id,
                        pf.user_id,
                        pf.feedback_type,
                        pf.content,
                        pf.status,
                        pf.curator_notes,
                        pf.created_at,
                        pf.updated_at,
                        c.title as prompt_title,
                        c.prompt_status,
                        u.email as user_email
                    FROM prompt_feedback pf
                    JOIN conversations c ON pf.conversation_id = c.id
                    LEFT JOIN users u ON pf.user_id = u.id
                    WHERE pf.status = %s
                    ORDER BY pf.created_at DESC
                    LIMIT %s
                """, (status, limit))
            else:
                cursor.execute("""
                    SELECT 
                        pf.id,
                        pf.conversation_id,
                        pf.user_id,
                        pf.feedback_type,
                        pf.content,
                        pf.status,
                        pf.curator_notes,
                        pf.created_at,
                        pf.updated_at,
                        c.title as prompt_title,
                        c.prompt_status,
                        u.email as user_email
                    FROM prompt_feedback pf
                    JOIN conversations c ON pf.conversation_id = c.id
                    LEFT JOIN users u ON pf.user_id = u.id
                    ORDER BY pf.created_at DESC
                    LIMIT %s
                """, (limit,))
            
            feedback_items = cursor.fetchall()
            
            result = []
            for item in feedback_items:
                result.append(dict(item))
            
            return result
        finally:
            cursor.close()
            conn.close()
    
    def approve_feedback(
        self,
        feedback_id: str,
        curator_id: str,
        curator_notes: Optional[str] = None
    ) -> bool:
        """
        Approve feedback (mark as approved)
        
        Args:
            feedback_id: Feedback ID
            curator_id: Curator user ID
            curator_notes: Optional notes from curator
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)
        
        try:
            cursor.execute("""
                UPDATE prompt_feedback
                SET status = 'approved',
                    curator_notes = COALESCE(%s, curator_notes),
                    updated_at = NOW()
                WHERE id = %s
            """, (curator_notes, feedback_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def reject_feedback(
        self,
        feedback_id: str,
        curator_id: str,
        curator_notes: Optional[str] = None
    ) -> bool:
        """
        Reject feedback
        
        Args:
            feedback_id: Feedback ID
            curator_id: Curator user ID
            curator_notes: Optional notes explaining rejection
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)
        
        try:
            cursor.execute("""
                UPDATE prompt_feedback
                SET status = 'rejected',
                    curator_notes = COALESCE(%s, curator_notes),
                    updated_at = NOW()
                WHERE id = %s
            """, (curator_notes, feedback_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def resolve_feedback(
        self,
        feedback_id: str,
        curator_id: str,
        curator_notes: Optional[str] = None
    ) -> bool:
        """
        Mark feedback as resolved (after prompt has been updated)
        
        Args:
            feedback_id: Feedback ID
            curator_id: Curator user ID
            curator_notes: Optional notes about resolution
        
        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)
        
        try:
            cursor.execute("""
                UPDATE prompt_feedback
                SET status = 'resolved',
                    curator_notes = COALESCE(%s, curator_notes),
                    updated_at = NOW()
                WHERE id = %s
            """, (curator_notes, feedback_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_feedback_for_prompt(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get all feedback for a specific prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID (for RLS)
            limit: Maximum number of feedback items
        
        Returns:
            List of feedback dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    pf.id,
                    pf.user_id,
                    pf.feedback_type,
                    pf.content,
                    pf.status,
                    pf.curator_notes,
                    pf.created_at,
                    u.email as user_email
                FROM prompt_feedback pf
                LEFT JOIN users u ON pf.user_id = u.id
                WHERE pf.conversation_id = %s
                ORDER BY pf.created_at DESC
                LIMIT %s
            """, (conversation_id, limit))
            
            feedback_items = cursor.fetchall()
            
            result = []
            for item in feedback_items:
                result.append(dict(item))
            
            return result
        finally:
            cursor.close()
            conn.close()

