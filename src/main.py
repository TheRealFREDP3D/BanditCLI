"""Main application module for BanditCLI.

This module contains the main Textual application class that provides a terminal
interface for the OverTheWire Bandit wargame. It includes SSH connection management,
AI mentor integration, and level information display.

The main class is BanditCLIApp, which extends Textual's App class and provides
three main tabs: Terminal, Level Info, and AI Mentor.
"""

# src/main.py
import asyncio
import os
import random
import re
import time
from contextlib import suppress
from typing import Any

from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Function, ValidationResult
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from src import __version__
from src.ai_mentor import BanditAIMentor
from src.command_history import CommandHistory
from src.config import ConfigManager
from src.level_info import BanditLevelInfo
from src.performance_monitor import get_performance_monitor, track_performance
from src.session_manager import SessionManager
from src.ssh_manager import SSHManager
from src.terminal_output import EnhancedTerminalOutput

# Load environment variables
load_dotenv()


class DeleteSessionModal(ModalScreen[bool]):
    """Modal screen for deleting sessions."""

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__()
        self.session_manager = session_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="delete_dialog"):
            yield Label("Select session to delete:", id="delete_label")

            # Get available sessions (excluding active one)
            active_session = self.session_manager.get_active_session()
            active_id = active_session.session_id if active_session else None

            options = []
            for session in self.session_manager.list_sessions():
                if session.session_id != active_id:
                    options.append(
                        (
                            f"{session.get_display_name()} (Level {session.current_level})",
                            session.session_id,
                        )
                    )

            if not options:
                yield Label("No other sessions available to delete.", id="no_sessions_label")
                yield Button("Cancel", variant="primary", id="cancel_delete")
            else:
                yield SelectionList(*options, id="session_list")
                with Horizontal(id="delete_buttons"):
                    yield Button("Cancel", variant="primary", id="cancel_delete")
                    yield Button("Delete Selected", variant="error", id="confirm_delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_delete":
            self.dismiss(False)
        elif event.button.id == "confirm_delete":
            selection_list = self.query_one(SelectionList)
            if not selection_list.selected:
                self.notify("Please select a session to delete", severity="warning")
                return

            # Delete selected sessions
            deleted_count = 0
            for session_id in selection_list.selected:
                if self.session_manager.delete_session(session_id):
                    deleted_count += 1

            self.app.notify(f"Deleted {deleted_count} session(s)", severity="information")
            self.dismiss(True)


class ConnectionStatus(Static):
    """A widget to display SSH connection status with visual indicator."""

    connected = reactive(False)

    def _get_status_text(self) -> str:
        """Get the status text based on connection state."""
        if self.connected:
            return "[green]●[/green] Connected"
        else:
            return "[red]●[/red] Disconnected"

    def on_mount(self) -> None:
        """Set initial status text on mount."""
        self.update(self._get_status_text())

    def watch_connected(self, connected: bool) -> None:
        """Watch for changes to connected state and update content."""
        self.update(self._get_status_text())


class VersionFooter(Widget):
    """A custom footer widget that displays version information alongside key bindings."""

    def compose(self) -> ComposeResult:
        """Compose the footer with version display and standard footer functionality."""
        with Horizontal():
            yield Label(f"v{__version__}", id="version-label")
            yield Footer()


def validate_username(value: str) -> ValidationResult:
    """Validate SSH username for security.

    Args:
        value: The username string to validate.

    Returns:
        ValidationResult: Success if valid, failure with message if invalid.
    """

    def validate_field(val: str, error_msg: str) -> ValidationResult:
        return ValidationResult.failure([Function(lambda v: v != val, error_msg)])

    if not value:
        return validate_field(value, "Username is required")

    # Check for dangerous characters that could lead to injection
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'", "\\"]
    if any(char in value for char in dangerous_chars):
        return validate_field(value, "Username contains invalid characters")

    # Length check
    if len(value) > 32:
        return validate_field(value, "Username too long (max 32 characters)")

    # Pattern check (allow alphanumeric, underscores, hyphens)
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        return validate_field(
            value, "Username can only contain letters, numbers, underscores, and hyphens"
        )

    return ValidationResult.success()


class BanditCLIApp(App):
    """A Textual app for the Bandit Wargame CLI.

    This is the main application class that provides a terminal interface for
    the OverTheWire Bandit wargame. It features SSH connectivity, an AI mentor
    for guidance, and comprehensive level information.

    Attributes:
        current_level (int): The current Bandit level being attempted.
        session_id (str): Session identifier for SSH connections.
        recent_commands (list): List of recently executed commands.
        terminal_output (str): Accumulated terminal output from SSH sessions.
        offline_mode (bool): Flag indicating if the app is in offline mode.
        ssh_manager (SSHManager): Manages SSH connections and sessions.
        level_info (BanditLevelInfo): Provides level information and hints.
        ai_mentor (BanditAIMentor): AI-powered mentor for guidance.
        ssh_connected (reactive): Reactive property for SSH connection status.
        loading (reactive): Reactive property for loading indicator status.
        ai_generating (reactive): Reactive property for AI response generation.
        CSS_PATH (str): Path to the CSS file for styling.
        BINDINGS (list): Keyboard shortcuts and their corresponding actions.
    """

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("1", "switch_tab('terminal')", "Terminal"),
        ("2", "switch_tab('session')", "Session"),
        ("3", "switch_tab('level')", "Level Info"),
        ("4", "switch_tab('mentor')", "AI Mentor"),
        ("c", "show_cache_stats", "Cache Stats"),
        ("ctrl+c", "cancel_operation", "Cancel"),
        ("ctrl+shift+c", "clear_cache", "Clear Cache"),
        ("?", "ask_about_last_output", "Ask AI about last output"),
        ("s", "show_session_info", "Session Info"),
        ("n", "new_session", "New Session"),
        ("w", "switch_session_dialog", "Switch Session"),
    ]

    def _notify_wrapper(self, message: str, severity: str) -> None:
        """Wrapper to convert callback signature to Textual notify signature.

        Args:
            message: The message to display.
            severity: The severity level of the message.
        """
        self.notify(message, severity=severity)

    def __init__(self) -> None:
        """Initialize the BanditCLI application.

        Sets up the application state, loads configuration, initializes
        managers for SSH, AI mentor, and level information, and configures
        reactive properties for UI state management.
        """
        super().__init__()

        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()

        # Initialize configuration manager with validation
        self.config = ConfigManager()

        # Validate configuration on startup
        self._validate_configuration()

        self.current_level = 0
        self.session_id = "default"
        self.recent_commands = []
        self.terminal_output = ""
        self.max_terminal_output_size = 50000  # Limit to ~50KB of terminal output
        self.offline_mode = False
        self.ssh_manager = SSHManager(notify_callback=self._notify_wrapper)
        self.level_info = BanditLevelInfo(notify_callback=self._notify_wrapper)
        self.ai_mentor = BanditAIMentor(notify_callback=self._notify_wrapper, config=self.config)
        self.command_history = CommandHistory()
        self.session_manager = SessionManager()
        self.ssh_connected = reactive(False)
        self.loading = reactive(False)
        self.ai_generating = reactive(False)
        self.current_input_buffer = ""

        # Watch for reactive property changes
        self.watch(self, "ssh_connected", self.watch_ssh_connected)
        self.watch(self, "loading", self.watch_loading)

    def _validate_configuration(self) -> None:
        """Validate configuration settings on startup.

        Checks critical configuration values and provides user feedback
        for any invalid or missing settings.
        """
        try:
            # Validate SSH configuration
            ssh_host = self.config.get("ssh.host")
            ssh_port = self.config.get("ssh.port")
            ssh_timeout = self.config.get("ssh.timeout")

            if not ssh_host or not isinstance(ssh_port, int) or not isinstance(ssh_timeout, int):
                self.notify(
                    "Warning: Invalid SSH configuration detected. Using defaults.",
                    severity="warning",
                )
                # Reset to defaults if invalid
                self.config.set("ssh.host", "bandit.labs.overthewire.org")
                self.config.set("ssh.port", 2220)
                self.config.set("ssh.timeout", 10)
                self.config.save_config()

            # Validate AI configuration
            ai_model = self.config.get("ai.model")
            if not ai_model:
                self.notify("Warning: No AI model configured. Using default.", severity="warning")
                self.config.set("ai.model", "gpt-3.5-turbo")
                self.config.save_config()

        except Exception as e:
            self.notify(f"Configuration validation error: {e}", severity="error")

    def watch_ssh_connected(self, connected: bool) -> None:
        """Called when the ssh_connected reactive property changes.

        Updates the UI state based on SSH connection status. Enables/disables
        buttons as appropriate, and updates the connection status indicator.

        Args:
            connected: Whether SSH is connected or not.
        """
        # Update buttons
        try:
            self.query_one("#ssh_connect", Button).disabled = connected
            self.query_one("#ssh_disconnect", Button).disabled = not connected
        except Exception:
            # Widgets might not be ready/mounted yet
            pass

        # Update connection status indicator
        try:
            connection_status = self.query_one("#connection_status", ConnectionStatus)
            connection_status.connected = connected
        except Exception:
            pass

        # Set focus to the terminal output if connected
        if connected:
            try:
                self.query_one("#terminal_output", EnhancedTerminalOutput).focus()
            except Exception:
                pass

    def watch_loading(self, loading: bool) -> None:
        """Called when the loading reactive property changes.

        Shows or hides all loading indicators in the UI based on the loading state.

        Args:
            loading: Whether the app is in a loading state.
        """
        for indicator in self.query(LoadingIndicator):
            indicator.display = loading

    def compose(self) -> ComposeResult:
        """Create child widgets for the app.

        Composes the main application layout with a header, tabbed content
        containing four tabs (Terminal, Session, Level Info, and AI Mentor), and a custom footer.

        Yields:
            Header: The application header.
            TabbedContent: Container for the four main tabs.
            VersionFooter: A custom footer with version display and key bindings.
        """
        yield Header()

        with TabbedContent(initial="terminal"):
            with TabPane("Terminal", id="terminal"):
                with Vertical():
                    yield from self.compose_terminal_view()
            with TabPane("Session", id="session"):
                yield from self.compose_session_view()
            with TabPane("Level Info", id="level"):
                yield from self.compose_level_view()
            with TabPane("AI Mentor", id="mentor"):
                yield from self.compose_mentor_view()

        yield VersionFooter()

    def compose_terminal_view(self) -> ComposeResult:
        """Compose the terminal view.

        Creates the terminal tab layout with only terminal output display
        and command input field, maximizing screen space for terminal usage.

        Yields:
            EnhancedTerminalOutput: Terminal output display.
            Input: Command input field for SSH interaction.
        """
        yield EnhancedTerminalOutput(id="terminal_output", read_only=True)
        with Horizontal(id="command-input-bar"):
            yield Input(placeholder="Enter command...", id="command_input")

    def compose_session_view(self) -> ComposeResult:
        """Compose the session management view.

        Creates the session tab layout with SSH connection controls and
        session management features.

        Yields:
            LoadingIndicator: Shows loading state.
            ConnectionStatus: Shows connection status with visual indicator.
            Various input widgets and buttons for SSH connection and session management.
        """
        with Vertical():
            yield LoadingIndicator()
            with Horizontal(id="connection-status-bar"):
                yield ConnectionStatus(id="connection_status")

            # SSH Connection Controls
            with Vertical(id="ssh-controls"):
                yield Label("[bold]SSH Connection[/bold]")
                with Horizontal():
                    yield Label("Username:", id="username-label")
                    yield Input(
                        placeholder="bandit0",
                        id="ssh_username",
                        validators=[Function(validate_username, "Invalid username")],
                    )
                    yield Label("Password:", id="password-label")
                    yield Input(placeholder="bandit0", id="ssh_password", password=True)
                with Horizontal():
                    yield Label("Port:", id="port-label")
                    yield Input(placeholder="2220", id="ssh_port")
                    yield Button("Connect", variant="primary", id="ssh_connect")
                    yield Button("Disconnect", variant="error", id="ssh_disconnect")

            # Session Management Controls
            with Horizontal(id="session-controls"):
                yield Label("Session:", id="session-label")
                yield Button("New Session", id="new_session")
                yield Button("Switch Session", id="switch_session")
                yield Button("Delete Session", id="delete_session", variant="error")
                yield Static(id="current_session_display")

    def compose_level_view(self) -> ComposeResult:
        """Compose the level information view.

        Creates the level info tab with a text area for displaying level
        information and navigation buttons for switching between levels.

        Yields:
            TextArea: Display area for level information.
            Buttons: Previous and Next level navigation.
        """
        with Vertical():
            yield TextArea(id="level_info", read_only=True)
            with Horizontal():
                yield Button("Previous Level", id="prev_level")
                yield Button("Next Level", id="next_level")

    def compose_mentor_view(self) -> ComposeResult:
        """Compose the AI mentor view.

        Creates the AI mentor tab with a chat interface for interacting with
        the AI mentor, including a loading indicator, message input, and
        conversation management controls.

        Yields:
            LoadingIndicator: Shows AI response generation state.
            TextArea: Chat interface display.
            Input and Button: Message input and send controls.
            Buttons: Conversation management controls.
        """
        with Vertical():
            yield LoadingIndicator()
            yield TextArea(id="mentor_chat", read_only=True)
            with Horizontal():
                yield Input(placeholder="Ask the AI mentor...", id="mentor_input")
                yield Button("Send", variant="primary", id="mentor_send")
            with Horizontal(id="conversation-controls"):
                yield Button("Clear History", id="clear_history", variant="error")
                yield Button("Export Chat", id="export_chat", variant="success")

    def on_mount(self) -> None:
        """Called when the app is mounted.

        Initializes the application state, sets the title and subtitle,
        updates level information, configures initial button states,
        and warms up the cache for frequently accessed levels.
        """
        self.title = "Bandit Wargame CLI"
        self.sub_title = f"A terminal interface for OverTheWire Bandit v{__version__}"

        # Initialize the level info
        self.update_level_info()
        # Initial state of buttons
        self.query_one("#ssh_disconnect", Button).disabled = True
        # Ensure loading indicators are hidden initially
        self.loading = False
        # Hide loading indicators explicitly
        for indicator in self.query(LoadingIndicator):
            indicator.display = False

        # Initialize session management
        self._initialize_session()

        # Run the welcome animation
        asyncio.create_task(self.run_welcome_animation())

        # Warm up cache for frequently accessed levels (0-5)
        asyncio.create_task(self._warm_up_cache())

    def on_unmount(self) -> None:
        """Called when the app is about to exit.

        Performs cleanup operations including cache cleanup.
        """
        try:
            # Clean up expired cache entries
            level_cleanup = self.level_info.cache.cleanup_expired()
            ai_cleanup = self.ai_mentor.cache.cleanup_expired()

            if level_cleanup > 0 or ai_cleanup > 0:
                self.notify(
                    f"Cleaned up {level_cleanup + ai_cleanup} expired cache entries on exit",
                    severity="information",
                )
        except Exception as e:
            # Don't fail the application exit
            self.notify(f"Cache cleanup failed on exit: {e}", severity="warning")

    async def _warm_up_cache(self) -> None:
        """Warm up cache for frequently accessed levels (0-5).

        Pre-loads level information for the most commonly accessed levels
        to improve performance during user interaction.
        """
        try:
            # Warm up levels 0-5 (most frequently accessed)
            for level in range(6):
                # Pre-load level info
                self.level_info.get_level_info(level)
                # Pre-load formatted level info
                self.level_info.format_level_info(level)

        except Exception as e:
            # Don't fail the application if cache warming fails
            self.notify(f"Cache warming failed: {e}", severity="warning")

    async def run_welcome_animation(self) -> None:
        """Displays the welcome animation with ASCII art and instructions."""
        terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)

        # False Server Loading
        loading_steps = [
            " [ init ] Connecting to OTW secure gateway...",
            " [ net  ] Establishing encrypted tunnel...",
            " [ auth ] Verifying handshake keys...",
            " [ load ] Loading Bandit wargame modules...",
            " [ ok   ] Connection established."
        ]

        for step in loading_steps:
            if self.ssh_connected:
                return
            terminal.append_text(step + "\n", scroll_to_bottom=False)
            await asyncio.sleep(0.4)

        await asyncio.sleep(0.5)

        # ASCII Art Title
        ascii_title = r"""
  ____                  _ _ _    ____ _     ___ 
 | __ )  __ _ _ __   __| (_) |_ / ___| |   |_ _|
 |  _ \ / _` | '_ \ / _` | | __| |   | |    | | 
 | |_) | (_| | | | | (_| | | |_| |___| |___ | | 
 |____/ \__,_|_| |_|\__,_|_|\__|\____|_____|___|
"""
        terminal.append_text(ascii_title + "\n", scroll_to_bottom=False)
        await asyncio.sleep(0.5)

        # Instructions
        instructions = [
            "\n",
            "HOW TO START:",
            "1. Read Level 0 directives in the Level Info tab",
            "2. Connect to the server in the Session tab",
            "3. Play the game by sending commands in the Terminal tab",
            "\n",
        ]

        for line in instructions:
            if self.ssh_connected:
                return
            terminal.append_text(line + "\n", scroll_to_bottom=False)
            await asyncio.sleep(0.1)

        terminal.scroll_to_bottom()

    @track_performance("update_level_info")
    def update_level_info(self) -> None:
        """Update the level information display.

        Refreshes the level info text area with formatted information for
        the current level.
        """
        level_info_text = self.level_info.format_level_info(self.current_level)
        level_info_widget = self.query_one("#level_info", TextArea)
        level_info_widget.load_text(level_info_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Routes button presses to their corresponding handler methods.

        Args:
            event: The button press event containing the button reference.
        """
        if event.button.id == "ssh_connect":
            self.connect_ssh()
        elif event.button.id == "ssh_disconnect":
            self.disconnect_ssh()
        elif event.button.id == "prev_level":
            self.previous_level()
        elif event.button.id == "next_level":
            self.next_level()
        elif event.button.id == "mentor_send":
            self.send_mentor_message()
        elif event.button.id == "clear_history":
            self.clear_conversation_history()
        elif event.button.id == "export_chat":
            self.export_conversation()
        elif event.button.id == "new_session":
            self.create_new_session()
        elif event.button.id == "switch_session":
            self.show_session_switch_dialog()
        elif event.button.id == "delete_session":
            self.show_delete_session_dialog()

    def on_key(self, event: Key) -> None:
        """Handle keyboard events including command history navigation.

        Handles SSH key forwarding when connected, command history navigation
        with up/down arrows, and other keyboard shortcuts.

        Args:
            event: The key event containing the pressed key information.
        """
        # Handle command history navigation when not connected to SSH
        if not self.ssh_connected:
            if event.key == "up":
                self._navigate_history_up()
                return
            elif event.key == "down":
                self._navigate_history_down()
                return

        # Only handle keyboard input when SSH is connected and we're on the terminal tab
        if not self.ssh_connected:
            return

        try:
            # Check if we're on the terminal tab
            tabbed = self.query_one(TabbedContent)
            if tabbed.active != "terminal":
                return
        except Exception:
            return

        # Don't capture keys that should be handled by the UI
        if event.key in ["ctrl+c", "ctrl+d", "ctrl+z", "escape"]:
            # Let these be handled by the system or other handlers
            return

        # Get the SSH connection and send the key
        if connection := self.ssh_manager.get_connection(self.session_id):
            # Handle special keys
            if event.key == "enter":
                connection.send_command("\n")
            elif event.key == "backspace":
                connection.send_command("\b")  # Backspace character
            elif event.key == "delete":
                connection.send_command("\x1b[3~")  # Delete character
            elif event.key == "left":
                connection.send_command("\x1b[D")  # Left arrow
            elif event.key == "right":
                connection.send_command("\x1b[C")  # Right arrow
            elif event.key == "up":
                connection.send_command("\x1b[A")  # Up arrow
            elif event.key == "down":
                connection.send_command("\x1b[B")  # Down arrow
            elif event.key == "home":
                connection.send_command("\x1b[H")  # Home
            elif event.key == "end":
                connection.send_command("\x1b[F")  # End
            elif event.key == "pageup":
                connection.send_command("\x1b[5~")  # Page up
            elif event.key == "pagedown":
                connection.send_command("\x1b[6~")  # Page down
            elif event.key == "tab":
                connection.send_command("\t")  # Tab
            elif event.character:
                # Regular character input
                connection.send_command(event.character)
                # Add to command history if it's a complete command (Enter key)
                if event.character == "\n":
                    # This would be handled by SSH output callback
                    pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission events.

        Routes input submissions to their corresponding handler methods
        based on the input field ID.

        Args:
            event: The input submission event containing the input reference.
        """
        if event.input.id == "mentor_input":
            self.send_mentor_message()
        elif event.input.id == "command_input":
            self.send_ssh_command()

    @track_performance("connect_ssh")
    def connect_ssh(self) -> None:
        """Connect to the SSH server with validation.

        Validates user input, establishes an SSH connection to the OverTheWire
        Bandit server, and sets up the output callback for terminal display.
        Handles connection errors and provides user feedback.

        Security Considerations:
            - Hostname validation prevents injection attacks (alphanumeric, dots, hyphens only)
            - Port validation ensures valid range (1-65535) and prevents port scanning
            - Timeout validation prevents resource exhaustion (1-300 seconds)
            - Input validation prevents malformed data from reaching SSH layer
            - Rate limiting prevents brute force attacks via SSHManager
            - Host key verification enabled by default to prevent MITM attacks
        """
        self.loading = True

        try:
            username_input = self.query_one("#ssh_username", Input)
            password_input = self.query_one("#ssh_password", Input)

            # Validate inputs
            username = username_input.value or ""
            password = password_input.value or ""

            # Use configuration values from ConfigManager
            hostname = self.config.get("ssh.host", "bandit.labs.overthewire.org")
            port = self.config.get("ssh.port", "2220")
            timeout = self.config.get("ssh.timeout", "10")

            # Check if inputs are valid
            if not username_input.validate(username):
                self._handle_error_and_stop_loading("Invalid username")
                return

            if not password:
                self._handle_error_and_stop_loading("Password is required")
                return

            # Validate hostname format to prevent injection attacks
            import re

            hostname_pattern = re.compile(r"^[a-zA-Z0-9.-]+$")
            if not hostname or not hostname_pattern.match(hostname):
                self._handle_error_and_stop_loading("Invalid hostname format")
                return

            # Prevent hostname injection attacks
            if ".." in hostname or hostname.startswith(".") or hostname.endswith("."):
                self._handle_error_and_stop_loading("Invalid hostname: potential injection attempt")
                return

            # Validate port format and range before conversion
            port_str = str(port) if not isinstance(port, str) else port
            if not port_str or not port_str.isdigit() or int(port_str) < 1 or int(port_str) > 65535:
                self._handle_error_and_stop_loading(
                    "Port must be a valid integer between 1 and 65535"
                )
                return

            # Validate timeout format and range
            timeout_str = str(timeout) if not isinstance(timeout, str) else timeout
            if not timeout_str or not timeout_str.isdigit():
                self._handle_error_and_stop_loading("Timeout must be a valid positive integer")
                return

            timeout_int = int(timeout)
            if timeout_int < 1 or timeout_int > 300:  # Reasonable range: 1 second to 5 minutes
                self._handle_error_and_stop_loading("Timeout must be between 1 and 300 seconds")
                return

            # Convert port to integer (already validated)
            port_int = int(port)

            # Attempt to connect with security settings
            start_time = time.perf_counter()

            # Default to secure host key verification for educational tool
            insecure_value = os.getenv("BANDIT_CLI_INSECURE", "").lower()
            verify_host_key = insecure_value not in ("true", "1", "yes")

            success = self.ssh_manager.create_connection(
                self.session_id,
                hostname,
                port_int,
                username,
                password,
                timeout=timeout_int,
                verify_host_key=verify_host_key,
            )

            # Track SSH connection performance
            connection_time_ms = (time.perf_counter() - start_time) * 1000
            self.performance_monitor.update_ssh_performance(connection_time_ms)

            if success:
                # Update session with connection details
                self.session_manager.update_session_connection(
                    self.session_id, hostname, port_int, username
                )

                # Set session as active
                self.session_manager.set_active_session(self.session_id)

                self.ssh_connected = True
                self.loading = False  # Ensure loading is stopped on success
                self.notify("SSH connection established", severity="information")
                # Set up the output callback
                if connection := self.ssh_manager.get_connection(self.session_id):
                    connection.set_output_callback(self.on_ssh_output)

                # Update session display
                self.update_session_display()
            else:
                self.notify(
                    "Failed to establish SSH connection. Please check your credentials, network connection, and ensure the Bandit server is accessible.",
                    severity="error",
                )
            self.loading = False

        except (ValueError, OSError, ConnectionError, TimeoutError) as e:
            # Log detailed error information
            self._log_error(f"SSH connection error: {type(e).__name__}: {e}")

            # Provide user-friendly error message
            user_message = self._get_user_friendly_error_message(str(e))

            self.notify(user_message, severity="error")
            self.loading = False
        except Exception as e:
            # Log detailed error information
            self._log_error(f"Unexpected SSH error: {type(e).__name__}: {e}")

            # Import traceback for detailed logging
            import traceback

            error_details = traceback.format_exc()
            self._log_error(f"Full traceback: {error_details}")

            # Provide user-friendly error message
            user_message = self._get_user_friendly_error_message(str(e))

            self.notify(user_message, severity="error")
            self.loading = False

    def disconnect_ssh(self) -> None:
        """Disconnect from the SSH server.

        Closes the SSH connection and updates the UI state to reflect
        the disconnected status.
        """
        self.ssh_manager.disconnect_session(self.session_id)
        self.ssh_connected = False
        self.notify("SSH connection closed", severity="information")

    def send_ssh_command(self) -> None:
        """Send a command from the command input field to the SSH connection.

        Retrieves the command from the command_input field, sends it to the
        active SSH connection, clears the input field, and adds the command
        to the history.
        """
        try:
            # Get the command input widget
            command_input = self.query_one("#command_input", Input)
            command = command_input.value.strip()

            # Only proceed if we have a command
            if not command:
                return

            # Support local 'clear' command
            if command.lower() == "clear":
                terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)
                terminal.clear()
                command_input.value = ""
                return

            if not self.ssh_connected:
                self.notify("Not connected to SSH. Please connect first.", severity="warning")
                return

            # Get the SSH connection
            connection = self.ssh_manager.get_connection(self.session_id)
            if not connection:
                self.notify("SSH connection lost", severity="error")
                self.ssh_connected = False
                return

            # Send the command with newline
            connection.send_command(command + "\n")

            # Add to command history
            self.command_history.add_command(command)

            # Clear the input field
            command_input.value = ""

            # Scroll terminal to bottom
            terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)
            terminal.scroll_to_bottom()

        except Exception as e:
            self.notify(f"Error sending command: {e}", severity="error")

    def on_ssh_output(self, data: str) -> None:
        """Handle SSH output data with memory optimization.

        Appends received SSH output to the enhanced terminal display with ANSI parsing,
        buffering, and auto-scrolling. Also tracks commands in history.
        Limits terminal_output size to prevent memory issues.

        Args:
            data: The output data received from the SSH connection.
        """
        # Add new data and enforce size limit
        self.terminal_output += data

        # Trim terminal_output if it exceeds maximum size
        if len(self.terminal_output) > self.max_terminal_output_size:
            # Keep only the most recent data (last 80% of max size)
            trim_size = int(self.max_terminal_output_size * 0.8)
            self.terminal_output = self.terminal_output[-trim_size:]

        # Use the enhanced terminal output widget
        try:
            terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)
            terminal.append_text(data, scroll_to_bottom=True)
        except Exception:
            # Fallback to regular TextArea if enhanced widget is not available
            terminal_output = self.query_one("#terminal_output", TextArea)
            terminal_output.insert(data)

        # Extract commands from output (simple heuristic - lines ending with $ or #)
        lines = data.split("\n")
        for line in lines:
            # Look for command prompts and extract commands
            if ("$ " in line or "# " in line) and len(line.strip()) > 2:
                # This might be a command output, look for the actual command
                parts = line.strip().split()
                if len(parts) > 1:
                    # Assume the first part after prompt is the command
                    cmd_start = line.find("$ ") if "$ " in line else line.find("# ")
                    if cmd_start != -1:
                        cmd = line[cmd_start + 2 :].strip()
                        if cmd and not cmd.startswith("["):  # Skip status messages
                            self.command_history.add_command(cmd)
                            # Update recent commands list
                            self.recent_commands.append(cmd)
                            if len(self.recent_commands) > 5:
                                self.recent_commands = self.recent_commands[-5:]

                            # Update session level if we detect level progression
                            self._detect_level_progression(cmd)

    def clear_conversation_history(self) -> None:
        """Clear conversation history for current session.

        Args:
            None
        """
        if self.session_id in self.ai_mentor.conversation_history:
            del self.ai_mentor.conversation_history[self.session_id]
            self.notify("Conversation history cleared", severity="information")

    def export_conversation(self) -> None:
        """Export conversation to markdown file.

        Creates a markdown file with the conversation history and level information.
        """
        try:
            import os
            from datetime import datetime

            if self.session_id not in self.ai_mentor.conversation_history:
                self.notify("No conversation history to export", severity="warning")
                return

            history = self.ai_mentor.conversation_history[self.session_id]
            if not history:
                self.notify("Empty conversation history", severity="warning")
                return

            # Create export filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bandit_cli_conversation_{timestamp}.md"
            export_path = os.path.expanduser(f"~/Documents/{filename}")

            # Build markdown content
            markdown_content = f"""# Bandit CLI Conversation Export\n\n**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n**Level:** {self.current_level}\n**Session:** {self.session_id}\n\n---\n\n## Conversation History\n\n"""

            for i, message in enumerate(history):
                role = message.get("role", "unknown").title()
                content = message.get("content", "")
                markdown_content += f"**{i + 1}. {role}:** {content}\n\n"

            # Write to file
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.notify(f"Conversation exported to {export_path}", severity="information")

        except Exception as e:
            self.notify(f"Failed to export conversation: {e}", severity="error")

    def _handle_mentor_response(self, message: str) -> None:
        """Handle AI mentor response generation.

        Streams AI mentor responses to the chat interface, handling both
        user messages and AI responses. Manages loading states and error
        handling for the AI interaction.

        Args:
            message: The user's message to the AI mentor.
        """
        try:
            mentor_chat = self.query_one("#mentor_chat", TextArea)
            current_text = mentor_chat.text or ""
            mentor_chat.load_text(f"{current_text}\nYou: {message}\nMentor: ")

            # Get AI response
            response_stream = self.ai_mentor.get_response(
                message,
                self.session_id,
                self.current_level,
                self.recent_commands,
                self.terminal_output,
            )

            # Stream response
            for chunk in response_stream:
                mentor_chat.insert(chunk)
                mentor_chat.move_cursor(
                    (mentor_chat.cursor_row, mentor_chat.cursor_column + len(chunk))
                )

        except Exception as e:
            self.notify(f"Error getting AI response: {e}", severity="error")
        finally:
            # Clear input
            mentor_input = self.query_one("#mentor_input", Input)
            mentor_input.value = ""
            self.loading = False
            self.ai_generating = False

    @track_performance("send_mentor_message")
    def send_mentor_message(self) -> None:
        """Send a message to the AI mentor.

        Validates the message, checks for offline mode, and initiates
        AI mentor response generation. Updates loading states accordingly.
        """
        # Check if we're in offline mode
        if self.offline_mode:
            self.notify("Cannot send messages to AI mentor in offline mode", severity="error")
            return

        mentor_input = self.query_one("#mentor_input", Input)
        message = mentor_input.value.strip()

        if not message:
            return

        self.ai_generating = True
        self.loading = True

        self._handle_mentor_response(message)

    def previous_level(self) -> None:
        """Go to the previous level.

        Decrements the current level if not already at level 0 and
        updates the level information display.
        """
        if self.current_level > 0:
            self.current_level -= 1
            self.update_level_info()
            self.notify(f"Switched to Level {self.current_level}", severity="information")

    def next_level(self) -> None:
        """Go to the next level.

        Increments the current level if not already at the maximum
        available level and updates the level information display.
        """
        max_level = max([int(k) for k in self.level_info.levels_data.keys()] + [0])
        if self.current_level < max_level:
            self.current_level += 1
            self.update_level_info()
            self.notify(f"Switched to Level {self.current_level}", severity="information")
        else:
            self.notify("Already at the highest available level", severity="warning")

    def action_show_cache_stats(self) -> None:
        """Display cache statistics."""
        level_stats = self.level_info.cache.get_stats()
        ai_stats = self.ai_mentor.get_cache_stats()
        perf_metrics = self.performance_monitor.get_metrics()

        stats_message = f"""Cache & Performance Statistics:

Level Info Cache:
- Hits: {level_stats["hits"]}
- Misses: {level_stats["misses"]}
- Hit Rate: {level_stats["hit_rate_percent"]}%
- Cache Size: {level_stats["cache_size"]} items

AI Mentor Cache:
- Hits: {ai_stats["hits"]}
- Misses: {ai_stats["misses"]}
- Hit Rate: {ai_stats["hit_rate_percent"]}%
- Cache Size: {ai_stats["cache_size"]} items

Performance Metrics:
- Memory Usage: {perf_metrics.memory_usage_mb:.1f} MB
- SSH Connection Time: {perf_metrics.ssh_connection_time_ms:.2f} ms
- Cache Hit Rate: {perf_metrics.cache_hit_rate:.1f}%
- Terminal Lines: {perf_metrics.terminal_output_lines}

Recent Performance Alerts: {len(self.performance_monitor.get_recent_alerts(3))}

Press Ctrl+Shift+C to clear all caches and metrics."""

        self.notify(stats_message, severity="information")

    def action_clear_cache(self) -> None:
        """Clear all caches and performance metrics."""
        self.level_info.clear_cache()
        self.ai_mentor.clear_cache()
        self.performance_monitor.clear_metrics()
        self.notify("All caches and performance metrics cleared", severity="information")

    def action_ask_about_last_output(self) -> None:
        """Ask AI about the last terminal output.

        Automatically switches to AI mentor tab and asks about recent terminal output.
        """
        if not self.terminal_output.strip():
            self.notify("No terminal output to analyze", severity="warning")
            return

        # Switch to AI mentor tab
        self.action_switch_tab("mentor")

        # Get last few lines of terminal output
        lines = self.terminal_output.strip().split("\n")
        last_output = "\n".join(lines[-5:]) if len(lines) > 5 else self.terminal_output.strip()

        # Auto-populate the mentor input with a context-aware question
        mentor_input = self.query_one("#mentor_input", Input)
        mentor_input.value = f"Can you help me understand this output?\n\n{last_output}"
        mentor_input.focus()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode.

        Switches between light and dark themes for the application.
        """
        self.dark = not self.dark

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to the specified tab.

        Changes the active tab in the tabbed interface. Validates the
        tab ID and provides user feedback for invalid tab names.

        Args:
            tab_id: The ID of the tab to switch to.

        Returns:
            None: Always returns None.

        Examples:
            app.action_switch_tab('terminal')
            app.action_switch_tab('level')
        """
        try:
            tabbed = self.query_one(TabbedContent)
            if not tabbed:
                self.notify("Tabbed content not found", severity="error")
                return None

            # Get all valid tab IDs from panes that have an ID
            valid_tab_ids = {p.id for p in tabbed.panes if p.id}

            if not tab_id:
                self.notify("No tab ID provided", severity="warning")
                return None

            if tab_id not in valid_tab_ids:
                self.notify(f"Unknown tab: {tab_id}", severity="warning")
                return None

            tabbed.active = tab_id
            return None

        except Exception as e:
            self.notify(f"Failed to switch tab: {e}", severity="error")
            return None

    def on_resize(self, event: Any) -> None:
        """Handle terminal resize events.

        Resizes the SSH PTY to match the new terminal dimensions,
        accounting for UI elements that reduce available space.
        Includes safety checks for invalid dimensions and connection status.

        Args:
            event: The resize event containing the new dimensions.
        """
        if not self.ssh_connected:
            return

        if connection := self.ssh_manager.get_connection(self.session_id):
            try:
                # Calculate safe dimensions for the PTY
                new_width = max(20, event.size.width - 2)
                new_height = max(5, event.size.height - 10)

                # Attempt to resize via the connection manager
                connection.resize_pty(width=new_width, height=new_height)
            except Exception as e:
                # Silently suppress resize errors or provide a warning notification
                with suppress(Exception):
                    self.notify(f"Terminal resize failed: {e}", severity="warning")

    def action_show_session_info(self) -> None:
        """Display session information."""
        session = self.session_manager.get_active_session()
        if session:
            info = f"""Session Information:

Name: {session.name}
ID: {session.session_id[:8]}...
Connection: {session.get_display_name()}
Current Level: {session.current_level}
Created: {session.created_at.strftime("%Y-%m-%d %H:%M")}
Last Used: {session.last_used.strftime("%Y-%m-%d %H:%M")}
Connections: {session.connection_count}
Active: {session.is_active}"""
            self.notify(info, severity="information")
        else:
            self.notify("No active session", severity="warning")

    def action_new_session(self) -> None:
        """Create a new session."""
        self.create_new_session()

    def action_switch_session_dialog(self) -> None:
        """Show session switching dialog."""
        self.show_session_switch_dialog()

    def _navigate_history_up(self) -> None:
        """Navigate up through command history."""
        # Get current input from terminal (this would need a command input field)
        # For now, we'll just get the previous command
        previous_cmd = self.command_history.get_previous()
        if previous_cmd:
            # This would update a command input field
            self.notify(f"Previous: {previous_cmd}", severity="information")

    def _navigate_history_down(self) -> None:
        """Navigate down through command history."""
        next_cmd = self.command_history.get_next()
        if next_cmd is not None:
            # This would update a command input field
            if next_cmd:
                self.notify(f"Next: {next_cmd}", severity="information")
            else:
                self.notify("New command", severity="information")

    def create_new_session(self) -> None:
        """Create a new session."""
        try:
            # Get current connection details if available
            hostname = self.config.get("ssh.host", "bandit.labs.overthewire.org")
            port = self.config.get("ssh.port", 2220)
            username = ""  # Will be set when user connects

            # Create new session
            session_id = self.session_manager.create_session(
                hostname=hostname, port=port, username=username, current_level=self.current_level
            )

            # Switch to new session
            if self.session_manager.set_active_session(session_id):
                self.session_id = session_id
                self.update_session_display()
                self.notify(f"Created new session: {session_id[:8]}...", severity="information")
            else:
                self.notify("Failed to switch to new session", severity="error")

        except Exception as e:
            self.notify(f"Failed to create session: {e}", severity="error")

    def show_session_switch_dialog(self) -> None:
        """Show a dialog to switch sessions."""
        sessions = self.session_manager.list_sessions()
        if not sessions:
            self.notify("No sessions available", severity="warning")
            return

        # For now, just show available sessions in a notification
        # In a full implementation, this would show a proper dialog
        session_list = "\n".join(
            [
                f"{i + 1}. {s.name} ({s.get_display_name()}) - Level {s.current_level}"
                for i, s in enumerate(sessions[:5])  # Show first 5 sessions
            ]
        )

        self.notify(
            f"Available sessions:\n{session_list}\n\nUse session number to switch",
            severity="information",
        )

    def show_delete_session_dialog(self) -> None:
        """Show the delete session dialog."""

        def after_delete(changed: bool) -> None:
            if changed:
                # Refresh UI if needed
                self.update_session_display()

        self.push_screen(DeleteSessionModal(self.session_manager), after_delete)

    def update_session_display(self) -> None:
        """Update the session display in the UI."""
        try:
            session = self.session_manager.get_active_session()
            display_widget = self.query_one("#current_session_display", Static)
            if session:
                display_widget.update(
                    f"{session.get_display_name()} | Level {session.current_level}"
                )
            else:
                display_widget.update("No active session")
        except Exception:
            pass  # Widget might not be ready yet

    def _detect_level_progression(self, command: str) -> None:
        """Detect level progression from commands and update session.

        Args:
            command: The command that was executed.
        """
        # Simple heuristic to detect level progression
        # Look for commands that might indicate level completion
        level_indicators = [
            "cat",
            "ls",
            "cd",
            "find",
            "grep",
            "sort",
            "strings",
            "base64",
            "hexdump",
            "xxd",
            "file",
            "tar",
            "gzip",
            "bzip2",
        ]

        # If command contains level indicators and we see success patterns
        if any(indicator in command for indicator in level_indicators):
            # Look for potential level progression in recent output
            if "bandit" in self.terminal_output.lower():
                # Try to extract current level from terminal output
                import re

                level_matches = re.findall(r"bandit(\d+)", self.terminal_output.lower())
                if level_matches:
                    try:
                        new_level = int(level_matches[-1])  # Get the most recent match
                        if new_level != self.current_level:
                            self.current_level = new_level
                            self.session_manager.update_session_level(self.session_id, new_level)
                            self.update_level_info()
                            self.update_session_display()
                            self.notify(
                                f"Detected level progression to Level {new_level}",
                                severity="information",
                            )
                    except ValueError:
                        pass  # Ignore invalid level numbers

    def _initialize_session(self) -> None:
        """Initialize or restore the active session."""
        try:
            # Try to get the active session
            active_session = self.session_manager.get_active_session()

            if active_session:
                # Restore session state
                self.session_id = active_session.session_id
                self.current_level = active_session.current_level
                self.update_session_display()
                self.notify(f"Restored session: {active_session.name}", severity="information")
            else:
                # Create a default session if none exists
                sessions = self.session_manager.list_sessions()
                if sessions:
                    # Use the most recently used session
                    session = sessions[0]
                    self.session_manager.set_active_session(session.session_id)
                    self.session_id = session.session_id
                    self.current_level = session.current_level
                    self.update_session_display()
                else:
                    # Create a new default session
                    self.create_new_session()
        except Exception as e:
            self._handle_error_and_stop_loading(f"Failed to initialize session: {e}")
            # Create a fallback session
            self.session_id = "default"
            self.current_level = 0

    def _handle_error_and_stop_loading(self, message: str) -> None:
        """Handle error with user-friendly feedback and stop loading.

        Args:
            message: Error message to display.
        """
        # Log error for debugging
        self._log_error(f"Validation error: {message}")

        # Provide actionable feedback based on error type
        user_message = self._get_user_friendly_error_message(message)

        self.notify(user_message, severity="error")
        self.loading = False

    def _log_error(self, message: str) -> None:
        """Log error to file for debugging."""
        try:
            import os
            from datetime import datetime

            # Create logs directory if it doesn't exist
            log_dir = os.path.expanduser("~/.bandit_cli/logs")
            os.makedirs(log_dir, exist_ok=True)

            # Create error log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"errors_{timestamp}.log")

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
        except Exception:
            # Fallback if logging fails
            pass

    def _get_user_friendly_error_message(self, technical_message: str) -> str:
        """Convert technical error messages to user-friendly, actionable messages.

        Args:
            technical_message: The original technical error message.

        Returns:
            str: User-friendly error message with suggestions.
        """
        message_lower = technical_message.lower()

        # Connection-related errors
        if "connection" in message_lower or "network" in message_lower:
            if "timeout" in message_lower:
                return "🔌 Connection timeout. Check your internet connection and try again."
            elif "refused" in message_lower:
                return "🚫 Connection refused. The server may be busy or down. Try again in a few minutes."
            elif "authentication" in message_lower or "password" in message_lower:
                return "🔑 Authentication failed. Double-check your username and password, then try again."
            elif "host" in message_lower:
                return "🌐 Host not found. Verify the server address and your network connection."
            else:
                return "🔌 Network error. Check your connection and try again."

        # Input validation errors
        elif "invalid" in message_lower or "validation" in message_lower:
            if "username" in message_lower:
                return "👤 Invalid username. Use only letters, numbers, underscores, and hyphens (3-32 chars)."
            elif "password" in message_lower:
                return "🔒 Password required. Please enter a valid password."
            elif "port" in message_lower:
                return "🔌 Invalid port. Use a number between 1-65535."
            elif "format" in message_lower:
                return "📝 Invalid format. Please check your input and try again."
            else:
                return "❌ Invalid input. Please check your input and try again."

        # File/system errors
        elif "file" in message_lower or "not found" in message_lower:
            if "permission" in message_lower:
                return "🔒 Permission denied. Check file permissions and try running with appropriate access."
            elif "directory" in message_lower:
                return "📁 Directory not found. Check the file path and try again."
            else:
                return (
                    "📄 File error. Check if the file exists and you have permission to access it."
                )

        # AI/mentor errors
        elif "ai" in message_lower or "mentor" in message_lower:
            if "api" in message_lower or "key" in message_lower:
                return "🤖 AI service unavailable. Check your API key and internet connection."
            elif "rate" in message_lower or "limit" in message_lower:
                return "⏱️ Rate limit reached. Wait a moment before trying again."
            else:
                return "🧠 AI mentor error. Try again or check your configuration."

        # Default fallback
        return f"❌ Error: {technical_message}. Please try again or check the documentation."


def main() -> None:
    """Run the BanditCLI application."""
    app = BanditCLIApp()
    app.run()


if __name__ == "__main__":
    main()
