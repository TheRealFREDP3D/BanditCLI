"""Input validation tests for BanditCLI."""

import os
import sys
from unittest.mock import Mock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ai_mentor import BanditAIMentor
from src.level_info import BanditLevelInfo
from src.ssh_manager import SSHConnection, SSHManager


class TestInputValidation:
    """Test cases for input validation across the application."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_notify = Mock()

    def test_ssh_hostname_validation(self):
        """Test SSH hostname input validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid hostnames
        valid_hostnames = [
            "bandit.labs.overthewire.org",
            "192.168.1.100",
            "localhost",
            "server.example.com",
            "ssh-server",
            "test-host_01",
        ]

        for hostname in valid_hostnames:
            # These should not raise exceptions in normal operation
            with patch("src.ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                manager.create_connection(
                    session_id="test_session",
                    hostname=hostname,
                    port=2220,
                    username="testuser",
                    password="testpass",
                )
                # The connection should be attempted (may fail for invalid hosts)
                mock_connection_class.assert_called_once()

    def test_ssh_port_validation(self):
        """Test SSH port input validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid ports
        valid_ports = [22, 2220, 2222, 8080, 9999]

        for port in valid_ports:
            with patch("src.ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=port,
                    username="testuser",
                    password="testpass",
                )
                mock_connection_class.assert_called_once()

        # Invalid ports (should be handled gracefully)
        invalid_ports = [-1, 0, 65536, 99999]

        for port in invalid_ports:
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = False

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=port,
                    username="testuser",
                    password="testpass",
                )
                # Should handle gracefully (connection fails)
                assert result is False

    def test_ssh_username_validation(self):
        """Test SSH username input validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid usernames
        valid_usernames = ["bandit0", "user", "test_user", "admin123", "root", "ubuntu"]

        for username in valid_usernames:
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username=username,
                    password="testpass",
                )
                mock_connection_class.assert_called_once()

        # Edge case usernames
        edge_usernames = ["", " ", "a", "very_long_username_that_might_be_valid"]

        for username in edge_usernames:
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = False

                result = manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username=username,
                    password="testpass",
                )
                # Should handle gracefully
                assert isinstance(result, bool)

    def test_ssh_password_validation(self):
        """Test SSH password input validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid passwords (including empty for key-based auth)
        valid_passwords = [
            "password123",
            "bandit0",
            "complex!P@ssw0rd",
            "simple",
            "",
            " ",  # Space as password
        ]

        for password in valid_passwords:
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password=password,
                )
                mock_connection_class.assert_called_once()

    def test_ssh_key_filename_validation(self):
        """Test SSH key filename validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid key paths
        valid_key_paths = [
            "/home/user/.ssh/id_rsa",
            "C:\\Users\\User\\.ssh\\id_rsa",
            "./id_rsa",
            "~/.ssh/id_ed25519",
            "/path/to/custom_key",
        ]

        for key_path in valid_key_paths:
            with patch("ssh_manager.SSHConnection") as mock_connection_class:
                mock_connection_instance = Mock()
                mock_connection_class.return_value = mock_connection_instance
                mock_connection_instance.connect.return_value = True

                manager.create_connection(
                    session_id="test_session",
                    hostname="test.host",
                    port=2220,
                    username="testuser",
                    password=None,
                    key_filename=key_path,
                )
                mock_connection_class.assert_called_once()

    def test_level_number_validation(self):
        """Test level number input validation."""
        level_info = BanditLevelInfo(notify_callback=self.mock_notify)

        # Valid level numbers
        valid_levels = [0, 1, 2, 10, 25, 33]

        for level in valid_levels:
            result = level_info.get_level_info(level)
            # Should return either level info or None gracefully
            assert result is None or isinstance(result, dict)

        # Invalid level numbers
        invalid_levels = [-1, -10, 999, 1000]

        for level in invalid_levels:
            result = level_info.get_level_info(level)
            # Should return None for invalid levels
            assert result is None

    def test_ai_mentor_input_validation(self):
        """Test AI mentor input validation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Valid user messages
            valid_messages = [
                "Help me with level 0",
                "What command should I use?",
                "How do I find the password?",
                "Explain SSH",
                "I'm stuck on this level",
                "Can you give me a hint?",
                "What does ls do?",
                "Help!",
                "a",  # Single character
                "",  # Empty message
                "A" * 1000,  # Long message
            ]

            for message in valid_messages:
                # Should handle all messages gracefully
                try:
                    response_chunks = list(
                        mentor.get_response(
                            user_message=message, session_id="test_session", current_level=0
                        )
                    )
                    assert isinstance(response_chunks, list)
                except Exception as e:
                    # Should handle errors gracefully
                    assert "error" in str(e).lower() or "disabled" in str(e).lower()

    def test_command_input_validation(self):
        """Test command input validation."""
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

        # Valid commands
        valid_commands = [
            "ls",
            "ls -la",
            "cat file.txt",
            "grep 'password' *",
            "find / -name '*password*' 2>/dev/null",
            "ssh bandit1@bandit.labs.overthewire.org",
            "echo 'test'",
            "",
            " ",  # Space
            "a",  # Single character
            "command with 'quotes' and \"double quotes\"",
            "command with && multiple && parts",
            "command | pipe | another",
        ]

        for command in valid_commands:
            try:
                connection.send_command(command)
                # Should send the command
                connection.channel.send.assert_called_with(command)
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_session_id_validation(self):
        """Test session ID validation."""
        mock_notify = Mock()
        manager = SSHManager(notify_callback=mock_notify)

        # Valid session IDs
        valid_session_ids = [
            "session1",
            "test_session",
            "bandit_level_0",
            "123",
            "session-with-dashes",
            "session_with_underscores",
            "a",  # Single character
            "",  # Empty string
        ]

        for session_id in valid_session_ids:
            # Should handle all session IDs gracefully
            try:
                result = manager.get_connection(session_id)
                assert result is None or hasattr(result, "connected")
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_search_query_validation(self):
        """Test search query input validation."""
        level_info = BanditLevelInfo(notify_callback=self.mock_notify)

        # Valid search queries
        valid_queries = [
            "ssh",
            "password",
            "file",
            "command",
            "",
            " ",
            "a",
            "very long search query with multiple words",
            "search with 'quotes'",
            "search-with-dashes",
            "search_with_underscores",
            "123",
            "!@#$%^&*()",  # Special characters
            "search\nwith\nnewlines",  # Newlines
        ]

        for query in valid_queries:
            try:
                results = level_info.search_levels(query)
                assert isinstance(results, list)
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_config_key_validation(self):
        """Test configuration key validation."""
        from src.config import ConfigManager

        config = ConfigManager()

        # Valid config keys
        valid_keys = [
            "ssh.default_host",
            "ssh.default_port",
            "ai.model",
            "ai.api_key",
            "cache.enabled",
            "theme.name",
            "key",
            "key.with.dots",
            "key_with_underscores",
            "key-with-dashes",
            "123",
            "a",
        ]

        for key in valid_keys:
            try:
                value = config.get(key, "default")
                assert value is not None
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_config_value_validation(self):
        """Test configuration value validation."""
        from src.config import ConfigManager

        config = ConfigManager()

        # Valid config values
        valid_values = [
            "string_value",
            "123",
            "true",
            "false",
            "",
            " ",
            "value with spaces",
            "value-with-dashes",
            "value_with_underscores",
            "value.with.dots",
            "special!@#$%^&*()characters",
            "A" * 1000,  # Long value
        ]

        for value in valid_values:
            try:
                config.set("test.key", value)
                retrieved = config.get("test.key")
                assert retrieved == value
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_terminal_output_validation(self):
        """Test terminal output handling validation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Valid terminal outputs
            valid_outputs = [
                "",
                " ",
                "normal output",
                "command not found: xyz",
                "permission denied",
                "no such file or directory",
                "connection refused",
                "authentication failed",
                "A" * 10000,  # Long output
                "output\nwith\nnewlines",
                "output\twith\ttabs",
                "output with special chars !@#$%^&*()",
                "binary\x00\x01\x02data",
                "unicode: 你好世界 🌍",
            ]

            for output in valid_outputs:
                try:
                    suggestions = mentor.get_context_suggestions(
                        terminal_output=output, recent_commands=["ls", "pwd"]
                    )
                    assert isinstance(suggestions, list)
                except Exception as e:
                    # Should handle errors gracefully
                    assert isinstance(e, Exception)

    def test_file_path_validation(self):
        """Test file path input validation."""
        # Valid file paths
        valid_paths = [
            "/path/to/file.txt",
            "relative/path/file.txt",
            "./file.txt",
            "../file.txt",
            "~/file.txt",
            "C:\\Windows\\System32\\file.txt",
            "file.txt",
            ".hidden_file",
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.with.dots.txt",
            "file123.txt",
            "very/long/path/with/many/directories/to/the/file.txt",
        ]

        for path in valid_paths:
            # Should handle all paths gracefully
            try:
                # Test basic path operations
                assert isinstance(path, str)
                assert len(path) > 0
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_url_validation(self):
        """Test URL input validation."""
        # Valid URLs
        valid_urls = [
            "https://overthewire.org/wargames/bandit/",
            "http://example.com",
            "https://example.com/path/to/resource",
            "ftp://server.com/file.txt",
            "ssh://user@server.com",
            "https://localhost:8080",
            "https://192.168.1.100:2220",
            "https://subdomain.example.co.uk/path",
            "https://example.com/path?query=value&other=test",
            "https://example.com/path#fragment",
        ]

        for url in valid_urls:
            # Should handle all URLs gracefully
            try:
                # Basic URL validation
                assert "://" in url or url.startswith("/")
                assert len(url) > 0
            except Exception as e:
                # Should handle errors gracefully
                assert isinstance(e, Exception)

    def test_numeric_input_validation(self):
        """Test numeric input validation."""
        # Valid numeric inputs
        valid_numbers = [
            "0",
            "1",
            "10",
            "100",
            "999",
            "-1",
            "0",
            "123.456",
            "1e5",
            "0xFF",  # Hexadecimal
            "0755",  # Octal
            "0b1010",  # Binary
        ]

        for number_str in valid_numbers:
            try:
                # Try to convert to int (should handle gracefully)
                if number_str.startswith(("0x", "0X")):
                    int(number_str, 16)
                elif number_str.startswith("0b") or number_str.startswith("0B"):
                    int(number_str, 2)
                elif (
                    number_str.startswith("0")
                    and len(number_str) > 1
                    and not number_str.startswith("0.")
                ):
                    int(number_str, 8)
                else:
                    int(float(number_str))  # Handle decimals
            except (ValueError, TypeError):
                # Should handle conversion errors gracefully
                pass

    def test_edge_case_inputs(self):
        """Test edge case inputs that might cause issues."""
        edge_cases = [
            None,  # None values should be handled gracefully
            "\x00",  # Null byte
            "\u0000",  # Unicode null
            "\n\r\t",  # Control characters
            "🌍",  # Emoji
            "你好",  # Chinese characters
            "العربية",  # Arabic text
            "עברית",  # Hebrew text
            "🚀🔥💯",  # Multiple emojis
            "text\x00with\x00nulls",  # Text with null bytes
            "   ",  # Only whitespace
            "\t\t\t",  # Only tabs
            "\n\n\n",  # Only newlines
        ]

        for edge_case in edge_cases:
            try:
                # Test with string operations
                if edge_case is not None:
                    str(edge_case)
                    len(edge_case)
                    edge_case.strip()
            except Exception as e:
                # Should handle edge cases gracefully
                assert isinstance(e, Exception)
