"""Command history management for the Bandit CLI application."""
import json
import os
from typing import List, Optional


class CommandHistory:
    """Manages command history with persistence."""
    
    def __init__(self, max_size: int = 100, history_file: str = None):
        """
        Initialize command history manager.
        
        Args:
            max_size: Maximum number of commands to store
            history_file: Path to file for persistent storage
        """
        self.max_size = max_size
        self.history_file = history_file
        self.commands: List[str] = []
        self.index = -1
        
        # Load history from file if specified
        if self.history_file:
            self.load_history()
    
    def add_command(self, command: str):
        """
        Add a command to history.
        
        Args:
            command: Command to add
        """
        if not command or not command.strip():
            return
            
        # Remove duplicates
        if command in self.commands:
            self.commands.remove(command)
            
        # Add to beginning of list
        self.commands.insert(0, command.strip())
        
        # Limit size
        if len(self.commands) > self.max_size:
            self.commands = self.commands[:self.max_size]
            
        # Reset index
        self.index = -1
        
        # Save to file if specified
        if self.history_file:
            self.save_history()
    
    def get_previous_command(self) -> Optional[str]:
        """
        Get the previous command in history.
        
        Returns:
            Previous command or None if at beginning
        """
        if not self.commands:
            return None
            
        if self.index < len(self.commands) - 1:
            self.index += 1
            return self.commands[self.index]
        return None
    
    def get_next_command(self) -> Optional[str]:
        """
        Get the next command in history.
        
        Returns:
            Next command or None if at end
        """
        if not self.commands:
            return None
            
        if self.index > 0:
            self.index -= 1
            return self.commands[self.index]
        elif self.index == 0:
            self.index = -1
            return ""
        return None
    
    def reset_index(self):
        """Reset the history index."""
        self.index = -1
    
    def save_history(self):
        """Save history to file."""
        if not self.history_file:
            return
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            with open(self.history_file, 'w') as f:
                json.dump(self.commands, f)
        except Exception as e:
            print(f"Warning: Could not save command history: {e}")
    
    def load_history(self):
        """Load history from file."""
        if not self.history_file or not os.path.exists(self.history_file):
            return
            
        try:
            with open(self.history_file, 'r') as f:
                self.commands = json.load(f)
                
            # Limit size
            if len(self.commands) > self.max_size:
                self.commands = self.commands[:self.max_size]
        except Exception as e:
            print(f"Warning: Could not load command history: {e}")
    
    def get_all_commands(self) -> List[str]:
        """
        Get all commands in history.
        
        Returns:
            List of all commands
        """
        return self.commands.copy()
    
    def clear_history(self):
        """Clear all command history."""
        self.commands = []
        self.index = -1
        if self.history_file:
            self.save_history()