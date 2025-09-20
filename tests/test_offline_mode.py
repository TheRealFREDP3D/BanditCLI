"""Unit tests for offline mode functionality."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import BanditCLIApp


class TestOfflineMode:
    """Test cases for offline mode functionality."""
    
    def test_toggle_offline_mode(self):
        """Test toggling offline mode."""
        app = BanditCLIApp()
        app.notify = Mock()  # Mock notify to avoid actual notifications
        
        # Initially offline mode should be False
        assert app.offline_mode is False
        
        # Toggle offline mode on
        app.action_toggle_offline_mode()
        assert app.offline_mode is True
        app.notify.assert_called_with("Offline mode enabled", severity="information")
        
        # Toggle offline mode off
        app.action_toggle_offline_mode()
        assert app.offline_mode is False
        app.notify.assert_called_with("Offline mode disabled", severity="information")
    
    def test_toggle_offline_mode_disconnects_ssh(self):
        """Test that toggling offline mode disconnects SSH when connected."""
        app = BanditCLIApp()
        app.notify = Mock()  # Mock notify to avoid actual notifications
        app.ssh_connected = True
        app.disconnect_ssh = Mock()  # Mock disconnect_ssh method
        
        # Toggle offline mode on
        app.action_toggle_offline_mode()
        assert app.offline_mode is True
        # Check that disconnect_ssh was called
        app.disconnect_ssh.assert_called_once()
    
    def test_connect_ssh_in_offline_mode(self):
        """Test that SSH connection is blocked in offline mode."""
        app = BanditCLIApp()
        app.notify = Mock()  # Mock notify to avoid actual notifications
        app.offline_mode = True
        
        # Try to connect SSH in offline mode
        app.connect_ssh()
        
        # Check that notify was called with the correct error message
        app.notify.assert_called_with("Cannot connect in offline mode", severity="error")
    
    def test_send_command_in_offline_mode(self):
        """Test that sending commands is blocked in offline mode."""
        app = BanditCLIApp()
        app.notify = Mock()  # Mock notify to avoid actual notifications
        app.offline_mode = True
        
        # Try to send a command in offline mode
        app.send_command()
        
        # Check that notify was called with the correct error message
        app.notify.assert_called_with("Cannot send commands in offline mode", severity="error")
    
    def test_send_mentor_message_in_offline_mode(self):
        """Test that sending mentor messages works in offline mode."""
        app = BanditCLIApp()
        app.offline_mode = True
        
        # Mock the query_one method to return inputs
        with patch.object(app, 'query_one') as mock_query:
            # Mock mentor input with a message
            mock_mentor_input = Mock()
            mock_mentor_input.value = "Test message"
            
            # Mock mentor chat text area
            mock_mentor_chat = Mock()
            mock_mentor_chat.text = ""
            
            # Set up the mock to return the appropriate widgets
            def query_one_side_effect(query, input_type=None):
                if "#mentor_input" in query:
                    return mock_mentor_input
                elif "#mentor_chat" in query:
                    return mock_mentor_chat
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call send_mentor_message
            app.send_mentor_message()
            
            # Check that the offline mentor message method was called
            # We can check this by verifying the response in the chat
            assert mock_mentor_chat.load_text.called
            call_args = mock_mentor_chat.load_text.call_args[0][0]
            assert "AI mentor is not available in offline mode" in call_args
            
            # Check that the input was cleared
            assert mock_mentor_input.value == ""