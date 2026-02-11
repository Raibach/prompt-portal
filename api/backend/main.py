from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import sys
import os
import json
import tempfile
import whisper
from datetime import datetime

# Add the parent directory to Python path so we can import the existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grace_api import (
    search_news,
    summarize_pdfs,
    retrieve_memory_context,
    query_llm,
    load_logs_to_vectorstore
)

# Import conversation API
try:
    from backend.conversation_api import ConversationAPI
except ImportError:
    # Fallback for direct import
    from conversation_api import ConversationAPI

# Import projects API
try:
    from backend.projects_api import ProjectsAPI
except ImportError:
    # Fallback for direct import
    from projects_api import ProjectsAPI

# Import memory API
try:
    from grace_memory_api import GraceMemoryAPI
except ImportError:
    from backend.grace_memory_api import GraceMemoryAPI

# Import tag extractor for historical context
try:
    from backend.tag_extractor import TagExtractor
except ImportError:
    from tag_extractor import TagExtractor

app = FastAPI(title="Grace AI API", description="Backend API for Grace AI assistant")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://grace-editor-production.up.railway.app",  # Production
        "http://localhost:5173",  # Local frontend dev
        "http://localhost:5001",  # Local backend dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
conversation_api = None
projects_api = None
memory_api = None
tag_extractor = None

@app.on_event("startup")
async def startup_event():
    load_logs_to_vectorstore()
    
    # Initialize APIs if DATABASE_URL is available
    global conversation_api, projects_api, memory_api, tag_extractor
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            conversation_api = ConversationAPI(database_url)
            print("✅ Conversation API initialized")
        except Exception as e:
            print(f"⚠️  Failed to initialize Conversation API: {e}")
            conversation_api = None
        
        try:
            projects_api = ProjectsAPI(database_url)
            print("✅ Projects API initialized")
        except Exception as e:
            print(f"⚠️  Failed to initialize Projects API: {e}")
            projects_api = None
        
        try:
            memory_api = GraceMemoryAPI(database_url)
            print("✅ Memory API initialized")
        except Exception as e:
            print(f"⚠️  Failed to initialize Memory API: {e}")
            memory_api = None
        
        # Initialize tag extractor (requires query_llm function from grace_gui)
        try:
            # TagExtractor needs query_llm function - we'll pass it when needed
            # For now, just mark it as available
            tag_extractor = None  # Will be initialized on first use with query_llm
            print("✅ Tag extractor ready (will initialize on first use)")
        except Exception as e:
            print(f"⚠️  Failed to initialize Tag Extractor: {e}")
            tag_extractor = None
    else:
        print("⚠️  DATABASE_URL not found - Database APIs disabled")

# Helper function to get user_id (placeholder for now)
def get_user_id_from_header(x_user_id: Optional[str] = None) -> str:
    """Get user ID from header or use default placeholder"""
    # TODO: Integrate with authentication system
    if x_user_id:
        return x_user_id
    # For now, use a default user ID (will be replaced with real auth)
    return os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000000")

# Models for request/response
class NewsQuery(BaseModel):
    query: str
    reasoning: bool = False
    include_memory: bool = True

class MemoryQuery(BaseModel):
    query: str
    reasoning: bool = True

class SourceEvalRequest(BaseModel):
    url: str
    title: Optional[str] = None
    content: Optional[str] = None

# Endpoints
@app.get("/api/health")
async def api_health():
    """Health check endpoint with Milvus status"""
    health_data = {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }
    
    # Check Milvus status
    try:
        from backend.milvus_client import get_milvus_client
        from backend.memory_embedder import get_embedder
        from config.milvus_config import get_all_collections
        
        milvus_client = get_milvus_client()
        embedder = get_embedder()
        
        milvus_status = {
            "available": False,
            "mode": None,
            "collections": {},
            "embedder_available": embedder is not None and embedder.model is not None,
            "total_vectors": 0
        }
        
        if milvus_client and milvus_client.client:
            milvus_status["available"] = True
            milvus_status["mode"] = milvus_client.mode
            
            # Get collection stats
            try:
                collections = get_all_collections()
                total_vectors = 0
                for collection_name in collections:
                    try:
                        stats = milvus_client.get_collection_stats(collection_name)
                        # Extract entity count from stats
                        entity_count = stats.get("row_count", 0) if isinstance(stats, dict) else 0
                        milvus_status["collections"][collection_name] = {
                            "exists": True,
                            "vectors": entity_count
                        }
                        total_vectors += entity_count
                    except Exception as e:
                        milvus_status["collections"][collection_name] = {
                            "exists": False,
                            "error": str(e)
                        }
                
                milvus_status["total_vectors"] = total_vectors
            except Exception as e:
                milvus_status["error"] = str(e)
        
        health_data["milvus"] = milvus_status
        
        # Check database connection for memory stats
        if memory_api:
            try:
                conn = memory_api.get_db()
                cursor = conn.cursor()
                
                # Count total memories
                cursor.execute("SELECT COUNT(*) as total FROM user_memories")
                total_memories = cursor.fetchone()['total']
                
                # Count memories with vector_id
                cursor.execute("SELECT COUNT(*) as total FROM user_memories WHERE vector_id IS NOT NULL")
                memories_with_vectors = cursor.fetchone()['total']
                
                # Calculate percentage
                embedding_coverage = (memories_with_vectors / total_memories * 100) if total_memories > 0 else 0
                
                health_data["memory_stats"] = {
                    "total_memories": total_memories,
                    "memories_with_vectors": memories_with_vectors,
                    "embedding_coverage_percent": round(embedding_coverage, 2)
                }
                
                cursor.close()
                conn.close()
            except Exception as e:
                health_data["memory_stats"] = {"error": str(e)}
        
    except Exception as e:
        health_data["milvus"] = {"error": str(e)}
    
    return health_data

@app.post("/api/news/search")
async def api_search_news(query: NewsQuery):
    memory = retrieve_memory_context(query.query) if query.include_memory else ""
    result = search_news(query.query, query.reasoning, memory)
    return {"result": result}

@app.post("/api/pdf/summarize")
async def api_summarize_pdfs(files: List[UploadFile] = File(...), reasoning: bool = False):
    # Save uploaded files temporarily
    temp_files = []
    for file in files:
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        temp_files.append(temp_path)

    # Process PDFs
    try:
        from types import SimpleNamespace
        wrapped_files = [SimpleNamespace(name=path) for path in temp_files]
    except Exception:
        class _F:  # minimal object with name attr
            def __init__(self, name):
                self.name = name
        wrapped_files = [_F(path) for path in temp_files]
    result = summarize_pdfs(wrapped_files, reasoning)

    # Clean up temp files
    for path in temp_files:
        try:
            os.remove(path)
        except Exception:
            pass

    return {"result": result}

@app.post("/api/memory/recall")
async def api_memory_recall(query: MemoryQuery):
    memory_context = retrieve_memory_context(query.query)
    result = query_llm(
        "",
        query.query,
        query.reasoning,
        "reflexion",
        memory_context
    )
    return {"result": result}

@app.get("/api/reasoning/trace")
async def api_reasoning_trace():
    try:
        if not os.path.exists(REASONING_TRACE_PATH):
            return {"latest": None, "all": []}
        with open(REASONING_TRACE_PATH, "r") as f:
            data = json.load(f)
        latest = data[-1] if data else None
        return {"latest": latest, "all": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/source/evaluate")
async def api_source_evaluate(req: SourceEvalRequest):
    try:
        result = evaluate_source(req.url, req.title or "", req.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TrainPayload(BaseModel):
    data: Any

@app.post("/api/train")
async def api_train(payload: TrainPayload):
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/training_data.jsonl", "a") as f:
            f.write(json.dumps(payload.data) + "\n")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CONVERSATION ENDPOINTS
# ============================================

class CreateConversationRequest(BaseModel):
    project_id: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[dict] = None

class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    message_count: Optional[int] = None

class AddMessageRequest(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

@app.get("/api/conversations")
async def get_conversations(
    projectId: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get all conversations for a user"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        conversations = conversation_api.get_all_conversations(
            uid,
            project_id=projectId,  # Use projectId from query param
            include_archived=include_archived
        )
        return {"conversations": conversations}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error loading conversations: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Conversations API error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error loading conversations: {str(e)}")

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get a specific conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        conversation = conversation_api.get_conversation(conversation_id, uid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error loading conversation: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Get conversation error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error loading conversation: {str(e)}")

@app.post("/api/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Create a new conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        conversation_id = conversation_api.create_conversation(
            uid,
            project_id=request.project_id,
            title=request.title,
            metadata=request.metadata
        )
        return {"id": conversation_id, "success": True}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error creating conversation: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Create conversation error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.put("/api/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Update a conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = conversation_api.update_conversation(
            conversation_id,
            uid,
            title=request.title,
            message_count=request.message_count
        )
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving conversation: {str(e)}")

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Delete a conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = conversation_api.delete_conversation(conversation_id, uid)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@app.post("/api/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    archived: bool = Query(True),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Archive or unarchive a conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = conversation_api.archive_conversation(conversation_id, uid, archived)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error archiving conversation: {str(e)}")

@app.get("/api/conversations/archived")
async def get_archived_conversations(
    projectId: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get archived conversations"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        conversations = conversation_api.get_archived_conversations(uid, projectId)
        return {"conversations": conversations}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading archived conversations: {str(e)}")

@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: Optional[int] = Query(None),
    offset: int = Query(0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get messages for a conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        messages = conversation_api.get_messages(conversation_id, uid, limit, offset)
        return {"messages": messages}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading messages: {str(e)}")

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Add a message to a conversation"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        message_id = conversation_api.add_message(
            conversation_id,
            uid,
            request.role,
            request.content,
            request.metadata
        )
        return {"id": message_id, "success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving message: {str(e)}")

@app.delete("/api/messages/{message_id}")
async def delete_message(
    message_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Delete a message"""
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = conversation_api.delete_message(message_id, uid)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")

class ConfirmTagRequest(BaseModel):
    confirmed_tags: Optional[List[str]] = None
    detected_entities: Dict[str, Any]

@app.post("/api/conversation/confirm-tag")
async def confirm_tag(
    request: ConfirmTagRequest,
    conversation_id: str = Query(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Confirm and store literary tags for a conversation
    
    Input:
    - conversation_id: Conversation UUID
    - confirmed_tags: Optional list of confirmed tag paths
    - detected_entities: ContextDetector entities (characters, work_focus, literary_elements, topics)
    
    Returns confirmation with stored tag paths
    """
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        
        # Get conversation to verify ownership and get content
        conversation = conversation_api.get_conversation(conversation_id, uid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get conversation messages for content
        messages = conversation_api.get_messages(conversation_id, uid, limit=1000)
        conversation_content = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        # Get project_id from conversation metadata
        project_id = conversation.get('project_id') or conversation.get('metadata', {}).get('project_id')
        
        # Get Milvus client and embedder if available
        milvus_client = None
        memory_embedder = None
        try:
            from backend.milvus_client import get_milvus_client
            from backend.memory_embedder import get_embedder
            milvus_client = get_milvus_client()
            if milvus_client:
                milvus_client.connect()
            memory_embedder = get_embedder()
        except Exception as e:
            print(f"⚠️ Milvus/Memory embedder not available: {e}")
        
        # Store tags using store_literary_tags function
        result = conversation_api.store_literary_tags(
            conversation_id=conversation_id,
            user_id=uid,
            detected_entities=request.detected_entities,
            conversation_content=conversation_content,
            project_id=project_id,
            milvus_client=milvus_client,
            memory_embedder=memory_embedder
        )
        
        return {
            "success": True,
            "tag_paths": result['tag_paths'],
            "tag_ids": result['tag_ids'],
            "milvus_inserted": result['milvus_inserted']
        }
        
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error confirming tags: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Confirm tag error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error confirming tags: {str(e)}")

@app.post("/api/conversation/track-tag-suggestion")
async def track_tag_suggestion(
    conversation_id: str = Query(...),
    suggested_tags: List[str] = Query(...),
    confirmed: bool = Query(False),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Track Grace's tag suggestions (for analytics and confirmation tracking)
    
    Input:
    - conversation_id: Conversation UUID
    - suggested_tags: List of suggested tag paths
    - confirmed: Whether user confirmed the suggestion
    
    Returns suggestion tracking ID
    """
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        
        # Get detected entities if available (optional)
        detected_entities = {}  # Can be enhanced to extract from conversation
        
        suggestion_id = conversation_api.track_tag_suggestion(
            conversation_id=conversation_id,
            user_id=uid,
            suggested_tags=suggested_tags,
            detected_entities=detected_entities,
            confirmed=confirmed
        )
        
        return {
            "success": True,
            "suggestion_id": suggestion_id
        }
        
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking tag suggestion: {str(e)}")

@app.get("/api/conversation/tag-suggestion-stats")
async def get_tag_suggestion_stats(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Get tag suggestion statistics for a user
    
    Returns:
    - total_suggestions: Total number of tag suggestions
    - confirmed_suggestions: Number of confirmed suggestions
    - confirmation_rate: Rate of confirmation (0.0 to 1.0)
    """
    if not conversation_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        stats = conversation_api.get_tag_suggestion_stats(uid)
        return stats
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tag suggestion stats: {str(e)}")

# ============================================
# PROJECTS ENDPOINTS
# ============================================

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None

@app.get("/api/projects")
async def get_projects(
    include_archived: bool = Query(False),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get all projects for a user"""
    if not projects_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        projects = projects_api.get_all_projects(
            uid,
            include_archived=include_archived
        )
        return {"projects": projects}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error loading projects: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Projects API error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error loading projects: {str(e)}")

@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get a specific project by ID"""
    if not projects_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        project = projects_api.get_project(project_id, uid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error loading project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Project API error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error loading project: {str(e)}")

@app.post("/api/projects")
async def create_project(
    request: CreateProjectRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Create a new project"""
    if not projects_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        project_id = projects_api.create_project(
            uid,
            name=request.name,
            description=request.description
        )
        return {"id": project_id, "success": True}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error creating project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Create project error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")

@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Update a project"""
    if not projects_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = projects_api.update_project(
            project_id,
            uid,
            name=request.name,
            description=request.description,
            is_archived=request.is_archived
        )
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error updating project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Update project error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error updating project: {str(e)}")

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Delete a project (soft delete by archiving)"""
    if not projects_api:
        raise HTTPException(status_code=503, detail="Database not available. Please check your connection.")
    
    try:
        uid = get_user_id_from_header(x_user_id)
        success = projects_api.delete_project(project_id, uid)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True}
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error deleting project: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Delete project error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")

# ============================================
# WHISPER TRANSCRIPTION ENDPOINT
# ============================================

# Initialize Whisper model (lazy load on first request)
_whisper_model = None

def get_whisper_model():
    """Lazy load Whisper model on first use"""
    global _whisper_model
    if _whisper_model is None:
        try:
            print("Loading Whisper model (base)...")
            _whisper_model = whisper.load_model("base")
            print("✅ Whisper model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load Whisper model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load Whisper model: {str(e)}")
    return _whisper_model

@app.post("/api/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe audio file using local Whisper model.
    Accepts WAV, MP3, WebM, and other audio formats supported by Whisper.
    """
    if not audio_file:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    # Validate file type
    content_type = audio_file.content_type or ""
    if not any(ext in content_type.lower() for ext in ["audio", "video", "webm", "wav", "mp3", "mpeg", "ogg"]):
        # Still allow the file - Whisper can handle many formats
        print(f"⚠️  Unusual content type: {content_type}, proceeding anyway")
    
    temp_file_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename or "audio")[1]) as temp_file:
            temp_file_path = temp_file.name
            content = await audio_file.read()
            temp_file.write(content)
        
        print(f"📁 Saved audio file to: {temp_file_path} ({len(content)} bytes)")
        
        # Load Whisper model (lazy initialization)
        model = get_whisper_model()
        
        # Transcribe audio
        print("🎤 Transcribing audio...")
        result = model.transcribe(temp_file_path, language="en")
        
        transcription = result.get("text", "").strip()
        
        if not transcription:
            print("⚠️  Whisper returned empty transcription")
            return {"text": "", "error": "No speech detected in audio file"}
        
        print(f"✅ Transcription complete: {len(transcription)} characters")
        return {"text": transcription}
        
    except Exception as e:
        import traceback
        error_detail = f"Error transcribing audio: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Transcription error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"🗑️  Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete temporary file: {e}")

# ============================================
# MEMORY STORAGE ENDPOINTS
# ============================================

class StoreDictationRequest(BaseModel):
    user_id: str
    content: str
    project_id: Optional[str] = None
    title: Optional[str] = None
    memory_id: Optional[str] = None  # If provided, update existing memory instead of creating new

@app.post("/api/memory/store-dictation")
async def store_dictation_memory(
    request: StoreDictationRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Store dictation content in memory system with historical context tags.
    Content is embedded and stored in Milvus for semantic search.
    """
    if not memory_api:
        raise HTTPException(status_code=503, detail="Memory API not available. Please check your database connection.")
    
    try:
        user_id = get_user_id_from_header(x_user_id) or request.user_id
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        if not request.content or not request.content.strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty")
        
        print(f"📝 Storing dictation content: {len(request.content)} characters")
        
        # Extract historical context tags using TagExtractor
        historical_tags = {
            'periods': [],
            'movements': [],
            'events': []
        }
        
        try:
            # Initialize tag extractor with query_llm function
            global tag_extractor
            if tag_extractor is None:
                # Import query_llm from grace_gui (already imported at top)
                from grace_gui import query_llm
                tag_extractor = TagExtractor(query_llm)
            
            # Extract historical context
            historical_tags = tag_extractor.extract_historical_context_tags(request.content)
            print(f"🏛️  Extracted historical context: {historical_tags}")
        except Exception as tag_error:
            print(f"⚠️  Failed to extract historical tags (non-blocking): {tag_error}")
            # Continue without tags - don't fail the storage
        
        # Prepare source metadata with historical context
        # Note: Both 'historical_context' dict and direct fields for compatibility
        source_metadata = {
            'project_id': request.project_id,
            'source': 'editor_content',  # Changed from 'dictation' to be more general
            'input_method': 'editor',  # Can be dictation, paste, or typing
            'historical_context': historical_tags,  # Nested structure
            'periods': historical_tags.get('periods', []),  # Direct fields for easy access
            'movements': historical_tags.get('movements', []),
            'events': historical_tags.get('events', []),
            'stored_at': datetime.now().isoformat()
        }
        
        # Store or update in memory system
        if request.memory_id:
            # Update existing memory
            print(f"📝 Updating existing memory: {request.memory_id}")
            memory_id = memory_api.update_memory(
                memory_id=request.memory_id,
                user_id=user_id,
                content=request.content,
                title=request.title or f"Dictation - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                source_metadata=source_metadata,
                generate_embedding=True  # Regenerate embeddings for updated content
            )
            print(f"✅ Memory updated: {memory_id}")
        else:
            # Determine if embedding should be generated based on rules
            try:
                from config.embedding_rules import should_embed_automatically
                generate_embedding = should_embed_automatically(
                    content_type='text',
                    source_type='dictation',
                    metadata=source_metadata,
                    content_length=len(request.content),
                    project_id=request.project_id,
                    quarantine_status='safe'
                )
            except Exception as rule_error:
                # If rules fail, default to True for dictation (user-initiated save)
                print(f"⚠️  Failed to check embedding rules: {rule_error}")
                generate_embedding = True  # User explicitly saved - embed by default
            
            # Create new memory
            memory_id = memory_api.create_memory(
                user_id=user_id,
                content=request.content,
                content_type='text',
                source_type='dictation',
                title=request.title or f"Dictation - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                source_metadata=source_metadata,
                quarantine_score=0.9,  # Dictation is generally safe
                quarantine_status='safe',
                generate_embedding=generate_embedding  # Use embedding rules to determine
            )
            print(f"✅ Dictation stored in memory: {memory_id}")
        
        return {
            "memory_id": memory_id,
            "success": True,
            "historical_context": historical_tags
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error storing dictation memory: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Store dictation error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error storing dictation memory: {str(e)}")

class UpdateMemoryRequest(BaseModel):
    title: Optional[str] = None
    project_id: Optional[str] = None
    pattern_summary: Optional[str] = None

@app.put("/api/memory/{memory_id}")
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Update a memory's title, project, or summary.
    """
    if not memory_api:
        raise HTTPException(status_code=503, detail="Memory API not available. Please check your database connection.")
    
    try:
        user_id = get_user_id_from_header(x_user_id) or 'default-user'
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Get existing memory to update
        conn = memory_api.get_db()
        cursor = conn.cursor()
        memory_api.set_user_context(cursor, user_id)
        
        # Check if memory exists and belongs to user
        cursor.execute("""
            SELECT id, source_metadata FROM user_memories
            WHERE id = %s AND user_id = %s
        """, (memory_id, user_id))
        
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Update source_metadata with new project_id if provided
        source_metadata = existing.get('source_metadata') or {}
        if isinstance(source_metadata, str):
            import json
            source_metadata = json.loads(source_metadata)
        
        if request.project_id:
            source_metadata['project_id'] = request.project_id
        
        # Update memory
        update_fields = []
        update_values = []
        
        if request.title is not None:
            update_fields.append("title = %s")
            update_values.append(request.title)
        
        if request.project_id is not None:
            update_fields.append("project_id = %s")
            update_values.append(request.project_id)
        
        if request.pattern_summary is not None:
            # Store pattern_summary in source_metadata
            source_metadata['pattern_summary'] = request.pattern_summary
        
        if source_metadata:
            update_fields.append("source_metadata = %s")
            update_values.append(json.dumps(source_metadata))
        
        update_fields.append("updated_at = NOW()")
        
        if not update_fields:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_values.extend([memory_id, user_id])
        
        cursor.execute(f"""
            UPDATE user_memories
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
            RETURNING id
        """, update_values)
        
        updated = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not updated:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        print(f"✅ Memory updated: {memory_id}")
        return {
            "memory_id": memory_id,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error updating memory: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Update memory error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error updating memory: {str(e)}")

@app.delete("/api/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Delete a memory.
    """
    if not memory_api:
        raise HTTPException(status_code=503, detail="Memory API not available. Please check your database connection.")
    
    conn = None
    cursor = None
    try:
        user_id = get_user_id_from_header(x_user_id) or 'default-user'
        
        print(f"🗑️ [DELETE MEMORY] Attempting to delete memory_id={memory_id}, user_id={user_id}")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Validate memory_id format (should be UUID)
        try:
            import uuid
            uuid.UUID(memory_id)  # Validate UUID format
        except ValueError as ve:
            print(f"❌ [DELETE MEMORY] Invalid UUID format: {memory_id}, error: {ve}")
            raise HTTPException(status_code=400, detail=f"Invalid memory ID format: {memory_id}")
        
        # Delete memory
        print(f"🗑️ [DELETE MEMORY] Getting database connection...")
        conn = memory_api.get_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Failed to get database connection")
        
        cursor = None
        try:
            # Use RealDictCursor to match memory_api pattern (it uses dict access like cursor.fetchone()['id'])
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            memory_api.set_user_context(cursor, user_id)
            print(f"🗑️ [DELETE MEMORY] Database connection established, checking if memory exists...")
            
            # First check if memory exists and belongs to user
            cursor.execute("""
                SELECT id FROM user_memories
                WHERE id = %s AND user_id = %s
            """, (memory_id, user_id))
            
            existing = cursor.fetchone()
            if not existing:
                print(f"❌ [DELETE MEMORY] Memory not found: memory_id={memory_id}, user_id={user_id}")
                cursor.close()
                conn.close()
                raise HTTPException(status_code=404, detail="Memory not found")
            
            print(f"✅ [DELETE MEMORY] Memory found, proceeding with deletion...")
            
            # Delete memory from database
            # Note: Foreign key constraints with ON DELETE CASCADE will handle related records
            cursor.execute("""
                DELETE FROM user_memories
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (memory_id, user_id))
            
            deleted = cursor.fetchone()
            cursor.close()  # Close cursor before commit
            
            if not deleted:
                print(f"❌ [DELETE MEMORY] Deletion returned no rows: memory_id={memory_id}, user_id={user_id}")
                conn.rollback()
                conn.close()
                raise HTTPException(status_code=404, detail="Memory not found or already deleted")
            
            # Commit the deletion
            print(f"✅ [DELETE MEMORY] Deletion successful, committing transaction...")
            conn.commit()
            print(f"✅ [DELETE MEMORY] Transaction committed successfully")
            
        except HTTPException:
            # Re-raise HTTP exceptions (they're already properly formatted)
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
                try:
                    conn.close()
                except:
                    pass
            raise
        except Exception as db_error:
            # Catch any database errors
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            import traceback
            error_trace = traceback.format_exc()
            error_msg = str(db_error)
            print(f"❌ [DELETE MEMORY] Database error: {error_msg}")
            print(f"❌ [DELETE MEMORY] Traceback: {error_trace}")
            # Return more specific error message to help debug
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to delete memory: {error_msg}. Check backend logs for details."
            )
        finally:
            # Ensure cursor is closed
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            # Connection will be returned to pool by close()
            if conn:
                try:
                    conn.close()
                except:
                    pass
        
        # Try to delete embeddings from Milvus (non-blocking)
        # This happens AFTER database deletion is committed, so it won't affect the main operation
        try:
            from backend.milvus_client import get_milvus_client
            
            milvus_client = get_milvus_client()
            if milvus_client and hasattr(milvus_client, 'client') and milvus_client.client:
                # Delete from all possible collections using memory_id filter
                collections = ['grace_memory_character', 'grace_memory_plot', 'grace_memory_general']
                for collection_name in collections:
                    try:
                        # Use the wrapper method which handles errors better
                        milvus_client.delete_by_filter(
                            collection_name=collection_name,
                            filter_expr=f'memory_id == "{memory_id}"'
                        )
                        print(f"✅ Deleted embeddings from Milvus collection {collection_name} for memory {memory_id}")
                    except Exception as milvus_error:
                        # Non-blocking - log but don't fail
                        print(f"⚠️ Failed to delete from Milvus collection {collection_name}: {milvus_error}")
        except Exception as milvus_error:
            # Non-blocking - log but don't fail the deletion
            print(f"⚠️ Milvus cleanup failed (non-blocking): {milvus_error}")
        
        print(f"✅ Memory deleted: {memory_id}")
        return {
            "memory_id": memory_id,
            "success": True
        }
        
    except HTTPException:
        # HTTP exceptions are already properly formatted - re-raise them
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error deleting memory: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ [DELETE MEMORY] Unexpected error: {error_detail}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error deleting memory: {str(e)}")
    finally:
        # Connection will be returned to pool automatically when close() is called
        # Only close if it wasn't already closed in the inner finally block
        if conn:
            try:
                # Check if connection is still open before closing
                if not conn.closed:
                    conn.close()
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
