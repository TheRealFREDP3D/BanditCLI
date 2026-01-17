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
from typing import Dict, List, Optional, Tuple

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
        lines = text.split('\n')
        self.buffer.extend(lines)
        
        # Rotate buffer if it exceeds max_lines
        if len(self.buffer) > self.max_lines:
            # Keep only the most recent lines
            excess = len(self.buffer) - self.max_lines
            self.buffer = self.buffer[excess:]
    def get_text(self) -> str:
        """Get all buffer content as a single string."""
        return '\n'.join(self.buffer)
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
    
    def size(self) -> int:
        """Get current buffer size in lines."""
        return len(self.buffer)


class ANSIColorParser:
    """Parser for ANSI color codes and terminal escape sequences."""

    # ANSI color mapping to Textual markup
    ANSI_TO_TEXTUAL = {
        '30': '[black]',  # Black
        '31': '[red]',  # Red
        '32': '[green]',  # Green
        '33': '[yellow]',  # Yellow
        '34': '[blue]',  # Blue
        '35': '[magenta]',  # Magenta
        '36': '[cyan]',  # Cyan
        '37': '[white]',  # White
        '90': '[dim black]',  # Bright Black (Gray)
        '91': '[bright red]',  # Bright Red
        '92': '[bright green]',  # Bright Green
        '93': '[bright yellow]',  # Bright Yellow
        '94': '[bright blue]',  # Bright Blue
        '95': '[bright magenta]',  # Bright Magenta
        '96': '[bright cyan]',  # Bright Cyan
        '97': '[bright white]',  # Bright White

        # Background colors
        '40': 'on black',
        '41': 'on red',
        '42': 'on green',
        '43': 'on yellow',
        '44': 'on blue',
        '45': 'on magenta',
        '46': 'on cyan',
        '47': 'on white',
        '100': 'on dim black',
        '101': 'on bright red',
        '102': 'on bright green',
        '103': 'on bright yellow',
        '104': 'on bright blue',
        '105': 'on bright magenta',
        '106': 'on bright cyan',
        '107': 'on bright white',
    }

    # ANSI reset codes
    RESET_CODES = {'0', '39', '49'}
    
    def __init__(self) -> None:
        self.ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        self.current_format = []
    
    def parse_ansi_text(self, text: str) -> str:
        """Parse ANSI escape sequences and convert to Textual markup."""
        if not text:
            return text
        
        # Find all ANSI escape sequences
        matches = list(self.ansi_pattern.finditer(text))
        if not matches:
            return text
        result = []
        last_end = 0
        
        for match in matches:
            # Add text before the escape sequence
            if match.start() > last_end:
                plain_text = text[last_end:match.start()]
                result.append(plain_text)

            # Parse the ANSI sequence
            ansi_code = match.group()
            parsed_format = self._parse_ansi_sequence(ansi_code)

            if parsed_format:
                result.append(parsed_format)

            last_end = match.end()
        # Add remaining text
        if last_end < len(text):
            result.append(text[last_end:])

        return ''.join(result)
    
    def _parse_ansi_sequence(self, ansi_code: str) -> str:
        """Parse a single ANSI escape sequence."""
        # Extract the numbers between \x1b[ and m
        code_content = ansi_code[2:-1]  # Remove \x1b[ and m
        if not code_content:
            return '[/]'  # Reset if no codes
        
        codes = code_content.split(';')
        result_parts = []
        
        for code in codes:
            if code in self.RESET_CODES:
                # Reset all formatting
                self.current_format.clear()
                return '[/]'
            elif code in self.ANSI_TO_TEXTUAL:
                # Add the formatting
                format_str = self.ANSI_TO_TEXTUAL[code]
                if 'on ' in format_str:
                    # Background color
                    result_parts.append(format_str)
                else:
                    # Foreground color or style
                    result_parts.append(format_str)
        if result_parts:
            return f"[{' '.join(result_parts)}]"
        
        return ''


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
        lines_before = text[:pos].split('\n')
        line = len(lines_before) - 1
        col = len(lines_before[-1])
        return line, col


class EnhancedTerminalOutput(TextArea):
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
        self._update_pending = False
        self._batch_buffer = []
        self._batch_size = 50  # Process updates in batches
        self._last_scroll_position = 0
    def append_text(self, text: str, scroll_to_bottom: bool = True) -> None:
        """Append text to the terminal output with enhanced features.
        
        Args:
            text: The text to append
            scroll_to_bottom: Whether to scroll to bottom after appending
        """
        # Parse ANSI color codes
        parsed_text = self.ansi_parser.parse_ansi_text(text)
        
        # Add to buffer
        self.buffer.append(parsed_text)
        
        # Batch updates for better performance
        self._batch_buffer.append(parsed_text)

        if len(self._batch_buffer) >= self._batch_size:
            self._flush_batch(scroll_to_bottom)
        else:
            # Schedule a batch flush if not already pending
            if not self._update_pending:
                self._update_pending = True
                self.set_timer(0.05, lambda: self._flush_batch(scroll_to_bottom))
    def _flush_batch(self, scroll_to_bottom: bool = True) -> None:
        """Flush the batch buffer to the UI."""
        if not self._batch_buffer:
            return
        
        batch_text = ''.join(self._batch_buffer)
        self._batch_buffer.clear()
        self._update_pending = False
        
        # Insert the batched text
        self.insert(batch_text)

        # Auto-scroll if enabled and requested
        if scroll_to_bottom and self.auto_scroll_enabled:
            self._scroll_to_bottom()
    def _scroll_to_bottom(self) -> None:
        """Scroll the terminal to the bottom."""
        try:
            # Get the total number of lines
            total_lines = len(self.text.split('\n'))
            if total_lines > 0:
                # Move cursor to the last line
                self.move_cursor((total_lines - 1, 0))
                # Scroll to make the cursor visible
                self.scroll_to_visible()
        except Exception:
            # If scrolling fails, continue without it
            pass
    def action_search(self) -> None:
        """Open search dialog."""
        # This would open a search input dialog
        # For now, we'll just show a notification
        self.app.notify("Press Ctrl+F to search (implementation pending)", severity="info")
    
    def action_search_next(self) -> None:
        """Go to next search result."""
        result = self.search.next_result()
        if result:
            line, start_col, end_col = result
            self.move_cursor((line, start_col))
            self.scroll_to_visible()
            self.app.notify(
                f"Result {self.search.current_result_index + 1}/{len(self.search.search_results)}",
                severity="info"
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
                severity="info"
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
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(self.buffer.get_text())

            self.app.notify(f"Terminal output exported to {export_path}", severity="success")
        except Exception as e:
            self.app.notify(f"Failed to export terminal output: {e}", severity="error")
    
    def action_clear(self) -> None:
        """Clear the terminal output."""
        self.buffer.clear()
        self.clear()
        self.search.clear_search()
        self.app.notify("Terminal output cleared", severity="info")
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling."""
        self.auto_scroll_enabled = enabled
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """Get buffer statistics."""
        return {
            "lines": self.buffer.size(),
            "max_lines": self.buffer.max_lines,
            "usage_percent": (self.buffer.size() / self.buffer.max_lines) * 100
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
        self.terminal.app.notify("Search dialog - implementation pending", severity="info")
    
    def perform_search(self, term: str, case_sensitive: bool = False) -> None:
        """Perform the search."""
        results = self.terminal.search.search(term, case_sensitive)
        if results > 0:
            self.terminal.app.notify(f"Found {results} matches for '{term}'", severity="success")
            # Go to first result
            self.terminal.action_search_next()
        else:
            self.terminal.app.notify(f"No matches found for '{term}'", severity="warning")
