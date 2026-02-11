# Memory & Artifact System for User Stories

## Overview

The database is **critical** to the application. It handles memory and artifacts related to user stories, allowing the model to access them based on questions from users.

---

## Architecture

### Flow
1. **User writes story** → Artifacts stored in database
2. **User asks question** → Model queries database for relevant artifacts
3. **Model accesses artifacts** → Uses them to answer questions about the story

---

## Database Tables

### 1. User Memories (`user_memories`)

**Purpose:** Store all user-submitted content (story artifacts, notes, etc.)

**Key Fields:**
- `content` - The actual story content/artifact
- `content_type` - Type: 'pdf', 'text', 'story', 'conversation', 'url'
- `source_type` - Source: 'user_upload', 'story_section', 'conversation'
- `source_metadata` - JSONB with story context (chapter, scene, character, etc.)
- `quarantine_status` - Safety check: 'pending', 'safe', 'flagged'
- `vector_id` - Link to vector store (Qdrant) for semantic search
- `promoted_to_grace` - Whether Grace can access this (curation layer)

**Example:**
```sql
INSERT INTO user_memories (
  user_id, content, content_type, source_type, source_metadata
) VALUES (
  'user-uuid',
  'Chapter 1: The hero enters the forest...',
  'story',
  'story_section',
  '{"chapter": 1, "scene": "forest", "character": "hero"}'
);
```

### 2. Memory Log (`user_memory_log`)

**Purpose:** Audit trail linking to vector store (Qdrant)

**Key Fields:**
- `qdrant_point_id` - Vector store point ID
- `qdrant_collection` - Collection name (per user)
- `content_preview` - Preview of content
- `content_hash` - Hash for deduplication
- `source_type` - Type of source
- `importance_score` - How important this memory is

**Usage:** Links PostgreSQL to Qdrant vector store for semantic search

### 3. Conversations (`conversations` & `conversation_messages`)

**Purpose:** Store user questions and model responses about stories

**Key Fields:**
- `conversations.title` - Conversation title
- `conversation_messages.role` - 'user' or 'assistant'
- `conversation_messages.content` - Question or answer
- `conversation_messages.metadata` - JSONB with story context

**Example:**
```sql
-- User asks about story
INSERT INTO conversation_messages (
  conversation_id, user_id, role, content, metadata
) VALUES (
  'conv-uuid',
  'user-uuid',
  'user',
  'What happened in Chapter 3?',
  '{"story_id": "story-uuid", "chapter": 3}'
);

-- Model responds using artifacts
INSERT INTO conversation_messages (
  conversation_id, user_id, role, content, metadata
) VALUES (
  'conv-uuid',
  'user-uuid',
  'assistant',
  'In Chapter 3, the hero...',
  '{"sources": ["memory-uuid-1", "memory-uuid-2"]}'
);
```

### 4. Grace Context (`grace_context`) - Advanced

**Purpose:** Curated subset of memories Grace can actually see

**Key Fields:**
- `memory_id` - Link to `user_memories`
- `context_category` - 'writing_style', 'story_elements', 'character_traits'
- `priority` - 0-100, higher = more important
- `is_active` - Whether Grace can currently use this

**Usage:** Wikipedia-style curation - only promoted memories are accessible

---

## How Model Accesses Artifacts

### Step 1: User Asks Question

```python
# User asks: "What happened in Chapter 3?"
question = "What happened in Chapter 3?"
user_id = get_user_id_from_railway()
```

### Step 2: Query Relevant Memories

```python
# Search for relevant story artifacts
from grace_memory_api import GraceMemoryAPI

memory_api = GraceMemoryAPI(DATABASE_URL)

# Semantic search in vector store
relevant_memories = memory_api.recall_memories(
    user_id=user_id,
    query=question,
    limit=10,
    min_score=0.7
)

# Results include:
# - Chapter 3 content
# - Related scenes
# - Character interactions
```

### Step 3: Model Uses Artifacts

```python
# Model receives context
context = "\n".join([m['content'] for m in relevant_memories])

# Model generates response using artifacts
response = query_llm(
    system_prompt="You are Grace, helping with the user's story...",
    user_query=question,
    context=context  # Artifacts from database
)
```

### Step 4: Store Response

```python
# Store model's response in conversation
conversation_api.add_message(
    conversation_id=conv_id,
    user_id=user_id,
    role='assistant',
    content=response,
    metadata={
        'sources': [m['id'] for m in relevant_memories],
        'story_context': {'chapter': 3}
    }
)
```

---

## Story Artifact Storage

### Storing Story Sections

```python
def store_story_artifact(user_id, chapter, scene, content):
    """Store a story section as an artifact"""
    memory_api = GraceMemoryAPI(DATABASE_URL)
    
    memory_id = memory_api.create_memory(
        user_id=user_id,
        content=content,
        content_type='story',
        source_type='story_section',
        title=f"Chapter {chapter}, Scene {scene}",
        source_metadata={
            'chapter': chapter,
            'scene': scene,
            'story_id': story_id
        },
        quarantine_score=0.9,  # Stories are generally safe
        quarantine_status='safe'
    )
    
    return memory_id
```

### Querying Story Artifacts

```python
def get_story_context(user_id, query):
    """Get relevant story artifacts for a question"""
    memory_api = GraceMemoryAPI(DATABASE_URL)
    
    # Semantic search
    memories = memory_api.recall_memories(
        user_id=user_id,
        query=query,
        limit=5
    )
    
    # Filter by story context if needed
    story_memories = [
        m for m in memories 
        if m.get('source_type') == 'story_section'
    ]
    
    return story_memories
```

---

## Database Queries for Story Access

### Get All Story Artifacts for User

```sql
SELECT 
  id, content, content_type, source_metadata,
  created_at, importance_score
FROM user_memories
WHERE user_id = :user_id
  AND content_type = 'story'
  AND quarantine_status = 'safe'
ORDER BY created_at DESC;
```

### Get Artifacts by Chapter

```sql
SELECT 
  id, content, source_metadata
FROM user_memories
WHERE user_id = :user_id
  AND content_type = 'story'
  AND source_metadata->>'chapter' = '3'
ORDER BY source_metadata->>'scene';
```

### Get Recent Conversations About Story

```sql
SELECT 
  cm.content, cm.role, cm.created_at,
  cm.metadata->>'story_context' as story_context
FROM conversation_messages cm
JOIN conversations c ON cm.conversation_id = c.id
WHERE c.user_id = :user_id
  AND cm.metadata->>'story_id' = :story_id
ORDER BY cm.created_at DESC
LIMIT 20;
```

---

## Vector Search Integration

### Qdrant Vector Store

**Purpose:** Fast semantic search across story artifacts

**Setup:**
- Each user has a collection: `grace_memory_{user_id}`
- Content is embedded using sentence-transformers
- Vector IDs stored in `user_memory_log.qdrant_point_id`

**Query Flow:**
1. User asks question
2. Question is embedded to vector
3. Vector search finds similar story artifacts
4. PostgreSQL provides full content and metadata

---

## Row-Level Security (RLS)

**Critical:** All tables use RLS to ensure users only see their own artifacts

```sql
-- RLS Policy
CREATE POLICY user_isolation ON user_memories
  USING (user_id = current_setting('app.current_user_id', true)::UUID);
```

**Usage:**
```python
# Set user context before querying
cursor.execute(f"SET app.current_user_id = '{user_id}'")

# All queries automatically filtered to user's data
cursor.execute("SELECT * FROM user_memories")
# Only returns this user's memories
```

---

## Ngrok Tunnel Integration

### Architecture

```
Production (Railway) → Ngrok Tunnel → Local Model (localhost:1234)
```

**Flow:**
1. User in production asks question
2. Railway API receives request
3. API queries database for artifacts
4. API sends question + artifacts to local model via Ngrok
5. Model responds using artifacts
6. Response stored in database

### Configuration

**Ngrok URL in production:**
```python
# Railway environment variable
NGROK_URL = os.getenv('NGROK_URL')  # e.g., https://xxx.ngrok-free.dev

# Model endpoint
MODEL_URL = f"{NGROK_URL}/v1/chat/completions"
```

**Local model (localhost:1234):**
- LM Studio or llama.cpp server
- Exposed via Ngrok tunnel
- Receives requests from Railway production

---

## Critical Database Operations

### 1. Store Story Artifact

```python
def store_artifact(user_id, story_content, metadata):
    """Store story artifact - CRITICAL for model access"""
    memory_api = GraceMemoryAPI(DATABASE_URL)
    
    return memory_api.create_memory(
        user_id=user_id,
        content=story_content,
        content_type='story',
        source_type='story_section',
        source_metadata=metadata,
        quarantine_status='safe'
    )
```

### 2. Retrieve Artifacts for Question

```python
def get_relevant_artifacts(user_id, question):
    """Get artifacts relevant to user's question - CRITICAL"""
    memory_api = GraceMemoryAPI(DATABASE_URL)
    
    # Semantic search
    artifacts = memory_api.recall_memories(
        user_id=user_id,
        query=question,
        limit=10
    )
    
    return artifacts
```

### 3. Store Question-Answer Pair

```python
def store_qa(user_id, question, answer, artifact_ids):
    """Store Q&A with artifact references"""
    conversation_api = ConversationAPI(DATABASE_URL)
    
    conversation_api.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role='user',
        content=question
    )
    
    conversation_api.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role='assistant',
        content=answer,
        metadata={
            'artifact_sources': artifact_ids,
            'story_context': story_context
        }
    )
```

---

## Security Considerations

### User Isolation

- **RLS policies** ensure users only see their artifacts
- **User ID from Railway** must be correct (why we remove API keys)
- **Vector collections** are per-user

### Quarantine System

- All artifacts checked before storage
- Unsafe content flagged and not accessible to model
- User can review and approve flagged content

---

## Performance

### Indexes

```sql
-- Fast user lookups
CREATE INDEX idx_memories_user ON user_memories(user_id, created_at DESC);

-- Fast content hash lookups (deduplication)
CREATE INDEX idx_memories_hash ON user_memories(user_id, content_hash);

-- Fast metadata queries
CREATE INDEX idx_memories_metadata ON user_memories USING GIN (source_metadata);
```

### Caching

- Vector search results can be cached
- Frequently accessed artifacts cached in memory
- Conversation history paginated

---

## Summary

**Database is Critical Because:**
1. Stores all story artifacts
2. Enables semantic search via vector store
3. Links questions to relevant artifacts
4. Maintains conversation history
5. Ensures user isolation via RLS

**Model Access Flow:**
1. User asks question → Database queried
2. Relevant artifacts retrieved → Sent to model
3. Model generates response → Uses artifacts
4. Response stored → Linked to artifacts

**Railway Authentication:**
- Must provide correct `user_id`
- RLS depends on correct user context
- No API keys needed - Railway handles auth

---

**Last Updated:** 2024
**Status:** Production System

