"""
FastAPI Backend for PartSelect Chatbot
Phase 6: REST API with session management
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from .models import (
    ChatRequest, 
    ChatResponse, 
    SessionResponse, 
    HealthResponse, 
    ErrorResponse
)
from .session_manager import SessionManager
from .agents import PlannerAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
session_manager = SessionManager(session_timeout_minutes=30)
planner_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global planner_agent
    
    # Startup
    logger.info("Starting PartSelect Chatbot API...")
    try:
        planner_agent = PlannerAgent(enable_validation=True)
        logger.info("✓ PlannerAgent initialized")
        
        # Test database connections
        from .tools import SQLTool, VectorTool
        sql_tool = SQLTool()
        vector_tool = VectorTool()
        
        # Quick health check
        sql_tool.get_part_by_id("PS11752778")  # Test query
        vector_tool.get_collection_info()  # Test Qdrant
        
        logger.info("✓ Database connections verified")
        logger.info("API ready to accept requests")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    session_manager.cleanup_expired_sessions()


# Create FastAPI app
app = FastAPI(
    title="PartSelect Chatbot API",
    description="Intelligent chatbot for dishwasher and refrigerator replacement parts",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=str(exc.detail),
            detail=None
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            detail=str(exc) if os.getenv("DEBUG") else None
        ).model_dump()
    )


# API Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": "PartSelect Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        from .tools import SQLTool, VectorTool
        
        # Test database connections
        sql_healthy = False
        vector_healthy = False
        
        try:
            sql_tool = SQLTool()
            sql_tool.get_part_by_id("PS11752778")
            sql_healthy = True
        except Exception as e:
            logger.warning(f"SQL health check failed: {e}")
        
        try:
            vector_tool = VectorTool()
            vector_tool.get_collection_info()
            vector_healthy = True
        except Exception as e:
            logger.warning(f"Vector DB health check failed: {e}")
        
        return HealthResponse(
            status="healthy" if (sql_healthy and vector_healthy) else "degraded",
            version="1.0.0",
            database={
                "postgresql": sql_healthy,
                "qdrant": vector_healthy
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )


@app.post("/api/session/new", response_model=SessionResponse)
async def create_session():
    """Create a new conversation session"""
    try:
        session_id = session_manager.create_session()
        logger.info(f"Created new session: {session_id}")
        return SessionResponse(session_id=session_id)
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint
    
    - **message**: User's query/message
    - **session_id**: Optional session ID for conversation context
    - **enable_validation**: Enable/disable validation layer (default: True)
    - **validation_threshold**: Score threshold for validation (default: 70)
    """
    try:
        # Validate session or create new one
        session_id = request.session_id
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Invalid/expired session: {session_id}, creating new one")
                session_id = session_manager.create_session()
        else:
            session_id = session_manager.create_session()
            logger.info(f"Created new session: {session_id}")
        
        # Get conversation history
        history = session_manager.get_history(session_id)
        
        # Convert history to format expected by agent
        conversation_history = []
        if history:
            from google.genai import types
            for msg in history:
                # Add user message
                conversation_history.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg["user"])]
                ))
                # Add agent response
                conversation_history.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg["agent"])]
                ))
        
        # Call agent (validation is handled internally)
        logger.info(f"Processing message for session {session_id}: {request.message[:50]}...")
        
        result = planner_agent.chat(
            user_message=request.message,
            conversation_history=conversation_history if conversation_history else None,
            validation_threshold=request.validation_threshold,
            max_retries=2  # Enable validation with 2 retry attempts
        )
        
        # Update session
        session_manager.update_session(
            session_id=session_id,
            user_message=request.message,
            agent_response=result["response"]
        )
        
        logger.info(f"Response generated for session {session_id}")
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            validation_score=result.get("validation_score"),
            function_calls=result.get("function_calls")
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session"""
    try:
        session_manager.delete_session(session_id)
        logger.info(f"Deleted session: {session_id}")
        return {"message": "Session deleted", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session"""
    try:
        history = session_manager.get_history(session_id)
        if history is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired"
            )
        return {"session_id": session_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history"
        )


# Development server runner
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
