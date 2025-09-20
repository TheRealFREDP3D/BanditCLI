"""Unit tests for the command history module."""
import pytest
import os
import json
from pathlib import Path
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from command_history import CommandHistory


class TestCommandHistory:
    """Test cases for the CommandHistory class."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        history = CommandHistory()
        
        assert history.max_size == 100
        assert history.history_file is None
        assert history.commands == []
        assert history.index == -1
    
    def test_init_with_custom_values(self, tmp_path):
        """Test initialization with custom values."""
        history_file = tmp_path / "history.json"
        history = CommandHistory(max_size=50, history_file=str(history_file))
        
        assert history.max_size == 50
        assert history.history_file == str(history_file)
        assert history.commands == []
        assert history.index == -1
    
    def test_add_command(self):
        """Test adding commands to history."""
        history = CommandHistory()
        
        # Add a command
        history.add_command("ls -la")
        assert history.commands == ["ls -la"]
        
        # Add another command
        history.add_command("pwd")
        assert history.commands == ["pwd", "ls -la"]
        
        # Add a duplicate command (should move it to the front)
        history.add_command("ls -la")
        assert history.commands == ["ls -la", "pwd"]
        
        # Add an empty command (should be ignored)
        history.add_command("")
        assert history.commands == ["ls -la", "pwd"]
        
        # Add a command with whitespace (should be stripped)
        history.add_command("  cd /home  ")
        assert history.commands == ["cd /home", "ls -la", "pwd"]
    
    def test_add_command_limit_size(self):
        """Test that history is limited to max_size."""
        history = CommandHistory(max_size=3)
        
        # Add more commands than max_size
        for i in range(5):
            history.add_command(f"command{i}")
        
        # Should only keep the last max_size commands
        assert len(history.commands) == 3
        assert history.commands == ["command4", "command3", "command2"]
    
    def test_get_previous_command(self):
        """Test getting previous commands from history."""
        history = CommandHistory()
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        history.add_command("cmd3")
        
        # Get previous commands
        assert history.get_previous_command() == "cmd3"
        assert history.get_previous_command() == "cmd2"
        assert history.get_previous_command() == "cmd1"
        assert history.get_previous_command() is None  # No more commands
        
        # Check index
        assert history.index == 2
    
    def test_get_next_command(self):
        """Test getting next commands from history."""
        history = CommandHistory()
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        history.add_command("cmd3")
        
        # Move to the middle of history
        history.get_previous_command()  # cmd3
        history.get_previous_command()  # cmd2
        
        # Get next commands
        assert history.get_next_command() == "cmd3"
        assert history.get_next_command() == ""  # Empty string when at the end
        assert history.get_next_command() is None  # No more commands
        
        # Check index
        assert history.index == -1
    
    def test_reset_index(self):
        """Test resetting the history index."""
        history = CommandHistory()
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        
        # Move through history
        history.get_previous_command()  # cmd2
        assert history.index == 0
        
        # Reset index
        history.reset_index()
        assert history.index == -1
    
    def test_get_all_commands(self):
        """Test getting all commands."""
        history = CommandHistory()
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        history.add_command("cmd3")
        
        # Get all commands
        all_commands = history.get_all_commands()
        assert all_commands == ["cmd3", "cmd2", "cmd1"]
        
        # Verify it's a copy (modifying it doesn't affect the original)
        all_commands.append("cmd4")
        assert history.commands == ["cmd3", "cmd2", "cmd1"]
    
    def test_clear_history(self):
        """Test clearing history."""
        history = CommandHistory()
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        
        # Clear history
        history.clear_history()
        assert history.commands == []
        assert history.index == -1
    
    def test_save_history(self, tmp_path):
        """Test saving history to file."""
        history_file = tmp_path / "history.json"
        history = CommandHistory(history_file=str(history_file))
        
        # Add some commands
        history.add_command("cmd1")
        history.add_command("cmd2")
        
        # Save history
        history.save_history()
        
        # Check that file was created
        assert history_file.exists()
        
        # Check file contents
        with open(history_file, 'r') as f:
            saved_commands = json.load(f)
        assert saved_commands == ["cmd2", "cmd1"]
    
    def test_load_history(self, tmp_path):
        """Test loading history from file."""
        history_file = tmp_path / "history.json"
        
        # Create a history file
        commands = ["cmd1", "cmd2", "cmd3"]
        with open(history_file, 'w') as f:
            json.dump(commands, f)
        
        # Load history
        history = CommandHistory(history_file=str(history_file))
        
        # Check that commands were loaded
        assert history.commands == commands
    
    def test_load_history_limit_size(self, tmp_path):
        """Test that loaded history is limited to max_size."""
        history_file = tmp_path / "history.json"
        
        # Create a history file with more commands than max_size
        commands = [f"cmd{i}" for i in range(10)]
        with open(history_file, 'w') as f:
            json.dump(commands, f)
        
        # Load history with smaller max_size
        history = CommandHistory(max_size=5, history_file=str(history_file))
        
        # Check that only max_size commands were loaded
        assert len(history.commands) == 5
        assert history.commands == commands[:5]