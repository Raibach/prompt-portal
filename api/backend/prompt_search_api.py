"""
Prompt Search API - Handles search and filtering for prompts
"""

from typing import List, Dict, Optional
from backend.database_pool import DatabasePool


class PromptSearchAPI:
    """API for searching and filtering prompts"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
    
    def get_db(self):
        """Get database connection from pool"""
        return self.db_pool.get_connection()
    
    def set_user_context(self, cursor, user_id: str):
        """Set user context for RLS policies"""
        cursor.execute("SET LOCAL app.current_user_id = %s", (user_id,))
    
    def search_prompts(
        self,
        user_id: str,
        query: Optional[str] = None,
        status: Optional[str] = None,
        tag_path: Optional[str] = None,
        curator_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Search prompts with filters
        
        Args:
            user_id: User ID (for RLS)
            query: Search query text
            status: Filter by prompt status
            tag_path: Filter by tag path
            curator_id: Filter by curator
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            Dict with prompts and total count
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)
        
        try:
            conditions = []
            params = []
            
            # Status filter
            if status:
                conditions.append("c.prompt_status = %s")
                params.append(status)
            
            # Curator filter
            if curator_id:
                conditions.append("c.curator_id = %s")
                params.append(curator_id)
            
            # Tag filter
            if tag_path:
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM conversation_tags ct
                        JOIN tag_definitions td ON ct.tag_id = td.id
                        WHERE ct.conversation_id = c.id
                          AND td.tag_path LIKE %s
                    )
                """)
                params.append(f"{tag_path}%")
            
            # Text search
            if query:
                conditions.append("""
                    (c.title ILIKE %s OR c.metadata::text ILIKE %s)
                """)
                search_term = f"%{query}%"
                params.extend([search_term, search_term])
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Count query
            count_query = f"""
                SELECT COUNT(*) as total
                FROM conversations c
                {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Results query
            results_query = f"""
                SELECT 
                    c.id,
                    c.title,
                    c.prompt_status,
                    c.prompt_version,
                    c.curator_id,
                    c.created_at,
                    c.updated_at,
                    c.metadata
                FROM conversations c
                {where_clause}
                ORDER BY c.updated_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            cursor.execute(results_query, params)
            
            prompts = cursor.fetchall()
            
            # Parse metadata
            result = []
            for prompt in prompts:
                prompt_dict = dict(prompt)
                if prompt_dict.get('metadata') and isinstance(prompt_dict['metadata'], str):
                    try:
                        import json
                        prompt_dict['metadata'] = json.loads(prompt_dict['metadata'])
                    except:
                        prompt_dict['metadata'] = {}
                elif prompt_dict.get('metadata') is None:
                    prompt_dict['metadata'] = {}
                result.append(prompt_dict)
            
            return {
                'prompts': result,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        finally:
            cursor.close()
            conn.close()

