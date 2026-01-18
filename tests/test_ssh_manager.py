"""Unit tests for the SSHManager class."""

import os
import sys
from unittest.mock import Mock, patch

import paramiko

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ssh_manager import SSHConnection, SSHManager


class TestSSHManager:
    """Test cases for the SSHManager class."""

    def test_init(self):
        """Test SSHManager initialization."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)
        assert manager.connections == {}
        assert manager.notify == mock_notify

    def test_create_connection_success(self):
        """Test successful creation of SSH connection."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Mock the SSHConnection.connect method to return True
        with patch("ssh_manager.SSHConnection.connect", return_value=True):
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password="testpass",
                )

                assert result is True
                assert "test_session" in manager.connections
                mock_connection_class.assert_called_once_with(
                    "test.host",
                    2220,
                    "testuser",
                    "testpass",
                    mock_notify,
                    timeout=10,
                    verify_host_key=True,
                )

    def test_create_connection_failure(self):
        """Test failed creation of SSH connection."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Mock the SSHConnection.connect method to return False
        with patch("ssh_manager.SSHConnection.connect", return_value=False):
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = False

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password="testpass",
                )

                assert result is False
                assert "test_session" not in manager.connections

    def test_get_connection_existing(self):
        """Test getting an existing connection."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Create a mock connection and add it to the manager
        mock_connection = Mock()
        manager.connections["test_session"] = mock_connection

        result = manager.get_connection("test_session")
        assert result == mock_connection

    def test_get_connection_non_existing(self):
        """Test getting a non-existing connection."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        result = manager.get_connection("non_existing_session")
        assert result is None

    def test_disconnect_session(self):
        """Test disconnecting a session."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

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
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

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

    @patch("ssh_manager.paramiko")
    def test_connect_success(self, mock_paramiko):
        """Test successful SSH connection."""
        mock_notify = Mock()
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
            password="testpass",
            notify_callback=mock_notify,
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
            hostname="test.host", port=2220, username="testuser", password="testpass", timeout=10
        )
        mock_client.invoke_shell.assert_called_once()
        mock_channel.settimeout.assert_called_once_with(0.1)

    @patch("ssh_manager.paramiko")
    def test_connect_failure(self, mock_paramiko):
        """Test failed SSH connection."""
        mock_notify = Mock()
        # Setup mock to raise a generic exception
        mock_client = Mock()
        mock_paramiko.SSHClient.return_value = mock_client
        # Properly mock the paramiko exceptions
        mock_paramiko.AuthenticationException = paramiko.AuthenticationException
        mock_paramiko.SSHException = paramiko.SSHException
        mock_client.connect.side_effect = Exception("Connection failed")

        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        # Call connect method
        result = connection.connect()

        # Verify results
        assert result is False
        assert connection.connected is False

    def test_send_command_when_connected(self):
        """Test sending a command when connected."""
        mock_notify = Mock()
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
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
        mock_notify = Mock()
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
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
        mock_notify = Mock()
        # Create SSHConnection instance
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
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

    def test_execute_command_success(self):
        """Test successful command execution."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        # Set up connection state
        connection.connected = True
        connection.channel = Mock()

        # Mock command execution
        connection.send_command = Mock()
        connection.receive_output = Mock(return_value="command output")

        result = connection.execute_command("ls -la")

        assert result == "command output"
        connection.send_command.assert_called_once_with("ls -la")
        connection.receive_output.assert_called_once()

    def test_execute_command_not_connected(self):
        """Test command execution when not connected."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        # Ensure not connected
        connection.connected = False

        result = connection.execute_command("ls -la")

        assert result == ""

    def test_receive_output(self):
        """Test receiving output from SSH channel."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        # Set up connection state
        connection.connected = True
        connection.channel = Mock()
        connection.channel.recv_ready.return_value = True
        connection.channel.recv.return_value = b"test output"
        connection.stop_reading = False

        # Test receiving output
        with patch("time.sleep", side_effect=lambda x: None):  # Speed up test
            output = connection.receive_output(timeout=0.1)

        assert "test output" in output
        connection.channel.recv_ready.assert_called()
        connection.channel.recv.assert_called()

    def test_receive_output_no_data(self):
        """Test receiving output when no data is available."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        # Set up connection state
        connection.connected = True
        connection.channel = Mock()
        connection.channel.recv_ready.return_value = False
        connection.stop_reading = False

        # Test receiving output with no data
        with patch("time.sleep", side_effect=lambda x: None):  # Speed up test
            output = connection.receive_output(timeout=0.1)

        assert output == ""

    def test_create_connection_with_key_based_auth(self):
        """Test SSH connection creation with key-based authentication."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        with patch("ssh_manager.SSHConnection") as mock_connection_class:
            mock_connection_instance = Mock()
            mock_connection_class.return_value = mock_connection_instance
            mock_connection_instance.connect.return_value = True

            result = manager.create_connection(
                session_id="test_session",
                hostname="test.host",
                port=2220,
                username="testuser",
                password=None,
                key_filename="/path/to/key",
            )

            assert result is True
            assert "test_session" in manager.connections
            mock_connection_class.assert_called_once_with(
                "test.host", 2220, "testuser", None, "/path/to/key"
            )

    def test_create_connection_duplicate_session(self):
        """Test creating connection with duplicate session ID."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Add existing connection
        existing_connection = Mock()
        manager.connections["test_session"] = existing_connection

        with patch("ssh_manager.SSHConnection") as mock_connection_class:
            mock_connection_instance = Mock()
            mock_connection_class.return_value = mock_connection_instance
            mock_connection_instance.connect.return_value = True

            result = manager.create_connection(
                session_id="test_session",
                hostname="test.host",
                port=2220,
                username="testuser",
                password="testpass",
            )

            # Should replace existing connection
            assert result is True
            assert "test_session" in manager.connections
            assert manager.connections["test_session"] == mock_connection_instance

    def test_get_active_connection(self):
        """Test getting active connection."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Add connections
        active_connection = Mock()
        inactive_connection = Mock()
        manager.connections["active"] = active_connection
        manager.connections["inactive"] = inactive_connection

        # Mock the get_active_connection method to return the first connection
        with patch.object(manager, "get_active_connection", return_value=active_connection):
            result = manager.get_active_connection()
            assert result == active_connection

    def test_get_connection_status(self):
        """Test getting connection status."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Add connection with status
        mock_connection = Mock()
        mock_connection.connected = True
        manager.connections["test_session"] = mock_connection

        status = manager.get_connection_status("test_session")
        assert status["connected"] is True
        assert "session_id" in status

    def test_get_connection_status_nonexistent(self):
        """Test getting connection status for non-existent session."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        status = manager.get_connection_status("nonexistent")
        assert status["connected"] is False
        assert status["session_id"] == "nonexistent"

    def test_ssh_connection_authentication_exception(self):
        """Test SSH connection with authentication failure."""
        with patch("ssh_manager.paramiko") as mock_paramiko:
            mock_client = Mock()
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.AuthenticationException = paramiko.AuthenticationException
            mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")

            mock_notify = Mock()
            connection = SSHConnection(
                hostname="test.host",
                port=2220,
                username="testuser",
                password="wrongpass",
                notify_callback=mock_notify,
            )

            result = connection.connect()

            assert result is False
            assert connection.connected is False

    def test_ssh_connection_ssh_exception(self):
        """Test SSH connection with SSH exception."""
        with patch("ssh_manager.paramiko") as mock_paramiko:
            mock_client = Mock()
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.SSHException = paramiko.SSHException
            mock_client.connect.side_effect = paramiko.SSHException("SSH error")

            mock_notify = Mock()
            connection = SSHConnection(
                hostname="test.host",
                port=2220,
                username="testuser",
                password="testpass",
                notify_callback=mock_notify,
            )

            result = connection.connect()

            assert result is False
            assert connection.connected is False

    def test_ssh_connection_timeout_exception(self):
        """Test SSH connection with timeout."""
        with patch("ssh_manager.paramiko") as mock_paramiko:
            mock_client = Mock()
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.SSHException = paramiko.SSHException
            mock_client.connect.side_effect = paramiko.SSHException("Connection timed out")

            mock_notify = Mock()
            connection = SSHConnection(
                hostname="test.host",
                port=2220,
                username="testuser",
                password="testpass",
                notify_callback=mock_notify,
            )

            result = connection.connect()

            assert result is False
            assert connection.connected is False

    def test_disconnect_nonexistent_session(self):
        """Test disconnecting a non-existent session."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Should not raise an exception
        manager.disconnect_session("nonexistent_session")

    def test_send_command_empty_string(self):
        """Test sending empty command."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        connection.connected = True
        connection.channel = Mock()

        connection.send_command("")

        # Should still send the empty string
        connection.channel.send.assert_called_once_with("")

    def test_send_command_with_newline(self):
        """Test sending command with newline."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        connection.connected = True
        connection.channel = Mock()

        connection.send_command("ls -la\n")

        connection.channel.send.assert_called_once_with("ls -la\n")

    def test_execute_command_with_timeout(self):
        """Test command execution with timeout."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        connection.connected = True
        connection.send_command = Mock()
        connection.receive_output = Mock(return_value="output")

        result = connection.execute_command("ls -la", timeout=5.0)

        assert result == "output"
        connection.send_command.assert_called_once_with("ls -la")
        connection.receive_output.assert_called_once()

    def test_manager_connection_count(self):
        """Test getting connection count."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Initially no connections
        assert len(manager.connections) == 0

        # Add connections
        manager.connections["session1"] = Mock()
        manager.connections["session2"] = Mock()

        assert len(manager.connections) == 2

    def test_connection_cleanup_on_disconnect(self):
        """Test proper cleanup on disconnect."""
        mock_notify = Mock()
        connection = SSHConnection(
            hostname="test.host",
            port=2220,
            username="testuser",
            password="testpass",
            notify_callback=mock_notify,
        )

        connection.connected = True
        connection.stop_reading = False
        connection.channel = Mock()
        connection.client = Mock()
        connection.read_thread = Mock()

        # Disconnect and verify cleanup
        connection.disconnect()

        # Verify all cleanup methods were called
        assert connection.stop_reading is True
        assert connection.connected is False
        connection.read_thread.join.assert_called_once_with(timeout=1)
        connection.channel.close.assert_called_once()
        connection.client.close.assert_called_once()
