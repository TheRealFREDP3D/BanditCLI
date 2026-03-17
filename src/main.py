"""Main application module for BanditCLI.

This module contains the main Textual application class that provides a
terminal interface for the OverTheWire Bandit wargame. It includes SSH
connection management, AI mentor integration, and level information display.
"""

import asyncio
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional

from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Function
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

if TYPE_CHECKING:
    from textual.timer import Timer

from . import __version__
from .ai_mentor import BanditAIMentor
from .command_history import CommandHistory
from .config import ConfigManager
from .level_info import BanditLevelInfo
from .performance_monitor import get_performance_monitor, track_performance
from .session_manager import SessionManager
from .ssh_manager import SSHManager
from .terminal_output import EnhancedTerminalOutput

load_dotenv()

# ---------------------------------------------------------------------------
# Bandit password pattern: exactly 32 printable non-whitespace characters.
# Real Bandit passwords are alphanumeric, but this is intentionally slightly
# broader to cope with any future format changes.
# ---------------------------------------------------------------------------
_PASSWORD_RE = re.compile(r"\b([A-Za-z0-9]{32})\b")

# Minimum gap between successive password-detection triggers (seconds).
_PASSWORD_DETECT_COOLDOWN = 5.0


def validate_username(value: str) -> bool:
    """Validate SSH username for security.

    Args:
        value: The username string to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not value:
        return False
    if any(c in value for c in [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'", "\\"]):
        return False
    if len(value) > 32:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", value))


# ---------------------------------------------------------------------------
# Password detector
# ---------------------------------------------------------------------------

class PasswordDetector:
    """Scans terminal output lines for Bandit-style passwords.

    Uses a sliding window of recent output so a password split across
    two SSH data chunks is still matched.

    Attributes:
        _seen (set[str]): Passwords already reported this session to avoid
            duplicate notifications.
        _last_trigger (float): Epoch time of the last detection event, used
            to enforce a cooldown between successive triggers.
    """

    # Lines of context kept between chunks to catch split passwords.
    _CONTEXT_LINES = 4

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._last_trigger: float = 0.0
        self._tail: str = ""  # leftover partial line from previous chunk

    def reset(self) -> None:
        """Clear state when starting a new level / session."""
        self._seen.clear()
        self._last_trigger = 0.0
        self._tail = ""

    def feed(self, raw_text: str) -> list[str]:
        """Feed a chunk of terminal text and return any new passwords found.

        Args:
            raw_text: Raw (ANSI-stripped) text received from SSH.

        Returns:
            List of newly-discovered password strings (may be empty).
        """
        now = time.monotonic()
        if now - self._last_trigger < _PASSWORD_DETECT_COOLDOWN:
            return []

        # Prepend any leftover tail from the previous chunk so we don't
        # miss a password that straddles a chunk boundary.
        combined = self._tail + raw_text

        # Keep a small tail for the next call.
        lines = combined.split("\n")
        self._tail = "\n".join(lines[-self._CONTEXT_LINES :])

        found: list[str] = []
        for match in _PASSWORD_RE.finditer(combined):
            candidate = match.group(1)
            if candidate not in self._seen:
                self._seen.add(candidate)
                found.append(candidate)
                self._last_trigger = now

        return found


# ---------------------------------------------------------------------------
# Modal: level complete / next-level login offer
# ---------------------------------------------------------------------------

class LevelCompleteModal(ModalScreen[Optional[bool]]):
    """Congratulations modal shown when a password is detected.

    Offers the user a one-click option to disconnect and reconnect as the
    next Bandit level using the recovered password.

    Returns:
        True  → user wants to auto-login to the next level.
        False → user wants to stay on the current level.
        None  → modal was dismissed without choosing.
    """

    DEFAULT_CSS = """
    LevelCompleteModal {
        align: center middle;
    }

    #complete_dialog {
        width: 70;
        height: auto;
        border: thick $accent 80%;
        background: $surface;
        padding: 2 3;
    }

    #complete_title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }

    #complete_body {
        width: 100%;
        margin: 0 0 1 0;
    }

    #complete_password_label {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin: 1 0;
    }

    #complete_buttons {
        align: center bottom;
        height: auto;
        margin: 1 0 0 0;
    }

    #complete_buttons > Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        current_level: int,
        password: str,
    ) -> None:
        super().__init__()
        self._current_level = current_level
        self._next_level = current_level + 1
        self._password = password

    def compose(self) -> ComposeResult:
        with Vertical(id="complete_dialog"):
            yield Label(
                f"🎉  Level {self._current_level} Complete!",
                id="complete_title",
            )
            yield Label(
                f"A password for [bold]bandit{self._next_level}[/bold] was detected "
                f"in the terminal output.\n\n"
                f"Progress has been saved automatically.",
                id="complete_body",
            )
            yield Label(
                f"[dim]{self._password}[/dim]",
                id="complete_password_label",
            )
            with Horizontal(id="complete_buttons"):
                yield Button(
                    f"Login to Level {self._next_level} →",
                    variant="primary",
                    id="next_level_login",
                )
                yield Button("Stay on Level", id="stay_level")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next_level_login":
            self.dismiss(True)
        else:
            self.dismiss(False)


# ---------------------------------------------------------------------------
# Existing modal screens (unchanged)
# ---------------------------------------------------------------------------

class SessionSwitchModal(ModalScreen[Optional[tuple[str, bool]]]):
    """Modal screen for switching sessions with restore option."""

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__()
        self.session_manager = session_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="switch_dialog"):
            yield Label("Switch Session", id="switch_label")

            sessions = self.session_manager.list_sessions()
            active_session = self.session_manager.get_active_session()
            active_id = active_session.session_id if active_session else None

            if not sessions:
                yield Label("No sessions available.", id="no_sessions_label")
                yield Button("Cancel", variant="primary", id="cancel_switch")
            else:
                options = []
                for session in sessions:
                    if session.session_id != active_id:
                        timestamp_str = ""
                        if session.last_used:
                            timestamp_str = f" | Last: {session.last_used.strftime('%m/%d %H:%M')}"
                        options.append(
                            (
                                f"{session.get_display_name()} (Level {session.current_level}){timestamp_str}",
                                session.session_id,
                            )
                        )

                if not options:
                    yield Label("No other sessions available.", id="no_other_sessions_label")
                    yield Button("Cancel", variant="primary", id="cancel_switch")
                else:
                    yield SelectionList(*options, id="session_list")
                    with Horizontal(id="switch_buttons"):
                        yield Button("Restore & Switch", variant="primary", id="restore_switch")
                        yield Button("Switch Without Restore", id="switch_only")
                        yield Button("Cancel", id="cancel_switch")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_switch":
            self.dismiss(None)
        elif event.button.id in ["restore_switch", "switch_only"]:
            selection_list = self.query_one(SelectionList)
            if not selection_list.selected:
                self.notify("Please select a session to switch to", severity="warning")
                return
            session_id = list(selection_list.selected)[0]
            restore_flag = event.button.id == "restore_switch"
            self.dismiss((session_id, restore_flag))


class DeleteSessionModal(ModalScreen[bool]):
    """Modal screen for deleting sessions."""

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__()
        self.session_manager = session_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="delete_dialog"):
            yield Label("Select session to delete:", id="delete_label")

            active_session = self.session_manager.get_active_session()
            active_id = active_session.session_id if active_session else None

            options = [
                (
                    f"{session.get_display_name()} (Level {session.current_level})",
                    session.session_id,
                )
                for session in self.session_manager.list_sessions()
                if session.session_id != active_id
            ]

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
            deleted_count = sum(
                1 for sid in selection_list.selected if self.session_manager.delete_session(sid)
            )
            self.app.notify(f"Deleted {deleted_count} session(s)", severity="information")
            self.dismiss(True)


# ---------------------------------------------------------------------------
# UI helper widgets
# ---------------------------------------------------------------------------

class ConnectionStatus(Static):
    """A widget to display SSH connection status with visual indicator."""

    connected = reactive(False)

    def _get_status_text(self) -> str:
        if self.connected:
            return "[green]●[/green] Connected"
        return "[red]●[/red] Disconnected"

    def on_mount(self) -> None:
        self.update(self._get_status_text())

    def watch_connected(self, connected: bool) -> None:
        self.update(self._get_status_text())


class VersionFooter(Widget):
    """A custom footer widget that displays version information."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(f"v{__version__}", id="version-label")
            yield Footer()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class BanditCLIApp(App):
    """A Textual app for the Bandit Wargame CLI."""

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("1", "switch_tab('terminal')", "Terminal"),
        ("2", "switch_tab('session')", "Session"),
        ("3", "switch_tab('level')", "Level Info"),
        ("4", "switch_tab('mentor')", "AI Mentor"),
        ("ctrl+s", "save_progress", "Save Progress"),
        ("n", "new_session", "New Session"),
        ("w", "switch_session_dialog", "Switch Session"),
    ]

    def _notify_wrapper(self, message: str, severity: str) -> None:
        """Convert callback severity string to Textual's Literal type."""
        severity_map: dict[str, Literal["information", "warning", "error"]] = {
            "info": "information",
            "success": "information",
            "error": "error",
            "warning": "warning",
        }
        self.notify(message, severity=severity_map.get(severity, "information"))

    def __init__(self) -> None:
        super().__init__()

        self.performance_monitor = get_performance_monitor()
        self.config = ConfigManager()
        self._validate_configuration()

        self.current_level = 0
        self.session_id = "default"
        self.recent_commands: list[str] = []
        self.terminal_output = ""
        self.max_terminal_output_size = 50000
        self.ssh_manager = SSHManager(notify_callback=self._notify_wrapper)
        self.level_info = BanditLevelInfo(notify_callback=self._notify_wrapper)
        self.ai_mentor = BanditAIMentor(notify_callback=self._notify_wrapper, config=self.config)
        self.command_history = CommandHistory()
        self.session_manager = SessionManager()
        self.ssh_connected: reactive[bool] = reactive(False)
        self.loading: reactive[bool] = reactive(False)
        self._session_has_content = False

        self._last_save_time: float = 0
        self._pending_save: bool = False
        self._save_timer: Optional["Timer"] = None
        self._save_debounce_seconds: int = 5

        self._watchers_setup = False

        # Password detection
        self._password_detector = PasswordDetector()
        self._level_complete_modal_open = False

    # ─── Setup ────────────────────────────────────────────────────────────────

    def _setup_watchers(self) -> None:
        if not self._watchers_setup:
            self.watch(self, "ssh_connected", self.watch_ssh_connected)
            self.watch(self, "loading", self.watch_loading)
            self._watchers_setup = True

    def _validate_configuration(self) -> None:
        try:
            ssh_host = self.config.get("ssh.host")
            ssh_port = self.config.get("ssh.port")
            ssh_timeout = self.config.get("ssh.timeout")

            if not ssh_host or not isinstance(ssh_port, int) or not isinstance(ssh_timeout, int):
                self.notify(
                    "Warning: Invalid SSH configuration. Using defaults.", severity="warning"
                )
                self.config.set("ssh.host", "bandit.labs.overthewire.org")
                self.config.set("ssh.port", 2220)
                self.config.set("ssh.timeout", 10)
                self.config.save_config()

            if not self.config.get("ai.model"):
                self.notify("Warning: No AI model configured. Using default.", severity="warning")
                self.config.set("ai.model", "gpt-3.5-turbo")
                self.config.save_config()
        except Exception as e:
            self.notify(f"Configuration validation error: {e}", severity="error")

    # ─── Output callback (called from reader thread) ──────────────────────────

    def _on_ssh_output_threadsafe(self, data: str) -> None:
        """Receive SSH output from the reader thread and dispatch to the main thread."""
        self.call_from_thread(self._on_ssh_output, data)

    def _on_ssh_output(self, data: str) -> None:
        """Handle SSH output on the main thread."""
        self.terminal_output += data
        if len(self.terminal_output) > self.max_terminal_output_size:
            trim_size = int(self.max_terminal_output_size * 0.8)
            self.terminal_output = self.terminal_output[-trim_size:]

        try:
            self.query_one("#terminal_output", EnhancedTerminalOutput).append_text(
                data, scroll_to_bottom=True
            )
        except Exception:
            try:
                self.query_one("#terminal_output", TextArea).insert(data)
            except Exception:
                pass

        self._mark_state_dirty()

        # Extract commands hinted at in the output for history / level detection
        for line in data.split("\n"):
            if ("$ " in line or "# " in line) and len(line.strip()) > 2:
                prompt_pos = line.find("$ ") if "$ " in line else line.find("# ")
                if prompt_pos != -1:
                    cmd = line[prompt_pos + 2 :].strip()
                    if cmd and not cmd.startswith("["):
                        self.command_history.add_command(cmd)
                        self.recent_commands.append(cmd)
                        if len(self.recent_commands) > 5:
                            self.recent_commands = self.recent_commands[-5:]
                        self._detect_level_progression(cmd)

        # ── Password detection ──────────────────────────────────────────────
        # Strip ANSI before scanning so escape sequences don't fragment tokens.
        from .terminal_output import ANSIColorParser
        clean_data = ANSIColorParser().parse_ansi_text(data)
        new_passwords = self._password_detector.feed(clean_data)
        for pwd in new_passwords:
            self._handle_password_detected(pwd)

    # ─── Password detection logic ─────────────────────────────────────────────

    def _handle_password_detected(self, password: str) -> None:
        """React to a newly detected password in terminal output.

        - Saves the password to the current session.
        - Marks the current level complete.
        - Shows the LevelCompleteModal (once at a time).

        Args:
            password: The 32-character password string that was detected.
        """
        if self._level_complete_modal_open:
            return  # don't stack modals

        level = self.current_level

        # Persist password and mark level complete.
        self.session_manager.store_recovered_password(self.session_id, level, password)
        session = self.session_manager.get_session(self.session_id)
        if session:
            session.mark_level_complete(level)
        self._auto_save_session_state(force=True)

        self.notify(
            f"🔑 Password detected for Level {level + 1}! Progress saved.",
            severity="information",
        )

        self._level_complete_modal_open = True

        def _after_modal(proceed: Optional[bool]) -> None:
            self._level_complete_modal_open = False
            if proceed:
                self._auto_login_next_level(level, password)

        self.push_screen(LevelCompleteModal(level, password), _after_modal)

    def _auto_login_next_level(self, completed_level: int, password: str) -> None:
        """Disconnect from the current level and reconnect as the next bandit user.

        Args:
            completed_level: The level that was just completed.
            password: The password for the next level.
        """
        next_level = completed_level + 1
        next_username = f"bandit{next_level}"

        # Update UI inputs before connecting.
        try:
            self.query_one("#ssh_username", Input).value = next_username
            self.query_one("#ssh_password", Input).value = password
        except Exception:
            pass

        # Disconnect current session.
        if self.ssh_connected:
            self.disconnect_ssh()

        # Advance level counter and update level info panel.
        self.current_level = next_level
        self.update_level_info()

        # Reset password detector for the new level.
        self._password_detector.reset()

        # Reconnect — connect_ssh() reads values from the Input widgets.
        self.connect_ssh()

        self.notify(
            f"Connecting to Level {next_level} as {next_username}…",
            severity="information",
        )

    # ─── Reactive watchers ────────────────────────────────────────────────────

    def watch_ssh_connected(self, connected: bool) -> None:
        try:
            self.query_one("#ssh_connect", Button).disabled = connected
            self.query_one("#ssh_disconnect", Button).disabled = not connected
        except Exception:
            pass

        try:
            self.query_one("#connection_status", ConnectionStatus).connected = connected
        except Exception:
            pass

        try:
            terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)
            command_input = self.query_one("#command_input", Input)
            terminal.read_only = True
            terminal.set_ssh_input_callback(None)
            if connected:
                command_input.focus()
            else:
                terminal.focus()
        except Exception:
            pass

        # Reset password detector whenever the connection state changes.
        if not connected:
            self._password_detector.reset()
            self._level_complete_modal_open = False

    def watch_loading(self, loading: bool) -> None:
        for indicator in self.query(LoadingIndicator):
            indicator.display = loading

    # ─── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
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
        yield EnhancedTerminalOutput(id="terminal_output", read_only=True)
        with Horizontal(id="command-input-bar", classes="command-input-container"):
            yield Input(placeholder="Enter command...", id="command_input", classes="command-input")

    def compose_session_view(self) -> ComposeResult:
        with Vertical():
            yield LoadingIndicator()
            with Horizontal(id="connection-status-bar"):
                yield ConnectionStatus(id="connection_status")
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
            with Horizontal(id="session-controls"):
                yield Label("Session:", id="session-label")
                yield Button("New Session", id="new_session")
                yield Button("Switch Session", id="switch_session")
                yield Button("Delete Session", id="delete_session", variant="error")
                yield Static(id="current_session_display")
            with Horizontal(id="save-controls"):
                yield Label("[bold]Progress Management[/bold]")
                yield Button("Save Progress", variant="success", id="save_progress")
                yield Static("", id="last_save_indicator")

    def compose_level_view(self) -> ComposeResult:
        with Vertical():
            yield TextArea(id="level_info", read_only=True)
            with Horizontal():
                yield Button("Previous Level", id="prev_level")
                yield Button("Next Level", id="next_level")

    def compose_mentor_view(self) -> ComposeResult:
        with Vertical():
            yield LoadingIndicator()
            yield TextArea(id="mentor_chat", read_only=True)
            with Horizontal():
                yield Input(placeholder="Ask the AI mentor...", id="mentor_input")
                yield Button("Send", variant="primary", id="mentor_send")
            with Horizontal(id="conversation-controls"):
                yield Button("Clear History", id="clear_history", variant="error")
                yield Button("Export Chat", id="export_chat", variant="success")

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.title = "Bandit Wargame CLI"
        self.sub_title = f"A terminal interface for OverTheWire Bandit v{__version__}"

        self.update_level_info()
        self.query_one("#ssh_connect", Button).disabled = False
        self.query_one("#ssh_disconnect", Button).disabled = True

        self.loading = False
        for indicator in self.query(LoadingIndicator):
            indicator.display = False

        self._setup_watchers()
        self._initialize_session()

        if not self._session_has_content:
            asyncio.create_task(self.run_welcome_animation())

        asyncio.create_task(self._warm_up_cache())

    def on_unmount(self) -> None:
        try:
            self._auto_save_session_state(force=True)
            if self._save_timer is not None:
                self._save_timer.stop()
                self._save_timer = None
            level_cleanup = self.level_info.cache.cleanup_expired()
            ai_cleanup = self.ai_mentor.cache.cleanup_expired()
            if level_cleanup + ai_cleanup > 0:
                self.notify(
                    f"Cleaned up {level_cleanup + ai_cleanup} expired cache entries on exit",
                    severity="information",
                )
        except Exception as e:
            self.notify(f"Cleanup failed on exit: {e}", severity="warning")

    async def _warm_up_cache(self) -> None:
        try:
            for level in range(6):
                self.level_info.get_level_info(level)
                self.level_info.format_level_info(level)
        except Exception as e:
            self.notify(f"Cache warming failed: {e}", severity="warning")

    async def run_welcome_animation(self) -> None:
        terminal = self.query_one("#terminal_output", EnhancedTerminalOutput)

        if hasattr(terminal, "_virtual_buffer") and terminal._virtual_buffer:
            return

        loading_steps = [
            " [ init ] Connecting to OTW secure gateway...",
            " [ net  ] Establishing encrypted tunnel...",
            " [ auth ] Verifying handshake keys...",
            " [ load ] Loading Bandit wargame modules...",
            " [ ok   ] Connection established.",
        ]
        for step in loading_steps:
            if self.ssh_connected:
                return
            terminal.append_text(step + "\n", scroll_to_bottom=False)
            await asyncio.sleep(0.4)

        await asyncio.sleep(0.5)

        ascii_title = r"""
  ____                  _ _ _    ____ _     ___
 | __ )  __ _ _ __   __| (_) |_ / ___| |   |_ _|
 |  _ \ / _` | '_ \ / _` | | __| |   | |    | |
 | |_) | (_| | | | | (_| | | |_| |___| |___ | |
 |____/ \__,_|_| |_|\__,_|_|\__|\____|_____|___|
"""
        terminal.append_text(ascii_title + "\n", scroll_to_bottom=False)
        await asyncio.sleep(0.5)

        for line in [
            "\n",
            "HOW TO START:",
            "1. Read Level 0 directives in the Level Info tab",
            "2. Connect to the server in the Session tab",
            "3. Play the game by sending commands in the Terminal tab",
            "\n",
        ]:
            if self.ssh_connected:
                return
            terminal.append_text(line + "\n", scroll_to_bottom=False)
            await asyncio.sleep(0.1)

        terminal.scroll_to_bottom()

    # ─── Actions ──────────────────────────────────────────────────────────────

    def action_switch_tab(self, tab_id: str) -> None:
        try:
            self.query_one(TabbedContent).active = tab_id
        except Exception:
            pass

    def action_save_progress(self) -> None:
        try:
            self._auto_save_session_state(force=True)
            self.notify("Progress saved successfully", severity="information")
        except Exception as e:
            self.notify(f"Failed to save progress: {e}", severity="error")

    def action_new_session(self) -> None:
        self.create_new_session()

    def action_switch_session_dialog(self) -> None:
        self.show_session_switch_dialog()

    # ─── Button routing ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "ssh_connect": self.connect_ssh,
            "ssh_disconnect": self.disconnect_ssh,
            "prev_level": self.previous_level,
            "next_level": self.next_level,
            "mentor_send": self.send_mentor_message,
            "clear_history": self.clear_conversation_history,
            "export_chat": self.export_conversation,
            "new_session": self.create_new_session,
            "switch_session": self.show_session_switch_dialog,
            "delete_session": self.show_delete_session_dialog,
            "save_progress": self.action_save_progress,
        }
        handler = handlers.get(event.button.id or "")
        if handler:
            handler()

    def on_key(self, event: Key) -> None:
        """Global key handler — only fires when no Input/TextArea is focused."""
        if isinstance(self.focused, (Input, TextArea)):
            return

        if not self.ssh_connected:
            if event.key == "up":
                self._navigate_history_up()
            elif event.key == "down":
                self._navigate_history_down()
            return

        # SSH key forwarding — terminal tab only
        try:
            if self.query_one(TabbedContent).active != "terminal":
                return
        except Exception:
            return

        if event.key in ["ctrl+c", "ctrl+d", "ctrl+z", "escape"]:
            return

        if connection := self.ssh_manager.get_connection(self.session_id):
            key_map = {
                "enter": "\r\n",
                "backspace": "\b",
                "delete": "\x1b[3~",
                "left": "\x1b[D",
                "right": "\x1b[C",
                "up": "\x1b[A",
                "down": "\x1b[B",
                "home": "\x1b[H",
                "end": "\x1b[F",
                "pageup": "\x1b[5~",
                "pagedown": "\x1b[6~",
            }
            if event.key in key_map:
                connection.send_command(key_map[event.key])
            elif event.character:
                connection.send_command(event.character)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "mentor_input":
            self.send_mentor_message()
        elif event.input.id == "command_input":
            self.send_ssh_command()

    # ─── SSH ──────────────────────────────────────────────────────────────────

    @track_performance("connect_ssh")
    def connect_ssh(self) -> None:
        """Validate inputs, establish SSH connection, wire up the output callback."""
        self.loading = True

        try:
            username_input = self.query_one("#ssh_username", Input)
            password_input = self.query_one("#ssh_password", Input)

            username = username_input.value or ""
            password = password_input.value or ""

            hostname = self.config.get("ssh.host", "bandit.labs.overthewire.org")
            port = self.config.get("ssh.port", "2220")
            timeout = self.config.get("ssh.timeout", "10")

            if not username_input.validate(username):
                self._handle_error_and_stop_loading("Invalid username")
                return

            if not password:
                self._handle_error_and_stop_loading("Password is required")
                return

            if (
                not re.match(r"^[a-zA-Z0-9.-]+$", str(hostname))
                or ".." in str(hostname)
                or str(hostname).startswith(".")
                or str(hostname).endswith(".")
            ):
                self._handle_error_and_stop_loading("Invalid hostname format")
                return

            port_str = str(port)
            if not port_str.isdigit() or not (1 <= int(port_str) <= 65535):
                self._handle_error_and_stop_loading("Port must be between 1 and 65535")
                return

            timeout_str = str(timeout)
            if not timeout_str.isdigit() or not (1 <= int(timeout_str) <= 300):
                self._handle_error_and_stop_loading("Timeout must be between 1 and 300 seconds")
                return

            port_int = int(port_str)
            timeout_int = int(timeout_str)

            insecure_value = os.getenv("BANDIT_CLI_INSECURE", "").lower()
            verify_host_key = insecure_value not in ("true", "1", "yes")

            start_time = time.perf_counter()

            success = self.ssh_manager.create_connection(
                self.session_id,
                str(hostname),
                port_int,
                username,
                password,
                timeout=timeout_int,
                verify_host_key=verify_host_key,
                output_callback=self._on_ssh_output_threadsafe,
            )

            connection_time_ms = (time.perf_counter() - start_time) * 1000
            self.performance_monitor.update_ssh_performance(connection_time_ms)

            if success:
                self.session_manager.update_session_connection(
                    self.session_id, str(hostname), port_int, username
                )
                self.session_manager.set_active_session(self.session_id)
                self.ssh_connected = True
                self.loading = False
                self.notify("SSH connection established", severity="information")
                self.update_session_display()
            else:
                self.notify(
                    "Failed to establish SSH connection. "
                    "Please check your credentials and network.",
                    severity="error",
                )
                self.loading = False

        except (ValueError, OSError, ConnectionError, TimeoutError) as e:
            self._log_error(f"SSH connection error: {type(e).__name__}: {e}")
            self.notify(self._get_user_friendly_error_message(str(e)), severity="error")
            self.loading = False
        except Exception as e:
            import traceback

            self._log_error(f"Unexpected SSH error: {type(e).__name__}: {e}")
            self._log_error(traceback.format_exc())
            self.notify(self._get_user_friendly_error_message(str(e)), severity="error")
            self.loading = False

    def disconnect_ssh(self) -> None:
        self._auto_save_session_state(force=True)
        self.ssh_manager.disconnect_session(self.session_id)
        self.ssh_connected = False

        try:
            self.query_one("#ssh_connect", Button).disabled = False
            self.query_one("#ssh_disconnect", Button).disabled = True
        except Exception:
            pass
        try:
            self.query_one("#connection_status", ConnectionStatus).connected = False
        except Exception:
            pass

        self.notify("SSH connection closed", severity="information")

    def send_ssh_command(self) -> None:
        """Read the command input, send it over SSH, update history."""
        try:
            command_input = self.query_one("#command_input", Input)
            command = command_input.value.strip()

            if not command:
                return

            if command.lower() == "clear":
                self.query_one("#terminal_output", EnhancedTerminalOutput).clear()
                command_input.value = ""
                return

            if not self.ssh_connected:
                self.notify("Not connected to SSH. Please connect first.", severity="warning")
                return

            connection = self.ssh_manager.get_connection(self.session_id)
            if not connection:
                self.notify("SSH connection lost", severity="error")
                self.ssh_connected = False
                return

            connection.send_command(command + "\r\n")
            self.command_history.add_command(command)

            session = self.session_manager.get_active_session()
            if session:
                session.increment_command_count()

            command_input.value = ""
            self.query_one("#terminal_output", EnhancedTerminalOutput).scroll_to_bottom()
            self._mark_state_dirty()

        except Exception as e:
            self.notify(f"Error sending command: {e}", severity="error")

    # ─── Levels ───────────────────────────────────────────────────────────────

    @track_performance("update_level_info")
    def update_level_info(self) -> None:
        self.query_one("#level_info", TextArea).load_text(
            self.level_info.format_level_info(self.current_level)
        )

    def previous_level(self) -> None:
        if self.current_level > 0:
            self.current_level -= 1
            self.update_level_info()

    def next_level(self) -> None:
        self.current_level += 1
        self.update_level_info()

    def _detect_level_progression(self, command: str) -> None:
        level_indicators = [
            "cat", "ls", "cd", "find", "grep", "sort", "strings",
            "base64", "hexdump", "xxd", "file", "tar", "gzip", "bzip2",
        ]
        if not any(ind in command for ind in level_indicators):
            return
        if "bandit" not in self.terminal_output.lower():
            return

        level_matches = re.findall(r"bandit(\d+)", self.terminal_output.lower())
        if not level_matches:
            return

        try:
            new_level = int(level_matches[-1])
            if new_level != self.current_level:
                self.current_level = new_level
                terminal_lines = (
                    self.terminal_output.strip().split("\n") if self.terminal_output.strip() else []
                )
                ai_history = self.ai_mentor.conversation_history.get(self.session_id, [])
                self.session_manager.update_session_level(
                    self.session_id,
                    new_level,
                    terminal_history=terminal_lines,
                    ai_history=ai_history,
                )
                self.update_level_info()
                self.update_session_display()
                self.notify(
                    f"Detected level progression to Level {new_level}", severity="information"
                )
        except ValueError:
            pass

    # ─── AI Mentor ────────────────────────────────────────────────────────────

    def send_mentor_message(self) -> None:
        try:
            mentor_input = self.query_one("#mentor_input", Input)
            message = mentor_input.value.strip()
            if not message:
                return

            mentor_chat = self.query_one("#mentor_chat", TextArea)
            current_text = mentor_chat.text or ""
            mentor_chat.load_text(f"{current_text}\nYou: {message}\nMentor: ")

            for chunk in self.ai_mentor.get_response(
                message,
                self.session_id,
                self.current_level,
                self.recent_commands,
                self.terminal_output,
            ):
                mentor_chat.insert(chunk)

            mentor_input.value = ""
            self._mark_state_dirty()

        except Exception as e:
            self.notify(f"Error sending mentor message: {e}", severity="error")

    def clear_conversation_history(self) -> None:
        self.ai_mentor.clear_conversation(self.session_id)
        self.notify("Conversation history cleared", severity="information")

    def export_conversation(self) -> None:
        try:
            history = self.ai_mentor.conversation_history.get(self.session_id, [])
            if not history:
                self.notify("No conversation history to export", severity="warning")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.expanduser(f"~/Documents/bandit_cli_conversation_{timestamp}.md")
            content = (
                f"# Bandit CLI Conversation Export\n\n"
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"**Level:** {self.current_level}\n"
                f"**Session:** {self.session_id}\n\n---\n\n## Conversation History\n\n"
            )
            for i, msg in enumerate(history):
                content += f"**{i + 1}. {msg.get('role', 'unknown').title()}:** {msg.get('content', '')}\n\n"

            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.notify(f"Conversation exported to {export_path}", severity="information")
        except Exception as e:
            self.notify(f"Failed to export conversation: {e}", severity="error")

    # ─── Sessions ─────────────────────────────────────────────────────────────

    def create_new_session(self) -> None:
        try:
            if self.ssh_connected:
                self.disconnect_ssh()

            session_id = self.session_manager.create_session(
                name=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                current_level=self.current_level,
            )
            if session_id and self.session_manager.set_active_session(session_id):
                self.session_id = session_id
                new_session = self.session_manager.get_active_session()
                if new_session and new_session.level_start_time is None:
                    new_session.level_start_time = datetime.now()
                self.update_session_display()
                self.notify(f"Created new session: {session_id[:8]}...", severity="information")
            else:
                self.notify("Failed to switch to new session", severity="error")
        except Exception as e:
            self.notify(f"Failed to create session: {e}", severity="error")

    def show_session_switch_dialog(self) -> None:
        def after_switch(result: Optional[tuple[str, bool]]) -> None:
            if result is None:
                return
            session_id, restore_flag = result
            try:
                active = self.session_manager.get_active_session()
                if active and session_id == active.session_id:
                    self.notify("Already in this session", severity="information")
                    return
                if self.ssh_connected:
                    self.disconnect_ssh()
                if self.session_manager.set_active_session(session_id):
                    self.session_id = session_id
                    if restore_flag:
                        self._initialize_session()
                        self.notify("Switched and restored state", severity="information")
                    else:
                        session = self.session_manager.get_session(session_id)
                        if session:
                            self.current_level = session.current_level
                        self.update_level_info()
                        self.notify("Switched without restoring", severity="information")
                    self.update_session_display()
                else:
                    self.notify("Failed to switch session", severity="error")
            except Exception as e:
                self.notify(f"Error switching session: {e}", severity="error")

        self.push_screen(SessionSwitchModal(self.session_manager), after_switch)

    def show_delete_session_dialog(self) -> None:
        def after_delete(changed: bool) -> None:
            if changed:
                self.update_session_display()

        self.push_screen(DeleteSessionModal(self.session_manager), after_delete)

    def update_session_display(self) -> None:
        try:
            session = self.session_manager.get_active_session()
            display_widget = self.query_one("#current_session_display", Static)
            if session:
                ts = (
                    f" | Last saved: {session.last_saved_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    if session.last_saved_at
                    else ""
                )
                display_widget.update(
                    f"{session.get_display_name()} | Level {session.current_level}{ts}"
                )
            else:
                display_widget.update("No active session")

            try:
                save_indicator = self.query_one("#last_save_indicator", Static)
                save_indicator.update(
                    "✓ Saved" if session and session.last_saved_at else "⚠ Not saved"
                )
            except Exception:
                pass
        except Exception:
            pass

    def _initialize_session(self) -> None:
        try:
            self.create_new_session()
        except Exception as e:
            self._handle_error_and_stop_loading(f"Failed to initialize session: {e}")
            self.session_id = "default"
            self.current_level = 0
        self._session_has_content = False

    # ─── Auto-save ────────────────────────────────────────────────────────────

    def _mark_state_dirty(self) -> None:
        self._pending_save = True
        if self._save_timer is not None:
            self._save_timer.stop()
            self._save_timer = None
        self._save_timer = self.set_timer(
            self._save_debounce_seconds, self._auto_save_session_state
        )

    def _auto_save_session_state(self, force: bool = False) -> None:
        if not force and not self._pending_save:
            return
        try:
            try:
                terminal_widget = self.query_one("#terminal_output", EnhancedTerminalOutput)
                raw: Any = terminal_widget._virtual_buffer
                terminal_history_lines: list[str] = (
                    raw if isinstance(raw, list) else str(raw).splitlines()
                )
            except Exception:
                terminal_history_lines = self.terminal_output.splitlines()

            ai_history = self.ai_mentor.conversation_history.get(self.session_id, [])

            active_tab = "terminal"
            try:
                active_tab = self.query_one(TabbedContent).active
            except Exception:
                pass

            self.session_manager.update_session_state(
                session_id=self.session_id,
                terminal_history=terminal_history_lines,
                ai_history=ai_history,
                active_tab=active_tab,
            )
            self._last_save_time = time.time()
            self._pending_save = False

            if not force:
                try:
                    save_indicator = self.query_one("#last_save_indicator", Static)
                    save_indicator.update("✓ Auto-saved")
                    self.set_timer(3.0, lambda: save_indicator.update(""))
                except Exception:
                    pass
        except Exception as e:
            self._log_error(f"Auto-save failed: {e}")
        finally:
            self._save_timer = None

    # ─── Utility ──────────────────────────────────────────────────────────────

    def _navigate_history_up(self) -> None:
        try:
            cmd = self.command_history.get_previous()
            if cmd is not None:
                self.query_one("#command_input", Input).value = cmd
        except Exception:
            pass

    def _navigate_history_down(self) -> None:
        try:
            cmd = self.command_history.get_next()
            if cmd is not None:
                self.query_one("#command_input", Input).value = cmd
        except Exception:
            pass

    def _handle_error_and_stop_loading(self, message: str) -> None:
        self._log_error(f"Validation error: {message}")
        self.notify(self._get_user_friendly_error_message(message), severity="error")
        self.loading = False

    def _log_error(self, message: str) -> None:
        try:
            log_dir = os.path.expanduser("~/.bandit_cli/logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(
                log_dir, f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
        except Exception:
            pass

    def _get_user_friendly_error_message(self, technical_message: str) -> str:
        msg = technical_message.lower()
        if "connection" in msg or "network" in msg:
            if "timeout" in msg:
                return "🔌 Connection timeout. Check your internet connection and try again."
            if "refused" in msg:
                return "🚫 Connection refused. The server may be busy or down."
            if "authentication" in msg or "password" in msg:
                return "🔑 Authentication failed. Double-check your username and password."
            if "host" in msg:
                return "🌐 Host not found. Verify the server address and network connection."
            return "🔌 Network error. Check your connection and try again."
        if "invalid" in msg or "validation" in msg:
            if "username" in msg:
                return "👤 Invalid username. Use only letters, numbers, underscores, and hyphens."
            if "password" in msg:
                return "🔒 Password required. Please enter a valid password."
            if "port" in msg:
                return "🔌 Invalid port. Use a number between 1–65535."
            return "❌ Invalid input. Please check your input and try again."
        if "file" in msg or "not found" in msg:
            if "permission" in msg:
                return "🔒 Permission denied. Check file permissions."
            if "directory" in msg:
                return "📁 Directory not found. Check the file path."
            return "📄 File error. Check if the file exists and is accessible."
        if "ai" in msg or "mentor" in msg:
            if "api" in msg or "key" in msg:
                return "🤖 AI service unavailable. Check your API key and internet connection."
            if "rate" in msg or "limit" in msg:
                return "⏱️ Rate limit reached. Wait a moment before trying again."
            return "🧠 AI mentor error. Try again or check your configuration."
        return f"❌ Error: {technical_message}. Please try again or check the documentation."


def main() -> None:
    """Run the BanditCLI application."""
    BanditCLIApp().run()


if __name__ == "__main__":
    main()