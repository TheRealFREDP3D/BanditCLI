import os
from dotenv import load_dotenv
from textual.app import App
from textual.widgets import Header, Footer, TabbedContent, TabPane, TextArea, Input, Button, Label
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.events import Key


class CommandInput(Input):
    """Custom Input widget with command history support."""
    
    def __init__(self, command_history, **kwargs):
        super().__init__(**kwargs)
        self.command_history = command_history
    
    def on_key(self, event: Key) -> None:
        """Handle key presses."""
        if event.key == "up":
            previous_command = self.command_history.get_previous_command()
            if previous_command is not None:
                self.value = previous_command
                self.cursor_position = len(self.value)
                event.prevent_default()
        elif event.key == "down":
            next_command = self.command_history.get_next_command()
            if next_command is not None:
                self.value = next_command
                self.cursor_position = len(self.value)
                event.prevent_default()
        elif event.key == "enter":
            # Reset history index when user types a new command
            self.command_history.reset_index()

from ssh_manager import SSHManager
from ai_mentor import ai_mentor
from level_info import BanditLevelInfo
from command_history import CommandHistory
from config import ConfigManager
from cache import cache
from session_manager import SessionManager

# Load environment variables
load_dotenv()

class BanditCLIApp(App):
    """A Textual app for the Bandit Wargame CLI."""
    
    CSS_PATH = "app.tcss"
    offline_mode = reactive(False)
    
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("1", "switch_tab('terminal')", "Terminal"),
        ("2", "switch_tab('level')", "Level Info"),
        ("3", "switch_tab('mentor')", "AI Mentor"),
        ("o", "toggle_offline_mode", "Toggle Offline Mode"),
    ]
    
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.current_level = 0
        self.session_id = "default"
        self.recent_commands = []
        self.terminal_output = ""
        self.ssh_manager = SSHManager()
        self.level_info = BanditLevelInfo()
        self.ssh_connected = False
        self.config = ConfigManager()
        self.command_history = CommandHistory(
            max_size=self.config.get("history.max_commands", 100),
            history_file=os.path.expanduser("~/.bandit_cli/command_history.json")
        )
        self.offline_mode = False
    
    def compose(self):
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
    
    def compose_terminal_view(self):
        """Compose the terminal view."""
        with Vertical():
            yield TextArea(id="terminal_output", read_only=True)
            with Horizontal():
                yield Label("SSH Login:")
                yield Input(placeholder="bandit0", id="ssh_username")
                yield Input(placeholder="bandit0", id="ssh_password")
                yield Input(placeholder="2220", id="ssh_port")
                yield Button("Connect", variant="primary", id="ssh_connect")
                yield Button("Disconnect", variant="error", id="ssh_disconnect")
            with Horizontal():
                yield Label("Command:")
                yield CommandInput(self.command_history, placeholder="Enter command...", id="command_input")
                yield Button("Send", variant="primary", id="send_button")
    
    def compose_level_view(self):
        """Compose the level information view."""
        with Vertical():
            yield TextArea(id="level_info", read_only=True)
            with Horizontal():
                yield Button("Previous Level", id="prev_level")
                yield Button("Next Level", id="next_level")
    
    def compose_mentor_view(self):
        """Compose the AI mentor view."""
        with Vertical():
            yield TextArea(id="mentor_chat", read_only=True)
            with Horizontal():
                yield Input(placeholder="Ask the AI mentor...", id="mentor_input")
                yield Button("Send", variant="primary", id="mentor_send")
    
    def on_mount(self):
        """Called when the app is mounted."""
        self.title = "Bandit Wargame CLI"
        self.sub_title = "A terminal interface for OverTheWire Bandit"
        
        # Initialize the level info
        self.update_level_info()
    
    def watch_offline_mode(self, offline_mode: bool):
        """Watch for changes to offline_mode and update the subtitle."""
        if offline_mode:
            self.sub_title = "A terminal interface for OverTheWire Bandit (Offline Mode)"
        else:
            self.sub_title = "A terminal interface for OverTheWire Bandit"
    
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
        """Connect to the SSH server."""
        # Check if we're in offline mode
        if self.offline_mode:
            self.notify("Cannot connect in offline mode", severity="error")
            return
        
        username_input = self.query_one("#ssh_username", Input)
        password_input = self.query_one("#ssh_password", Input)
        port_input = self.query_one("#ssh_port", Input)
        
        username = username_input.value
        password = password_input.value
        port = port_input.value if port_input.value else "2220"  # Default to 2220 if empty
        
        if not username or not password:
            self.notify("Please enter both username and password", severity="error")
            return
        
        # Convert port to integer
        try:
            port_int = int(port)
        except ValueError:
            self.notify("Port must be a valid number", severity="error")
            return
            
        # Validate port range
        if port_int < 1 or port_int > 65535:
            self.notify("Port must be between 1 and 65535", severity="error")
            return
        
        # Create or update session
        session_name = f"{username}@bandit.labs.overthewire.org:{port_int}"
        self.session_manager.create_session(
            self.session_id,
            session_name,
            "bandit.labs.overthewire.org",
            port_int,
            username,
            self.current_level
        )
        self.session_manager.set_current_session(self.session_id)
        
        # Attempt to connect with retries
        success = self.ssh_manager.create_connection(
            self.session_id,
            "bandit.labs.overthewire.org",
            port_int,
            username,
            password,
            retries=3
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
            
        # Validate command length
        if len(command) > 1000:
            self.notify("Command is too long (maximum 1000 characters)", severity="error")
            return
        
        # Add command to history
        self.command_history.add_command(command)
        self.command_history.reset_index()
        
        # Add command to recent commands (for AI context)
        self.recent_commands.append(command)
        if len(self.recent_commands) > 10:
            self.recent_commands.pop(0)
        
        # Send command to SSH server
        connection = self.ssh_manager.get_connection(self.session_id)
        if connection:
            try:
                connection.send_command(command + "\n")
            except Exception as e:
                self.notify(f"Failed to send command: {str(e)}", severity="error")
        
        # Clear the input
        command_input.value = ""
        
        # Clear the input
        command_input.value = ""
    
    def send_mentor_message(self):
        """Send a message to the AI mentor."""
        # Check if we're in offline mode
        if self.offline_mode:
            # In offline mode, provide a cached response or default message
            self._send_offline_mentor_message()
            return
        
        mentor_input = self.query_one("#mentor_input", Input)
        message = mentor_input.value
        
        if not message:
            return
            
        # Validate message length
        if len(message) > 1000:
            self.notify("Message is too long (maximum 1000 characters)", severity="error")
            return
        
        try:
            # Get AI response
            response = ai_mentor.get_response(
                message,
                self.session_id,
                self.current_level,
                self.recent_commands,
                self.terminal_output
            )
            
            # Update chat display
            mentor_chat = self.query_one("#mentor_chat", TextArea)
            current_text = mentor_chat.text if mentor_chat.text else ""
            new_text = f"{current_text}\nYou: {message}\nMentor: {response}"
            mentor_chat.load_text(new_text)
            mentor_chat.scroll_end(animate=False)
        except Exception as e:
            self.notify(f"Failed to get AI response: {str(e)}", severity="error")
        
        # Clear the input
        mentor_input.value = ""
    
    def _send_offline_mentor_message(self):
        """Send a message to the AI mentor in offline mode."""
        mentor_input = self.query_one("#mentor_input", Input)
        message = mentor_input.value
        
        if not message:
            return
            
        # Validate message length
        if len(message) > 1000:
            self.notify("Message is too long (maximum 1000 characters)", severity="error")
            return
        
        # Provide a default offline response
        response = "AI mentor is not available in offline mode. Please connect to the internet and disable offline mode to use the AI mentor."
        
        # Update chat display
        mentor_chat = self.query_one("#mentor_chat", TextArea)
        current_text = mentor_chat.text if mentor_chat.text else ""
        new_text = f"{current_text}\nYou: {message}\nMentor: {response}"
        mentor_chat.load_text(new_text)
        mentor_chat.scroll_end(animate=False)
        
        # Clear the input
        mentor_input.value = ""
    
    def previous_level(self):
        """Go to the previous level."""
        if self.current_level > 0:
            self.current_level -= 1
            self.update_level_info()
            # Update session
            current_session = self.session_manager.get_current_session()
            if current_session:
                self.session_manager.update_session(self.session_id, level=self.current_level)
            self.notify(f"Switched to Level {self.current_level}", severity="information")
        else:
            self.notify("Already at the first level", severity="warning")
    
    def next_level(self):
        """Go to the next level."""
        # Check if we're trying to go beyond the available levels
        max_level = max([int(level) for level in self.level_info.get_all_levels().keys()], default=0)
        if self.current_level < max_level:
            self.current_level += 1
            self.update_level_info()
            # Update session
            current_session = self.session_manager.get_current_session()
            if current_session:
                self.session_manager.update_session(self.session_id, level=self.current_level)
            self.notify(f"Switched to Level {self.current_level}", severity="information")
        else:
            self.notify(f"Level {self.current_level} is the highest available level", severity="warning")
    
    def action_toggle_dark(self):
        """Toggle dark mode."""
        self.dark = not self.dark
    
    def action_toggle_offline_mode(self):
        """Toggle offline mode."""
        self.offline_mode = not self.offline_mode
        if self.offline_mode:
            self.notify("Offline mode enabled", severity="information")
            # Disable SSH connection in offline mode
            if self.ssh_connected:
                self.disconnect_ssh()
        else:
            self.notify("Offline mode disabled", severity="information")

if __name__ == "__main__":
    app = BanditCLIApp()
    app.run()