"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message/query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    enable_validation: bool = Field(True, description="Enable validation layer")
    validation_threshold: int = Field(70, ge=0, le=100, description="Validation score threshold (0-100)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID for this conversation")
    validation_score: Optional[int] = Field(None, description="Validation score if validation is enabled")
    function_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Function calls made by agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str = Field(..., description="New session ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
    database: Dict[str, bool] = Field(..., description="Database connection status")


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
