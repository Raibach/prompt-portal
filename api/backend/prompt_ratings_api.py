"""
Prompt Ratings API - Handles user ratings for prompts
"""

from typing import List, Dict, Optional
from backend.database_pool import DatabasePool


class PromptRatingsAPI:
    """API for managing prompt ratings"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def submit_rating(
        self,
        conversation_id: str,
        user_id: str,
        rating: int
    ) -> bool:
        """
        Submit or update a rating for a prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID submitting rating
            rating: Rating value (1-5)
        
        Returns:
            bool: True if successful
        """
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                INSERT INTO prompt_ratings (conversation_id, user_id, rating)
                VALUES (%s, %s, %s)
                ON CONFLICT (conversation_id, user_id) 
                DO UPDATE SET rating = EXCLUDED.rating
            """, (conversation_id, user_id, rating))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_rating_for_prompt(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[int]:
        """
        Get user's rating for a prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID
        
        Returns:
            Optional[int]: Rating (1-5) or None if not rated
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT rating FROM prompt_ratings
                WHERE conversation_id = %s AND user_id = %s
            """, (conversation_id, user_id))
            
            result = cursor.fetchone()
            return result['rating'] if result else None
        finally:
            cursor.close()
            conn.close()
    
    def get_average_rating(self, conversation_id: str, user_id: str) -> Dict:
        """
        Get average rating and rating breakdown for a prompt
        
        Args:
            conversation_id: Prompt ID
            user_id: User ID (for RLS)
        
        Returns:
            Dict with average, count, and breakdown
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            cursor.execute("""
                SELECT 
                    AVG(rating) as average_rating,
                    COUNT(*) as rating_count,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
                FROM prompt_ratings
                WHERE conversation_id = %s
            """, (conversation_id,))
            
            result = cursor.fetchone()
            
            return {
                'average': float(result['average_rating']) if result['average_rating'] else 0.0,
                'count': result['rating_count'] or 0,
                'breakdown': {
                    '5': result['five_star'] or 0,
                    '4': result['four_star'] or 0,
                    '3': result['three_star'] or 0,
                    '2': result['two_star'] or 0,
                    '1': result['one_star'] or 0
                }
            }
        finally:
            cursor.close()
            conn.close()

