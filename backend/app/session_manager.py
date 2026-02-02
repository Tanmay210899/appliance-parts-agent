"""
In-memory session manager for conversation history
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class SessionManager:
    """Manages conversation sessions in memory"""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "history": []
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data if it exists and hasn't expired"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session has expired
        if datetime.utcnow() - session["last_activity"] > self.session_timeout:
            self.delete_session(session_id)
            return None
        
        return session
    
    def update_session(self, session_id: str, user_message: str, agent_response: str):
        """Add message exchange to session history"""
        session = self.get_session(session_id)
        if session:
            session["history"].append({
                "timestamp": datetime.utcnow(),
                "user": user_message,
                "agent": agent_response
            })
            session["last_activity"] = datetime.utcnow()
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired = [
            sid for sid, session in self.sessions.items()
            if datetime.utcnow() - session["last_activity"] > self.session_timeout
        ]
        for sid in expired:
            self.delete_session(sid)
    
    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        session = self.get_session(session_id)
        return session["history"] if session else []
