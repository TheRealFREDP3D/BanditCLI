"""Session management module for BanditCLI.

This module provides persistent session management with the ability to save,
load, and switch between different SSH sessions. Sessions are stored in
~/.bandit_cli/sessions and include connection details, current level, and
metadata.

Features:
- Persistent session storage to disk
- Multiple session support
- Session switching functionality
- Level tracking and progress
- Session metadata and timestamps
- Thread-safe operations
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from threading import Lock


class Session:
    """Represents a single SSH session with connection details and metadata.
    
    Stores session information including SSH connection parameters, current
    Bandit level, timestamps, and usage statistics.
    
    Attributes:
        session_id (str): Unique identifier for the session.
        name (str): Human-readable name for the session.
        hostname (str): SSH server hostname.
        port (int): SSH server port.
        username (str): SSH username.
        current_level (int): Current Bandit level being attempted.
        created_at (datetime): When the session was created.
        last_used (datetime): When the session was last used.
        connection_count (int): Number of times this session was connected.
        is_active (bool): Whether this session is currently active.
        metadata (Dict[str, Any]): Additional session metadata.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        hostname: str = "",
        port: int = 2220,
        username: str = "",
        current_level: int = 0
    ) -> None:
        """Initialize a new session.
        
        Args:
            session_id: Unique session identifier (generated if not provided).
            name: Human-readable session name.
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
            current_level: Current Bandit level.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.name = name or f"Session {self.session_id[:8]}"
        self.hostname = hostname
        self.port = port
        self.username = username
        self.current_level = current_level
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.connection_count = 0
        self.is_active = False
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization.
        
        Returns:
            Dictionary representation of the session.
        """
        return {
            'session_id': self.session_id,
            'name': self.name,
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'current_level': self.current_level,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'connection_count': self.connection_count,
            'is_active': self.is_active,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary.
        
        Args:
            data: Dictionary containing session data.
            
        Returns:
            Session instance.
        """
        session = cls(
            session_id=data.get('session_id'),
            name=data.get('name'),
            hostname=data.get('hostname', ''),
            port=data.get('port', 2220),
            username=data.get('username', ''),
            current_level=data.get('current_level', 0)
        )
        
        session.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        session.last_used = datetime.fromisoformat(data.get('last_used', datetime.now().isoformat()))
        session.connection_count = data.get('connection_count', 0)
        session.is_active = data.get('is_active', False)
        session.metadata = data.get('metadata', {})
        
        return session
    
    def update_usage(self) -> None:
        """Update session usage statistics.
        
        Updates the last used timestamp and increments connection count.
        """
        self.last_used = datetime.now()
        self.connection_count += 1
    
    def set_active(self, active: bool) -> None:
        """Set session active status.
        
        Args:
            active: Whether the session should be marked as active.
        """
        self.is_active = active
        if active:
            self.update_usage()
    
    def update_level(self, level: int) -> None:
        """Update the current Bandit level.
        
        Args:
            level: The new current level.
        """
        self.current_level = level
        self.last_used = datetime.now()
    
    def update_connection_details(self, hostname: str, port: int, username: str) -> None:
        """Update SSH connection details.
        
        Args:
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.last_used = datetime.now()
    
    def get_display_name(self) -> str:
        """Get a display name for the session.
        
        Returns:
            Human-readable display name including username and hostname.
        """
        if self.hostname and self.username:
            return f"{self.username}@{self.hostname}:{self.port}"
        return self.name
    
    def get_summary(self) -> str:
        """Get a summary of the session.
        
        Returns:
            Summary string with key session information.
        """
        return (
            f"{self.get_display_name()} | "
            f"Level {self.current_level} | "
            f"Last used: {self.last_used.strftime('%Y-%m-%d %H:%M')}"
        )


class SessionManager:
    """Manages multiple SSH sessions with persistent storage.
    
    Provides session creation, loading, saving, switching, and management
    functionality with disk persistence and thread safety.
    
    Attributes:
        sessions_file (Path): Path to the sessions storage file.
        sessions (Dict[str, Session]): In-memory session cache.
        active_session_id (Optional[str]): ID of the currently active session.
        lock (Lock): Thread safety lock for session operations.
    """
    
    def __init__(self) -> None:
        """Initialize the session manager.
        
        Sets up storage paths and loads existing sessions from disk.
        """
        self.lock = Lock()
        
        # Create ~/.bandit_cli directory if it doesn't exist
        self.bandit_dir = Path.home() / ".bandit_cli"
        self.bandit_dir.mkdir(exist_ok=True)
        
        # Set sessions file path
        self.sessions_file = self.bandit_dir / "sessions"
        
        # Initialize sessions storage
        self.sessions: Dict[str, Session] = {}
        self.active_session_id: Optional[str] = None
        
        # Load existing sessions
        self._load_sessions()
    
    def _load_sessions(self) -> None:
        """Load sessions from disk file.
        
        Reads the sessions file and populates the in-memory session cache.
        Handles file corruption and missing files gracefully.
        """
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Load sessions
                    sessions_data = data.get('sessions', {})
                    for session_id, session_data in sessions_data.items():
                        try:
                            session = Session.from_dict(session_data)
                            self.sessions[session_id] = session
                            
                            # Restore active session if marked
                            if session.is_active and self.active_session_id is None:
                                self.active_session_id = session_id
                        except (ValueError, KeyError):
                            # Skip corrupted session entries
                            continue
            else:
                self.sessions = {}
        except (json.JSONDecodeError, OSError):
            # If file is corrupted or unreadable, start with empty sessions
            self.sessions = {}
            # Try to backup the corrupted file
            if self.sessions_file.exists():
                backup_file = self.sessions_file.with_suffix('.backup')
                try:
                    self.sessions_file.rename(backup_file)
                except OSError:
                    pass  # If backup fails, just continue
    
    def _save_sessions(self) -> None:
        """Save sessions to disk file.
        
        Persists the current in-memory sessions to disk with proper error handling.
        Creates atomic writes to prevent data corruption.
        """
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.sessions_file.with_suffix('.tmp')
            data = {
                'sessions': {
                    session_id: session.to_dict()
                    for session_id, session in self.sessions.items()
                },
                'active_session_id': self.active_session_id,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.sessions_file)
            
        except OSError:
            # If save fails, continue without saving to avoid breaking functionality
            pass
    
    def create_session(
        self,
        name: Optional[str] = None,
        hostname: str = "",
        port: int = 2220,
        username: str = "",
        current_level: int = 0
    ) -> str:
        """Create a new session.
        
        Creates a new session with the provided parameters and saves it to disk.
        
        Args:
            name: Human-readable session name.
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
            current_level: Current Bandit level.
            
        Returns:
            The ID of the newly created session.
        """
        with self.lock:
            session = Session(
                name=name,
                hostname=hostname,
                port=port,
                username=username,
                current_level=current_level
            )
            
            self.sessions[session.session_id] = session
            self._save_sessions()
            
            return session.session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.
        
        Args:
            session_id: The session ID to retrieve.
            
        Returns:
            The session if found, None otherwise.
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def get_active_session(self) -> Optional[Session]:
        """Get the currently active session.
        
        Returns:
            The active session if one exists, None otherwise.
        """
        if self.active_session_id:
            return self.get_session(self.active_session_id)
        return None
    
    def set_active_session(self, session_id: str) -> bool:
        """Set the active session.
        
        Deactivates the current active session and activates the specified one.
        
        Args:
            session_id: The session ID to activate.
            
        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            # Deactivate current session
            if self.active_session_id and self.active_session_id in self.sessions:
                self.sessions[self.active_session_id].set_active(False)
            
            # Activate new session
            self.sessions[session_id].set_active(True)
            self.active_session_id = session_id
            
            self._save_sessions()
            return True
    
    def update_session_level(self, session_id: str, level: int) -> bool:
        """Update the current level for a session.
        
        Args:
            session_id: The session ID to update.
            level: The new current level.
            
        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            self.sessions[session_id].update_level(level)
            self._save_sessions()
            return True
    
    def update_session_connection(
        self,
        session_id: str,
        hostname: str,
        port: int,
        username: str
    ) -> bool:
        """Update connection details for a session.
        
        Args:
            session_id: The session ID to update.
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
            
        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            self.sessions[session_id].update_connection_details(hostname, port, username)
            self._save_sessions()
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Removes a session from storage. Cannot delete the active session.
        
        Args:
            session_id: The session ID to delete.
            
        Returns:
            True if successful, False if session not found or is active.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            # Cannot delete the active session
            if session_id == self.active_session_id:
                return False
            
            del self.sessions[session_id]
            self._save_sessions()
            return True
    
    def list_sessions(self) -> List[Session]:
        """Get all sessions.
        
        Returns:
            List of all sessions, sorted by last used time.
        """
        with self.lock:
            return sorted(
                self.sessions.values(),
                key=lambda s: s.last_used,
                reverse=True
            )
    
    def get_session_names(self) -> List[str]:
        """Get all session names.
        
        Returns:
            List of session display names.
        """
        with self.lock:
            return [session.get_display_name() for session in self.sessions.values()]
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Remove old inactive sessions.
        
        Removes sessions that haven't been used in the specified number of days.
        The active session is never removed.
        
        Args:
            max_age_days: Maximum age in days for inactive sessions.
            
        Returns:
            Number of sessions removed.
        """
        with self.lock:
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            to_remove = []
            
            for session_id, session in self.sessions.items():
                # Don't remove active sessions or recently used sessions
                if (session_id != self.active_session_id and
                    session.last_used.timestamp() < cutoff_time):
                    to_remove.append(session_id)
            
            # Remove old sessions
            for session_id in to_remove:
                del self.sessions[session_id]
            
            if to_remove:
                self._save_sessions()
            
            return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Dictionary containing session statistics.
        """
        with self.lock:
            total_sessions = len(self.sessions)
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active)
            total_connections = sum(s.connection_count for s in self.sessions.values())
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'total_connections': total_connections,
                'file_size': self.sessions_file.stat().st_size if self.sessions_file.exists() else 0,
                'last_updated': datetime.fromtimestamp(
                    self.sessions_file.stat().st_mtime
                ).isoformat() if self.sessions_file.exists() else None
            }
    
    def export_sessions(self, file_path: str) -> bool:
        """Export sessions to a file.
        
        Args:
            file_path: Path to export file.
            
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            with self.lock:
                data = {
                    'export_date': datetime.now().isoformat(),
                    'total_sessions': len(self.sessions),
                    'active_session_id': self.active_session_id,
                    'sessions': {
                        session_id: session.to_dict()
                        for session_id, session in self.sessions.items()
                    }
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            return True
        except OSError:
            return False
