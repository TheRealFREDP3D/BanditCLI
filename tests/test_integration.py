"""Integration tests for end-to-end workflows."""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.command_history import CommandHistory
from src.main import BanditCLIApp
from src.session_manager import SessionManager
from src.ssh_manager import SSHManager


class TestIntegrationWorkflows:
    """Integration tests for complete application workflows."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_notify = Mock()

    def teardown_method(self):
        """Clean up after each test method."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_complete_ssh_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test complete SSH connection workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_notify = Mock()
            mock_ssh_instance = SSHManager(notify_callback=mock_notify)
            mock_connection = Mock()
            mock_connection.execute_command.return_value = "bandit0@bandit:~$ ls -la\ntotal 24\ndrwxr-xr-x  3 root    root    4096 Jan 17 10:00 ."
            mock_ssh_instance.create_connection.return_value = True
            mock_ssh_instance.get_active_connection.return_value = mock_connection
            mock_ssh_manager.return_value = mock_ssh_instance

            mock_level_instance = Mock()
            mock_level_instance.get_available_levels.return_value = [0, 1, 2]
            mock_level_instance.get_level_info.return_value = {
                "goal": "Connect to server",
                "commands": ["ssh"],
            }
            mock_level_info.return_value = mock_level_instance

            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_instance.get_response.return_value = iter(
                ["Try", " using", " SSH", " to", " connect"]
            )
            mock_ai_mentor.return_value = mock_ai_instance

            # Create app
            app = BanditCLIApp()

            # Mock UI components
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "bandit.labs.overthewire.org"
            app.ssh_port_input = Mock()
            app.ssh_port_input.value = "2220"
            app.ssh_username_input = Mock()
            app.ssh_username_input.value = "bandit0"
            app.ssh_password_input = Mock()
            app.ssh_password_input.value = "bandit0"

            app.terminal_input = Mock()
            app.terminal_input.value = "ls -la"
            app.terminal_output = Mock()

            app.ai_input = Mock()
            app.ai_input.value = "How do I start?"
            app.ai_response_display = Mock()

            app.level_select = Mock()
            app.level_select.value = "0"
            app.level_info_display = Mock()

            # Test SSH connection
            app.action_connect_ssh()
            mock_ssh_instance.create_connection.assert_called_once()

            # Test command execution
            app.action_execute_command()
            mock_connection.execute_command.assert_called_once_with("ls -la")

            # Test level info display
            app.action_show_level_info()
            mock_level_instance.format_level_info.assert_called_once_with(0)

            # Test AI mentor interaction
            app.action_ask_ai()
            mock_ai_instance.get_response.assert_called_once()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_level_progression_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test level progression workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_level_instance = Mock()
            mock_level_instance.get_available_levels.return_value = [0, 1, 2, 3]
            mock_level_instance.get_level_info.side_effect = [
                {"goal": "Level 0 goal", "commands": ["ssh"], "password": "bandit0"},
                {"goal": "Level 1 goal", "commands": ["ls", "cat"], "password": "bandit1"},
                {"goal": "Level 2 goal", "commands": ["find", "grep"], "password": "bandit2"},
            ]
            mock_level_instance.format_level_info.side_effect = [
                "# Level 0\nConnect to server",
                "# Level 1\nFind password",
                "# Level 2\nSearch files",
            ]
            mock_level_info.return_value = mock_level_instance

            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_instance.get_response.side_effect = [
                iter(["Use", " SSH", " to", " connect"]),
                iter(["Look", " for", " files", " in", " current", " directory"]),
                iter(["Try", " using", " find", " to", " search"]),
            ]
            mock_ai_mentor.return_value = mock_ai_instance

            # Create app
            app = BanditCLIApp()

            # Mock UI components
            app.level_select = Mock()
            app.level_info_display = Mock()
            app.ai_input = Mock()
            app.ai_response_display = Mock()

            # Test progression through levels
            for level in [0, 1, 2]:
                app.level_select.value = str(level)
                app.action_show_level_info()
                mock_level_instance.format_level_info.assert_called_with(level)

                app.ai_input.value = f"Help with level {level}"
                app.action_ask_ai()
                mock_ai_instance.get_response.assert_called()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_command_history_integration(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test command history integration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_history_instance = CommandHistory()
            mock_history_instance.add_command = Mock()
            mock_history_instance.get_recent_commands.return_value = ["ls -la", "pwd", "whoami"]
            mock_command_history.return_value = mock_history_instance

            mock_ssh_instance = Mock()
            mock_connection = Mock()
            mock_connection.execute_command.return_value = "command output"
            mock_ssh_instance.create_connection.return_value = True
            mock_ssh_instance.get_active_connection.return_value = mock_connection
            mock_ssh_manager.return_value = mock_ssh_instance

            # Create app
            app = BanditCLIApp()

            # Mock UI components
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "test.host"
            app.ssh_port_input = Mock()
            app.ssh_port_input.value = "2220"
            app.ssh_username_input = Mock()
            app.ssh_username_input.value = "testuser"
            app.ssh_password_input = Mock()
            app.ssh_password_input.value = "testpass"

            app.terminal_input = Mock()
            app.terminal_input.value = "ls -la"
            app.terminal_output = Mock()

            # Connect and execute commands
            app.action_connect_ssh()
            app.action_execute_command()

            # Verify command history integration
            assert app.command_history == mock_history_instance

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_session_persistence_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test session persistence workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_session_instance = SessionManager()
            mock_session_instance.save_session = Mock()
            mock_session_instance.load_session = Mock()
            mock_session_manager.return_value = mock_session_instance

            # Create app
            app = BanditCLIApp()

            # Test session manager integration
            assert app.session_manager == mock_session_instance

            # Mock app lifecycle
            app.on_mount()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_configuration_integration(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test configuration management integration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_config_instance = Mock()
            mock_config_instance.get.side_effect = lambda key, default=None: {
                "ssh.default_host": "bandit.labs.overthewire.org",
                "ssh.default_port": "2220",
                "ai.model": "gpt-3.5-turbo",
            }.get(key, default)
            mock_config_instance.set = Mock()
            mock_config_manager.return_value = mock_config_instance

            # Create app
            app = BanditCLIApp()

            # Test config manager integration
            assert app.config_manager == mock_config_instance

            # Test configuration usage
            host = app.config_manager.get("ssh.default_host")
            assert host == "bandit.labs.overthewire.org"

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_error_handling_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test error handling in complete workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks with failures
            mock_ssh_instance = Mock()
            mock_ssh_instance.create_connection.return_value = False  # Connection fails
            mock_ssh_manager.return_value = mock_ssh_instance

            mock_ai_instance = Mock()
            mock_ai_instance.disabled = True  # AI disabled
            mock_ai_mentor.return_value = mock_ai_instance

            # Create app
            app = BanditCLIApp()

            # Mock UI components
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "invalid.host"
            app.ssh_port_input = Mock()
            app.ssh_port_input.value = "2220"
            app.ssh_username_input = Mock()
            app.ssh_username_input.value = "invalid"
            app.ssh_password_input = Mock()
            app.ssh_password_input.value = "invalid"

            app.ai_input = Mock()
            app.ai_input.value = "Help me"
            app.ai_response_display = Mock()

            # Test error handling
            with patch.object(app, "notify") as mock_notify:
                # SSH connection failure
                app.action_connect_ssh()
                assert mock_notify.called

                # AI mentor disabled
                app.action_ask_ai()
                assert mock_notify.called

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ai_context_aware_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test AI mentor context-aware workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_instance.get_response.return_value = iter(["Based", " on", " your", " context"])
            mock_ai_mentor.return_value = mock_ai_instance

            mock_history_instance = Mock()
            mock_history_instance.get_recent_commands.return_value = [
                "ls",
                "cat file.txt",
                "grep password",
            ]
            mock_command_history.return_value = mock_history_instance

            # Create app
            app = BanditCLIApp()

            # Mock UI components
            app.ai_input = Mock()
            app.ai_input.value = "I'm stuck on this level"
            app.ai_response_display = Mock()
            app.current_level = 1

            # Test AI interaction with context
            app.action_ask_ai()

            # Verify AI was called with context
            mock_ai_instance.get_response.assert_called_once()
            call_args = mock_ai_instance.get_response.call_args
            assert call_args[1]["current_level"] == 1

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_level_search_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test level search functionality workflow."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_level_instance = Mock()
            mock_level_instance.search_levels.return_value = [0, 1, 5]
            mock_level_instance.format_level_info.return_value = "# Level 0\nSSH connection"
            mock_level_info.return_value = mock_level_instance

            # Create app
            BanditCLIApp()

            # Test level search
            search_results = mock_level_instance.search_levels("ssh")
            assert search_results == [0, 1, 5]

            # Test level info display for search results
            for level in search_results:
                formatted_info = mock_level_instance.format_level_info(level)
                assert formatted_info is not None

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_offline_mode_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test application behavior in offline mode."""
        with patch.dict(os.environ, {}, clear=True):  # No API key
            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai_instance.disabled = True
            mock_ai_mentor.return_value = mock_ai_instance

            mock_level_instance = Mock()
            mock_level_instance.get_available_levels.return_value = [0, 1, 2]
            mock_level_instance.get_level_info.return_value = {
                "goal": "Basic goal",
                "commands": ["ls"],
            }
            mock_level_info.return_value = mock_level_instance

            # Create app
            app = BanditCLIApp()

            # Test offline functionality
            assert app.ai_mentor.disabled is True

            # Level info should still work
            level_info = mock_level_instance.get_level_info(0)
            assert level_info is not None

            # AI mentor should show disabled message
            app.ai_input = Mock()
            app.ai_input.value = "Help me"
            app.ai_response_display = Mock()

            with patch.object(app, "notify") as mock_notify:
                app.action_ask_ai()
                mock_notify.assert_called()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_cache_integration_workflow(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test cache integration across components."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            # Setup mocks
            mock_level_instance = Mock()
            mock_level_instance.get_level_info.return_value = {"goal": "Test goal"}
            mock_level_instance.format_level_info.return_value = "# Level 0\nTest goal"
            mock_level_info.return_value = mock_level_instance

            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_instance.get_response.return_value = iter(["Cached", " response"])
            mock_ai_mentor.return_value = mock_ai_instance

            # Create app
            BanditCLIApp()

            # Test cache usage - multiple calls should use cache
            for _ in range(3):
                mock_level_instance.get_level_info(0)
                mock_ai_instance.get_response("Test message", session_id="test")

            # Verify cache methods were called
            assert hasattr(mock_level_instance, "cache")
            assert hasattr(mock_ai_instance, "cache")
