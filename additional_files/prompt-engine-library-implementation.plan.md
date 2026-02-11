<!-- 43c5d679-c453-4f0f-b445-cd864ec91d72 475bef24-fbdd-4504-934d-506c9992a957 -->
# Prompt Engine Library Implementation Plan

## Overview

Transform the existing Grace Editor into a centralized **Prompt Engine Library** by repurposing existing structures. The library will serve as the single source of truth for enterprise-approved prompts, with governance workflows, role-based access, feedback loops, and comprehensive search capabilities.

## Core Repurposing Strategy

### 1. Conversations → Prompts

- **`conversations` table** stores prompts (repurposed)
- **`conversation_messages`** stores prompt content/versions
- **`conversations.metadata`** stores prompt-specific data:
  - `status`: draft/review/published/archived
  - `lifecycle`: workflow state
  - `curator_id`: assigned curator UUID
  - `version`: current version number
  - `prompt_type`: type classification
  - `use_case`: specific use case
  - `output_type`: expected output format

### 2. Tag System → Prompt Taxonomy

- **`tag_definitions`** repurposed for prompt categories:
  - **Level 1**: Prompt Type (e.g., "Prompt for Novel", "Prompt for Engineering", "Prompt for Forms")
  - **Level 2**: Use Case (e.g., "Character Development", "Wiring Harness Design", "Data Collection")
  - **Level 3**: Specificity (e.g., specific character names, component types, form fields)
  - **Level 4**: Output Type (e.g., "Document", "Form", "Bento Box UI", "Schematic")
- **`conversation_tags`** links prompts to categories
- Tag paths change from "Novel > Character Development" to "Prompt for Novel > Character Development"

### 3. Projects → Prompt Collections

- Keep name "Projects" (represents prompt history/category)
- Projects contain prompts and their outputs/artifacts
- Project = collection of related prompts and their generated outputs

### 4. User Structure

- Extend `users.role` to include prompt roles OR add `prompt_role` column
- Roles: `contributor`, `curator`, `viewer`, `admin`
- Existing `role` column (teacher/student/admin) remains for education features

### 5. Milvus Integration

- Continue using existing Milvus setup
- Update metadata schema for prompts instead of conversations
- Tag paths updated for prompt taxonomy
- Vector embeddings represent prompt aspects for agent/generative AI use

## Database Schema Changes

### Migration File: `database/migration_014_prompt_engine_library.sql`

#### Extend `conversations` table

```sql
-- Add prompt lifecycle columns
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS prompt_status VARCHAR(20) DEFAULT 'draft' 
  CHECK (prompt_status IN ('draft', 'review', 'published', 'archived')),
ADD COLUMN IF NOT EXISTS curator_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS prompt_version INTEGER DEFAULT 1;

-- Update metadata structure for prompts
-- metadata will store: status, lifecycle, curator_id, prompt_type, use_case, output_type
```

#### New Supporting Tables

1. **`prompt_feedback`** - End user feedback queue
   - `id`, `conversation_id` (prompt), `user_id`, `feedback_type`, `content`, `status` (pending/approved/rejected), `curator_notes`, `created_at`

2. **`prompt_ratings`** - User ratings (1-5 stars)
   - `id`, `conversation_id` (prompt), `user_id`, `rating` (1-5), `created_at`

3. **`prompt_comments`** - Comments and discussions
   - `id`, `conversation_id` (prompt), `user_id`, `parent_id` (for threading), `content`, `created_at`

4. **`prompt_shares`** - Sharing relationships
   - `id`, `conversation_id` (prompt), `shared_by`, `shared_with`, `permission_level`, `created_at`

5. **`prompt_history`** - Audit log for all changes
   - `id`, `conversation_id` (prompt), `action`, `user_id`, `changes` (JSONB), `timestamp`

6. **`prompt_permissions`** - Role-based access control
   - `id`, `conversation_id` (prompt), `user_id`, `permission` (read/write/admin), `granted_by`, `created_at`

7. **`prompt_artifacts`** - Links prompts to project outputs
   - `id`, `conversation_id` (prompt), `project_id`, `artifact_type`, `artifact_data` (JSONB), `created_at`

#### Update `tag_definitions` Seed Data

- Replace literary tag taxonomy with prompt taxonomy
- Seed Level 1: "Prompt for Novel", "Prompt for Engineering", "Prompt for Forms", etc.
- Seed Level 2-4 based on prompt use cases

#### Extend `users` table

```sql
ALTER TABLE users
ADD COLUMN IF NOT EXISTS prompt_role VARCHAR(20) DEFAULT 'viewer'
  CHECK (prompt_role IN ('contributor', 'curator', 'viewer', 'admin'));
```

## Backend Implementation

### Files to Create/Modify

#### New Files

1. **`backend/prompts_api.py`** - Main prompt CRUD with lifecycle management
   - Repurpose `conversation_api.py` methods for prompts
   - Add workflow state machine (draft → review → published)
   - Version tracking using `conversation_messages`
   - Role-based access checks

2. **`backend/prompt_feedback_api.py`** - Feedback submission and queue management
   - Submit feedback endpoint
   - Curator feedback queue
   - Approve/reject feedback workflow

3. **`backend/prompt_permissions.py`** - Permission checking logic
   - Check user prompt role
   - Validate access permissions
   - RLS policy helpers

4. **`backend/prompt_tag_extractor.py`** - AI tag generation for prompts
   - Repurpose `tag_extractor.py` for prompt categories
   - Extract prompt type, use case, specificity, output type
   - Update prompts to use prompt taxonomy

5. **`backend/prompt_history_api.py`** - History retrieval
   - Get prompt change history
   - Audit log queries

6. **`backend/prompt_search_api.py`** - Search endpoints
   - Extend `query_generator.py` for prompt search
   - Filter by categories, roles, users, tags, status
   - Semantic search via Milvus

#### Files to Modify

1. **`backend/tag_extractor.py`** - Update for prompt taxonomy
   - Change extraction prompts from literary to prompt categories
   - Update tag path generation for prompts

2. **`backend/conversation_api.py`** - Add prompt lifecycle methods
   - `submit_for_review()`, `approve_prompt()`, `publish_prompt()`, `archive_prompt()`
   - Version management methods

3. **`backend/milvus_client.py`** - Update metadata schema
   - Change tag paths from "Novel > ..." to "Prompt for Novel > ..."
   - Update metadata structure for prompts

4. **`backend/projects_api.py`** - Keep as-is (or rename references in UI only)
   - Projects remain as collections
   - Add artifact linking methods

5. **`grace_api.py`** - Add prompt routes
   - `/api/prompts` - List prompts (with filters)
   - `/api/prompts/:id` - Get prompt details
   - `/api/prompts` POST - Create prompt (contributor)
   - `/api/prompts/:id` PUT - Update prompt
   - `/api/prompts/:id/submit` - Submit for review
   - `/api/prompts/:id/approve` - Approve (curator)
   - `/api/prompts/:id/publish` - Publish (curator)
   - `/api/prompts/:id/feedback` - Submit feedback
   - `/api/prompts/feedback/queue` - Get feedback queue (curator)
   - `/api/prompts/feedback/:id/approve` - Approve feedback
   - `/api/prompts/:id/history` - Get prompt history
   - `/api/prompts/:id/rate` - Rate prompt
   - `/api/prompts/:id/comment` - Add comment
   - `/api/prompts/search` - Search prompts

## Frontend Implementation

### Files to Create

1. **`frontend/src/pages/PromptEngineLibrary.tsx`** - Main catalog view
   - Grid/list view of prompts
   - Filter sidebar
   - Search bar
   - Status badges (draft/review/published)

2. **`frontend/src/pages/PromptDetail.tsx`** - Detail view
   - Prompt content display
   - History timeline
   - Comments section
   - Ratings display
   - Share button
   - Feedback submission

3. **`frontend/src/pages/PromptEditor.tsx`** - Create/edit prompt
   - Rich text editor for prompt content
   - Tag editor
   - Version management
   - Submit for review button

4. **`frontend/src/pages/CuratorDashboard.tsx`** - Curator tools
   - Feedback queue
   - Review workflow
   - Approval/rejection actions

5. **`frontend/src/components/PromptCard.tsx`** - Prompt card component
   - Title, description, tags
   - Status badge
   - Rating display
   - Quick actions

6. **`frontend/src/components/PromptFeedback.tsx`** - Feedback submission UI
   - Feedback form
   - Rating input
   - Comment field
   - Issue reporting

7. **`frontend/src/components/PromptTagEditor.tsx`** - Tag editing UI
   - Hierarchical tag selector
   - AI-suggested tags
   - Manual tag editing

8. **`frontend/src/components/PromptSearch.tsx`** - Search UI
   - Search input
   - Advanced filters
   - Results display

9. **`frontend/src/components/PromptHistory.tsx`** - Timeline UI
   - Version history
   - Change log
   - User actions

10. **`frontend/src/components/PromptRating.tsx`** - Rating component
    - Star rating input
    - Average rating display
    - Rating breakdown

11. **`frontend/src/components/PromptComments.tsx`** - Comments component
    - Threaded comments
    - @mentions support
    - Comment actions

12. **`frontend/src/components/PromptShare.tsx`** - Sharing component
    - Share with users/teams
    - Permission levels
    - Share link generation

13. **`frontend/src/components/PermissionsDisplay.tsx`** - Permissions UI
    - User role display
    - Permissions matrix
    - Role upgrade request

### Files to Modify

1. **`frontend/src/pages/WritingAreaIndex.tsx`** - Update references
   - Rename "Conversations" → "Prompts" in UI labels
   - Update navigation
   - Add Prompt Engine Library link

2. **`frontend/src/components/SettingsTab.tsx`** - Add permissions section
   - Display user's prompt role
   - Show permissions matrix

3. **`frontend/src/components/MemoriesTab.tsx`** - Update for prompts
   - Show prompts instead of conversations
   - Update tag display for prompt categories

## Implementation Phases

### Phase 1: Repurpose Core Structures

[ ] Update tag_definitions seed data with prompt taxonomy

[ ] Add prompt lifecycle columns to conversations table

[ ] Update tag_extractor.py for prompt category extraction

[ ] Rename UI references from "Conversations" to "Prompts"

[ ] Update conversation_api.py with prompt lifecycle methods

### Phase 2: Governance & Workflow

[ ] Add status field and workflow logic

[ ] Add curator assignment and review process

[ ] Add version tracking in conversation_messages

[ ] Build curator dashboard UI

[ ] Implement state machine for prompt lifecycle

### Phase 3: Feedback Loop

[ ] Create prompt_feedback table

[ ] Build feedback submission API

[ ] Build feedback submission UI

[ ] Build curator feedback queue

[ ] Integrate feedback into prompt update workflow

### Phase 4: Engagement & Discovery

[ ] Add prompt_ratings and prompt_comments tables

[ ] Build ratings/comments UI components

[ ] Add prompt_shares table and sharing UI

[ ] Update search to use prompt categories

[ ] Extend Milvus integration for prompt search

### Phase 5: History & Audit

[ ] Create prompt_history table

[ ] Build history API endpoints

[ ] Build history timeline UI

[ ] Add audit log access (role-based)

### Phase 6: Permissions & Settings

[ ] Add prompt_role column to users table

[ ] Create prompt_permissions table

[ ] Build permissions checking logic

[ ] Add permissions display to settings

[ ] Implement role-based access control

### Phase 7: Projects Integration

[ ] Update projects to show prompts and artifacts

[ ] Create prompt_artifacts table

[ ] Link artifacts to prompts

[ ] Update project detail view

## Key Implementation Notes

1. **Repurposing Approach**: All existing structures are repurposed, not replaced. The `conversations` table becomes the prompts table, `tag_definitions` becomes prompt taxonomy, etc.

2. **Vector Mapping**: Milvus embeddings represent aspects of prompts that will be used by agents and generative AI to build outcomes. Tag paths guide vector organization.

3. **Naming Convention**: Use "Prompt Engine Library" in all user-facing text, page titles, and documentation. Keep internal code names (e.g., `prompts_api.py`) for consistency.

4. **Version Control**: Use `conversation_messages` table to store prompt versions. Each version is a new message entry with version metadata.

5. **Lifecycle States**: Prompts flow through: draft → review → published → archived. Only curators can approve/publish.

6. **Feedback Flow**: End users submit feedback → stored in `prompt_feedback` → curator reviews → approved feedback triggers prompt update → updated prompt goes through review → publish cycle.

7. **Role System**: Extend existing `users.role` or add `prompt_role` column. Roles: contributor (create/edit), curator (review/publish), viewer (read-only), admin (full access).

8. **Tag Taxonomy**: Four-level hierarchy: Prompt Type → Use Case → Specificity → Output Type. Example: "Prompt for Novel > Character Development > Marcus > Document".

## Testing Considerations

- Test prompt creation and editing workflow
- Test curator review and approval process
- Test feedback submission and queue management
- Test search with prompt taxonomy
- Test version history and rollback
- Test role-based access control
- Test Milvus integration with prompt metadata
- Test sharing and permissions

## Migration Strategy

1. Run migration to add prompt-specific columns to existing tables
2. Create new supporting tables (feedback, ratings, comments, etc.)
3. Update seed data for `tag_definitions` with prompt taxonomy
4. Migrate existing conversations to prompts (if applicable)
5. Update Milvus metadata schema for prompts
6. Deploy backend API changes
7. Deploy frontend UI updates
8. Update documentation

