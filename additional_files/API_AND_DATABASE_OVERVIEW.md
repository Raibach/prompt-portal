# API Structure & PostgreSQL Database Setup Overview

## Executive Summary

This document provides a comprehensive overview of the Grace Editor API architecture and PostgreSQL database configuration.

---

## 1. API Architecture

### 1.1 Multi-Server Architecture

The application uses **three separate API servers**:

#### **A. FastAPI Server** (`backend/main.py`)
- **Port**: 8000 (default)
- **Framework**: FastAPI (Python)
- **Purpose**: Modern REST API with async support
- **Endpoints**: 
  - `/api/health` - Health check
  - `/api/news/search` - News search
  - `/api/pdf/summarize` - PDF processing
  - `/api/memory/recall` - Memory system
  - `/api/conversations/*` - Conversation management
  - `/api/projects/*` - Project management
- **Database Integration**: Uses `ConversationAPI` and `ProjectsAPI` classes
- **Initialization**: Connects to PostgreSQL on startup via `DATABASE_URL` env var

#### **B. Flask Server** (`grace_api.py`)
- **Port**: 5001 (default)
- **Framework**: Flask (Python)
- **Purpose**: Main Grace AI backend with full reasoning capabilities
- **Endpoints**: 
  - `/api/health` - Health check
  - `/api/teacher/query` - Main AI query endpoint
  - `/api/news/search` - News search with memory
  - `/api/pdf/summarize` - PDF summarization
  - `/api/conversations/*` - Conversation CRUD
  - `/api/projects/*` - Project CRUD
  - `/api/quarantine/*` - Quarantine management
- **Database Integration**: Full PostgreSQL integration with `ConversationAPI`, `ProjectsAPI`, `QuarantineAPI`
- **Initialization**: Validates `DATABASE_URL` or `DATABASE_PUBLIC_URL`, tests connection on startup

#### **C. Express.js Server** (`backend/server.js`)
- **Port**: 3001
- **Framework**: Express.js (Node.js)
- **Purpose**: Proxy/gateway server, routes requests to Python backends
- **Endpoints**:
  - `/api/lmstudio/query` - Routes to Flask API
  - `/api/grace/*` - Proxies to Flask API
  - `/api/pdf/summarize` - File upload handling, proxies to Flask
  - `/api/quarantine/*` - Proxies to Flask API
  - `/api/auth/*` - Authentication (dev mode)
  - `/api/conversations/*` - Currently returns empty (uses localStorage fallback)
  - `/api/projects/*` - Currently returns empty (uses localStorage fallback)
- **Database Integration**: None (pure proxy layer)

### 1.2 API Service Classes

#### **ConversationAPI** (`backend/conversation_api.py`)
- **Purpose**: PostgreSQL service for conversation and message storage
- **Features**:
  - User-scoped conversations with RLS (Row-Level Security)
  - Message management with metadata (JSONB)
  - Project association via metadata
  - Archive/unarchive functionality
  - Connection error handling with retry logic
  - Port validation and SSL mode configuration

#### **ProjectsAPI** (`backend/projects_api.py`)
- **Purpose**: PostgreSQL service for project management
- **Features**:
  - User-scoped projects
  - Archive/unarchive (soft delete)
  - RLS for multi-tenancy
  - Similar connection handling as ConversationAPI

#### **QuarantineAPI** (`backend/quarantine_api.py`)
- **Purpose**: PostgreSQL service for quarantine item management
- **Features**:
  - Threat level classification (CRITICAL, HIGH, MODERATE, SAFE)
  - Status tracking (pending_review, approved, rejected, quarantined)
  - User isolation via RLS
  - Summary statistics

---

## 2. PostgreSQL Database Configuration

### 2.1 Connection String Management

The application supports **two environment variables** for database connection:

1. **`DATABASE_PUBLIC_URL`** (Preferred for external connections)
   - Used for Railway public network connections
   - Format: `postgresql://user:password@host.rlwy.net:port/database`
   - Example: `postgresql://postgres:PASSWORD@hopper.proxy.rlwy.net:38834/railway`

2. **`DATABASE_URL`** (Fallback)
   - Used for Railway internal network or local connections
   - Format: `postgresql://user:password@host:port/database`
   - Internal Railway: `postgresql://postgres:PASSWORD@postgres.railway.internal:5432/railway`
   - Local: `postgresql://user:password@localhost:5432/grace_db`

### 2.2 Connection Logic

**Priority Order:**
1. Check `DATABASE_PUBLIC_URL` → validate → use if valid
2. Check `DATABASE_URL` → validate → use if valid
3. Disable database features if neither is valid

**Validation Checks:**
- Rejects URLs containing placeholder text like `hostname`
- Validates hostname format (Railway, localhost, etc.)
- Tests connection on startup
- Handles port parsing errors gracefully

### 2.3 Connection Features

**SSL Configuration:**
- Private Railway URLs (`railway.internal`): `sslmode=prefer`
- Public URLs: `sslmode=require`
- Local connections: `sslmode=prefer` (default)

**Timeout Settings:**
- Private Railway: 15 seconds
- Public Railway proxy: 15 seconds
- Other connections: 10 seconds

**Error Handling:**
- Detects invalid port numbers and removes them
- Retries with cleaned URL on port errors
- Logs connection errors to `logs/database_connection_error.log`
- Provides detailed error messages for debugging

---

## 3. Database Schema

### 3.1 Core Tables

#### **Users & Authentication**
- `users` - User accounts with email, password hash, status
- `subscription_plans` - Subscription tiers (Free, Pro, Enterprise)
- `user_subscriptions` - Active user subscriptions
- `payment_methods` - Payment method storage
- `invoices` - Invoice records
- `usage_metrics` - Usage tracking per user/month

#### **Grace Settings**
- `user_grace_settings` - Per-user Grace AI configuration
  - Temperature, reasoning style, self-reflection
  - Training mode, confidence threshold
  - Editorial framework settings

#### **Conversations & Messages**
- `conversations` - User conversations
  - Fields: `id`, `user_id`, `title`, `message_count`, `is_archived`, `metadata` (JSONB)
  - Metadata stores `project_id` for project association
- `conversation_messages` - Messages within conversations
  - Fields: `id`, `conversation_id`, `user_id`, `role`, `content`, `metadata` (JSONB)
  - Roles: `user`, `assistant`, `system`

#### **Projects**
- `projects` - User projects for organizing conversations
  - Fields: `id`, `user_id`, `name`, `description`, `is_archived`
  - Created via migration `migration_002_projects.sql`

#### **Memory System**
- `user_memory_log` - Links to Qdrant vector store
  - Stores: `qdrant_point_id`, `content_preview`, `source_type`, `importance_score`
  - Audit trail for memory operations

#### **Quarantine System**
- `quarantine_items` - Quarantined content
  - Fields: `source_type`, `source_id`, `url`, `title`, `threat_level`, `threat_category`, `threat_details` (JSONB), `status`
  - Threat levels: `CRITICAL`, `HIGH`, `MODERATE`, `SAFE`
  - Status: `pending_review`, `approved`, `rejected`, `quarantined`

#### **Training & Audit**
- `training_data` - Training data for fine-tuning
- `audit_logs` - System audit trail

### 3.2 Row-Level Security (RLS)

**Enabled on:**
- `user_subscriptions`
- `usage_metrics`
- `user_grace_settings`
- `conversations`
- `conversation_messages`
- `user_memory_log`
- `quarantine_items`
- `training_data`
- `projects` (via migration)

**RLS Policy:**
```sql
CREATE POLICY user_isolation ON <table>
  USING (user_id = current_setting('app.current_user_id', true)::UUID);
```

**Context Setting:**
Each API call sets user context via:
```python
cursor.execute(f"SET app.current_user_id = '{user_id}'")
```

### 3.3 Database Functions & Triggers

**Auto-update Timestamp:**
```sql
CREATE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Usage Quota Check:**
```sql
CREATE FUNCTION check_usage_quota(
  p_user_id UUID,
  p_metric_type VARCHAR(50)
) RETURNS BOOLEAN
```

### 3.4 Migrations

**Migration Files:**
1. `migration_001_memory_consciousness.sql` - Memory system tables
2. `migration_002_projects.sql` - Projects table with RLS
3. `migration_003_conversations_metadata.sql` - Adds `metadata` JSONB column to conversations

**Schema File:**
- `database/schema.sql` - Complete production schema (409 lines)
  - Includes all tables, indexes, RLS policies, functions, triggers

---

## 4. Local Database Setup

### 4.1 Connection String Format

For **local PostgreSQL**, use:
```
postgresql://username:password@localhost:5432/database_name
```

**Example:**
```
postgresql://postgres:postgres@localhost:5432/grace_db
```

### 4.2 Environment Configuration

**Option 1: `.env` file** (recommended)
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grace_db
```

**Option 2: Environment variable**
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grace_db
```

### 4.3 Database Initialization

**Script:** `scripts/database/init_database.py`

**Usage:**
```bash
python3 scripts/database/init_database.py
```

**What it does:**
1. Reads `DATABASE_URL` from environment
2. Connects to PostgreSQL
3. Executes `database/schema.sql`
4. Creates all tables, indexes, functions, triggers
5. Verifies tables were created

### 4.4 Applying Migrations

**Projects Migration:**
```bash
python3 scripts/database/apply_projects_migration.py
```

**Note:** Migrations should be run in order:
1. Base schema (`schema.sql`)
2. Migration 001 (memory)
3. Migration 002 (projects)
4. Migration 003 (conversations metadata)

---

## 5. API Endpoint Summary

### 5.1 FastAPI Endpoints (`backend/main.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/news/search` | News search |
| POST | `/api/pdf/summarize` | PDF summarization |
| POST | `/api/memory/recall` | Memory recall |
| GET | `/api/reasoning/trace` | Reasoning trace |
| POST | `/api/source/evaluate` | Source evaluation |
| POST | `/api/train` | Training data collection |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get conversation |
| POST | `/api/conversations` | Create conversation |
| PUT | `/api/conversations/{id}` | Update conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| POST | `/api/conversations/{id}/archive` | Archive conversation |
| GET | `/api/conversations/archived` | Get archived conversations |
| GET | `/api/conversations/{id}/messages` | Get messages |
| POST | `/api/conversations/{id}/messages` | Add message |
| DELETE | `/api/messages/{id}` | Delete message |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Get project |
| POST | `/api/projects` | Create project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

### 5.2 Flask Endpoints (`grace_api.py`)

Similar endpoints to FastAPI, plus:
- `/api/teacher/query` - Main AI query endpoint
- `/api/quarantine/*` - Quarantine management

### 5.3 Express.js Endpoints (`backend/server.js`)

Proxy endpoints that forward to Flask API:
- `/api/lmstudio/query` → Flask `/api/teacher/query`
- `/api/grace/*` → Flask `/api/*`
- `/api/pdf/summarize` → Flask `/api/pdf/summarize`
- `/api/quarantine/*` → Flask `/api/quarantine/*`

---

## 6. Authentication & User Context

### 6.1 Current Implementation

**FastAPI (`backend/main.py`):**
- Uses `X-User-ID` header
- Fallback: `DEFAULT_USER_ID` env var or placeholder UUID
- **TODO**: Integrate with real authentication system

**Flask (`grace_api.py`):**
- Uses `X-API-Key` header
- Function: `get_user_id_from_header()` extracts user ID
- Function: `get_or_create_user_from_api_key()` creates/retrieves user

**Express.js (`backend/server.js`):**
- Dev mode: Accepts all API keys
- Forwards `X-API-Key` header to Flask API

### 6.2 User ID Format

- **Format**: UUID v4
- **Example**: `00000000-0000-0000-0000-000000000000`
- **Storage**: Stored as UUID type in PostgreSQL

---

## 7. Key Features

### 7.1 Multi-Tenancy

- **RLS (Row-Level Security)** ensures users can only access their own data
- **User context** set per-request via `SET app.current_user_id`
- **Isolation** at database level, not just application level

### 7.2 Offline Support

- API classes handle connection errors gracefully
- Returns `ConnectionError` with helpful messages
- Frontend can fall back to localStorage when database unavailable

### 7.3 Error Handling

- **Connection errors**: Logged to `logs/database_connection_error.log`
- **Schema errors**: Detailed error messages with traceback
- **Data errors**: UUID validation, type checking
- **Retry logic**: Port parsing errors trigger URL cleanup and retry

### 7.4 Metadata Storage

- **JSONB columns** for flexible metadata:
  - `conversations.metadata` - Stores `project_id`, custom fields
  - `conversation_messages.metadata` - Message-specific metadata
  - `quarantine_items.threat_details` - Threat analysis details
- **GIN indexes** on JSONB for efficient queries

---

## 8. Recommendations

### 8.1 For Local Development

1. **Set up local PostgreSQL:**
   ```bash
   # macOS
   brew install postgresql
   brew services start postgresql
   
   # Create database
   createdb grace_db
   ```

2. **Create `.env` file:**
   ```bash
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grace_db
   ```

3. **Initialize database:**
   ```bash
   python3 scripts/database/init_database.py
   ```

4. **Apply migrations:**
   ```bash
   python3 scripts/database/apply_projects_migration.py
   ```

### 8.2 For Production (Railway)

1. **Use `DATABASE_PUBLIC_URL`** for external connections
2. **Use `DATABASE_URL`** for internal Railway network (no egress fees)
3. **Verify connection** on startup (already implemented)
4. **Monitor logs** for connection errors

### 8.3 Code Improvements

1. **Unify authentication** across FastAPI, Flask, and Express
2. **Add connection pooling** for better performance
3. **Implement migrations system** (Alembic or similar)
4. **Add database health checks** to health endpoints
5. **Consolidate API servers** (consider removing Express proxy layer)

---

## 9. File Structure

```
grace-editor/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── server.js            # Express.js proxy
│   ├── conversation_api.py  # Conversation PostgreSQL service
│   ├── projects_api.py      # Projects PostgreSQL service
│   └── quarantine_api.py    # Quarantine PostgreSQL service
├── database/
│   ├── schema.sql           # Complete production schema
│   ├── migration_001_memory_consciousness.sql
│   ├── migration_002_projects.sql
│   └── migration_003_conversations_metadata.sql
├── scripts/
│   └── database/
│       ├── init_database.py
│       └── apply_projects_migration.py
└── grace_api.py             # Flask server (main backend)
```

---

## 10. Testing Database Connection

### 10.1 Quick Test

```python
import os
from dotenv import load_dotenv
from backend.conversation_api import ConversationAPI

load_dotenv()
database_url = os.getenv('DATABASE_URL')

if database_url:
    api = ConversationAPI(database_url)
    conn = api.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print("✅ Connection successful!")
    cursor.close()
    conn.close()
else:
    print("❌ DATABASE_URL not set")
```

### 10.2 Verify Schema

```sql
-- Connect to database
psql postgresql://postgres:postgres@localhost:5432/grace_db

-- List all tables
\dt

-- Check RLS policies
SELECT tablename, policyname 
FROM pg_policies 
WHERE schemaname = 'public';

-- Verify projects table exists
SELECT * FROM projects LIMIT 1;
```

---

**Last Updated:** 2024
**Maintained By:** Grace Editor Development Team

