"""Terminal output enhancements for BanditCLI.

This module provides enhanced terminal output functionality including:
- ANSI escape sequence stripping
- Output buffering with configurable size limits
- Virtual scrolling for performance with large output
- Export capabilities
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from textual.binding import Binding
from textual.events import Key
from textual.widgets import TextArea


@dataclass
class OutputBuffer:
    """Buffer for managing terminal output with size limits."""

    max_lines: int = 10000
    buffer: list[str] = field(default_factory=list)

    def append(self, text: str) -> None:
        """Add text to buffer, enforcing size limits."""
        self.buffer.extend(text.split("\n"))
        if len(self.buffer) > self.max_lines:
            excess = len(self.buffer) - self.max_lines
            self.buffer = self.buffer[excess:]

    def get_text(self) -> str:
        """Get all buffer content as a single string."""
        return "\n".join(self.buffer)

    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()

    def size(self) -> int:
        """Get current buffer size in lines."""
        return len(self.buffer)


class ANSIColorParser:
    """Parser that strips ANSI escape sequences for plain-text display."""

    def __init__(self) -> None:
        self._ansi_pattern = re.compile(
            r"(?:\x1b\[\??[0-9;]*[a-zA-Z])|"  # CSI sequences
            r"(?:\x1b\].*?\x07)"  # OSC sequences
        )

    def parse_ansi_text(self, text: str) -> str:
        """Strip ANSI escape sequences and normalise line endings.

        Args:
            text: Raw terminal text that may contain ANSI codes.

        Returns:
            Plain text with escape sequences removed.
        """
        if not text:
            return text
        text = text.replace("\r\n", "\n").replace("\r", "")
        return self._ansi_pattern.sub("", text)


class VirtualScrollingTextArea(TextArea):
    """TextArea with virtual scrolling for large terminal output.

    Only the visible window of lines is passed to the underlying TextArea,
    significantly improving performance with large output buffers.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._virtual_buffer: list[str] = []
        self._visible_start = 0
        self._visible_count = 100
        self._total_lines = 0
        self._max_buffer_size = 50000

    def append_text(self, text: str, scroll_to_bottom: bool = True) -> None:
        """Append text with virtual scrolling.

        Args:
            text: Text to append.
            scroll_to_bottom: Whether to scroll to bottom after appending.
        """
        lines = text.split("\n")
        self._virtual_buffer.extend(lines)

        if len(self._virtual_buffer) > self._max_buffer_size:
            excess = len(self._virtual_buffer) - self._max_buffer_size
            self._virtual_buffer = self._virtual_buffer[excess:]

        self._total_lines = len(self._virtual_buffer)

        if scroll_to_bottom:
            self.scroll_to_bottom(refresh=True)
        else:
            self._update_display()

    def scroll_to_bottom(self, refresh: bool = True) -> None:
        """Scroll to the bottom of the content.

        Args:
            refresh: Whether to refresh the display immediately.
        """
        if self._total_lines > self._visible_count:
            self._visible_start = self._total_lines - self._visible_count
        else:
            self._visible_start = 0

        if refresh:
            self._update_display()
            visible_rows = min(len(self._virtual_buffer), self._visible_count)
            if visible_rows > 0:
                self.move_cursor((visible_rows - 1, 0))

    def _update_display(self) -> None:
        """Render the visible slice of the virtual buffer into the TextArea."""
        end_index = min(self._visible_start + self._visible_count, len(self._virtual_buffer))
        visible_lines = self._virtual_buffer[self._visible_start : end_index]
        display_text = "\n".join(visible_lines)

        if self.text != display_text:
            self.load_text(display_text)

    def scroll_up(self, lines: int = 10, **kwargs: Any) -> None:
        """Scroll up by the specified number of lines."""
        self._visible_start = max(0, self._visible_start - lines)
        self._update_display()

    def scroll_down(self, lines: int = 10, **kwargs: Any) -> None:
        """Scroll down by the specified number of lines."""
        max_start = max(0, self._total_lines - self._visible_count)
        self._visible_start = min(max_start, self._visible_start + lines)
        self._update_display()

    def get_buffer_stats(self) -> dict[str, Any]:
        """Get virtual buffer statistics."""
        return {
            "total_lines": self._total_lines,
            "visible_lines": min(
                self._visible_count, len(self._virtual_buffer) - self._visible_start
            ),
            "buffer_size": len(self._virtual_buffer),
            "max_buffer_size": self._max_buffer_size,
            "usage_percent": (len(self._virtual_buffer) / self._max_buffer_size) * 100,
        }

    def clear(self) -> Any:  # type: ignore[override]
        """Clear the text area and virtual buffer."""
        self._virtual_buffer.clear()
        self._total_lines = 0
        self._visible_start = 0
        super().clear()
        self._update_display()


class EnhancedTerminalOutput(VirtualScrollingTextArea):
    """Enhanced terminal output widget with ANSI parsing and export."""

    BINDINGS = [
        Binding("ctrl+e", "export", "Export"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.buffer = OutputBuffer(max_lines=10000)
        self.ansi_parser = ANSIColorParser()
        self.auto_scroll_enabled = True
        self.ssh_input_callback: Optional[Any] = None

    def set_ssh_input_callback(self, callback: Optional[Any]) -> None:
        """Set the callback for handling SSH key input.

        Args:
            callback: Function to call with key events when SSH is connected.
                      Pass None to disable SSH input forwarding.
        """
        self.ssh_input_callback = callback

    def on_key(self, event: Key) -> None:
        """Forward key events to SSH when a callback is set.

        Args:
            event: The key event.
        """
        if self.ssh_input_callback:
            self.ssh_input_callback(event)
            return
        super()._on_key(event)

    def append_text(self, text: str, scroll_to_bottom: bool = True) -> None:
        """Append text to the terminal, stripping ANSI codes.

        Handles ANSI clear-screen sequences by clearing the buffer first.

        Args:
            text: Raw text (may contain ANSI escape codes).
            scroll_to_bottom: Whether to scroll to bottom after appending.
        """
        if "\x1b[2J" in text or "\x1b[3J" in text:
            self.clear()
            text = text.replace("\x1b[2J", "").replace("\x1b[3J", "")
            if not text.strip():
                return

        parsed_text = self.ansi_parser.parse_ansi_text(text)
        self.buffer.append(parsed_text)
        super().append_text(parsed_text, scroll_to_bottom)

    def action_export(self) -> None:
        """Export terminal output to a timestamped text file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.expanduser(f"~/Documents/bandit_terminal_output_{timestamp}.txt")
            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                f.write(self.buffer.get_text())

            self.app.notify(f"Terminal output exported to {export_path}", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to export terminal output: {e}", severity="error")

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling.

        Args:
            enabled: True to enable auto-scroll, False to disable.
        """
        self.auto_scroll_enabled = enabled

    def clear(self) -> None:  # type: ignore[override]
        """Clear the terminal output and all internal buffers."""
        self.buffer.clear()
        super().clear()

    def action_clear(self) -> None:
        """Clear the terminal output (bound action)."""
        self.clear()
        self.app.notify("Terminal output cleared", severity="information")

    def get_buffer_stats(self) -> dict[str, Any]:
        """Get output buffer statistics."""
        return {
            "lines": self.buffer.size(),
            "max_lines": self.buffer.max_lines,
            "usage_percent": (self.buffer.size() / self.buffer.max_lines) * 100,
        }
