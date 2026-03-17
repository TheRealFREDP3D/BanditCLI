"""Session management module for BanditCLI.

This module provides persistent session management with the ability to save,
load, and switch between different SSH sessions.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional


class Session:
    """Represents a single SSH session with connection details and metadata.

    Attributes:
        session_id (str): Unique identifier for the session.
        name (str): Human-readable name for the session.
        hostname (str): SSH server hostname.
        port (int): SSH server port.
        username (str): SSH username.
        current_level (int): Current Bandit level being attempted.
        created_at (datetime): When the session was created.
        last_used (datetime): When the session was last used.
        last_saved_at (datetime): When the session was last saved.
        connection_count (int): Number of times this session was connected.
        is_active (bool): Whether this session is currently active.
        metadata (Dict[str, Any]): Additional session metadata.
        terminal_output_history (list[str]): History of terminal output.
        ai_conversation_history (list[dict[str, str]]): History of AI conversations.
        last_active_tab (str): The last active tab ID.
        completed_levels (list[int]): List of completed level numbers.
        time_spent_per_level (dict[int, float]): Time spent on each level in seconds.
        total_commands_executed (int): Total number of commands executed.
        level_start_time (Optional[datetime]): When the current level was started.
        recovered_passwords (dict[int, str]): Passwords recovered per level index.
            Key is the level whose password was found (e.g. 1 = password for bandit1).
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        hostname: str = "",
        port: int = 2220,
        username: str = "",
        current_level: int = 0,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.name = name or f"Session {self.session_id[:8]}"
        self.hostname = hostname
        self.port = port
        self.username = username
        self.current_level = current_level
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.last_saved_at = datetime.now()
        self.connection_count = 0
        self.is_active = False
        self.metadata: dict[str, Any] = {}
        self.terminal_output_history: list[str] = []
        self.ai_conversation_history: list[dict[str, str]] = []
        self.last_active_tab: str = "terminal"
        self.completed_levels: list[int] = []
        self.time_spent_per_level: dict[int, float] = {}
        self.total_commands_executed: int = 0
        self.level_start_time: Optional[datetime] = None
        # Maps level index → password that unlocks bandit(level+1)
        # e.g. recovered_passwords[0] = password found while on level 0
        self.recovered_passwords: dict[int, str] = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for serialisation."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "current_level": self.current_level,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "last_saved_at": self.last_saved_at.isoformat(),
            "connection_count": self.connection_count,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "terminal_output_history": self.terminal_output_history,
            "ai_conversation_history": self.ai_conversation_history,
            "last_active_tab": self.last_active_tab,
            "completed_levels": self.completed_levels,
            "time_spent_per_level": self.time_spent_per_level,
            "total_commands_executed": self.total_commands_executed,
            "recovered_passwords": {str(k): v for k, v in self.recovered_passwords.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        session = cls(
            session_id=data.get("session_id"),
            name=data.get("name"),
            hostname=data.get("hostname", ""),
            port=data.get("port", 2220),
            username=data.get("username", ""),
            current_level=data.get("current_level", 0),
        )

        session.created_at = datetime.fromisoformat(
            data.get("created_at", datetime.now().isoformat())
        )
        session.last_used = datetime.fromisoformat(
            data.get("last_used", datetime.now().isoformat())
        )
        session.last_saved_at = datetime.fromisoformat(
            data.get("last_saved_at", data.get("last_used", datetime.now().isoformat()))
        )
        session.connection_count = data.get("connection_count", 0)
        session.is_active = data.get("is_active", False)
        session.metadata = data.get("metadata", {})
        session.terminal_output_history = data.get("terminal_output_history", [])
        session.ai_conversation_history = data.get("ai_conversation_history", [])
        session.last_active_tab = data.get("last_active_tab", "terminal")
        session.completed_levels = data.get("completed_levels", [])
        session.time_spent_per_level = {
            int(k): v for k, v in data.get("time_spent_per_level", {}).items()
        }
        session.total_commands_executed = data.get("total_commands_executed", 0)
        session.level_start_time = None
        session.recovered_passwords = {
            int(k): v for k, v in data.get("recovered_passwords", {}).items()
        }

        return session

    def update_usage(self) -> None:
        """Update session usage statistics."""
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

        Note: This does NOT mark the previous level as complete.
        Call mark_level_complete() explicitly when a level is solved.

        Args:
            level: The new current level.
        """
        if level != self.current_level:
            self.level_start_time = datetime.now()

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
        """Get a display name for the session."""
        if self.hostname and self.username:
            return f"{self.username}@{self.hostname}:{self.port}"
        return self.name

    def get_summary(self) -> str:
        """Get a brief summary of the session."""
        return (
            f"{self.get_display_name()} | "
            f"Level {self.current_level} | "
            f"Last used: {self.last_used.strftime('%Y-%m-%d %H:%M')}"
        )

    def update_terminal_history(self, output_lines: list[str], max_lines: int = 1000) -> None:
        """Update terminal output history.

        Args:
            output_lines: List of terminal output lines to store.
            max_lines: Maximum number of lines to keep (keeps most recent).
        """
        self.terminal_output_history = (
            output_lines[-max_lines:] if len(output_lines) > max_lines else output_lines
        )
        self.last_used = datetime.now()

    def update_ai_conversation(
        self, messages: list[dict[str, str]], max_messages: int = 50
    ) -> None:
        """Update AI conversation history.

        Args:
            messages: List of AI conversation messages.
            max_messages: Maximum number of messages to keep.
        """
        self.ai_conversation_history = (
            messages[-max_messages:] if len(messages) > max_messages else messages
        )
        self.last_used = datetime.now()

    def update_active_tab(self, tab_id: str) -> None:
        """Update the last active tab.

        Args:
            tab_id: The tab ID to set as active.

        Raises:
            ValueError: If tab_id is not a valid tab.
        """
        valid_tabs = ["terminal", "session", "level", "mentor"]
        if tab_id not in valid_tabs:
            raise ValueError(f"Invalid tab_id '{tab_id}'. Must be one of: {valid_tabs}")

        self.last_active_tab = tab_id
        self.last_used = datetime.now()

    def mark_level_complete(self, level: int) -> None:
        """Mark a level as completed and track time spent.

        Args:
            level: The level number to mark as complete.
        """
        if level not in self.completed_levels:
            self.completed_levels.append(level)
            self.completed_levels.sort()

            if self.level_start_time:
                time_spent = (datetime.now() - self.level_start_time).total_seconds()
                if level in self.time_spent_per_level:
                    self.time_spent_per_level[level] += time_spent
                else:
                    self.time_spent_per_level[level] = time_spent

                self.level_start_time = None

            self.metadata["last_completed_level"] = level
            self.metadata["total_completed"] = len(self.completed_levels)

        self.last_used = datetime.now()

    def store_password(self, level: int, password: str) -> None:
        """Store a recovered password for the given level.

        The password at level N unlocks bandit(N+1).

        Args:
            level: The level during which the password was found.
            password: The recovered password string.
        """
        self.recovered_passwords[level] = password
        self.last_used = datetime.now()

    def get_password_for_level(self, level: int) -> Optional[str]:
        """Return the stored password that was found during *level*.

        Args:
            level: The level index whose password to retrieve.

        Returns:
            Password string, or None if not yet recovered.
        """
        return self.recovered_passwords.get(level)

    def get_progress_summary(self) -> dict[str, Any]:
        """Get a summary of progress statistics."""
        total_time = sum(self.time_spent_per_level.values())
        completed_count = len(self.completed_levels)
        avg_time = total_time / completed_count if completed_count > 0 else 0

        return {
            "total_levels_completed": completed_count,
            "completed_levels": sorted(self.completed_levels),
            "total_time_spent": total_time,
            "average_time_per_level": avg_time,
            "total_commands_executed": self.total_commands_executed,
            "current_level": self.current_level,
            "completion_percentage": (completed_count / 34) * 100,
            "passwords_recovered": len(self.recovered_passwords),
        }

    def increment_command_count(self) -> None:
        """Increment the total command execution count."""
        self.total_commands_executed += 1
        self.last_used = datetime.now()


class SessionManager:
    """Manages multiple SSH sessions with persistent storage.

    Attributes:
        sessions_file (Path): Path to the sessions storage file.
        sessions (Dict[str, Session]): In-memory session cache.
        active_session_id (Optional[str]): ID of the currently active session.
        lock (Lock): Thread safety lock for session operations.
    """

    def __init__(self, sessions_file: Optional[str] = None) -> None:
        """Initialize the session manager.

        Args:
            sessions_file: Optional path to the sessions storage file.
        """
        self.lock = Lock()

        if sessions_file:
            self.sessions_file = Path(sessions_file)
            self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            bandit_dir = Path.home() / ".bandit_cli"
            bandit_dir.mkdir(exist_ok=True)
            self.sessions_file = bandit_dir / "sessions.json"

        self.sessions: dict[str, Session] = {}
        self.active_session_id: Optional[str] = None
        self._load_sessions()

    def _load_sessions(self) -> None:
        """Load sessions from disk file."""
        try:
            if not self.sessions_file.exists():
                legacy_file = self.sessions_file.parent / "sessions"
                if legacy_file.exists():
                    self._migrate_legacy_file(legacy_file)

            if self.sessions_file.exists():
                with open(self.sessions_file, encoding="utf-8") as f:
                    data = json.load(f)

                for session_id, session_data in data.get("sessions", {}).items():
                    try:
                        session = Session.from_dict(session_data)
                        self.sessions[session_id] = session

                        if session.is_active and self.active_session_id is None:
                            self.active_session_id = session_id
                    except (ValueError, KeyError):
                        continue
        except (json.JSONDecodeError, OSError):
            self.sessions = {}
            if self.sessions_file.exists():
                backup_file = self.sessions_file.with_suffix(".backup")
                try:
                    self.sessions_file.rename(backup_file)
                except OSError:
                    pass

    def _migrate_legacy_file(self, legacy_file: Path) -> None:
        """Migrate data from legacy file to new JSON format."""
        try:
            with open(legacy_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "sessions" in data:
                legacy_file.replace(self.sessions_file)
            elif isinstance(data, dict):
                new_data = {
                    "sessions": data,
                    "active_session_id": None,
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                }
                with open(self.sessions_file, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)
                legacy_file.unlink()
        except (json.JSONDecodeError, ValueError, OSError):
            try:
                new_data = {
                    "sessions": {},
                    "active_session_id": None,
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                }
                with open(self.sessions_file, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)
                legacy_file.unlink()
            except OSError:
                pass

    def _save_sessions(self) -> None:
        """Save sessions to disk file atomically."""
        try:
            temp_file = self.sessions_file.with_suffix(".tmp")
            data = {
                "sessions": {sid: session.to_dict() for sid, session in self.sessions.items()},
                "active_session_id": self.active_session_id,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.sessions_file)
        except OSError:
            pass

    def create_session(
        self,
        name: Optional[str] = None,
        hostname: str = "",
        port: int = 2220,
        username: str = "",
        current_level: int = 0,
    ) -> str:
        """Create a new session.

        Returns:
            The ID of the newly created session.
        """
        with self.lock:
            session = Session(
                name=name,
                hostname=hostname,
                port=port,
                username=username,
                current_level=current_level,
            )
            session.last_saved_at = datetime.now()
            self.sessions[session.session_id] = session
            self._save_sessions()
            return session.session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self.lock:
            return self.sessions.get(session_id)

    def get_active_session(self) -> Optional[Session]:
        """Get the currently active session."""
        if self.active_session_id:
            return self.get_session(self.active_session_id)
        return None

    def set_active_session(self, session_id: str) -> bool:
        """Set the active session.

        Args:
            session_id: The session ID to activate.

        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            if self.active_session_id and self.active_session_id in self.sessions:
                self.sessions[self.active_session_id].set_active(False)

            self.sessions[session_id].set_active(True)
            self.active_session_id = session_id
            self.sessions[session_id].last_saved_at = datetime.now()
            self._save_sessions()
            return True

    def update_session_level(
        self,
        session_id: str,
        level: int,
        terminal_history: Optional[list[str]] = None,
        ai_history: Optional[list[dict[str, str]]] = None,
    ) -> bool:
        """Update the current level for a session.

        Args:
            session_id: The session ID to update.
            level: The new current level.
            terminal_history: Optional terminal output history to update.
            ai_history: Optional AI conversation history to update.

        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            self.sessions[session_id].update_level(level)

            if terminal_history is not None:
                self.sessions[session_id].update_terminal_history(terminal_history)

            if ai_history is not None:
                self.sessions[session_id].update_ai_conversation(ai_history)

            self.sessions[session_id].last_saved_at = datetime.now()
            self._save_sessions()
            return True

    def update_session_connection(
        self, session_id: str, hostname: str, port: int, username: str
    ) -> bool:
        """Update connection details for a session.

        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            self.sessions[session_id].update_connection_details(hostname, port, username)
            self.sessions[session_id].last_saved_at = datetime.now()
            self._save_sessions()
            return True

    def update_session_state(
        self,
        session_id: str,
        terminal_history: Optional[list[str]] = None,
        ai_history: Optional[list[dict[str, str]]] = None,
        active_tab: Optional[str] = None,
    ) -> bool:
        """Update session state including histories and active tab.

        Returns:
            True if successful, False if session not found or invalid tab.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            if terminal_history is not None:
                session.update_terminal_history(terminal_history)

            if ai_history is not None:
                session.update_ai_conversation(ai_history)

            if active_tab is not None:
                try:
                    session.update_active_tab(active_tab)
                except ValueError:
                    return False

            session.last_saved_at = datetime.now()
            self._save_sessions()
            return True

    def store_recovered_password(
        self, session_id: str, level: int, password: str
    ) -> bool:
        """Persist a password recovered while playing a given level.

        Args:
            session_id: The session to update.
            level: The level during which the password was found.
            password: The recovered password string.

        Returns:
            True if successful, False if session not found.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            self.sessions[session_id].store_password(level, password)
            self.sessions[session_id].last_saved_at = datetime.now()
            self._save_sessions()
            return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Cannot delete the active session.

        Returns:
            True if successful, False if session not found or is active.
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            if session_id == self.active_session_id:
                return False

            del self.sessions[session_id]
            self._save_sessions()
            return True

    def list_sessions(self) -> list[Session]:
        """Get all sessions sorted by last used time (most recent first)."""
        with self.lock:
            return sorted(self.sessions.values(), key=lambda s: s.last_used, reverse=True)

    def get_session_names(self) -> list[str]:
        """Get all session display names."""
        with self.lock:
            return [session.get_display_name() for session in self.sessions.values()]

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Remove old inactive sessions.

        Args:
            max_age_days: Maximum age in days for inactive sessions.

        Returns:
            Number of sessions removed.
        """
        with self.lock:
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            to_remove = [
                sid
                for sid, session in self.sessions.items()
                if sid != self.active_session_id and session.last_used.timestamp() < cutoff_time
            ]

            for sid in to_remove:
                del self.sessions[sid]

            if to_remove:
                self._save_sessions()

            return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        with self.lock:
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": sum(1 for s in self.sessions.values() if s.is_active),
                "total_connections": sum(s.connection_count for s in self.sessions.values()),
                "file_size": (
                    self.sessions_file.stat().st_size if self.sessions_file.exists() else 0
                ),
                "last_updated": (
                    datetime.fromtimestamp(self.sessions_file.stat().st_mtime).isoformat()
                    if self.sessions_file.exists()
                    else None
                ),
            }

    def export_sessions(self, file_path: str) -> bool:
        """Export sessions to a file.

        Returns:
            True if export was successful, False otherwise.
        """
        try:
            with self.lock:
                data = {
                    "export_date": datetime.now().isoformat(),
                    "total_sessions": len(self.sessions),
                    "active_session_id": self.active_session_id,
                    "sessions": {sid: session.to_dict() for sid, session in self.sessions.items()},
                }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except OSError:
            return False