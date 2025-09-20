"""Unit tests for the SSHManager class."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ssh_manager import SSHManager, SSHConnection


class TestSSHManager:
    """Test cases for the SSHManager class."""
    
    def test_init(self):
        """Test SSHManager initialization."""
        manager = SSHManager()
        assert manager.connections == {}
    
    def test_create_connection_success(self):
        """Test successful creation of SSH connection."""
        manager = SSHManager()
        
        # Mock the SSHConnection.connect method to return True
        with patch('ssh_manager.SSHConnection.connect', return_value=True):
            with patch('ssh_manager.SSHConnection') as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True
                
                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password="testpass"
                )
                
                assert result is True
                assert "test_session" in manager.connections
                mock_connection_class.assert_called_once_with(
                    "test.host", 2220, "testuser", "testpass"
                )
    
    def test_create_connection_failure(self):
        """Test failed creation of SSH connection."""
        manager = SSHManager()
        
        # Mock the SSHConnection.connect method to return False
        with patch('ssh_manager.SSHConnection.connect', return_value=False):
            with patch('ssh_manager.SSHConnection') as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = False
                
                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password="testpass"
                )
                
                assert result is False
                assert "test_session" not in manager.connections
    
    def test_get_connection_existing(self):
        """Test getting an existing connection."""
        manager = SSHManager()
        
        # Create a mock connection and add it to the manager
        mock_connection = Mock()
        manager.connections["test_session"] = mock_connection
        
        result = manager.get_connection("test_session")
        assert result == mock_connection
    
    def test_get_connection_non_existing(self):
        """Test getting a non-existing connection."""
        manager = SSHManager()
        
        result = manager.get_connection("non_existing_session")
        assert result is None
    
    def test_disconnect_session(self):
        """Test disconnecting a session."""
        manager = SSHManager()
        
        # Create a mock connection with a disconnect method
        mock_connection = Mock()
        mock_connection.disconnect = Mock()
        manager.connections["test_session"] = mock_connection
        
        manager.disconnect_session("test_session")
        
        # Verify the disconnect method was called and the connection was removed
        mock_connection.disconnect.assert_called_once()
        assert "test_session" not in manager.connections
    
    def test_disconnect_all(self):
        """Test disconnecting all sessions."""
        manager = SSHManager()
        
        # Create mock connections with disconnect methods
        mock_connection1 = Mock()
        mock_connection1.disconnect = Mock()
        mock_connection2 = Mock()
        mock_connection2.disconnect = Mock()
        
        manager.connections["session1"] = mock_connection1
        manager.connections["session2"] = mock_connection2
        
        manager.disconnect_all()
        
        # Verify the disconnect methods were called and connections were removed
        mock_connection1.disconnect.assert_called_once()
        mock_connection2.disconnect.assert_called_once()
        assert manager.connections == {}


class TestSSHConnection:
    """Test cases for the SSHConnection class."""
    
    @patch('ssh_manager.paramiko')
    def test_connect_success(self, mock_paramiko):
        """Test successful SSH connection."""
        # Setup mocks
        mock_client = Mock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_channel = Mock()
        mock_client.invoke_shell.return_value = mock_channel
        
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass"
        )
        
        # Call connect method
        result = connection.connect()
        
        # Verify results
        assert result is True
        assert connection.connected is True
        assert connection.client == mock_client
        assert connection.channel == mock_channel
        
        # Verify method calls
        mock_paramiko.SSHClient.assert_called_once()
        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            timeout=10
        )
        mock_client.invoke_shell.assert_called_once()
        mock_channel.settimeout.assert_called_once_with(0.1)
    
    @patch('ssh_manager.paramiko')
    def test_connect_failure(self, mock_paramiko):
        """Test failed SSH connection."""
        # Setup mock to raise a generic exception
        mock_client = Mock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_client.connect.side_effect = Exception("Connection failed")
        
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass"
        )
        
        # Call connect method
        result = connection.connect()
        
        # Verify results
        assert result is False
        assert connection.connected is False
        assert connection.client is None
    
    def test_send_command_when_connected(self):
        """Test sending a command when connected."""
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass"
        )
        
        # Set up connection state
        connection.connected = True
        connection.channel = Mock()
        
        # Send a command
        connection.send_command("ls -la")
        
        # Verify the command was sent
        connection.channel.send.assert_called_once_with("ls -la")
    
    def test_send_command_when_not_connected(self):
        """Test sending a command when not connected."""
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass"
        )
        
        # Ensure not connected
        connection.connected = False
        connection.channel = Mock()
        
        # Send a command
        connection.send_command("ls -la")
        
        # Verify the command was not sent
        connection.channel.send.assert_not_called()
    
    def test_disconnect(self):
        """Test disconnecting SSH connection."""
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass"
        )
        
        # Set up connection state
        connection.connected = True
        connection.stop_reading = False
        connection.channel = Mock()
        connection.client = Mock()
        connection.read_thread = Mock()
        
        # Call disconnect
        connection.disconnect()
        
        # Verify state changes
        assert connection.stop_reading is True
        assert connection.connected is False
        
        # Verify cleanup methods were called
        connection.read_thread.join.assert_called_once_with(timeout=1)
        connection.channel.close.assert_called_once()
        connection.client.close.assert_called_once()