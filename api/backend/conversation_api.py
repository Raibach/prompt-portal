"""
Conversation API - PostgreSQL service for conversation storage
Handles conversations and messages with offline support
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import psycopg2
from psycopg2 import InterfaceError, OperationalError, ProgrammingError
from psycopg2.extras import RealDictCursor

from backend.database_pool import DatabasePoolManager


class ConversationAPI:
    """PostgreSQL service for conversation and message management"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        # Initialize connection pool manager
        self.pool_manager = DatabasePoolManager.get_instance(database_url)

    def get_db(self):
        """
        Get database connection from pool.
        Connection will be automatically returned to pool when close() is called.
        """
        return self.pool_manager.get_db()

    def get_db_context(self):
        """
        Get database connection context manager from pool.
        Use with: with self.get_db_context() as conn:
        """
        return self.pool_manager.get_connection()

    def set_user_context(self, cursor, user_id: str):
        """Set PostgreSQL RLS context for multi-tenancy"""
        try:
            cursor.execute(f"SET app.current_user_id = '{user_id}'")
        except Exception:
            # RLS might not be enabled, continue without it
            pass

    # ============================================
    # CONVERSATIONS
    # ============================================

    def get_all_conversations(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        include_archived: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Get all conversations for a user, optionally filtered by project"""
        # Try to import debug logger
        try:
            from backend.debug_logger import debug_logger

            DEBUG_LOGGING_ENABLED = True
        except:
            DEBUG_LOGGING_ENABLED = False
            debug_logger = None

        if DEBUG_LOGGING_ENABLED:
            debug_logger.log_database(
                "get_all_conversations",
                None,
                {
                    "user_id": user_id[:8] + "..." if user_id else None,
                    "project_id": project_id,
                    "include_archived": include_archived,
                    "limit": limit,
                },
            )

        conn = None
        cursor = None
        start_time = time.time()
        try:
            # Import database logger if available
            try:
                from backend.database_logger import DatabaseLogger

                DB_LOGGER_AVAILABLE = True
            except ImportError:
                DB_LOGGER_AVAILABLE = False
                DatabaseLogger = None

            conn = self.get_db()
            cursor = conn.cursor()
            self.set_user_context(cursor, user_id)

            query = """
                SELECT id, user_id, title, message_count, is_archived,
                       created_at, updated_at,
                       metadata, project_id
                FROM conversations
                WHERE user_id = %s
            """
            params = [user_id]

            if not include_archived:
                query += " AND is_archived = FALSE"

            if project_id:
                # Project ID is now stored as an actual column (not in metadata)
                query += " AND project_id = %s"
                params.append(str(project_id))
            # If no project_id specified, don't filter by project_id (get all conversations)

            query += " ORDER BY updated_at DESC"
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cursor.execute(query, params)
            conversations = cursor.fetchall()

            # Convert to list of dicts and parse metadata
            result = []
            for conv in conversations:
                conv_dict = dict(conv)
                # Parse metadata JSONB
                if conv_dict.get("metadata") and isinstance(conv_dict["metadata"], str):
                    conv_dict["metadata"] = json.loads(conv_dict["metadata"])
                elif conv_dict.get("metadata") is None:
                    conv_dict["metadata"] = {}
                # Extract project_id from metadata
                conv_dict["project_id"] = conv_dict["metadata"].get("project_id")
                result.append(conv_dict)

            return result
        except psycopg2.ProgrammingError as e:
            # Table doesn't exist or SQL syntax error
            try:
                duration_ms = (time.time() - start_time) * 1000
            except (NameError, UnboundLocalError):
                duration_ms = 0
            import traceback

            error_msg = f"Database schema error: {str(e)}"

            # Log error with database logger
            if DB_LOGGER_AVAILABLE and DatabaseLogger:
                try:
                    error_category = DatabaseLogger.categorize_error(e)
                    DatabaseLogger.log_error(
                        "get_all_conversations",
                        error_msg,
                        {
                            "operation": "get_all_conversations",
                            "user_id": user_id[:8] + "..." if user_id else None,
                            "project_id": project_id,
                            "duration_ms": duration_ms,
                            **error_category,
                        },
                        e,
                    )
                except Exception:
                    pass  # Don't fail if logging fails

            # Log error
            try:
                from backend.debug_logger import debug_logger

                debug_logger.error(
                    "Database schema error in get_all_conversations",
                    e,
                    {
                        "user_id": user_id[:8] + "..." if user_id else None,
                        "error_type": "ProgrammingError",
                    },
                )
            except:
                pass

            print(f"❌ {error_msg}\n{traceback.format_exc()}")
            raise Exception(error_msg) from e
        except psycopg2.DataError as e:
            # Data type errors (like invalid UUID) - this is the key error we're tracking!
            import traceback

            try:
                duration_ms = (time.time() - start_time) * 1000
            except (NameError, UnboundLocalError):
                duration_ms = 0
            error_msg = f"Database data error: {str(e)}"

            # Log error with full context - THIS IS CRITICAL FOR DEBUGGING
            try:
                from backend.debug_logger import debug_logger

                debug_logger.error(
                    "Database data error in get_all_conversations - INVALID UUID",
                    e,
                    {
                        "user_id": user_id,  # Log full user_id to see what's wrong
                        "user_id_length": len(user_id) if user_id else 0,
                        "user_id_type": type(user_id).__name__,
                        "project_id": project_id,
                        "error_type": "DataError",
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                )
            except Exception as log_err:
                print(f"⚠️ Could not log error: {log_err}")
                import traceback

                traceback.print_exc()

            print(f"❌ {error_msg}")
            print(f"   User ID causing error: {user_id}")
            print(f"   User ID type: {type(user_id)}")
            print(f"   User ID length: {len(user_id) if user_id else 0}")
            traceback.print_exc()
            raise Exception(error_msg) from e
        except Exception as e:
            # Re-raise ConnectionError as-is
            if isinstance(e, ConnectionError):
                raise

            # Log and re-raise other errors
            import traceback

            error_msg = f"Database error in get_all_conversations: {str(e)}"

            # Log error
            try:
                from backend.debug_logger import debug_logger

                debug_logger.error(
                    "Database error in get_all_conversations",
                    e,
                    {
                        "user_id": user_id[:8] + "..." if user_id else None,
                        "project_id": project_id,
                        "error_type": type(e).__name__,
                    },
                )
            except:
                pass

            print(f"❌ {error_msg}\n{traceback.format_exc()}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific conversation by ID"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            cursor.execute(
                """
                SELECT id, user_id, title, message_count, is_archived,
                       created_at, updated_at, metadata
                FROM conversations
                WHERE id = %s AND user_id = %s
            """,
                (conversation_id, user_id),
            )

            conv = cursor.fetchone()
            if not conv:
                return None

            conv_dict = dict(conv)
            # Parse metadata JSONB
            if conv_dict.get("metadata") and isinstance(conv_dict["metadata"], str):
                conv_dict["metadata"] = json.loads(conv_dict["metadata"])
            elif conv_dict.get("metadata") is None:
                conv_dict["metadata"] = {}
            # Extract project_id from metadata
            conv_dict["project_id"] = conv_dict["metadata"].get("project_id")

            return conv_dict
        finally:
            cursor.close()
            conn.close()

    def create_conversation(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new conversation"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Build metadata with project_id and any additional metadata
            conv_metadata = {}
            if metadata:
                conv_metadata.update(metadata)
            if project_id:
                conv_metadata["project_id"] = project_id

            cursor.execute(
                """
                INSERT INTO conversations (user_id, title, message_count, metadata, prompt_status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """,
                (user_id, title or "New Prompt", 0, json.dumps(conv_metadata), "draft"),
            )

            conversation_id = cursor.fetchone()["id"]
            conn.commit()
            return str(conversation_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: Optional[str] = None,
        message_count: Optional[int] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        """Update a conversation (title, message_count, project_id) - with prompt workflow validation"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Check prompt status and enforce workflow rules
            cursor.execute(
                """
                SELECT prompt_status, user_id FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            prompt_result = cursor.fetchone()
            if prompt_result:
                prompt_status = prompt_result.get("prompt_status", "draft")
                prompt_owner = prompt_result.get("user_id")

                # Enforce workflow: published prompts cannot be edited directly (must create new version)
                if prompt_status == "published":
                    raise ValueError(
                        "Cannot edit published prompts. Create a new version or rollback first."
                    )

                # Only owners or curators can edit prompts in review
                if prompt_status == "review" and prompt_owner != user_id:
                    # Check if user is curator (will be enhanced in Phase 6)
                    pass  # For now, allow if user owns it

            updates = []
            params = []
            old_project_id = None

            if title is not None:
                updates.append("title = %s")
                params.append(title)

            if message_count is not None:
                updates.append("message_count = %s")
                params.append(message_count)

            if project_id is not None:
                # Get old project_id before updating
                cursor.execute(
                    """
                    SELECT metadata->>'project_id' as project_id
                    FROM conversations
                    WHERE id = %s AND user_id = %s
                """,
                    (conversation_id, user_id),
                )
                old_result = cursor.fetchone()
                if old_result:
                    old_project_id = old_result.get("project_id")

                # Update both metadata and direct column if it exists
                updates.append(
                    "metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{project_id}', to_jsonb(%s::text))"
                )
                params.append(project_id)

                # Also update direct project_id column if it exists
                try:
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'conversations' AND column_name = 'project_id'
                    """)
                    if cursor.fetchone():
                        updates.append("project_id = %s")
                        params.append(project_id)
                except:
                    pass  # Column might not exist, that's okay

            if not updates:
                return False

            updates.append("updated_at = NOW()")
            params.extend([conversation_id, user_id])

            query = f"""
                UPDATE conversations
                SET {", ".join(updates)}
                WHERE id = %s AND user_id = %s
            """

            cursor.execute(query, params)

            # CRITICAL: Update project's updated_at when conversation is modified or moved
            # This ensures modified projects move to the top of the list
            project_ids_to_update = set()

            # Add new project_id if conversation was moved
            if project_id:
                project_ids_to_update.add(project_id)

                # Get current project_id (after update)
                cursor.execute(
                    """
                    SELECT metadata->>'project_id' as project_id
                    FROM conversations
                    WHERE id = %s AND user_id = %s
                """,
                    (conversation_id, user_id),
                )
                result = cursor.fetchone()
                if result:
                    current_project_id = result.get("project_id")
                if current_project_id:
                    project_ids_to_update.add(current_project_id)

            # Also update old project if conversation was moved
            if old_project_id and old_project_id != project_id:
                project_ids_to_update.add(old_project_id)

            # Update timestamps for all affected projects
            for pid in project_ids_to_update:
                if pid:
                    cursor.execute(
                        """
                        UPDATE projects
                        SET updated_at = NOW()
                        WHERE id = %s AND user_id = %s
                    """,
                        (pid, user_id),
                    )
                    print(
                        f"✅ Updated project {pid} timestamp (conversation {conversation_id} was modified/moved)"
                    )

            conn.commit()

            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation (cascade deletes messages)"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            cursor.execute(
                """
                DELETE FROM conversations
                WHERE id = %s AND user_id = %s
            """,
                (conversation_id, user_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def archive_conversation(
        self, conversation_id: str, user_id: str, archived: bool = True
    ) -> bool:
        """Archive or unarchive a conversation"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            cursor.execute(
                """
                UPDATE conversations
                SET is_archived = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """,
                (archived, conversation_id, user_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_archived_conversations(
        self, user_id: str, project_id: Optional[str] = None
    ) -> List[Dict]:
        """Get archived conversations for a user"""
        return self.get_all_conversations(user_id, project_id, include_archived=True)

    # ============================================
    # MESSAGES
    # ============================================

    def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict]:
        """Get messages for a conversation"""
        # MEMORY SAFETY: Default limit to prevent loading entire conversation history
        # Large conversations can cause memory spikes
        if limit is None:
            limit = 1000  # Default: max 1000 messages per request

        # MEMORY SAFETY: Hard cap to prevent excessive memory usage
        MAX_MESSAGES = 5000
        if limit > MAX_MESSAGES:
            limit = MAX_MESSAGES

        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Verify conversation belongs to user
            cursor.execute(
                """
                SELECT id FROM conversations
                WHERE id = %s AND user_id = %s
            """,
                (conversation_id, user_id),
            )

            if not cursor.fetchone():
                return []

            query = """
                SELECT id, conversation_id, user_id, role, content, metadata, created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            """
            params = [conversation_id]

            # Always apply limit for memory safety
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            messages = cursor.fetchall()

            # Convert to list of dicts and parse metadata
            result = []
            for msg in messages:
                msg_dict = dict(msg)
                # Parse metadata JSONB
                if msg_dict.get("metadata") and isinstance(msg_dict["metadata"], str):
                    msg_dict["metadata"] = json.loads(msg_dict["metadata"])
                elif msg_dict.get("metadata") is None:
                    msg_dict["metadata"] = {}
                result.append(msg_dict)

            return result
        finally:
            cursor.close()
            conn.close()

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        memory_api=None,
        save_to_memory: bool = True,
    ) -> str:
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata
            memory_api: Optional GraceMemoryAPI instance to save to memory
            save_to_memory: Whether to save conversation to user_memories (default: True)

        Returns:
            message_id: UUID of created message
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Verify conversation belongs to user and get conversation details
            cursor.execute(
                """
                SELECT id, title, metadata FROM conversations
                WHERE id = %s AND user_id = %s
            """,
                (conversation_id, user_id),
            )

            conv = cursor.fetchone()
            if not conv:
                raise ValueError(
                    f"Conversation {conversation_id} not found or not owned by user"
                )

            conv_title = conv["title"] if conv else "Untitled Conversation"

            # Extract project_id from conversation metadata
            conv_metadata = conv.get("metadata", {}) if conv else {}
            if isinstance(conv_metadata, str):
                try:
                    conv_metadata = json.loads(conv_metadata)
                except:
                    conv_metadata = {}
            conv_project_id = conv_metadata.get("project_id") if conv_metadata else None

            # Insert message
            cursor.execute(
                """
                INSERT INTO conversation_messages (conversation_id, user_id, role, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """,
                (conversation_id, user_id, role, content, json.dumps(metadata or {})),
            )

            message_id = cursor.fetchone()["id"]

            # Update conversation message_count and updated_at
            cursor.execute(
                """
                UPDATE conversations
                SET message_count = message_count + 1,
                    updated_at = NOW()
                WHERE id = %s
            """,
                (conversation_id,),
            )

            # CRITICAL: Update project's updated_at when a message is added
            # This ensures modified projects move to the top of the list
            if conv_project_id:
                cursor.execute(
                    """
                    UPDATE projects
                    SET updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                """,
                    (conv_project_id, user_id),
                )
                print(
                    f"✅ Updated project {conv_project_id} timestamp (message added to conversation {conversation_id})"
                )

            conn.commit()

            # Save to memory system if enabled and memory_api is provided
            # For heavy content, memory saving is non-blocking and won't cause crashes
            if save_to_memory and memory_api and role in ["user", "assistant"]:
                try:
                    # For very long content, skip memory storage to prevent crashes
                    # Long entries are already saved to database, memory is for search
                    if (
                        len(content) > 100000
                    ):  # Skip memory for very large content (>100k chars)
                        print(
                            f"⚠️  Content too large for memory storage ({len(content)} chars), skipping (saved to DB)"
                        )
                    else:
                        # Check if conversation has tags (for embedding rules)
                        tag_paths = []
                        has_tags = False
                        try:
                            cursor.execute(
                                """
                                SELECT array_agg(td.tag_path ORDER BY td.tag_path) as tag_paths
                                FROM conversations c
                                LEFT JOIN conversation_tags ct ON c.id = ct.conversation_id
                                LEFT JOIN tag_definitions td ON ct.tag_id = td.id
                                WHERE c.id = %s
                                GROUP BY c.id
                            """,
                                (conversation_id,),
                            )
                            tag_result = cursor.fetchone()
                            if tag_result and tag_result.get("tag_paths"):
                                tag_paths = [tp for tp in tag_result["tag_paths"] if tp]
                                has_tags = len(tag_paths) > 0
                        except Exception as tag_error:
                            # Non-critical - continue without tags
                            pass

                        # Prepare memory metadata
                        memory_metadata = {
                            "conversation_id": conversation_id,
                            "message_id": str(message_id),
                            "role": role,
                            "project_id": conv_project_id,  # Include project_id from conversation
                            "tag_paths": tag_paths,
                            "tag_path": " > ".join(tag_paths[:3]) if tag_paths else "",
                            **(metadata or {}),
                        }

                        # Get conversation title for memory title
                        memory_title = f"{conv_title} - {role.capitalize()} Message"

                        # Basic quarantine check (safe by default for conversations)
                        # More sophisticated quarantine can be added later
                        quarantine_status = "safe"
                        quarantine_score = 0.9  # Conversations are generally safe

                        # Determine if embedding should be generated based on rules
                        try:
                            from config.embedding_rules import (
                                should_embed_automatically,
                            )

                            generate_embedding = should_embed_automatically(
                                content_type="conversation",
                                source_type="conversation",
                                metadata=memory_metadata,
                                content_length=len(content),
                                has_tags=has_tags,
                                tag_paths=tag_paths,
                                project_id=conv_project_id,
                                importance_score=quarantine_score,
                                quarantine_status=quarantine_status,
                            )
                        except Exception as rule_error:
                            # If rules fail, default to False (conservative)
                            print(f"⚠️  Failed to check embedding rules: {rule_error}")
                            generate_embedding = False

                        # Save to user_memories (non-blocking, won't crash on failure)
                        memory_api.create_memory(
                            user_id=user_id,
                            content=content,
                            content_type="conversation",
                            source_type="conversation",
                            title=memory_title,
                            generate_embedding=generate_embedding,  # Use embedding rules to determine
                            source_metadata=memory_metadata,
                            quarantine_score=quarantine_score,
                            quarantine_status=quarantine_status,
                        )
                        if generate_embedding:
                            print(
                                f"✅ Conversation message saved to memory with embedding: {message_id}"
                            )
                        else:
                            print(
                                f"✅ Conversation message saved to memory (no embedding): {message_id}"
                            )
                except Exception as mem_error:
                    # Don't fail message creation if memory save fails
                    # Heavy content may cause memory operations to fail, but DB save succeeds
                    print(
                        f"⚠️  Failed to save conversation to memory (non-blocking): {mem_error}"
                    )

            # Trigger real-time tag detection and storage if conversation has enough messages (threshold: 5 messages)
            # This is done asynchronously to avoid blocking message creation
            try:
                cursor.execute(
                    """
                    SELECT COUNT(*) as msg_count FROM conversation_messages
                    WHERE conversation_id = %s
                """,
                    (conversation_id,),
                )
                msg_count = cursor.fetchone()["msg_count"]

                # Extract and store tags if conversation has 5+ messages and hasn't been tagged recently
                if msg_count >= 5:
                    # Check if already tagged recently (within last hour)
                    cursor.execute(
                        """
                        SELECT metadata->>'tagged_at' as tagged_at
                        FROM conversations
                        WHERE id = %s
                    """,
                        (conversation_id,),
                    )
                    tagged_result = cursor.fetchone()
                    tagged_at = tagged_result["tagged_at"] if tagged_result else None

                    # Trigger tag detection and storage if not tagged recently
                    if not tagged_at:
                        # Import here to avoid circular dependencies
                        try:
                            from backend.context_detector import ContextDetector
                            from backend.memory_embedder import get_embedder
                            from backend.milvus_client import get_milvus_client

                            # Get all messages for tag detection
                            messages = self.get_messages(
                                conversation_id, user_id, limit=100
                            )
                            conversation_text = "\n".join(
                                [
                                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                                    for msg in messages
                                ]
                            )

                            # Detect entities using ContextDetector
                            context_detector = ContextDetector()
                            detected_entities = (
                                context_detector.detect_context_entities(
                                    user_input=conversation_text,
                                    conversation_history=messages[
                                        -10:
                                    ],  # Last 10 messages for context
                                )
                            )

                            # Only store if we detected meaningful entities
                            if (
                                detected_entities.get("characters")
                                or detected_entities.get("work_focus")
                                or detected_entities.get("literary_elements")
                            ):
                                # Get Milvus client and embedder
                                milvus_client = get_milvus_client()
                                if milvus_client:
                                    milvus_client.connect()
                                memory_embedder = get_embedder()

                                # Store tags using unified function
                                result = self.store_literary_tags(
                                    conversation_id=conversation_id,
                                    user_id=user_id,
                                    detected_entities=detected_entities,
                                    conversation_content=conversation_text,
                                    project_id=conv_project_id,
                                    milvus_client=milvus_client,
                                    memory_embedder=memory_embedder,
                                )
                                print(
                                    f"✅ Real-time tag storage completed for conversation {conversation_id}: {result['tag_paths']}"
                                )
                            else:
                                print(
                                    f"ℹ️ No meaningful entities detected for conversation {conversation_id}"
                                )
                        except Exception as tag_err:
                            # Don't fail message creation if tag storage fails
                            print(f"⚠️ Real-time tag storage failed: {tag_err}")
                            import traceback

                            traceback.print_exc()
            except Exception as trigger_err:
                # Don't fail message creation if tag trigger fails
                print(f"⚠️ Tag storage trigger failed: {trigger_err}")

            return str(message_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_conversations_by_tags(
        self,
        tag_paths: List[str],
        user_id: str,
        project_id: Optional[str] = None,
        character_names: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get conversations filtered by tag paths and character names

        Args:
            tag_paths: List of tag paths (e.g., ["Novel > Character Development > Marcus"])
            user_id: User ID
            project_id: Optional project ID filter
            character_names: Optional list of character names to filter by
            limit: Maximum number of conversations to return

        Returns:
            List of conversation dictionaries with messages
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Build query with tag filtering
            query = """
                SELECT DISTINCT c.id, c.user_id, c.title, c.message_count,
                       c.is_archived, c.created_at, c.updated_at, c.metadata
                FROM conversations c
            """

            params = [user_id]
            conditions = ["c.user_id = %s"]

            # Add tag path filtering
            if tag_paths:
                query += """
                    JOIN conversation_tags ct ON c.id = ct.conversation_id
                    JOIN tag_definitions td ON ct.tag_id = td.id
                """
                # Filter by tag paths (using LIKE for hierarchical matching)
                tag_conditions = []
                for tag_path in tag_paths:
                    tag_conditions.append("td.tag_path LIKE %s")
                    params.append(f"{tag_path}%")
                conditions.append(f"({' OR '.join(tag_conditions)})")

            # Add project filter
            if project_id:
                conditions.append("(c.metadata->>'project_id' = %s)")
                params.append(project_id)

            # Add character name filtering (search in conversation content)
            if character_names:
                query += """
                    JOIN conversation_messages cm ON c.id = cm.conversation_id
                """
                char_conditions = []
                for char_name in character_names:
                    char_conditions.append("cm.content ILIKE %s")
                    params.append(f"%{char_name}%")
                conditions.append(f"({' OR '.join(char_conditions)})")

            # Build final query
            query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY c.updated_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            conversations = cursor.fetchall()

            # Convert to list of dicts and parse metadata
            result = []
            for conv in conversations:
                conv_dict = dict(conv)
                # Parse metadata JSONB
                if conv_dict.get("metadata") and isinstance(conv_dict["metadata"], str):
                    conv_dict["metadata"] = json.loads(conv_dict["metadata"])
                elif conv_dict.get("metadata") is None:
                    conv_dict["metadata"] = {}
                # Extract project_id from metadata
                conv_dict["project_id"] = conv_dict["metadata"].get("project_id")
                result.append(conv_dict)

            return result
        except Exception as e:
            print(f"⚠️ Error in get_conversations_by_tags: {e}")
            import traceback

            traceback.print_exc()
            return []
        finally:
            cursor.close()
            conn.close()

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """Delete a message"""
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Get conversation_id first
            cursor.execute(
                """
                SELECT conversation_id FROM conversation_messages
                WHERE id = %s AND user_id = %s
            """,
                (message_id, user_id),
            )

            msg = cursor.fetchone()
            if not msg:
                return False

            conversation_id = msg["conversation_id"]

            # Delete message
            cursor.execute(
                """
                DELETE FROM conversation_messages
                WHERE id = %s AND user_id = %s
            """,
                (message_id, user_id),
            )

            # Update conversation message_count
            cursor.execute(
                """
                UPDATE conversations
                SET message_count = GREATEST(0, message_count - 1),
                    updated_at = NOW()
                WHERE id = %s
            """,
                (conversation_id,),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def track_tag_suggestion(
        self,
        conversation_id: str,
        user_id: str,
        suggested_tags: List[str],
        detected_entities: Optional[Dict] = None,
        confirmed: bool = False,
    ) -> str:
        """
        Track Grace's tag suggestions (even if not confirmed)

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            suggested_tags: List of suggested tag paths
            detected_entities: Optional detected entities
            confirmed: Whether user confirmed the suggestion

        Returns:
            suggestion_id: UUID of tracked suggestion
        """
        import uuid
        from datetime import datetime

        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            suggestion_id = str(uuid.uuid4())

            # Store suggestion in conversation metadata
            cursor.execute(
                """
                UPDATE conversations
                SET metadata = COALESCE(metadata, '{}'::jsonb) ||
                    jsonb_build_object(
                        'tag_suggestions', COALESCE(metadata->'tag_suggestions', '[]'::jsonb) ||
                        jsonb_build_array(jsonb_build_object(
                            'id', %s,
                            'suggested_tags', %s::jsonb,
                            'detected_entities', %s::jsonb,
                            'confirmed', %s,
                            'suggested_at', %s
                        ))
                    )
                WHERE id = %s AND user_id = %s
            """,
                (
                    suggestion_id,
                    json.dumps(suggested_tags),
                    json.dumps(detected_entities or {}),
                    confirmed,
                    datetime.now().isoformat(),
                    conversation_id,
                    user_id,
                ),
            )

            conn.commit()
            return suggestion_id
        except Exception as e:
            conn.rollback()
            print(f"⚠️ Failed to track tag suggestion: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_tag_suggestion_stats(self, user_id: str) -> Dict:
        """
        Get tag suggestion statistics for a user

        Returns:
            {
                'total_suggestions': 10,
                'confirmed_suggestions': 7,
                'confirmation_rate': 0.7
            }
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            cursor.execute(
                """
                SELECT metadata->'tag_suggestions' as suggestions
                FROM conversations
                WHERE user_id = %s
                AND metadata->'tag_suggestions' IS NOT NULL
            """,
                (user_id,),
            )

            all_suggestions = []
            for row in cursor.fetchall():
                suggestions = row.get("suggestions", [])
                if isinstance(suggestions, list):
                    all_suggestions.extend(suggestions)

            total = len(all_suggestions)
            confirmed = sum(1 for s in all_suggestions if s.get("confirmed", False))
            rate = confirmed / total if total > 0 else 0.0

            return {
                "total_suggestions": total,
                "confirmed_suggestions": confirmed,
                "confirmation_rate": rate,
            }
        except Exception as e:
            print(f"⚠️ Failed to get tag suggestion stats: {e}")
            return {
                "total_suggestions": 0,
                "confirmed_suggestions": 0,
                "confirmation_rate": 0.0,
            }
        finally:
            cursor.close()
            conn.close()

    def store_literary_tags(
        self,
        conversation_id: str,
        user_id: str,
        detected_entities: Dict,
        conversation_content: str,
        project_id: Optional[str] = None,
        milvus_client=None,
        memory_embedder=None,
    ) -> Dict[str, any]:
        """
        Store literary tags to both Milvus and PostgreSQL

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            detected_entities: ContextDetector entities dict with:
                - characters: List[str]
                - work_focus: List[str]
                - literary_elements: List[str]
                - topics: List[str]
            conversation_content: Full conversation text
            project_id: Optional project UUID
            milvus_client: Optional MilvusClientWrapper instance
            memory_embedder: Optional MemoryEmbedder instance

        Returns:
            {
                'tag_paths': ['Novel > Character Development > Marcus'],
                'tag_ids': [uuid1, uuid2],
                'milvus_inserted': True/False
            }
        """
        from datetime import datetime

        from backend.query_generator import QueryGenerator

        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Build tag paths using QueryGenerator
            query_gen = QueryGenerator()
            tag_paths = query_gen.build_tag_filters(
                intent=None,  # Will build from detected_entities
                detected_entities=detected_entities,
            )

            # If no tag paths generated, create from entities directly
            if not tag_paths:
                base_genre = "Novel"  # Default genre
                characters = detected_entities.get("characters", [])
                work_focus = detected_entities.get("work_focus", [])

                # Build tag paths: "Novel > [Work Focus] > [Character]"
                for focus in work_focus:
                    focus_display = focus.replace("_", " ").title()
                    if characters:
                        for character in characters:
                            tag_path = f"{base_genre} > {focus_display} > {character}"
                            tag_paths.append(tag_path)
                    else:
                        # Just work focus, no character
                        tag_path = f"{base_genre} > {focus_display}"
                        tag_paths.append(tag_path)

            # Get or create tag definitions and link to conversation
            tag_ids = []
            for tag_path in tag_paths:
                # Find or create tag definition
                cursor.execute(
                    """
                    SELECT id FROM tag_definitions
                    WHERE tag_path = %s AND (user_id = %s OR user_id IS NULL)
                    LIMIT 1
                """,
                    (tag_path, user_id),
                )

                tag_def = cursor.fetchone()
                if tag_def:
                    tag_id = tag_def["id"]
                else:
                    # Create new tag definition
                    # Parse tag path to determine level and parent
                    parts = tag_path.split(" > ")
                    level = len(parts)
                    tag_name = parts[-1]

                    # Find parent tag if level > 1
                    parent_id = None
                    if level > 1:
                        parent_path = " > ".join(parts[:-1])
                        cursor.execute(
                            """
                            SELECT id FROM tag_definitions
                            WHERE tag_path = %s AND (user_id = %s OR user_id IS NULL)
                            LIMIT 1
                        """,
                            (parent_path, user_id),
                        )
                        parent = cursor.fetchone()
                        if parent:
                            parent_id = parent["id"]

                    # Insert new tag definition
                    cursor.execute(
                        """
                        INSERT INTO tag_definitions (
                            tag_name, tag_level, parent_tag_id, tag_path, user_id
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, tag_path) DO UPDATE
                        SET updated_at = NOW()
                        RETURNING id
                    """,
                        (tag_name, level, parent_id, tag_path, user_id),
                    )

                    tag_id = cursor.fetchone()["id"]

                tag_ids.append(tag_id)

                # Link tag to conversation (conversation_tags)
                cursor.execute(
                    """
                    INSERT INTO conversation_tags (
                        conversation_id, tag_id, user_id, confidence_score, tagged_at, tagged_by
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (conversation_id, tag_id) DO UPDATE
                    SET confidence_score = EXCLUDED.confidence_score,
                        tagged_at = EXCLUDED.tagged_at,
                        tagged_by = EXCLUDED.tagged_by
                """,
                    (
                        conversation_id,
                        tag_id,
                        user_id,
                        0.75,  # Default confidence for detected tags
                        datetime.now(),
                        "auto",  # Tagged automatically by system
                    ),
                )

            # Update conversation metadata with tags (including emotional dimensions)
            cursor.execute(
                """
                UPDATE conversations
                SET metadata = COALESCE(metadata, '{}'::jsonb) ||
                    jsonb_build_object(
                        'tags', %s::jsonb,
                        'tagged_at', %s,
                        'character_names', %s::jsonb,
                        'work_focus', %s::jsonb,
                        'literary_elements', %s::jsonb,
                        'emotional_concepts', %s::jsonb,
                        'emotions', %s::jsonb,
                        'dominant_emotion', %s,
                        'polarity', %s,
                        'emotional_intensity', %s
                    )
                WHERE id = %s AND user_id = %s
            """,
                (
                    json.dumps(tag_paths),
                    datetime.now().isoformat(),
                    json.dumps(detected_entities.get("characters", [])),
                    json.dumps(detected_entities.get("work_focus", [])),
                    json.dumps(detected_entities.get("literary_elements", [])),
                    json.dumps(detected_entities.get("emotional_concepts", [])),
                    json.dumps(detected_entities.get("emotions", {})),
                    detected_entities.get("dominant_emotion", ""),
                    detected_entities.get("polarity", 0.0),
                    detected_entities.get("emotional_intensity", 0.0),
                    conversation_id,
                    user_id,
                ),
            )

            conn.commit()

            # Store to Milvus if client provided
            milvus_inserted = False
            if milvus_client and memory_embedder:
                try:
                    # Generate embedding for conversation content
                    embedding = memory_embedder.generate_embedding(conversation_content)

                    # Prepare metadata for Milvus (including emotional dimensions)
                    milvus_metadata = {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "project_id": project_id or "",
                        "tag_path": tag_paths[0]
                        if tag_paths
                        else "",  # Primary tag path
                        "tag_paths": tag_paths,  # All tag paths
                        "character_names": detected_entities.get("characters", []),
                        "work_focus": detected_entities.get("work_focus", []),
                        "literary_elements": detected_entities.get(
                            "literary_elements", []
                        ),
                        "topics": detected_entities.get("topics", []),
                        "content": conversation_content[:1000],  # Truncate for metadata
                        "tagged_at": datetime.now().isoformat(),
                        "content_type": "conversation",
                        # Emotional dimensions (if available)
                        "emotional_concepts": detected_entities.get(
                            "emotional_concepts", []
                        ),
                        "emotions": detected_entities.get("emotions", {}),
                        "dominant_emotion": detected_entities.get(
                            "dominant_emotion", ""
                        ),
                        "polarity": detected_entities.get("polarity", 0.0),
                        "emotional_intensity": detected_entities.get(
                            "emotional_intensity", 0.0
                        ),
                    }

                    # Determine collection name based on context type
                    from config.milvus_config import get_collection_name

                    context_type = "general"
                    if detected_entities.get("work_focus"):
                        focus = detected_entities["work_focus"][0].lower()
                        if "character" in focus:
                            context_type = "character"
                        elif "plot" in focus or "structure" in focus:
                            context_type = "plot"

                    collection_name = get_collection_name(context_type)

                    # Insert into Milvus
                    milvus_client.insert(
                        collection_name=collection_name,
                        vectors=[embedding],
                        metadata=[milvus_metadata],
                    )

                    milvus_inserted = True
                    print(f"✅ Stored tags to Milvus: {tag_paths}")
                except Exception as e:
                    print(f"⚠️ Failed to store tags to Milvus: {e}")
                    import traceback

                    traceback.print_exc()

            return {
                "tag_paths": tag_paths,
                "tag_ids": tag_ids,
                "milvus_inserted": milvus_inserted,
            }

        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to store literary tags: {e}")
            import traceback

            traceback.print_exc()
            raise e
        finally:
            cursor.close()
            conn.close()

    # ============================================
    # PROMPT LIFECYCLE METHODS & STATE MACHINE
    # ============================================

    def _validate_state_transition(
        self, current_status: str, new_status: str, user_role: str = "viewer"
    ) -> bool:
        """
        Validate state transition based on prompt lifecycle state machine

        Valid transitions:
        - draft → review (contributor)
        - review → published (curator/admin)
        - review → draft (curator/admin - reject)
        - published → archived (curator/admin)
        - archived → draft (curator/admin - restore)

        Args:
            current_status: Current prompt status
            new_status: Desired new status
            user_role: User's prompt role

        Returns:
            bool: True if transition is valid
        """
        valid_transitions = {
            "draft": ["review", "archived"],
            "review": ["published", "draft", "archived"],
            "published": ["archived"],
            "archived": ["draft"],
        }

        allowed_statuses = valid_transitions.get(current_status, [])
        if new_status not in allowed_statuses:
            return False

        # Role-based validation
        if new_status == "review" and user_role not in (
            "contributor",
            "curator",
            "admin",
        ):
            return False

        if new_status == "published" and user_role not in ("curator", "admin"):
            return False

        if new_status == "archived" and user_role not in ("curator", "admin"):
            return False

        return True

    def assign_curator(
        self, conversation_id: str, curator_id: str, assigned_by: str
    ) -> bool:
        """
        Assign a curator to a prompt

        Args:
            conversation_id: Prompt ID
            curator_id: Curator user ID to assign
            assigned_by: User ID making the assignment (must be admin or existing curator)

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, assigned_by)

        try:
            # Update curator assignment
            cursor.execute(
                """
                UPDATE conversations
                SET curator_id = %s,
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'curator_assigned_at', NOW(),
                            'curator_assigned_by', %s
                        )
                WHERE id = %s
            """,
                (curator_id, assigned_by, conversation_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_prompts_for_review(self, curator_id: str, limit: int = 50) -> List[Dict]:
        """
        Get prompts awaiting curator review

        Args:
            curator_id: Curator user ID
            limit: Maximum number of prompts to return

        Returns:
            List of prompt dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)

        try:
            cursor.execute(
                """
                SELECT id, user_id, title, prompt_status, curator_id,
                       prompt_version, created_at, updated_at, metadata
                FROM conversations
                WHERE prompt_status = 'review'
                  AND (curator_id IS NULL OR curator_id = %s)
                ORDER BY updated_at DESC
                LIMIT %s
            """,
                (curator_id, limit),
            )

            prompts = cursor.fetchall()

            result = []
            for prompt in prompts:
                prompt_dict = dict(prompt)
                # Parse metadata
                if prompt_dict.get("metadata") and isinstance(
                    prompt_dict["metadata"], str
                ):
                    prompt_dict["metadata"] = json.loads(prompt_dict["metadata"])
                elif prompt_dict.get("metadata") is None:
                    prompt_dict["metadata"] = {}
                result.append(prompt_dict)

            return result
        finally:
            cursor.close()
            conn.close()

    def reject_prompt(
        self,
        conversation_id: str,
        curator_id: str,
        rejection_notes: Optional[str] = None,
    ) -> bool:
        """
        Reject a prompt (return to draft with notes)

        Args:
            conversation_id: Prompt ID
            curator_id: Curator user ID
            rejection_notes: Optional notes explaining rejection

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)

        try:
            # Verify prompt is in review
            cursor.execute(
                """
                SELECT prompt_status FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Prompt {conversation_id} not found")

            current_status = result.get("prompt_status", "draft")
            if current_status != "review":
                raise ValueError(f"Cannot reject prompt in {current_status} status")

            # Validate state transition
            if not self._validate_state_transition(current_status, "draft", "curator"):
                raise ValueError(
                    f"Invalid state transition from {current_status} to draft"
                )

            # Update status back to draft
            metadata_update = {
                "rejected_at": datetime.now().isoformat(),
                "rejected_by": curator_id,
            }
            if rejection_notes:
                metadata_update["rejection_notes"] = rejection_notes

            cursor.execute(
                """
                UPDATE conversations
                SET prompt_status = 'draft',
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                WHERE id = %s
            """,
                (json.dumps(metadata_update), conversation_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def submit_prompt_for_review(self, conversation_id: str, user_id: str) -> bool:
        """
        Submit a prompt for curator review

        Args:
            conversation_id: Prompt ID (conversation_id repurposed)
            user_id: User ID submitting the prompt

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Verify prompt belongs to user and is in draft status
            cursor.execute(
                """
                SELECT prompt_status FROM conversations
                WHERE id = %s AND user_id = %s
            """,
                (conversation_id, user_id),
            )

            result = cursor.fetchone()
            if not result:
                raise ValueError(
                    f"Prompt {conversation_id} not found or not owned by user"
                )

            current_status = result.get("prompt_status", "draft")
            if current_status != "draft":
                raise ValueError(
                    f"Cannot submit prompt in {current_status} status. Only draft prompts can be submitted."
                )

            # Validate state transition
            if not self._validate_state_transition(
                current_status, "review", "contributor"
            ):
                raise ValueError(
                    f"Invalid state transition from {current_status} to review"
                )

            # Update status to review
            cursor.execute(
                """
                UPDATE conversations
                SET prompt_status = 'review',
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'submitted_at', NOW(),
                            'submitted_by', %s
                        )
                WHERE id = %s AND user_id = %s
            """,
                (user_id, conversation_id, user_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def approve_prompt(self, conversation_id: str, curator_id: str) -> bool:
        """
        Approve a prompt (curator action)

        Args:
            conversation_id: Prompt ID
            curator_id: Curator user ID

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)

        try:
            # Verify prompt is in review status
            cursor.execute(
                """
                SELECT prompt_status FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Prompt {conversation_id} not found")

            current_status = result.get("prompt_status", "draft")
            if current_status != "review":
                raise ValueError(
                    f"Cannot approve prompt in {current_status} status. Only prompts in review can be approved."
                )

            # Validate state transition (approval keeps in review, just marks as approved)
            # Approval is a step before publishing, so we stay in review
            # Update status and set curator
            cursor.execute(
                """
                UPDATE conversations
                SET prompt_status = 'review',
                    curator_id = %s,
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'approved_at', NOW(),
                            'approved_by', %s
                        )
                WHERE id = %s
            """,
                (curator_id, curator_id, conversation_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def publish_prompt(self, conversation_id: str, curator_id: str) -> bool:
        """
        Publish a prompt (curator action)

        Args:
            conversation_id: Prompt ID
            curator_id: Curator user ID

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, curator_id)

        try:
            # Get current prompt state
            cursor.execute(
                """
                SELECT prompt_status, prompt_version, title, metadata
                FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Prompt {conversation_id} not found")

            current_status = result.get("prompt_status", "draft")
            if current_status not in ("review", "draft"):
                raise ValueError(f"Cannot publish prompt in {current_status} status")

            # Validate state transition
            if not self._validate_state_transition(
                current_status, "published", "curator"
            ):
                raise ValueError(
                    f"Invalid state transition from {current_status} to published"
                )

            current_version = result.get("prompt_version", 1)
            new_version = current_version + 1

            # Get prompt content from latest message for version history
            cursor.execute(
                """
                SELECT content, role FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (conversation_id,),
            )

            message_result = cursor.fetchone()
            prompt_content = message_result.get("content", "") if message_result else ""

            # Create version snapshot in conversation_messages
            if prompt_content:
                cursor.execute(
                    """
                    INSERT INTO conversation_messages (
                        conversation_id, user_id, role, content, metadata
                    ) VALUES (%s, %s, 'system', %s, %s)
                """,
                    (
                        conversation_id,
                        curator_id,
                        prompt_content,
                        json.dumps(
                            {
                                "version": new_version,
                                "version_type": "published",
                                "published_at": datetime.now().isoformat(),
                                "published_by": curator_id,
                            }
                        ),
                    ),
                )

            # Update prompt to published status
            cursor.execute(
                """
                UPDATE conversations
                SET prompt_status = 'published',
                    prompt_version = %s,
                    curator_id = %s,
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'published_at', NOW(),
                            'published_by', %s,
                            'version', %s
                        )
                WHERE id = %s
            """,
                (new_version, curator_id, curator_id, new_version, conversation_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def archive_prompt(self, conversation_id: str, user_id: str) -> bool:
        """
        Archive a prompt

        Args:
            conversation_id: Prompt ID
            user_id: User ID (must be curator or admin)

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Get current status for validation
            cursor.execute(
                """
                SELECT prompt_status FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Prompt {conversation_id} not found")

            current_status = result.get("prompt_status", "draft")

            # Validate state transition
            if not self._validate_state_transition(
                current_status, "archived", "curator"
            ):
                raise ValueError(
                    f"Invalid state transition from {current_status} to archived"
                )

            # Update status to archived
            cursor.execute(
                """
                UPDATE conversations
                SET prompt_status = 'archived',
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'archived_at', NOW(),
                            'archived_by', %s
                        )
                WHERE id = %s
            """,
                (user_id, conversation_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_prompt_versions(self, conversation_id: str, user_id: str) -> List[Dict]:
        """
        Get version history for a prompt

        Args:
            conversation_id: Prompt ID
            user_id: User ID

        Returns:
            List of version dictionaries
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Get version snapshots from conversation_messages (all version types)
            cursor.execute(
                """
                SELECT id, content, metadata, created_at, user_id
                FROM conversation_messages
                WHERE conversation_id = %s
                  AND role = 'system'
                  AND metadata->>'version_type' IS NOT NULL
                ORDER BY created_at DESC
            """,
                (conversation_id,),
            )

            versions = cursor.fetchall()

            result = []
            for version in versions:
                version_dict = dict(version)
                # Parse metadata
                if version_dict.get("metadata") and isinstance(
                    version_dict["metadata"], str
                ):
                    version_dict["metadata"] = json.loads(version_dict["metadata"])
                elif version_dict.get("metadata") is None:
                    version_dict["metadata"] = {}
                result.append(version_dict)

            return result
        finally:
            cursor.close()
            conn.close()

    def rollback_prompt_version(
        self, conversation_id: str, version_number: int, user_id: str
    ) -> bool:
        """
        Rollback a prompt to a previous version

        Args:
            conversation_id: Prompt ID
            version_number: Version number to rollback to
            user_id: User ID

        Returns:
            bool: True if successful
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Get the version content
            cursor.execute(
                """
                SELECT content, metadata FROM conversation_messages
                WHERE conversation_id = %s
                  AND role = 'system'
                  AND metadata->>'version' = %s
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (conversation_id, str(version_number)),
            )

            version_result = cursor.fetchone()
            if not version_result:
                raise ValueError(
                    f"Version {version_number} not found for prompt {conversation_id}"
                )

            version_content = version_result.get("content", "")

            # Get current version
            cursor.execute(
                """
                SELECT prompt_version FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            current_result = cursor.fetchone()
            current_version = (
                current_result.get("prompt_version", 1) if current_result else 1
            )
            new_version = current_version + 1

            # Create new version with rolled-back content
            cursor.execute(
                """
                INSERT INTO conversation_messages (
                    conversation_id, user_id, role, content, metadata
                ) VALUES (%s, %s, 'user', %s, %s)
            """,
                (
                    conversation_id,
                    user_id,
                    version_content,
                    json.dumps(
                        {
                            "version": new_version,
                            "version_type": "rollback",
                            "rolled_back_from": version_number,
                            "rolled_back_at": datetime.now().isoformat(),
                            "rolled_back_by": user_id,
                        }
                    ),
                ),
            )

            # Update prompt version
            cursor.execute(
                """
                UPDATE conversations
                SET prompt_version = %s,
                    prompt_status = 'draft',
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'rolled_back_at', NOW(),
                            'rolled_back_from', %s,
                            'rolled_back_by', %s
                        )
                WHERE id = %s
            """,
                (new_version, version_number, user_id, conversation_id),
            )

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def _check_prompt_permission(
        self, user_id: str, conversation_id: str, required_role: str
    ) -> bool:
        """
        Check if user has required permission for prompt

        Args:
            user_id: User ID
            conversation_id: Prompt ID
            required_role: Required role ('contributor', 'curator', 'viewer', 'admin')

        Returns:
            bool: True if user has permission
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self.set_user_context(cursor, user_id)

        try:
            # Check user's prompt_role (will be added in Phase 6, placeholder for now)
            cursor.execute(
                """
                SELECT prompt_role FROM users
                WHERE id = %s
            """,
                (user_id,),
            )

            user_result = cursor.fetchone()
            if not user_result:
                return False

            user_role = user_result.get("prompt_role", "viewer")

            # Role hierarchy: admin > curator > contributor > viewer
            role_hierarchy = {"admin": 4, "curator": 3, "contributor": 2, "viewer": 1}

            user_level = role_hierarchy.get(user_role, 1)
            required_level = role_hierarchy.get(required_role, 1)

            # Also check if user owns the prompt (owners can always edit their own drafts)
            cursor.execute(
                """
                SELECT user_id, prompt_status FROM conversations
                WHERE id = %s
            """,
                (conversation_id,),
            )

            prompt_result = cursor.fetchone()
            if prompt_result:
                prompt_owner = prompt_result.get("user_id")
                prompt_status = prompt_result.get("prompt_status", "draft")

                # Owners can edit their own drafts regardless of role
                if (
                    prompt_owner == user_id
                    and prompt_status == "draft"
                    and required_role == "contributor"
                ):
                    return True

            return user_level >= required_level
        finally:
            cursor.close()
            conn.close()
