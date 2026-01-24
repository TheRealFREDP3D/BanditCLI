"""Terminal output enhancements for BanditCLI.

This module provides enhanced terminal output functionality including:
- ANSI color code parsing and rendering
- Output buffering to prevent UI freezing
- Search functionality
- Export capabilities
- Size limits with rotation
- Performance optimizations
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from textual.binding import Binding
from textual.widgets import TextArea


@dataclass
class OutputBuffer:
    """Buffer for managing terminal output with size limits."""

    max_lines: int = 10000
    buffer: List[str] = None

    def __post_init__(self) -> None:
        if self.buffer is None:
            self.buffer = []

    def append(self, text: str) -> None:
        """Add text to buffer, enforcing size limits."""
        lines = text.split("\n")
        self.buffer.extend(lines)

        # Rotate buffer if it exceeds max_lines
        if len(self.buffer) > self.max_lines:
            # Keep only the most recent lines
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
    """Parser for ANSI color codes and terminal escape sequences."""

    def __init__(self) -> None:
        # Match CSI sequences (ending in letter) and OSC sequences (ending in BEL)
        self.ansi_pattern = re.compile(
            r"(?:\x1b\[\??[0-9;]*[a-zA-Z])|"  # CSI
            r"(?:\x1b\].*?\x07)"  # OSC
        )

    def parse_ansi_text(self, text: str) -> str:
        """Parse ANSI escape sequences and strip them for plain text display."""
        if not text:
            return text

        # Remove carriage returns usually associated with newlines in SSH output
        text = text.replace("\r\n", "\n").replace("\r", "")

        # Remove all ANSI sequences
        return self.ansi_pattern.sub("", text)


class TerminalOutputSearch:
    """Search functionality for terminal output."""

    def __init__(self, text_area: TextArea) -> None:
        self.text_area = text_area
        self.search_results: List[Tuple[int, int, int]] = []  # (line, start_col, end_col)
        self.current_result_index = 0
        self.search_term = ""

    def search(self, term: str, case_sensitive: bool = False) -> int:
        """Search for a term in the terminal output.

        Args:
            term: The search term
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            Number of matches found
        """
        if not term:
            self.clear_search()
            return 0

        self.search_term = term
        self.search_results.clear()
        self.current_result_index = 0

        text = self.text_area.text
        if not case_sensitive:
            search_text = text.lower()
            term = term.lower()
        else:
            search_text = text

        # Find all matches
        start = 0
        while True:
            pos = search_text.find(term, start)
            if pos == -1:
                break

            # Convert position to line and column
            line, col = self._position_to_line_col(text, pos)

            # Find end position
            end_pos = pos + len(term)
            end_line, end_col = self._position_to_line_col(text, end_pos)

            self.search_results.append((line, col, end_col))
            start = pos + 1

        return len(self.search_results)

    def next_result(self) -> Optional[Tuple[int, int, int]]:
        """Go to the next search result."""
        if not self.search_results:
            return None

        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
        else:
            self.current_result_index = 0  # Wrap around

        return self.search_results[self.current_result_index]

    def previous_result(self) -> Optional[Tuple[int, int, int]]:
        """Go to the previous search result."""
        if not self.search_results:
            return None

        if self.current_result_index > 0:
            self.current_result_index -= 1
        else:
            self.current_result_index = len(self.search_results) - 1  # Wrap around

        return self.search_results[self.current_result_index]

    def clear_search(self) -> None:
        """Clear search results."""
        self.search_results.clear()
        self.current_result_index = 0
        self.search_term = ""

    def _position_to_line_col(self, text: str, pos: int) -> Tuple[int, int]:
        """Convert a position in text to line and column numbers."""
        lines_before = text[:pos].split("\n")
        line = len(lines_before) - 1
        col = len(lines_before[-1])
        return line, col


class VirtualScrollingTextArea(TextArea):
    """TextArea with virtual scrolling for better performance with large content.

    Implements virtual scrolling to only render visible lines,
    significantly improving performance with large terminal output.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._virtual_buffer = []
        self._visible_start = 0
        self._visible_count = 100  # Number of lines to render
        self._total_lines = 0
        self._scroll_position = 0
        self._max_buffer_size = 50000  # Maximum lines to keep in memory

    def append_text(self, text: str, scroll_to_bottom: bool = True) -> None:
        """Append text with virtual scrolling optimization.

        Args:
            text: Text to append.
            scroll_to_bottom: Whether to scroll to bottom after appending.
        """
        lines = text.split("\n")

        # Add to virtual buffer
        self._virtual_buffer.extend(lines)

        # Enforce buffer size limit
        if len(self._virtual_buffer) > self._max_buffer_size:
            excess = len(self._virtual_buffer) - self._max_buffer_size
            self._virtual_buffer = self._virtual_buffer[excess:]
            self._total_lines = len(self._virtual_buffer)
        else:
            self._total_lines += len(lines)

        # Update visible range if scrolling to bottom
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
            # Move cursor to the bottom of the currently visible content
            # This ensures the widget physically scrolls to show the last line
            visible_rows = min(len(self._virtual_buffer), self._visible_count)
            if visible_rows > 0:
                self.move_cursor((visible_rows - 1, 0))

    def _update_display(self) -> None:
        """Update the visible display with current virtual buffer content."""
        # Get visible slice of buffer
        end_index = min(self._visible_start + self._visible_count, len(self._virtual_buffer))
        visible_lines = self._virtual_buffer[self._visible_start : end_index]

        # Update the TextArea with only visible content
        display_text = "\n".join(visible_lines)

        # Only update if content actually changed
        if self.text != display_text:
            self.load_text(display_text)

    def scroll_up(self, lines: int = 10, **kwargs: Any) -> None:
        """Scroll up by specified number of lines."""
        self._visible_start = max(0, self._visible_start - lines)
        self._update_display()

    def scroll_down(self, lines: int = 10, **kwargs: Any) -> None:
        """Scroll down by specified number of lines."""
        max_start = max(0, self._total_lines - self._visible_count)
        self._visible_start = min(max_start, self._visible_start + lines)
        self._update_display()

    def get_buffer_stats(self) -> Dict[str, int]:
        """Get buffer statistics for monitoring."""
        return {
            "total_lines": self._total_lines,
            "visible_lines": min(
                self._visible_count, len(self._virtual_buffer) - self._visible_start
            ),
            "buffer_size": len(self._virtual_buffer),
            "max_buffer_size": self._max_buffer_size,
            "usage_percent": (len(self._virtual_buffer) / self._max_buffer_size) * 100,
        }

    def clear(self) -> None:
        """Clear the text area and virtual buffer."""
        self._virtual_buffer.clear()
        self._total_lines = 0
        self._visible_start = 0
        super().clear()
        self._update_display()


class EnhancedTerminalOutput(VirtualScrollingTextArea):
    """Enhanced terminal output widget with advanced features."""

    BINDINGS = [
        Binding("ctrl+f", "search", "Search"),
        Binding("ctrl+n", "search_next", "Next Result"),
        Binding("ctrl+p", "search_previous", "Previous Result"),
        Binding("ctrl+e", "export", "Export"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("f3", "search_next", "Next Result"),
        Binding("shift+f3", "search_previous", "Previous Result"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.buffer = OutputBuffer(max_lines=10000)
        self.ansi_parser = ANSIColorParser()
        self.search = TerminalOutputSearch(self)
        self.auto_scroll_enabled = True

    def append_text(self, text: str, scroll_to_bottom: bool = True) -> None:
        """Append text to the terminal output with enhanced features.

        Args:
            text: The text to append
            scroll_to_bottom: Whether to scroll to bottom after appending
        """
        # Check for ANSI clear screen sequences (\x1b[2J or \x1b[3J)
        if "\x1b[2J" in text or "\x1b[3J" in text:
            self.clear()
            # If there's more text after the clear sequence, we should still process it
            # Strip the clear sequences and continue
            text = text.replace("\x1b[2J", "").replace("\x1b[3J", "")
            if not text.strip():
                return

        # Parse ANSI color codes (stripping them for plain text)
        parsed_text = self.ansi_parser.parse_ansi_text(text)

        # Add to buffer for export functionality
        self.buffer.append(parsed_text)

        # Delegate to parent's virtual scrolling implementation
        super().append_text(parsed_text, scroll_to_bottom)

    def action_search(self) -> None:
        """Open search dialog."""
        # This would open a search input dialog
        # For now, we'll just show a notification
        self.app.notify("Press Ctrl+F to search (implementation pending)", severity="information")

    def action_search_next(self) -> None:
        """Go to next search result."""
        result = self.search.next_result()
        if result:
            line, start_col, end_col = result
            self.move_cursor((line, start_col))
            self.scroll_to_visible()
            self.app.notify(
                f"Result {self.search.current_result_index + 1}/{len(self.search.search_results)}",
                severity="information",
            )
        else:
            self.app.notify("No search results", severity="warning")

    def action_search_previous(self) -> None:
        """Go to previous search result."""
        result = self.search.previous_result()
        if result:
            line, start_col, end_col = result
            self.move_cursor((line, start_col))
            self.scroll_to_visible()
            self.app.notify(
                f"Result {self.search.current_result_index + 1}/{len(self.search.search_results)}",
                severity="information",
            )
        else:
            self.app.notify("No search results", severity="warning")

    def action_export(self) -> None:
        """Export terminal output to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bandit_terminal_output_{timestamp}.txt"
            export_path = os.path.expanduser(f"~/Documents/{filename}")

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            # Write the output
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(self.buffer.get_text())

            self.app.notify(f"Terminal output exported to {export_path}", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to export terminal output: {e}", severity="error")

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling."""
        self.auto_scroll_enabled = enabled

    def clear(self) -> None:
        """Clear the terminal output and all buffers."""
        self.buffer.clear()
        self.search.clear_search()
        super().clear()

    def action_clear(self) -> None:
        """Clear the terminal output."""
        self.clear()
        self.app.notify("Terminal output cleared", severity="information")

    def get_buffer_stats(self) -> Dict[str, int]:
        """Get buffer statistics."""
        return {
            "lines": self.buffer.size(),
            "max_lines": self.buffer.max_lines,
            "usage_percent": (self.buffer.size() / self.buffer.max_lines) * 100,
        }


class OutputSearchDialog:
    """Dialog for searching terminal output."""

    def __init__(self, terminal_widget: EnhancedTerminalOutput) -> None:
        self.terminal = terminal_widget
        self.search_term = ""
        self.case_sensitive = False

    def show(self) -> None:
        """Show the search dialog."""
        # This would implement a proper search dialog
        # For now, we'll use a simple approach with notifications
        self.terminal.app.notify("Search dialog - implementation pending", severity="information")

    def perform_search(self, term: str, case_sensitive: bool = False) -> None:
        """Perform the search."""
        results = self.terminal.search.search(term, case_sensitive)
        if results > 0:
            self.terminal.app.notify(f"Found {results} matches for '{term}'", severity="information")
            # Go to first result
            self.terminal.action_search_next()
        else:
            self.terminal.app.notify(f"No matches found for '{term}'", severity="warning")
