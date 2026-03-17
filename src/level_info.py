"""Level information management module for BanditCLI.

This module provides comprehensive level information management for the
OverTheWire Bandit wargame. It handles loading, formatting, and searching
of level data from JSON files, with fallback data handling for missing files.

The BanditLevelInfo class is the main interface for accessing level information,
including goals, recommended commands, and reading materials.
"""

import importlib.resources
import json
import os
import threading
from typing import Callable, Optional

from .cache import Cache


class BanditLevelInfo:
    """Manager for Bandit level information and educational content.

    Attributes:
        levels_file_path (str): Path to the JSON file containing level data.
        notify (Callable[[str, str], None]): Callback for status notifications.
    """

    def __init__(
        self,
        levels_file_path: str = "bandit_levels.json",
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.levels_file_path = levels_file_path
        self.notify = notify_callback or self._default_notify
        self.cache = Cache(cache_dir=None, default_ttl=7200)
        self._levels_data: Optional[dict] = None
        self._load_lock = threading.Lock()

    def _default_notify(self, message: str, severity: str = "info") -> None:
        print(f"[{severity.upper()}] {message}")

    @property
    def levels_data(self) -> dict:
        """Lazy-loaded property for level data."""
        if self._levels_data is None:
            with self._load_lock:
                if self._levels_data is None:
                    self._levels_data = self._load_levels_data()
        return self._levels_data or {}

    def _load_levels_data(self) -> dict:
        cache_key = f"levels_data_{self.levels_file_path}"
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            self.notify("Loaded level data from cache", "info")
            return cached_data

        data = self._load_levels_data_from_file()
        self.cache.set(cache_key, data, ttl=7200)
        return data

    def _load_levels_data_from_file(self) -> dict:
        """Load level data from file without caching (internal method)."""
        try:
            with importlib.resources.open_text("src", self.levels_file_path) as f:
                data = json.load(f)
                self.notify(f"Loaded {len(data)} levels from {self.levels_file_path}", "info")
                return data
        except (FileNotFoundError, AttributeError):
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(current_dir, self.levels_file_path)
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.notify(f"Loaded {len(data)} levels from fallback path", "info")
                    return data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.notify(f"Error loading level data: {e}", "error")
                return self._get_fallback_data()
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON in level data file: {e}", "error")
            return self._get_fallback_data()

    def _get_fallback_data(self) -> dict:
        """Provide basic fallback data if level file can't be loaded."""
        return {
            "0": {
                "level": 0,
                "title": "Level 0",
                "goal": "Connect to bandit.labs.overthewire.org on port 2220 using SSH.\nUsername: bandit0, Password: bandit0",
                "commands": ["ssh"],
                "reading_material": [],
                "url": "https://overthewire.org/wargames/bandit/bandit0.html",
            }
        }

    def get_level_info(self, level_num: int) -> Optional[dict]:
        """Get complete information for a specific level with caching."""
        cache_key = f"level_info_{level_num}"
        cached_info = self.cache.get(cache_key)
        if cached_info is not None:
            return cached_info

        level_info = self.levels_data.get(str(level_num))
        self.cache.set(cache_key, level_info, ttl=3600)
        return level_info

    def get_all_levels(self) -> dict:
        """Get information for all available levels."""
        return self.levels_data

    def get_available_levels(self) -> list[int]:
        """Get sorted list of available level numbers."""
        return sorted([int(k) for k in self.levels_data.keys() if k.isdigit()])

    def get_level_goal(self, level_num: int) -> str:
        """Get the goal description for a specific level."""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("goal", "Level information not available")
        return "Level information not available"

    def get_recommended_commands(self, level_num: int) -> list[str]:
        """Get recommended commands for a specific level."""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("commands", [])
        return []

    def get_reading_materials(self, level_num: int) -> list[dict[str, str]]:
        """Get reading materials for a specific level."""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("reading_material", [])
        return []

    def format_level_info(self, level_num: int) -> str:
        """Format level information as a readable markdown string with caching."""
        cache_key = f"formatted_level_info_{level_num}"
        cached_formatted = self.cache.get(cache_key)
        if cached_formatted is not None:
            return cached_formatted

        level_info = self.get_level_info(level_num)
        if not level_info:
            available_levels = self.get_available_levels()
            formatted_info = f"""# Level {level_num} - Not Available

Level {level_num} information is not available.

Available levels: {', '.join(map(str, available_levels))}

If you're working on a level beyond our data, refer to: https://overthewire.org/wargames/bandit/"""
        else:
            formatted_info = self._format_level_info_from_data(level_num, level_info)

        self.cache.set(cache_key, formatted_info, ttl=1800)
        return formatted_info

    def _format_level_info_from_data(self, level_num: int, level_info: dict) -> str:
        """Format level information from data dictionary (internal method)."""
        formatted_info = f"# Bandit Level {level_num}"

        title = level_info.get("title", "")
        if title and title.strip():
            formatted_info += f" - {title}"

        formatted_info += "\n\n"

        goal = level_info.get("goal", "")
        if goal:
            formatted_info += f"## Goal\n{goal}\n\n"

        commands = level_info.get("commands", [])
        if commands:
            formatted_info += "## Recommended Commands\n"
            for command in commands:
                formatted_info += f"- `{command}`\n"
            formatted_info += "\n"

        materials = level_info.get("reading_material", [])
        if materials:
            formatted_info += "## Reading Materials\n"
            for material in materials:
                if isinstance(material, dict):
                    title = material.get("title", "")
                    url = material.get("url", "")
                    if title and url:
                        formatted_info += f"- [{title}]({url})\n"
                    elif title:
                        formatted_info += f"- {title}\n"
                elif isinstance(material, str):
                    formatted_info += f"- {material}\n"
            formatted_info += "\n"

        url = level_info.get("url", "")
        if url:
            formatted_info += f"## Official Level Page\n[{url}]({url})\n\n"

        return formatted_info

    def search_levels(self, query: str) -> list[int]:
        """Search levels by goal description or command content.

        Args:
            query: Search query string.

        Returns:
            List[int]: Sorted list of matching level numbers.
        """
        query_lower = query.lower()
        matching_levels = []

        for level_key, level_data in self.levels_data.items():
            if not level_key.isdigit():
                continue

            level_num = int(level_key)

            goal = level_data.get("goal", "").lower()
            if query_lower in goal:
                matching_levels.append(level_num)
                continue

            commands = level_data.get("commands", [])
            if any(query_lower in cmd.lower() for cmd in commands):
                matching_levels.append(level_num)

        return sorted(matching_levels)  # FIX: was missing return statement

    def clear_cache(self) -> None:
        """Clear all level-related cache entries."""
        self.cache.clear_key(f"levels_data_{self.levels_file_path}")

        available_levels = self.get_available_levels()
        for level in available_levels:
            self.cache.clear_key(f"level_info_{level}")
            self.cache.clear_key(f"formatted_level_info_{level}")

        self.notify("Level cache cleared", "info")
