"""Unit tests for the main application module."""

import os
import sys
from unittest.mock import Mock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import BanditCLIApp, ConnectionStatus


class TestBanditCLIApp:
    """Test cases for the BanditCLIApp class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_notify = Mock()

    def test_app_initialization(self):
        """Test BanditCLIApp initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            assert app.title == "BanditCLI - OverTheWire Bandit Wargame Assistant"
            assert hasattr(app, "ssh_manager")
            assert hasattr(app, "level_info")
            assert hasattr(app, "ai_mentor")
            assert hasattr(app, "config_manager")
            assert hasattr(app, "command_history")
            assert hasattr(app, "session_manager")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_app_components_creation(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test that all app components are created properly."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            BanditCLIApp()

            # Verify all components were instantiated
            mock_ssh_manager.assert_called_once()
            mock_level_info.assert_called_once()
            mock_ai_mentor.assert_called_once()
            mock_config_manager.assert_called_once()
            mock_command_history.assert_called_once()
            mock_session_manager.assert_called_once()

    def test_compose_ui(self):
        """Test UI composition."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Test that compose method returns widgets
            widgets = list(app.compose())

            # Should contain main UI components
            assert len(widgets) > 0

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_on_mount(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test app on_mount lifecycle method."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock the query_one method
            app.query_one = Mock()

            # Call on_mount
            app.on_mount()

            # Verify notifications were set up
            assert hasattr(app, "ssh_manager")
            assert hasattr(app, "level_info")
            assert hasattr(app, "ai_mentor")

    def test_connection_status_widget(self):
        """Test ConnectionStatus widget."""
        connection_status = ConnectionStatus()

        # Test initial state
        assert connection_status.renderable is None

    def test_connection_status_update(self):
        """Test ConnectionStatus widget updates."""
        connection_status = ConnectionStatus()

        # Test update method
        connection_status.update("Connected", "success")

        # Should have updated content
        assert connection_status.renderable is not None

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ssh_tab_functionality(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test SSH tab functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock SSH manager methods
            mock_ssh_instance = Mock()
            mock_ssh_manager.return_value = mock_ssh_instance

            # Test SSH connection inputs
            assert hasattr(app, "ssh_host_input")
            assert hasattr(app, "ssh_port_input")
            assert hasattr(app, "ssh_username_input")
            assert hasattr(app, "ssh_password_input")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_level_info_tab_functionality(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test Level Info tab functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock level info methods
            mock_level_instance = Mock()
            mock_level_instance.get_available_levels.return_value = [0, 1, 2]
            mock_level_info.return_value = mock_level_instance

            # Test level selection
            assert hasattr(app, "level_select")
            assert hasattr(app, "level_info_display")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ai_mentor_tab_functionality(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test AI Mentor tab functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock AI mentor methods
            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_mentor.return_value = mock_ai_instance

            # Test AI mentor interface
            assert hasattr(app, "ai_input")
            assert hasattr(app, "ai_response_display")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ssh_connection_handling(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test SSH connection handling."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock successful SSH connection
            mock_ssh_instance = Mock()
            mock_ssh_instance.create_connection.return_value = True
            mock_ssh_manager.return_value = mock_ssh_instance

            # Mock UI inputs
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "bandit.labs.overthewire.org"
            app.ssh_port_input = Mock()
            app.ssh_port_input.value = "2220"
            app.ssh_username_input = Mock()
            app.ssh_username_input.value = "bandit0"
            app.ssh_password_input = Mock()
            app.ssh_password_input.value = "bandit0"

            # Test connection button press
            with patch.object(app, "notify"):
                app.action_connect_ssh()

                # Should attempt to create connection
                mock_ssh_instance.create_connection.assert_called_once()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ssh_connection_failure(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test SSH connection failure handling."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock failed SSH connection
            mock_ssh_instance = Mock()
            mock_ssh_instance.create_connection.return_value = False
            mock_ssh_manager.return_value = mock_ssh_instance

            # Mock UI inputs
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "invalid.host"
            app.ssh_port_input = Mock()
            app.ssh_port_input.value = "2220"
            app.ssh_username_input = Mock()
            app.ssh_username_input.value = "invalid"
            app.ssh_password_input = Mock()
            app.ssh_password_input.value = "invalid"

            # Test connection button press with failure
            with patch.object(app, "notify") as mock_notify:
                app.action_connect_ssh()

                # Should show error notification
                mock_notify.assert_called()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_level_selection(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test level selection functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock level info
            mock_level_instance = Mock()
            mock_level_instance.get_available_levels.return_value = [0, 1, 2]
            mock_level_instance.format_level_info.return_value = "Level 0 info"
            mock_level_info.return_value = mock_level_instance

            # Mock UI components
            app.level_select = Mock()
            app.level_select.value = "0"
            app.level_info_display = Mock()

            # Test level selection
            with patch.object(app, "action_show_level_info"):
                app.action_show_level_info()

                # Should update level info display
                mock_level_instance.format_level_info.assert_called_once_with(0)

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ai_mentor_interaction(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test AI mentor interaction."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock AI mentor
            mock_ai_instance = Mock()
            mock_ai_instance.disabled = False
            mock_ai_instance.get_response.return_value = iter(["AI", " ", "response"])
            mock_ai_mentor.return_value = mock_ai_instance

            # Mock UI components
            app.ai_input = Mock()
            app.ai_input.value = "Help me with level 0"
            app.ai_response_display = Mock()
            app.current_level = 0

            # Test AI interaction
            with patch.object(app, "action_ask_ai"):
                app.action_ask_ai()

                # Should call AI mentor
                mock_ai_instance.get_response.assert_called_once()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_ai_mentor_disabled(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test AI mentor interaction when disabled."""
        with patch.dict(os.environ, {}, clear=True):  # No API key
            app = BanditCLIApp()

            # Mock AI mentor as disabled
            mock_ai_instance = Mock()
            mock_ai_instance.disabled = True
            mock_ai_mentor.return_value = mock_ai_instance

            # Mock UI components
            app.ai_input = Mock()
            app.ai_input.value = "Help me"
            app.ai_response_display = Mock()

            # Test AI interaction when disabled
            with patch.object(app, "notify") as mock_notify:
                app.action_ask_ai()

                # Should show disabled message
                mock_notify.assert_called()

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_terminal_command_execution(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test terminal command execution."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock SSH connection
            mock_ssh_instance = Mock()
            mock_connection = Mock()
            mock_connection.execute_command.return_value = "command output"
            mock_ssh_instance.get_active_connection.return_value = mock_connection
            mock_ssh_manager.return_value = mock_ssh_instance

            # Mock terminal UI
            app.terminal_input = Mock()
            app.terminal_input.value = "ls -la"
            app.terminal_output = Mock()

            # Test command execution
            with patch.object(app, "action_execute_command"):
                app.action_execute_command()

                # Should execute command via SSH
                mock_connection.execute_command.assert_called_once_with("ls -la")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_terminal_no_connection(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test terminal command execution without SSH connection."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock no active SSH connection
            mock_ssh_instance = Mock()
            mock_ssh_instance.get_active_connection.return_value = None
            mock_ssh_manager.return_value = mock_ssh_instance

            # Mock terminal UI
            app.terminal_input = Mock()
            app.terminal_input.value = "ls -la"
            app.terminal_output = Mock()

            # Test command execution without connection
            with patch.object(app, "notify") as mock_notify:
                app.action_execute_command()

                # Should show error message
                mock_notify.assert_called()

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
            app = BanditCLIApp()

            # Mock command history
            mock_history_instance = Mock()
            mock_history_instance.add_command.return_value = None
            mock_history_instance.get_recent_commands.return_value = ["ls", "pwd"]
            mock_command_history.return_value = mock_history_instance

            # Test command history usage
            assert app.command_history == mock_history_instance

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_session_management(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test session management integration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock session manager
            mock_session_instance = Mock()
            mock_session_instance.save_session.return_value = None
            mock_session_instance.load_session.return_value = None
            mock_session_manager.return_value = mock_session_instance

            # Test session manager usage
            assert app.session_manager == mock_session_instance

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_config_management(
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
            app = BanditCLIApp()

            # Mock config manager
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = "config_value"
            mock_config_instance.set.return_value = None
            mock_config_manager.return_value = mock_config_instance

            # Test config manager usage
            assert app.config_manager == mock_config_instance

    def test_app_key_bindings(self):
        """Test application key bindings."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Test that key bindings are defined
            assert hasattr(app, "action_connect_ssh")
            assert hasattr(app, "action_show_level_info")
            assert hasattr(app, "action_ask_ai")
            assert hasattr(app, "action_execute_command")

    @patch("src.main.BanditAIMentor")
    @patch("src.main.BanditLevelInfo")
    @patch("src.main.SSHManager")
    @patch("src.main.ConfigManager")
    @patch("src.main.CommandHistory")
    @patch("src.main.SessionManager")
    def test_error_handling(
        self,
        mock_session_manager,
        mock_command_history,
        mock_config_manager,
        mock_ssh_manager,
        mock_level_info,
        mock_ai_mentor,
    ):
        """Test error handling in the application."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Mock component that raises an exception
            mock_ssh_instance = Mock()
            mock_ssh_instance.create_connection.side_effect = Exception("Connection error")
            mock_ssh_manager.return_value = mock_ssh_instance

            # Mock UI inputs
            app.ssh_host_input = Mock()
            app.ssh_host_input.value = "test.host"

            # Test error handling
            with patch.object(app, "notify") as mock_notify:
                try:
                    app.action_connect_ssh()
                except Exception:
                    pass  # Expected to be handled

                # Should show error notification
                mock_notify.assert_called()

    def test_app_without_api_key(self):
        """Test app initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            app = BanditCLIApp()

            # App should still initialize but AI mentor should be disabled
            assert app.ai_mentor.disabled is True

    def test_app_version_display(self):
        """Test app version display."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            app = BanditCLIApp()

            # Should have version information
            assert hasattr(app, "title")
            assert "BanditCLI" in app.title
