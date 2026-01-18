"""Level information management module for BanditCLI.

This module provides comprehensive level information management for the OverTheWire
Bandit wargame. It handles loading, formatting, and searching of level data from
JSON files, with fallback data handling for missing files.

The BanditLevelInfo class is the main interface for accessing level information,
including goals, recommended commands, and reading materials.
"""

import importlib.resources
import json
import os
import threading
from typing import Callable, Dict, List, Optional

from src.cache import Cache


class BanditLevelInfo:
    """Manager for Bandit level information and educational content.

    This class handles loading and managing level data for the OverTheWire Bandit
    wargame. It provides methods to access level information, format it for display,
    and search across levels. Includes robust error handling and fallback data.

    Attributes:
        levels_file_path (str): Path to the JSON file containing level data.
        notify (Callable[[str, str], None]): Callback for status notifications.
        levels_data (Dict): Loaded level data dictionary.
    """

    def __init__(
        self,
        levels_file_path: str = "bandit_levels.json",
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Initialize level info manager with file path and notification callback.

        Args:
            levels_file_path: Path to the JSON file containing level data.
            notify_callback: Optional callback for status notifications.
        """
        self.levels_file_path = levels_file_path
        self.notify = notify_callback or self._default_notify
        self.cache = Cache(cache_dir=None, default_ttl=7200)  # 2 hours TTL for level data
        # Lazy loading - don't load all data at startup
        self._levels_data: Optional[Dict] = None
        self._load_lock = threading.Lock()

    def _default_notify(self, message: str, severity: str = "info") -> None:
        """Default notification handler that prints messages to console.

        Args:
            message: The message to display.
            severity: The severity level of the message.
        """
        print(f"[{severity.upper()}] {message}")

    @property
    def levels_data(self) -> Dict:
        """Lazy-loaded property for level data.

        Returns:
            Dict: Loaded level data dictionary.
        """
        if self._levels_data is None:
            with self._load_lock:
                if self._levels_data is None:  # Double-check pattern
                    self._levels_data = self._load_levels_data()
        return self._levels_data or {}

    def _load_levels_data(self) -> Dict:
        # Try to load from cache first
        cache_key = f"levels_data_{self.levels_file_path}"
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            self.notify("Loaded level data from cache", severity="info")
            return cached_data

        # Load from file and cache the result
        data = self._load_levels_data_from_file()
        self.cache.set(cache_key, data, ttl=7200)  # Cache for 2 hours
        return data

    def _load_levels_data_from_file(self) -> Dict:
        """Load level data from file without caching (internal method)."""
        try:
            # Try to load from the src package first
            with importlib.resources.open_text("src", self.levels_file_path) as f:
                data = json.load(f)
                self.notify(
                    f"Loaded {len(data)} levels from {self.levels_file_path}", severity="info"
                )
                return data
        except (FileNotFoundError, AttributeError):
            # Fallback to relative path
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(current_dir, self.levels_file_path)
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.notify(f"Loaded {len(data)} levels from fallback path", severity="info")
                    return data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.notify(f"Error loading level data: {e}", severity="error")
                return self._get_fallback_data()
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON in level data file: {e}", severity="error")
            return self._get_fallback_data()

    def _get_fallback_data(self) -> Dict:
        """Provide basic fallback data if level file can't be loaded.

        Returns minimal level data for Level 0 to ensure the application
        remains functional even when the main data file is unavailable.

        Returns:
            Dict: Basic fallback level data.
        """
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

    def get_level_info(self, level_num: int) -> Optional[Dict]:
        """Get complete information for a specific level with caching.

        Args:
            level_num: The level number to retrieve information for.

        Returns:
            Optional[Dict]: Level information dictionary, or None if not found.
        """
        cache_key = f"level_info_{level_num}"
        cached_info = self.cache.get(cache_key)
        if cached_info is not None:
            return cached_info

        level_key = str(level_num)
        level_info = self.levels_data.get(level_key)

        # Cache the result (even if None, to avoid repeated lookups)
        self.cache.set(cache_key, level_info, ttl=3600)  # Cache for 1 hour

        return level_info

    def get_all_levels(self) -> Dict:
        """Get information for all available levels.

        Returns:
            Dict: Complete dictionary of all loaded level data.
        """
        return self.levels_data

    def get_available_levels(self) -> List[int]:
        """Get sorted list of available level numbers.

        Returns:
            List[int]: Sorted list of numeric level identifiers.
        """
        return sorted([int(k) for k in self.levels_data.keys() if k.isdigit()])

    def get_level_goal(self, level_num: int) -> str:
        """Get the goal description for a specific level.

        Args:
            level_num: The level number to get the goal for.

        Returns:
            str: The level goal description, or a default message if not found.
        """
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("goal", "Level information not available")
        return "Level information not available"

    def get_recommended_commands(self, level_num: int) -> List[str]:
        """Get recommended commands for a specific level.

        Args:
            level_num: The level number to get commands for.

        Returns:
            List[str]: List of recommended commands, or empty list if not found.
        """
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("commands", [])
        return []

    def get_reading_materials(self, level_num: int) -> List[Dict[str, str]]:
        """Get reading materials for a specific level.

        Args:
            level_num: The level number to get reading materials for.

        Returns:
            List[Dict[str, str]]: List of reading material dictionaries with title and URL.
        """
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("reading_material", [])
        return []

    def format_level_info(self, level_num: int) -> str:
        """Format level information as a readable markdown string with caching.

        Creates a formatted markdown representation of level information including
        title, goal, recommended commands, reading materials, and official level URL.
        Handles missing levels gracefully by showing available alternatives.
        Uses caching to improve performance for repeated access.

        Args:
            level_num: The level number to format information for.

        Returns:
            str: Formatted markdown string of level information.
        """
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

If you're working on a level beyond our data, refer to:
https://overthewire.org/wargames/bandit/"""
        else:
            formatted_info = self._format_level_info_from_data(level_num, level_info)

        # Cache the formatted result
        self.cache.set(cache_key, formatted_info, ttl=1800)  # Cache for 30 minutes

        return formatted_info

    def _format_level_info_from_data(self, level_num: int, level_info: Dict) -> str:
        """Format level information from data dictionary (internal method)."""
        formatted_info = f"# Bandit Level {level_num}"

        # Add title if available
        title = level_info.get("title", "")
        if title and title.strip():
            formatted_info += f" - {title}"

        formatted_info += "\n\n"

        # Add goal
        goal = level_info.get("goal", "")
        if goal:
            formatted_info += f"## Goal\n{goal}\n\n"

        # Add recommended commands
        commands = level_info.get("commands", [])
        if commands:
            formatted_info += "## Recommended Commands\n"
            for command in commands:
                formatted_info += f"- `{command}`\n"
            formatted_info += "\n"

        # Add reading materials
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

        # Add level URL if available
        url = level_info.get("url", "")
        if url:
            formatted_info += f"## Official Level Page\n[{url}]({url})\n\n"

        return formatted_info

    def search_levels(self, query: str) -> List[int]:
        """Search levels by goal description or command content.

        Performs a case-insensitive search across level goals and recommended
        commands to find levels matching the query.

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

            # Search in goal
            goal = level_data.get("goal", "").lower()
            if query_lower in goal:
                matching_levels.append(level_num)
                continue

            # Search in commands
            commands = level_data.get("commands", [])
            if any(query_lower in cmd.lower() for cmd in commands):
                matching_levels.append(level_num)

    def clear_cache(self) -> None:
        """Clear all level-related cache entries."""
        # Clear level data cache
        self.cache.clear_key(f"levels_data_{self.levels_file_path}")

        # Clear individual level caches
        available_levels = self.get_available_levels()
        for level in available_levels:
            self.cache.clear_key(f"level_info_{level}")
            self.cache.clear_key(f"formatted_level_info_{level}")

        self.notify("Level cache cleared", severity="info")
