"""Unit tests for enhanced error handling and input validation."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import BanditCLIApp


class TestErrorHandlingAndValidation:
    """Test cases for enhanced error handling and input validation."""
    
    def test_connect_ssh_missing_credentials(self):
        """Test SSH connection with missing credentials."""
        app = BanditCLIApp()
        
        # Mock the query_one method to return inputs with empty values
        with patch.object(app, 'query_one') as mock_query:
            # Mock username and password inputs with empty values
            mock_username_input = Mock()
            mock_username_input.value = ""
            mock_password_input = Mock()
            mock_password_input.value = ""
            mock_port_input = Mock()
            mock_port_input.value = "2220"
            
            # Set up the mock to return the appropriate inputs
            def query_one_side_effect(query, input_type=None):
                if "#ssh_username" in query:
                    return mock_username_input
                elif "#ssh_password" in query:
                    return mock_password_input
                elif "#ssh_port" in query:
                    return mock_port_input
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call connect_ssh
            app.connect_ssh()
            
            # Check that notify was called with the correct error message
            app.notify.assert_called_once_with("Please enter both username and password", severity="error")
    
    def test_connect_ssh_invalid_port(self):
        """Test SSH connection with invalid port."""
        app = BanditCLIApp()
        
        # Mock the query_one method to return inputs with invalid port
        with patch.object(app, 'query_one') as mock_query:
            # Mock inputs with valid username/password but invalid port
            mock_username_input = Mock()
            mock_username_input.value = "bandit0"
            mock_password_input = Mock()
            mock_password_input.value = "bandit0"
            mock_port_input = Mock()
            mock_port_input.value = "invalid"
            
            # Set up the mock to return the appropriate inputs
            def query_one_side_effect(query, input_type=None):
                if "#ssh_username" in query:
                    return mock_username_input
                elif "#ssh_password" in query:
                    return mock_password_input
                elif "#ssh_port" in query:
                    return mock_port_input
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call connect_ssh
            app.connect_ssh()
            
            # Check that notify was called with the correct error message
            app.notify.assert_called_once_with("Port must be a valid number", severity="error")
    
    def test_connect_ssh_port_out_of_range(self):
        """Test SSH connection with port out of range."""
        app = BanditCLIApp()
        
        # Mock the query_one method to return inputs with out of range port
        with patch.object(app, 'query_one') as mock_query:
            # Mock inputs with valid username/password but out of range port
            mock_username_input = Mock()
            mock_username_input.value = "bandit0"
            mock_password_input = Mock()
            mock_password_input.value = "bandit0"
            mock_port_input = Mock()
            mock_port_input.value = "70000"  # Out of range
            
            # Set up the mock to return the appropriate inputs
            def query_one_side_effect(query, input_type=None):
                if "#ssh_username" in query:
                    return mock_username_input
                elif "#ssh_password" in query:
                    return mock_password_input
                elif "#ssh_port" in query:
                    return mock_port_input
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call connect_ssh
            app.connect_ssh()
            
            # Check that notify was called with the correct error message
            app.notify.assert_called_once_with("Port must be between 1 and 65535", severity="error")
    
    def test_send_command_not_connected(self):
        """Test sending command when not connected."""
        app = BanditCLIApp()
        app.ssh_connected = False
        
        # Mock the notify method to capture calls
        app.notify = Mock()
        
        # Call send_command
        app.send_command()
        
        # Check that notify was called with the correct error message
        app.notify.assert_called_once_with("Not connected to SSH server", severity="error")
    
    def test_send_command_too_long(self):
        """Test sending command that is too long."""
        app = BanditCLIApp()
        app.ssh_connected = True
        
        # Mock the query_one method to return input with long command
        with patch.object(app, 'query_one') as mock_query:
            # Mock command input with long value
            mock_command_input = Mock()
            mock_command_input.value = "a" * 1001  # Too long
            
            # Set up the mock to return the command input
            def query_one_side_effect(query, input_type=None):
                if "#command_input" in query:
                    return mock_command_input
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call send_command
            app.send_command()
            
            # Check that notify was called with the correct error message
            app.notify.assert_called_once_with("Command is too long (maximum 1000 characters)", severity="error")
    
    def test_send_mentor_message_too_long(self):
        """Test sending mentor message that is too long."""
        app = BanditCLIApp()
        
        # Mock the query_one method to return input with long message
        with patch.object(app, 'query_one') as mock_query:
            # Mock mentor input with long value
            mock_mentor_input = Mock()
            mock_mentor_input.value = "a" * 1001  # Too long
            
            # Set up the mock to return the mentor input
            def query_one_side_effect(query, input_type=None):
                if "#mentor_input" in query:
                    return mock_mentor_input
                else:
                    return Mock()
                    
            mock_query.side_effect = query_one_side_effect
            
            # Mock the notify method to capture calls
            app.notify = Mock()
            
            # Call send_mentor_message
            app.send_mentor_message()
            
            # Check that notify was called with the correct error message
            app.notify.assert_called_once_with("Message is too long (maximum 1000 characters)", severity="error")
    
    def test_previous_level_at_first_level(self):
        """Test navigating to previous level when already at first level."""
        app = BanditCLIApp()
        app.current_level = 0
        
        # Mock the notify method to capture calls
        app.notify = Mock()
        
        # Call previous_level
        app.previous_level()
        
        # Check that notify was called with the correct warning message
        app.notify.assert_called_once_with("Already at the first level", severity="warning")
    
    def test_next_level_beyond_available_levels(self):
        """Test navigating to next level beyond available levels."""
        app = BanditCLIApp()
        app.current_level = 10  # Set to a high level
        
        # Mock the level_info to return a limited set of levels
        mock_level_info = Mock()
        mock_level_info.get_all_levels.return_value = {"0": {}, "1": {}, "2": {}}
        app.level_info = mock_level_info
        
        # Mock the notify method to capture calls
        app.notify = Mock()
        
        # Call next_level
        app.next_level()
        
        # Check that notify was called with the correct warning message
        app.notify.assert_called_once_with("Level 10 is the highest available level", severity="warning")