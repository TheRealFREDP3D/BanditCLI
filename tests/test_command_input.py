"""Unit tests for the CommandInput class."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CommandInput


class TestCommandInput:
    """Test cases for the CommandInput class."""
    
    def test_init(self):
        """Test CommandInput initialization."""
        mock_history = Mock()
        input_widget = CommandInput(mock_history)
        
        assert input_widget.command_history == mock_history
    
    @patch('main.Key')
    def test_on_key_up_arrow(self, mock_key):
        """Test handling up arrow key press."""
        mock_history = Mock()
        mock_history.get_previous_command.return_value = "previous command"
        input_widget = CommandInput(mock_history)
        input_widget.value = "current command"
        
        # Create a mock key event for up arrow
        mock_event = Mock()
        mock_event.key = "up"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that the previous command was retrieved
        mock_history.get_previous_command.assert_called_once()
        
        # Check that the input value was updated
        assert input_widget.value == "previous command"
        assert input_widget.cursor_position == len("previous command")
        
        # Check that prevent_default was called
        mock_event.prevent_default.assert_called_once()
    
    @patch('main.Key')
    def test_on_key_up_arrow_no_command(self, mock_key):
        """Test handling up arrow key press when no previous command exists."""
        mock_history = Mock()
        mock_history.get_previous_command.return_value = None
        input_widget = CommandInput(mock_history)
        input_widget.value = "current command"
        
        # Create a mock key event for up arrow
        mock_event = Mock()
        mock_event.key = "up"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that the previous command was retrieved
        mock_history.get_previous_command.assert_called_once()
        
        # Check that the input value was not changed
        assert input_widget.value == "current command"
        
        # Check that prevent_default was not called
        mock_event.prevent_default.assert_not_called()
    
    @patch('main.Key')
    def test_on_key_down_arrow(self, mock_key):
        """Test handling down arrow key press."""
        mock_history = Mock()
        mock_history.get_next_command.return_value = "next command"
        input_widget = CommandInput(mock_history)
        input_widget.value = "current command"
        
        # Create a mock key event for down arrow
        mock_event = Mock()
        mock_event.key = "down"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that the next command was retrieved
        mock_history.get_next_command.assert_called_once()
        
        # Check that the input value was updated
        assert input_widget.value == "next command"
        assert input_widget.cursor_position == len("next command")
        
        # Check that prevent_default was called
        mock_event.prevent_default.assert_called_once()
    
    @patch('main.Key')
    def test_on_key_down_arrow_no_command(self, mock_key):
        """Test handling down arrow key press when no next command exists."""
        mock_history = Mock()
        mock_history.get_next_command.return_value = None
        input_widget = CommandInput(mock_history)
        input_widget.value = "current command"
        
        # Create a mock key event for down arrow
        mock_event = Mock()
        mock_event.key = "down"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that the next command was retrieved
        mock_history.get_next_command.assert_called_once()
        
        # Check that the input value was not changed
        assert input_widget.value == "current command"
        
        # Check that prevent_default was not called
        mock_event.prevent_default.assert_not_called()
    
    @patch('main.Key')
    def test_on_key_enter(self, mock_key):
        """Test handling enter key press."""
        mock_history = Mock()
        input_widget = CommandInput(mock_history)
        
        # Create a mock key event for enter
        mock_event = Mock()
        mock_event.key = "enter"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that reset_index was called
        mock_history.reset_index.assert_called_once()
        
        # Check that prevent_default was not called
        mock_event.prevent_default.assert_not_called()
    
    @patch('main.Key')
    def test_on_key_other_key(self, mock_key):
        """Test handling other key presses."""
        mock_history = Mock()
        input_widget = CommandInput(mock_history)
        
        # Create a mock key event for a different key
        mock_event = Mock()
        mock_event.key = "a"
        mock_key.return_value = mock_event
        
        # Call on_key
        input_widget.on_key(mock_event)
        
        # Check that no history methods were called
        mock_history.get_previous_command.assert_not_called()
        mock_history.get_next_command.assert_not_called()
        mock_history.reset_index.assert_not_called()
        
        # Check that prevent_default was not called
        mock_event.prevent_default.assert_not_called()