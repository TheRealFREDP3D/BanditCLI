"""Main application module for BanditCLI.

This module contains the main Textual application class that provides a terminal
interface for the OverTheWire Bandit wargame. It includes SSH connection management,
AI mentor integration, and level information display.

The main class is BanditCLIApp, which extends Textual's App class and provides
three main tabs: Terminal, Level Info, and AI Mentor.
"""
# src/main.py
from dotenv import load_dotenv
from contextlib import suppress
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, TextArea, Input, Button, Label, LoadingIndicator
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.validation import Function, ValidationResult
from textual.widget import Widget
import re
from typing import Optional, List, Callable, Any

from .ssh_manager import SSHManager
from .ai_mentor import BanditAIMentor
from .level_info import BanditLevelInfo
from . import __version__

# Load environment variables
load_dotenv()

class VersionFooter(Widget):
    """A custom footer widget that displays version information alongside key bindings."""
    
    def compose(self) -> ComposeResult:
        """Compose the footer with version display and standard footer functionality."""
        with Horizontal():
            yield Label(f"v{__version__}", id="version-label")
            yield Footer()

def validate_port(value: str) -> ValidationResult:
    """Validate port number.
    
    Args:
        value: The port number string to validate.
        
    Returns:
        ValidationResult: Success if valid, failure with message if invalid.
    """
    if not value:
        return ValidationResult.success()
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return ValidationResult.success()
        else:
            return ValidationResult.failure("Port must be between 1 and 65535")
    except ValueError:
        return ValidationResult.failure("Port must be a number")

def validate_timeout(value: str) -> ValidationResult:
    """Validate timeout value.
    
    Args:
        value: The timeout value string to validate.
        
    Returns:
        ValidationResult: Success if valid, failure with message if invalid.
    """
    if not value:
        return ValidationResult.success()
    try:
        timeout = int(value)
        if 1 <= timeout <= 300:
            return ValidationResult.success()
        else:
            return ValidationResult.failure("Timeout must be between 1 and 300 seconds")
    except ValueError:
        return ValidationResult.failure("Timeout must be a number")

def validate_username(value: str) -> ValidationResult:
    """Validate SSH username for security.
    
    Args:
        value: The username string to validate.
        
    Returns:
        ValidationResult: Success if valid, failure with message if invalid.
    """
    if not value:
        return ValidationResult.failure("Username is required")
    
    # Check for dangerous characters that could lead to injection
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", '\\']
    if any(char in value for char in dangerous_chars):
        return ValidationResult.failure("Username contains invalid characters")
    
    # Length check
    if len(value) > 32:
        return ValidationResult.failure("Username too long (max 32 characters)")
    
    # Pattern check (allow alphanumeric, underscores, hyphens)
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        return ValidationResult.failure("Username can only contain letters, numbers, underscores, and hyphens")
    
    return ValidationResult.success()

def validate_command(value: str) -> ValidationResult:
    """Validate SSH command for injection prevention.
    
    Args:
        value: The command string to validate.
        
    Returns:
        ValidationResult: Success if valid, failure with message if invalid.
    """
    if not value:
        return ValidationResult.failure("Command cannot be empty")
    
    # Check for obvious command injection attempts
    dangerous_patterns = [
        r'\s*;\s*',  # Command separator
        r'\s*&&\s*', # Command chaining
        r'\s*\|\s*', # Pipe
        r'\s*`.*`',  # Command substitution
        r'\s*\$\(', # Command substitution
        r'\s*>\s*',  # Output redirection
        r'\s*<\s*',  # Input redirection
        r'\s*>>\s*', # Output append
        r'\\x[0-9a-fA-F]{2}', # Hex escape sequences
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return ValidationResult.failure("Command contains potentially dangerous operators")
    
    # Length check to prevent buffer overflow attempts
    if len(value) > 1000:
        return ValidationResult.failure("Command too long (max 1000 characters)")
    
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
        ("2", "switch_tab('level')", "Level Info"),
        ("3", "switch_tab('mentor')", "AI Mentor"),
        ("ctrl+c", "cancel_operation", "Cancel"),
    ]
    
    def _notify_wrapper(self, message: str, severity: str) -> None:
        """Wrapper to convert callback signature to Textual notify signature.
        
        Args:
            message: The message to display.
            severity: The severity level of the message.
        """
        self.notify(message, severity=severity)
    
    def __init__(self) -> None:
        super().__init__()
        self.current_level = 0
        self.session_id = "default"
        self.recent_commands = []
        self.terminal_output = ""
        self.offline_mode = False
        self.ssh_manager = SSHManager(notify_callback=self.notify)
        self.level_info = BanditLevelInfo(notify_callback=self._notify_wrapper)
        self.ai_mentor = BanditAIMentor(notify_callback=self._notify_wrapper)
        self.ssh_connected = reactive(False)
        self.loading = reactive(False)
        self.ai_generating = reactive(False)

    def watch_ssh_connected(self, connected: bool) -> None:
        """Called when the ssh_connected reactive property changes.
        
        Updates the UI state based on SSH connection status. Enables/disables
        buttons and inputs as appropriate.
        
        Args:
            connected: Whether SSH is connected or not.
        """
        with suppress(Exception):
            # Widgets might not be ready yet
            self.query_one("#ssh_connect", Button).disabled = connected
            self.query_one("#ssh_disconnect", Button).disabled = not connected
            self.query_one("#command_input", Input).disabled = not connected
            self.query_one("#send_button", Button).disabled = not connected


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
        containing three tabs (Terminal, Level Info, AI Mentor), and a custom footer.
        
        Yields:
            Header: The application header.
            TabbedContent: Container for the three main tabs.
            VersionFooter: A custom footer with version display and key bindings.
        """
        yield Header()
        
        with TabbedContent(initial="terminal"):
            with TabPane("Terminal", id="terminal"):
                yield from self.compose_terminal_view()
            with TabPane("Level Info", id="level"):
                yield from self.compose_level_view()
            with TabPane("AI Mentor", id="mentor"):
                yield from self.compose_mentor_view()
        
        yield VersionFooter()

    def compose_terminal_view(self) -> ComposeResult:
        """Compose the terminal view.
        
        Creates the terminal tab layout with output display, SSH connection
        controls (username, password, port, timeout), and command input controls.
        
        Yields:
            LoadingIndicator: Shows loading state.
            TextArea: Terminal output display.
            Various input widgets and buttons for SSH and command controls.
        """
        with Vertical(id="terminal-view"):
            yield LoadingIndicator()
            yield TextArea(id="terminal_output", read_only=True)
            with Horizontal(id="ssh-controls"):
                with Vertical():
                    yield Label("Username:")
                    yield Input(
                        placeholder="bandit0", 
                        id="ssh_username",
                        validators=[Function(validate_username, "Invalid username")]
                    )
                with Vertical():
                    yield Label("Password:")
                    yield Input(placeholder="bandit0", id="ssh_password", password=True)
                with Vertical():
                    yield Label("Port:")
                    yield Input(
                        placeholder="2220", 
                        id="ssh_port",
                        validators=[Function(validate_port, "Invalid port")]
                    )
                with Vertical():
                    yield Label("Timeout:")
                    yield Input(
                        placeholder="10", 
                        id="ssh_timeout",
                        validators=[Function(validate_timeout, "Invalid timeout")]
                    )
                with Vertical(id="ssh-buttons"):
                    yield Button("Connect", variant="primary", id="ssh_connect")
                    yield Button("Disconnect", variant="error", id="ssh_disconnect")
            with Horizontal(id="command-controls"):
                yield Label("Command:")
                yield Input(
                    placeholder="Enter command...", 
                    id="command_input",
                    validators=[Function(validate_command, "Invalid command")]
                )
                yield Button("Send", variant="primary", id="send_button")

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
        the AI mentor, including a loading indicator and message input.
        
        Yields:
            LoadingIndicator: Shows AI response generation state.
            TextArea: Chat interface display.
            Input and Button: Message input and send controls.
        """
        with Vertical():
            yield LoadingIndicator()
            yield TextArea(id="mentor_chat", read_only=True)
            with Horizontal():
                yield Input(placeholder="Ask the AI mentor...", id="mentor_input")
                yield Button("Send", variant="primary", id="mentor_send")

    def on_mount(self) -> None:
        """Called when the app is mounted.
        
        Initializes the application state, sets the title and subtitle,
        updates level information, and configures initial button states.
        """
        self.title = "Bandit Wargame CLI"
        self.sub_title = f"A terminal interface for OverTheWire Bandit v{__version__}"
        
        # Initialize the level info
        self.update_level_info()
        # Initial state of buttons
        self.query_one("#ssh_disconnect", Button).disabled = True
        self.query_one("#command_input", Input).disabled = True
        self.query_one("#send_button", Button).disabled = True
        # Ensure loading indicators are hidden initially
        self.loading = False
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
        elif event.button.id == "send_button":
            self.send_command()
        elif event.button.id == "prev_level":
            self.previous_level()
        elif event.button.id == "next_level":
            self.next_level()
        elif event.button.id == "mentor_send":
            self.send_mentor_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission events.
        
        Routes input submissions to their corresponding handler methods
        based on the input field ID.
        
        Args:
            event: The input submission event containing the input reference.
        """
        if event.input.id == "command_input":
            self.send_command()
        elif event.input.id == "mentor_input":
            self.send_mentor_message()

    def _handle_error_and_stop_loading(self, message: str) -> None:
        """Handle error notification and stop loading."""
        self.notify(message, severity="error")
        self.loading = False

    def connect_ssh(self) -> None:
        """Connect to the SSH server with validation.
        
        Validates user input, establishes an SSH connection to the OverTheWire
        Bandit server, and sets up the output callback for terminal display.
        Handles connection errors and provides user feedback.
        """
        self.loading = True
        
        try:
            username_input = self.query_one("#ssh_username", Input)
            password_input = self.query_one("#ssh_password", Input)
            port_input = self.query_one("#ssh_port", Input)
            timeout_input = self.query_one("#ssh_timeout", Input)
            
            # Validate inputs
            username = username_input.value or ""
            password = password_input.value or ""
            port = port_input.value or "2220"
            timeout_str = timeout_input.value
            
            # Check if inputs are valid
            if not username_input.validate(username):
                self._handle_error_and_stop_loading("Invalid username")
                return
            
            if not password:
                self._handle_error_and_stop_loading("Password is required")
                return
            
            if not port_input.validate(port):
                self._handle_error_and_stop_loading("Invalid port")
                return
            
            if not timeout_input.validate(timeout_str):
                self._handle_error_and_stop_loading("Invalid timeout")
                return
            
            # Convert port and timeout to integer
            try:
                port_int = int(port)
                timeout_int = int(timeout_str)
            except ValueError:
                self._handle_error_and_stop_loading("Port and timeout must be valid numbers")
                return
                
            # Validate port range
            if port_int < 1 or port_int > 65535:
                self._handle_error_and_stop_loading("Port must be between 1 and 65535")
                return
            
            # Attempt to connect with security settings
            # Default to secure host key verification for educational tool
            verify_host_key = not os.getenv("BANDIT_CLI_INSECURE", "").lower() in ("true", "1", "yes")
            
            success = self.ssh_manager.create_connection(
                self.session_id,
                "bandit.labs.overthewire.org",
                port_int,
                username,
                password,
                timeout=timeout_int,
                verify_host_key=verify_host_key
            )
            
            if success:
                self.ssh_connected = True
                self.notify("SSH connection established", severity="success")
                # Set up the output callback
            if (connection := self.ssh_manager.get_connection(self.session_id)):
                connection.set_output_callback(self.on_ssh_output)
            else:
                self.notify("Failed to establish SSH connection. Please check your credentials, network connection, and ensure the Bandit server is accessible.", severity="error")
            self.loading = False
            
        except Exception as e:
            self.notify(f"Error during SSH connection: {e}", severity="error")
            self.loading = False
    
    def disconnect_ssh(self) -> None:
        """Disconnect from the SSH server.
        
        Closes the SSH connection and updates the UI state to reflect
        the disconnected status.
        """
        self.ssh_manager.disconnect_session(self.session_id)
        self.ssh_connected = False
        self.notify("SSH connection closed", severity="information")
    
    def on_ssh_output(self, data: str) -> None:
        """Handle SSH output data.
        
        Appends received SSH output to the terminal display and scrolls
        to show the latest output.
        
        Args:
            data: The output data received from the SSH connection.
        """
        self.terminal_output += data
        terminal_output = self.query_one("#terminal_output", TextArea)
        terminal_output.load_text(self.terminal_output)
        # Scroll to the end
        terminal_output.scroll_end(animate=False)
    
    def send_command(self) -> None:
        """Send a command to the SSH server.
        
        Validates connection status, adds the command to recent history,
        and sends it to the SSH server. Checks for offline mode before
        sending.
        """
        # Check if we're in offline mode
        if self.offline_mode:
            self.notify("Cannot send commands in offline mode", severity="error")
            return
        
        if not self.ssh_connected:
            self.notify("Not connected to SSH server", severity="error")
            return
        
        command_input = self.query_one("#command_input", Input)
        command = command_input.value
        
        if not command:
            return
        
        # Validate command for security
        if not command_input.validate(command):
            self.notify("Invalid command detected", severity="error")
            return
        # Add command to recent commands
        self.recent_commands.append(command)
        if len(self.recent_commands) > 20:
            self.recent_commands.pop(0)
        
        # Send command to SSH server
        if (connection := self.ssh_manager.get_connection(self.session_id)):
            connection.send_command(command + "\n")
        
        # Clear the input
        command_input.value = ""

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
                self.terminal_output
            )
            
            # Stream response
            for chunk in response_stream:
                mentor_chat.insert(chunk)
                mentor_chat.move_cursor((mentor_chat.cursor_row, mentor_chat.cursor_column + len(chunk)))
            
        except Exception as e:
            self.notify(f"Error getting AI response: {e}", severity="error")
        finally:
            # Clear input
            mentor_input = self.query_one("#mentor_input", Input)
            mentor_input.value = ""
            self.loading = False
            self.ai_generating = False

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
        
        Args:
            event: The resize event containing the new dimensions.
        """
        if connection := self.ssh_manager.get_connection(self.session_id):
            connection.resize_pty(width=event.size.width, height=event.size.height - 10)

if __name__ == "__main__":
    app = BanditCLIApp()
    app.run()
