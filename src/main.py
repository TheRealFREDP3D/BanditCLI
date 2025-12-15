# src/main.py
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, TextArea, Input, Button, Label, LoadingIndicator
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.validation import Function, ValidationResult

from ssh_manager import SSHManager
from ai_mentor import BanditAIMentor
from level_info import BanditLevelInfo

# Load environment variables
load_dotenv()

def validate_port(value: str) -> ValidationResult:
    """Validate port number"""
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
    """Validate timeout value"""
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

class BanditCLIApp(App):
    """A Textual app for the Bandit Wargame CLI."""
    
    CSS_PATH = "app.tcss"
    
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("1", "switch_tab('terminal')", "Terminal"),
        ("2", "switch_tab('level')", "Level Info"),
        ("3", "switch_tab('mentor')", "AI Mentor"),
        ("ctrl+c", "cancel_operation", "Cancel"),
    ]
    
    def __init__(self):
        super().__init__()
        self.current_level = 0
        self.session_id = "default"
        self.recent_commands = []
        self.terminal_output = ""
        self.ssh_manager = SSHManager(notify_callback=self.notify)
        self.level_info = BanditLevelInfo(notify_callback=self.notify)
        self.ai_mentor = BanditAIMentor(notify_callback=self.notify)
        self.ssh_connected = reactive(False)
        self.loading = reactive(False)
        self.ai_generating = reactive(False)

    def watch_ssh_connected(self, connected: bool):
        """Called when the ssh_connected reactive property changes."""
        try:
            self.query_one("#ssh_connect", Button).disabled = connected
            self.query_one("#ssh_disconnect", Button).disabled = not connected
            self.query_one("#command_input", Input).disabled = not connected
            self.query_one("#send_button", Button).disabled = not connected
        except Exception:
            # Widgets might not be ready yet
            pass

    def watch_loading(self, loading: bool):
        """Called when the loading reactive property changes."""
        for indicator in self.query(LoadingIndicator):
            indicator.display = loading

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with TabbedContent(initial="terminal"):
            with TabPane("Terminal", id="terminal"):
                yield from self.compose_terminal_view()
            with TabPane("Level Info", id="level"):
                yield from self.compose_level_view()
            with TabPane("AI Mentor", id="mentor"):
                yield from self.compose_mentor_view()
        
        yield Footer()

    def compose_terminal_view(self) -> ComposeResult:
        """Compose the terminal view."""
        with Vertical(id="terminal-view"):
            yield LoadingIndicator()
            yield TextArea(id="terminal_output", read_only=True)
            with Horizontal(id="ssh-controls"):
                with Vertical():
                    yield Label("Username:")
                    yield Input(placeholder="bandit0", id="ssh_username")
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
                yield Input(placeholder="Enter command...", id="command_input")
                yield Button("Send", variant="primary", id="send_button")

    def compose_level_view(self) -> ComposeResult:
        """Compose the level information view."""
        with Vertical():
            yield TextArea(id="level_info", read_only=True)
            with Horizontal():
                yield Button("Previous Level", id="prev_level")
                yield Button("Next Level", id="next_level")

    def compose_mentor_view(self) -> ComposeResult:
        """Compose the AI mentor view."""
        with Vertical():
            yield LoadingIndicator()
            yield TextArea(id="mentor_chat", read_only=True)
            with Horizontal():
                yield Input(placeholder="Ask the AI mentor...", id="mentor_input")
                yield Button("Send", variant="primary", id="mentor_send")

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Bandit Wargame CLI"
        self.sub_title = "A terminal interface for OverTheWire Bandit"
        
        # Initialize the level info
        self.update_level_info()
        # Initial state of buttons
        self.query_one("#ssh_disconnect", Button).disabled = True
        self.query_one("#command_input", Input).disabled = True
        self.query_one("#send_button", Button).disabled = True
    def update_level_info(self):
        """Update the level information display."""
        level_info_text = self.level_info.format_level_info(self.current_level)
        level_info_widget = self.query_one("#level_info", TextArea)
        level_info_widget.load_text(level_info_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
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
        """Handle input submissions."""
        if event.input.id == "command_input":
            self.send_command()
        elif event.input.id == "mentor_input":
            self.send_mentor_message()

    def connect_ssh(self):
        """Connect to the SSH server with validation."""
        self.loading = True
        
        try:
            username_input = self.query_one("#ssh_username", Input)
            password_input = self.query_one("#ssh_password", Input)
            port_input = self.query_one("#ssh_port", Input)
            timeout_input = self.query_one("#ssh_timeout", Input)
            
            username = username_input.value or ""
            password = password_input.value or ""
            port = port_input.value or "2220"
            timeout_str = timeout_input.value
            
            if not username or not password:
                self.notify("Please enter both username and password", severity="error")
                self.loading = False
                return
            
            # Convert port and timeout to integer
            try:
                port_int = int(port)
                timeout_int = int(timeout_str)
            except ValueError:
                self.notify("Port and timeout must be valid numbers", severity="error")
                self.loading = False
                return
                
            # Validate port range
            if port_int < 1 or port_int > 65535:
                self.notify("Port must be between 1 and 65535", severity="error")
                return
            
            # Attempt to connect
            success = self.ssh_manager.create_connection(
                self.session_id,
                "bandit.labs.overthewire.org",
                port_int,
                username,
                password,
                timeout=timeout_int
            )
            
            if success:
                self.ssh_connected = True
                self.notify("SSH connection established", severity="success")
                # Set up the output callback
                connection = self.ssh_manager.get_connection(self.session_id)
                if connection:
                    connection.set_output_callback(self.on_ssh_output)
            else:
                self.notify("Failed to establish SSH connection. Please check your credentials, network connection, and ensure the Bandit server is accessible.", severity="error")
            self.loading = False
            
        except Exception as e:
            self.notify(f"Error during SSH connection: {e}", severity="error")
            self.loading = False
    
    def disconnect_ssh(self):
        """Disconnect from the SSH server."""
        self.ssh_manager.disconnect_session(self.session_id)
        self.ssh_connected = False
        self.notify("SSH connection closed", severity="information")
    
    def on_ssh_output(self, data: str):
        """Handle SSH output."""
        self.terminal_output += data
        terminal_output = self.query_one("#terminal_output", TextArea)
        terminal_output.load_text(self.terminal_output)
        # Scroll to the end
        terminal_output.scroll_end(animate=False)
    
    def send_command(self):
        """Send a command to the SSH server."""
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
        # Add command to recent commands
        self.recent_commands.append(command)
        if len(self.recent_commands) > 20:
            self.recent_commands.pop(0)
        
        # Send command to SSH server
        connection = self.ssh_manager.get_connection(self.session_id)
        if connection:
            connection.send_command(command + "\n")
        
        # Clear the input
        command_input.value = ""

    def send_mentor_message(self):
        """Send a message to the AI mentor."""
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
                self.terminal_output[-1000:]  # Last 1000 chars of output
            )
            
            # Stream response
            for chunk in response_stream:
                mentor_chat.load_text(mentor_chat.text + chunk)
                mentor_chat.scroll_end(animate=False)
            
            mentor_chat.load_text(mentor_chat.text + "\n")
            
        except Exception as e:
            self.notify(f"Error getting AI response: {e}", severity="error")
        finally:
            # Clear input
            mentor_input.value = ""
            self.loading = False
            self.ai_generating = False

    def previous_level(self):
        """Go to the previous level."""
        if self.current_level > 0:
            self.current_level -= 1
            self.update_level_info()
            self.notify(f"Switched to Level {self.current_level}", severity="information")

    def next_level(self):
        """Go to the next level."""
        max_level = max([int(k) for k in self.level_info.levels_data.keys()] + [0])
        if self.current_level < max_level:
            self.current_level += 1
            self.update_level_info()
            self.notify(f"Switched to Level {self.current_level}", severity="information")
        else:
            self.notify("Already at the highest available level", severity="warning")

    def action_toggle_dark(self):
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to the specified tab.
        
        Args:
            tab_id: The ID of the tab to switch to
            
        Returns:
            None: Always returns None
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

    def on_resize(self, event):
        """Handle terminal resize events."""
        if connection := self.ssh_manager.get_connection(self.session_id):
            connection.resize_pty(width=event.size.width, height=event.size.height - 10)

if __name__ == "__main__":
    app = BanditCLIApp()
    app.run()
