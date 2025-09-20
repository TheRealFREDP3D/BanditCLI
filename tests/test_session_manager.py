"""Unit tests for the session manager module."""
import pytest
import os
import json
from pathlib import Path
from datetime import datetime
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from session_manager import SessionManager, SessionInfo


class TestSessionManager:
    """Test cases for the SessionManager class."""
    
    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default values."""
        session_manager = SessionManager()
        
        # Check that sessions file directory was created
        assert session_manager.sessions_file.parent.exists()
        assert ".bandit_cli" in str(session_manager.sessions_file.parent)
        assert session_manager.sessions == {}
        assert session_manager.current_session_id is None
    
    def test_init_with_custom_file(self, tmp_path):
        """Test initialization with custom sessions file."""
        sessions_file = tmp_path / "custom_sessions.json"
        session_manager = SessionManager(sessions_file=str(sessions_file))
        
        assert session_manager.sessions_file == sessions_file
        assert session_manager.sessions == {}
    
    def test_create_session(self, tmp_path):
        """Test creating a new session."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_info = session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Check that session was created
        assert session_info.id == "test_session"
        assert session_info.name == "Test Session"
        assert session_info.hostname == "test.host"
        assert session_info.port == 2220
        assert session_info.username == "testuser"
        assert session_info.level == 0
        assert session_info.created_at is not None
        assert session_info.last_used is not None
        
        # Check that session is in the manager
        assert "test_session" in session_manager.sessions
        assert session_manager.sessions["test_session"] == session_info
    
    def test_get_session(self, tmp_path):
        """Test getting a session."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Get the session
        session_info = session_manager.get_session("test_session")
        assert session_info is not None
        assert session_info.id == "test_session"
        
        # Try to get a nonexistent session
        nonexistent = session_manager.get_session("nonexistent")
        assert nonexistent is None
    
    def test_get_all_sessions(self, tmp_path):
        """Test getting all sessions."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create some sessions
        session_manager.create_session("session1", "Session 1", "host1", 2220, "user1", 0)
        session_manager.create_session("session2", "Session 2", "host2", 2221, "user2", 1)
        
        # Get all sessions
        sessions = session_manager.get_all_sessions()
        assert len(sessions) == 2
        session_ids = [session.id for session in sessions]
        assert "session1" in session_ids
        assert "session2" in session_ids
    
    def test_update_session(self, tmp_path):
        """Test updating a session."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Get initial last_used time
        initial_last_used = session_manager.sessions["test_session"].last_used
        
        # Update the session
        session_manager.update_session("test_session", level=5, username="newuser")
        
        # Check that session was updated
        session_info = session_manager.get_session("test_session")
        assert session_info.level == 5
        assert session_info.username == "newuser"
        # Check that last_used was updated
        assert session_info.last_used != initial_last_used
    
    def test_delete_session(self, tmp_path):
        """Test deleting a session."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Delete the session
        session_manager.delete_session("test_session")
        
        # Check that session was deleted
        assert "test_session" not in session_manager.sessions
        assert session_manager.get_session("test_session") is None
    
    def test_set_current_session(self, tmp_path):
        """Test setting the current session."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Set current session
        session_manager.set_current_session("test_session")
        
        # Check that current session is set
        assert session_manager.current_session_id == "test_session"
        current_session = session_manager.get_current_session()
        assert current_session is not None
        assert current_session.id == "test_session"
    
    def test_get_current_session_none(self, tmp_path):
        """Test getting current session when none is set."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Check that current session is None
        assert session_manager.get_current_session() is None
    
    def test_session_exists(self, tmp_path):
        """Test checking if a session exists."""
        session_manager = SessionManager(sessions_file=str(tmp_path / "sessions.json"))
        
        # Create a session
        session_manager.create_session(
            "test_session",
            "Test Session",
            "test.host",
            2220,
            "testuser",
            0
        )
        
        # Check that session exists
        assert session_manager.session_exists("test_session") is True
        assert session_manager.session_exists("nonexistent") is False
    
    def test_save_and_load_sessions(self, tmp_path):
        """Test saving and loading sessions from file."""
        sessions_file = tmp_path / "sessions.json"
        
        # Create first session manager and add sessions
        session_manager1 = SessionManager(sessions_file=str(sessions_file))
        session_manager1.create_session("session1", "Session 1", "host1", 2220, "user1", 0)
        session_manager1.create_session("session2", "Session 2", "host2", 2221, "user2", 1)
        
        # Create second session manager to load sessions
        session_manager2 = SessionManager(sessions_file=str(sessions_file))
        
        # Check that sessions were loaded
        assert len(session_manager2.sessions) == 2
        assert "session1" in session_manager2.sessions
        assert "session2" in session_manager2.sessions
        
        session1 = session_manager2.get_session("session1")
        assert session1.name == "Session 1"
        assert session1.hostname == "host1"
        assert session1.port == 2220
        assert session1.username == "user1"
        assert session1.level == 0
        
        session2 = session_manager2.get_session("session2")
        assert session2.name == "Session 2"
        assert session2.hostname == "host2"
        assert session2.port == 2221
        assert session2.username == "user2"
        assert session2.level == 1