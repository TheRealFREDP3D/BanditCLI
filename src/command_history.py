"""Command history management module for BanditCLI.

This module provides persistent command history functionality with navigation,
search, and filtering capabilities. Commands are stored in ~/.bandit_cli/history
and persist across application sessions.

Features:
- Persistent command storage to disk
- Up/down arrow navigation through history
- Command deduplication
- Search and filtering functionality
- Configurable history size limits
- Thread-safe operations
"""

import json
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional


class CommandHistory:
    """Manages command history with persistent storage and navigation.

    Provides thread-safe command history management with disk persistence,
    deduplication, search functionality, and navigation support for
    terminal up/down arrow keys.

    Attributes:
        history_file (Path): Path to the history file on disk.
        max_history_size (int): Maximum number of commands to store.
        history (List[str]): In-memory command history cache.
        position (int): Current position in history for navigation.
        lock (Lock): Thread safety lock for history operations.
    """

    def __init__(
        self,
        max_history_size: int = 1000,
        max_size: Optional[int] = None,
        history_file: Optional[str] = None,
    ) -> None:
        """Initialize the command history manager.

        Args:
            max_history_size: Maximum number of commands to store in history.
            max_size: Alias for max_history_size (for backward compatibility).
            history_file: Optional path to the history file.
        """
        self.max_history_size = max_size if max_size is not None else max_history_size
        self.history: list[str] = []
        self.position = -1
        self.lock = Lock()

        if history_file:
            self.history_file = Path(history_file)
            # Create parent directory if it doesn't exist
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Create ~/.bandit_cli directory if it doesn't exist
            self.bandit_dir = Path.home() / ".bandit_cli"
            self.bandit_dir.mkdir(exist_ok=True)
            self.history_file = self.bandit_dir / "history.json"

        # Load history from file
        self._load_history()

    def _load_history(self) -> None:
        """Load command history from disk file.

        Reads the history file and populates the in-memory history cache.
        Handles file corruption and missing files gracefully.
        Also migrates legacy files if they exist.
        """
        try:
            # Check for migration from legacy file
            if not self.history_file.exists():
                legacy_file = self.history_file.parent / "history"
                if legacy_file.exists():
                    self._migrate_legacy_file(legacy_file)

            if self.history_file.exists():
                with open(self.history_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("commands", [])
                    # Ensure we don't exceed max size
                    if len(self.history) > self.max_history_size:
                        self.history = self.history[-self.max_history_size :]
            else:
                self.history = []
        except (json.JSONDecodeError, OSError):
            # If file is corrupted or unreadable, start with empty history
            self.history = []
            # Try to backup the corrupted file
            if self.history_file.exists():
                backup_file = self.history_file.with_suffix(".backup")
                try:
                    self.history_file.rename(backup_file)
                except OSError:
                    pass  # If backup fails, just continue

    def _migrate_legacy_file(self, legacy_file: Path) -> None:
        """Migrate data from legacy file to new JSON format.

        Args:
            legacy_file: Path to the legacy history file.
        """
        try:
            # Try to read as JSON first (new format without extension)
            with open(legacy_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "commands" in data:
                    # Already in JSON format, just rename
                    legacy_file.replace(self.history_file)
                elif isinstance(data, list):
                    # Simple list format, convert to new format
                    new_data = {
                        "commands": data[: self.max_history_size],
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0",
                    }
                    with open(self.history_file, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=2)
                    legacy_file.unlink()
                else:
                    # Unknown format, treat as plain text lines
                    raise ValueError("Unknown format")
        except (json.JSONDecodeError, ValueError):
            # Treat as plain text file with one command per line
            try:
                with open(legacy_file, encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]

                # Convert to new JSON format
                new_data = {
                    "commands": lines[: self.max_history_size],
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                }

                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)

                # Remove legacy file after successful migration
                legacy_file.unlink()
            except OSError:
                # If migration fails, continue without data
                pass

    def _save_history(self) -> None:
        """Save command history to disk file.

        Persists the current in-memory history to disk with proper error handling.
        Creates atomic writes to prevent data corruption.
        """
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.history_file.with_suffix(".tmp")
            data = {
                "commands": self.history,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            temp_file.replace(self.history_file)

        except OSError:
            # If save fails, continue without saving to avoid breaking functionality
            pass

    def add_command(self, command: str) -> None:
        """Add a command to the history.

        Adds a command to history with deduplication (don't add if it's the same
        as the last command) and size limit enforcement.

        Args:
            command: The command string to add to history.
        """
        if not command or not command.strip():
            return  # Don't add empty commands

        command = command.strip()

        with self.lock:
            # Don't add if it's the same as the last command
            if self.history and self.history[-1] == command:
                return

            # Add command to history
            self.history.append(command)

            # Enforce size limit
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size :]

            # Reset position to end
            self.position = len(self.history)

            # Save to disk
            self._save_history()

    def get_previous(self, current_input: str = "") -> Optional[str]:
        """Get the previous command in history.

        Navigates up through command history. If current_input is provided,
        it's saved as the current editing position.

        Args:
            current_input: The current input in the terminal (for editing state).

        Returns:
            The previous command in history, or None if at the beginning.
        """
        with self.lock:
            if not self.history:
                return None

            # If we're at the end (position == len), save current input
            if self.position == len(self.history) and current_input:
                # This would be the "new" command being edited
                pass

            if self.position > 0:
                self.position -= 1
                return self.history[self.position]

            return None

    def get_next(self) -> Optional[str]:
        """Get the next command in history.

        Navigates down through command history. Returns None when past the end.

        Returns:
            The next command in history, or None if at the end.
        """
        with self.lock:
            if not self.history:
                return None

            if self.position < len(self.history) - 1:
                self.position += 1
                return self.history[self.position]
            elif self.position == len(self.history) - 1:
                # Move past the end to indicate "new" command
                self.position = len(self.history)
                return ""  # Return empty string for new command

            return None

    def reset_navigation(self) -> None:
        """Reset navigation position to the end of history.

        Call this when starting a new command input to reset the navigation
        position to the end of the history list.
        """
        with self.lock:
            self.position = len(self.history)

    def search(self, pattern: str, max_results: int = 50) -> list[str]:
        """Search command history for commands matching a pattern.

        Supports regex patterns for advanced searching. Returns commands
        that match the pattern, most recent first.

        Args:
            pattern: Search pattern (supports regex).
            max_results: Maximum number of results to return.

        Returns:
            List of matching commands in reverse chronological order.
        """
        with self.lock:
            if not pattern:
                return []

            try:
                # Compile regex pattern
                regex = re.compile(pattern, re.IGNORECASE)

                # Search through history (reverse order for most recent first)
                matches = []
                for command in reversed(self.history):
                    if regex.search(command):
                        matches.append(command)
                        if len(matches) >= max_results:
                            break

                return matches
            except re.error:
                # If regex is invalid, try simple substring search
                pattern_lower = pattern.lower()
                matches = []
                for command in reversed(self.history):
                    if pattern_lower in command.lower():
                        matches.append(command)
                        if len(matches) >= max_results:
                            break

                return matches

    def filter_by_prefix(self, prefix: str) -> list[str]:
        """Filter history by command prefix.

        Returns commands that start with the given prefix, most recent first.

        Args:
            prefix: The prefix to filter by.

        Returns:
            List of commands starting with the prefix.
        """
        with self.lock:
            if not prefix:
                return []

            prefix_lower = prefix.lower()
            return [cmd for cmd in reversed(self.history) if cmd.lower().startswith(prefix_lower)]

    def clear_history(self) -> None:
        """Clear all command history.

        Removes all commands from history and deletes the history file.
        """
        with self.lock:
            self.history.clear()
            self.position = -1

            # Delete history file
            try:
                if self.history_file.exists():
                    self.history_file.unlink()
            except OSError:
                pass

    def get_recent_commands(self, count: int = 10) -> list[str]:
        """Get the most recent commands from history.

        Args:
            count: Number of recent commands to return.

        Returns:
            List of recent commands in chronological order.
        """
        with self.lock:
            return self.history[-count:] if self.history else []

    def get_stats(self) -> dict:
        """Get statistics about the command history.

        Returns:
            Dictionary containing history statistics.
        """
        with self.lock:
            return {
                "total_commands": len(self.history),
                "max_size": self.max_history_size,
                "file_size": self.history_file.stat().st_size if self.history_file.exists() else 0,
                "last_updated": (
                    datetime.fromtimestamp(self.history_file.stat().st_mtime).isoformat()
                    if self.history_file.exists()
                    else None
                ),
            }

    def export_history(self, file_path: str, format_type: str = "text") -> bool:
        """Export command history to a file.

        Args:
            file_path: Path to export file.
            format_type: Export format ('text', 'json', or 'csv').

        Returns:
            True if export was successful, False otherwise.
        """
        try:
            with self.lock:
                if format_type == "json":
                    data = {
                        "export_date": datetime.now().isoformat(),
                        "total_commands": len(self.history),
                        "commands": self.history,
                    }
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                elif format_type == "csv":
                    import csv

                    with open(file_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["Index", "Command", "Timestamp"])
                        for i, cmd in enumerate(self.history, 1):
                            writer.writerow([i, cmd, ""])

                else:  # text format
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("# BanditCLI Command History Export\n")
                        f.write(f"# Exported: {datetime.now().isoformat()}\n")
                        f.write(f"# Total Commands: {len(self.history)}\n\n")
                        for i, cmd in enumerate(self.history, 1):
                            f.write(f"{i:4d}: {cmd}\n")

            return True
        except (OSError, ImportError):
            return False
