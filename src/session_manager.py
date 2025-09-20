"""Session management for the Bandit CLI application."""
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SessionInfo:
    """Information about a session."""
    id: str
    name: str
    created_at: str
    last_used: str
    hostname: str
    port: int
    username: str
    level: int = 0


class SessionManager:
    """Manages application sessions."""
    
    def __init__(self, sessions_file: str = None):
        """
        Initialize session manager.
        
        Args:
            sessions_file: Path to file for persistent session storage.
        """
        if sessions_file is None:
            # Default sessions file location
            sessions_dir = Path.home() / ".bandit_cli"
            sessions_dir.mkdir(exist_ok=True)
            self.sessions_file = sessions_dir / "sessions.json"
        else:
            self.sessions_file = Path(sessions_file)
            
        # Load sessions
        self.sessions: Dict[str, SessionInfo] = self._load_sessions()
        self.current_session_id: Optional[str] = None
    
    def _load_sessions(self) -> Dict[str, SessionInfo]:
        """Load sessions from file."""
        if not self.sessions_file.exists():
            return {}
        
        try:
            with open(self.sessions_file, 'r') as f:
                sessions_data = json.load(f)
            
            sessions = {}
            for session_id, session_info in sessions_data.items():
                sessions[session_id] = SessionInfo(**session_info)
            
            return sessions
        except Exception as e:
            print(f"Warning: Could not load sessions file: {e}")
            return {}
    
    def _save_sessions(self):
        """Save sessions to file."""
        try:
            # Convert SessionInfo objects to dictionaries
            sessions_data = {
                session_id: asdict(session_info) 
                for session_id, session_info in self.sessions.items()
            }
            
            # Create directory if it doesn't exist
            self.sessions_file.parent.mkdir(exist_ok=True)
            
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sessions file: {e}")
    
    def create_session(self, session_id: str, name: str, hostname: str, port: int, 
                      username: str, level: int = 0) -> SessionInfo:
        """
        Create a new session.
        
        Args:
            session_id: Unique identifier for the session
            name: Human-readable name for the session
            hostname: SSH hostname
            port: SSH port
            username: SSH username
            level: Current level in the game
            
        Returns:
            SessionInfo object for the new session
        """
        now = datetime.now().isoformat()
        session_info = SessionInfo(
            id=session_id,
            name=name,
            created_at=now,
            last_used=now,
            hostname=hostname,
            port=port,
            username=username,
            level=level
        )
        
        self.sessions[session_id] = session_info
        self._save_sessions()
        return session_info
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo object or None if not found
        """
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[SessionInfo]:
        """
        Get all sessions.
        
        Returns:
            List of all SessionInfo objects
        """
        return list(self.sessions.values())
    
    def update_session(self, session_id: str, **kwargs):
        """
        Update session information.
        
        Args:
            session_id: Session identifier
            **kwargs: Fields to update
        """
        if session_id not in self.sessions:
            return
        
        session_info = self.sessions[session_id]
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(session_info, key):
                setattr(session_info, key, value)
        
        # Update last_used timestamp
        session_info.last_used = datetime.now().isoformat()
        
        self._save_sessions()
    
    def delete_session(self, session_id: str):
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
    
    def set_current_session(self, session_id: str):
        """
        Set the current session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            self.current_session_id = session_id
            # Update last_used timestamp
            self.update_session(session_id, last_used=datetime.now().isoformat())
    
    def get_current_session(self) -> Optional[SessionInfo]:
        """
        Get the current session.
        
        Returns:
            Current SessionInfo object or None if no current session
        """
        if self.current_session_id:
            return self.get_session(self.current_session_id)
        return None
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self.sessions