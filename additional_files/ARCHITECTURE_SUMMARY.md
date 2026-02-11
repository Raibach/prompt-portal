# Grace Editor Architecture Summary

## System Overview

### Production Setup
- **Hosting:** Railway (production app)
- **Database:** Railway PostgreSQL (critical - stores memory/artifacts)
- **Model:** Local model (localhost) exposed via Ngrok tunnel
- **Authentication:** Railway login layer (remove API key layer)

### Architecture Flow

```
User (Browser)
  ↓
Railway Production App
  ↓ (Railway Auth)
Flask API (grace_api.py)
  ↓ (Queries Database)
Railway PostgreSQL
  ↓ (Retrieves Artifacts)
Flask API
  ↓ (Sends to Model via Ngrok)
Ngrok Tunnel
  ↓
Local Model (localhost:1234)
  ↓ (Response)
Flask API
  ↓ (Stores in Database)
Railway PostgreSQL
  ↓
User (Browser)
```

---

## Critical Components

### 1. Database (Railway PostgreSQL) ⭐ CRITICAL

**Purpose:** Stores memory and artifacts related to user stories

**Key Tables:**
- `user_memories` - Story artifacts, content
- `user_memory_log` - Links to vector store (Qdrant)
- `conversations` - User questions about stories
- `conversation_messages` - Q&A pairs with artifact references
- `grace_context` - Curated memories Grace can access

**Why Critical:**
- Model accesses artifacts based on user questions
- RLS ensures users only see their own artifacts
- Vector search enables semantic retrieval
- All story context stored here

### 2. Memory/Artifact System

**Flow:**
1. User writes story → Artifacts stored in `user_memories`
2. User asks question → Semantic search finds relevant artifacts
3. Model receives artifacts → Generates response using story context
4. Response stored → Linked to artifacts in `conversation_messages`

**Implementation:**
- `GraceMemoryAPI` - Handles memory storage/retrieval
- Vector store (Qdrant) - Fast semantic search
- PostgreSQL - Full content and metadata

### 3. Ngrok Tunnel

**Purpose:** Expose local model to Railway production

**Configuration:**
```python
# Railway environment variable
NGROK_URL = os.getenv('NGROK_URL')  # https://xxx.ngrok-free.dev

# Model endpoint
MODEL_URL = f"{NGROK_URL}/v1/chat/completions"
```

**Flow:**
- Production API → Ngrok URL → Local model (localhost:1234)
- Model processes request → Returns response → Production API

### 4. Authentication (Railway)

**Current:** Railway login + API key layer
**Target:** Railway login only (remove API keys)

**Why Remove API Keys:**
- Railway already provides authentication
- Database RLS depends on correct user_id
- Reduces complexity
- Single source of truth

---

## Action Items

### Priority 1: Remove API Key Authentication

**Files to Modify:**
1. `grace_api.py`
   - Remove `require_api_key` decorator
   - Remove `get_or_create_user_from_api_key()` function
   - Update `get_user_id_from_header()` to use Railway auth only

2. `backend/server.js`
   - Remove `X-API-Key` header forwarding
   - Trust Railway authentication

3. `backend/auth-middleware.js`
   - Remove `requireApiKey()` function
   - Use Railway/JWT only

**See:** `REMOVE_API_KEY_AUTH.md` for detailed plan

### Priority 2: Verify Database Setup

**Ensure:**
- Railway PostgreSQL connection working
- All tables created (20+ tables)
- RLS policies enabled
- Migrations applied

**See:** `SETUP_LOCAL_TO_MATCH_RAILWAY.md` for local setup

### Priority 3: Verify Memory System

**Ensure:**
- `GraceMemoryAPI` working correctly
- Vector store (Qdrant) connected
- Artifacts stored/retrieved properly
- User isolation via RLS

**See:** `MEMORY_ARTIFACT_SYSTEM.md` for details

---

## Database Schema (Critical Tables)

### User Memories
```sql
CREATE TABLE user_memories (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  content TEXT NOT NULL,  -- Story artifact content
  content_type VARCHAR(50),  -- 'story', 'text', 'pdf'
  source_metadata JSONB,  -- Chapter, scene, character info
  quarantine_status VARCHAR(20),  -- Safety check
  promoted_to_grace BOOLEAN,  -- Whether Grace can access
  ...
);
```

### Conversations
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  title VARCHAR(255),
  ...
);

CREATE TABLE conversation_messages (
  id UUID PRIMARY KEY,
  conversation_id UUID,
  user_id UUID,
  role VARCHAR(20),  -- 'user' or 'assistant'
  content TEXT,  -- Question or answer
  metadata JSONB,  -- Links to artifacts
  ...
);
```

---

## User Story Workflow

### 1. User Writes Story
```python
# Store story section as artifact
memory_api.create_memory(
    user_id=user_id,
    content=story_content,
    content_type='story',
    source_type='story_section',
    source_metadata={'chapter': 3, 'scene': 'forest'}
)
```

### 2. User Asks Question
```python
# User: "What happened in Chapter 3?"
question = "What happened in Chapter 3?"
```

### 3. System Retrieves Artifacts
```python
# Semantic search for relevant artifacts
artifacts = memory_api.recall_memories(
    user_id=user_id,
    query=question,
    limit=10
)
# Returns: Chapter 3 content, related scenes, etc.
```

### 4. Model Generates Response
```python
# Send to model via Ngrok
response = query_model(
    question=question,
    context=artifacts,  # Story artifacts
    model_url=NGROK_URL
)
```

### 5. Store Response
```python
# Store Q&A with artifact references
conversation_api.add_message(
    conversation_id=conv_id,
    user_id=user_id,
    role='assistant',
    content=response,
    metadata={'artifact_sources': [a['id'] for a in artifacts]}
)
```

---

## Security (RLS)

**Row-Level Security ensures:**
- Users only see their own artifacts
- Database queries automatically filtered
- No cross-user data access

**Implementation:**
```sql
CREATE POLICY user_isolation ON user_memories
  USING (user_id = current_setting('app.current_user_id', true)::UUID);
```

**Usage:**
```python
# Set user context before querying
cursor.execute(f"SET app.current_user_id = '{user_id}'")

# All queries automatically filtered
cursor.execute("SELECT * FROM user_memories")
# Only returns this user's memories
```

---

## Ngrok Configuration

### Local Model Setup
```bash
# Start local model (LM Studio or llama.cpp)
# Usually on localhost:1234

# Start Ngrok tunnel
ngrok http 1234

# Get Ngrok URL
# e.g., https://xxx.ngrok-free.dev
```

### Railway Environment Variable
```bash
# Set in Railway dashboard
NGROK_URL=https://xxx.ngrok-free.dev
```

### API Usage
```python
# In grace_api.py
NGROK_URL = os.getenv('NGROK_URL')
MODEL_URL = f"{NGROK_URL}/v1/chat/completions"

# Send request to local model via Ngrok
response = requests.post(MODEL_URL, json={
    'messages': [
        {'role': 'user', 'content': question},
        {'role': 'system', 'content': context}  # Artifacts
    ]
})
```

---

## Next Steps

1. **Review Documentation:**
   - `REMOVE_API_KEY_AUTH.md` - Remove API key layer
   - `MEMORY_ARTIFACT_SYSTEM.md` - Understand memory system
   - `SETUP_LOCAL_TO_MATCH_RAILWAY.md` - Local database setup

2. **Remove API Key Auth:**
   - Follow migration plan in `REMOVE_API_KEY_AUTH.md`
   - Test with Railway authentication only
   - Verify user_id is correct from Railway

3. **Verify Database:**
   - Ensure Railway PostgreSQL is accessible
   - Verify all tables exist
   - Test memory/artifact storage/retrieval

4. **Test End-to-End:**
   - User writes story → Artifacts stored
   - User asks question → Artifacts retrieved
   - Model generates response → Uses artifacts
   - Response stored → Linked to artifacts

---

## Key Points

✅ **Database is Critical** - All story artifacts stored here
✅ **Railway Auth** - Single source of truth for user identity
✅ **RLS** - Ensures user isolation
✅ **Ngrok** - Connects production to local model
✅ **Memory System** - Enables model to access story context

---

**Last Updated:** 2024
**Status:** Production System

