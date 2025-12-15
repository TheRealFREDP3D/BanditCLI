import json
import os
from typing import Dict, List, Optional, Callable
import importlib.resources
from textual.app import Notify
class BanditLevelInfo:
    def __init__(self, levels_file_path: str = "bandit_levels.json", notify_callback: Callable[[str, str], None] = None):
        self.levels_file_path = levels_file_path
        self.notify = notify_callback or self._default_notify
        self.levels_data = self._load_levels_data()

    def _default_notify(self, message: str, severity: str = "info"):
        """Default notification handler"""
        print(f"[{severity.upper()}] {message}")

    def _load_levels_data(self) -> Dict:
        """Load level data from JSON file with better error handling"""
        try:
            # Try to load from the src package first
            with importlib.resources.open_text("src", self.levels_file_path) as f:
                data = json.load(f)
                self.notify(f"Loaded {len(data)} levels from {self.levels_file_path}", "info")
                return data
        except (FileNotFoundError, AttributeError):
            # Fallback to relative path
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(current_dir, self.levels_file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notify(f"Loaded {len(data)} levels from fallback path", "info")
                    return data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.notify(f"Error loading level data: {e}", "error")
                return self._get_fallback_data()
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON in level data file: {e}", "error")
            return self._get_fallback_data()

    def _get_fallback_data(self) -> Dict:
        """Provide basic fallback data if file can't be loaded"""
        return {
            "0": {
                "level": 0,
                "title": "Level 0",
                "goal": "Connect to bandit.labs.overthewire.org on port 2220 using SSH.\nUsername: bandit0, Password: bandit0",
                "commands": ["ssh"],
                "reading_material": [],
                "url": "https://overthewire.org/wargames/bandit/bandit0.html"
            }
        }
    def get_level_info(self, level_num: int) -> Optional[Dict]:
        """Get information for a specific level"""
        level_key = str(level_num)
        return self.levels_data.get(level_key)

    def get_all_levels(self) -> Dict:
        """Get information for all levels"""
        return self.levels_data

    def get_available_levels(self) -> List[int]:
        """Get list of available level numbers"""
        return sorted([int(k) for k in self.levels_data.keys() if k.isdigit()])

    def get_level_goal(self, level_num: int) -> str:
        """Get the goal for a specific level"""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("goal", "Level information not available")
        return "Level information not available"

    def get_recommended_commands(self, level_num: int) -> List[str]:
        """Get recommended commands for a specific level"""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("commands", [])
        return []

    def get_reading_materials(self, level_num: int) -> List[Dict[str, str]]:
        """Get reading materials for a specific level"""
        level_info = self.get_level_info(level_num)
        if level_info:
            return level_info.get("reading_material", [])
        return []

    def format_level_info(self, level_num: int) -> str:
        """Format level information as a readable string"""
        level_info = self.get_level_info(level_num)
        if not level_info:
            available_levels = self.get_available_levels()
            return f"""# Level {level_num} - Not Available

Level {level_num} information is not available.

Available levels: {', '.join(map(str, available_levels))}

If you're working on a level beyond our data, refer to:
https://overthewire.org/wargames/bandit/"""

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
            formatted_info += f"## Recommended Commands\n"
            for command in commands:
                formatted_info += f"- `{command}`\n"
            formatted_info += "\n"

        # Add reading materials
        materials = level_info.get("reading_material", [])
        if materials:
            formatted_info += f"## Reading Materials\n"
            for material in materials:
                title = material.get("title", "")
                url = material.get("url", "")
                if title and url:
                    formatted_info += f"- [{title}]({url})\n"
                elif title:
                    formatted_info += f"- {title}\n"
            formatted_info += "\n"

        # Add level URL if available
        url = level_info.get("url", "")
        if url:
            formatted_info += f"## Official Level Page\n[{url}]({url})\n\n"

        return formatted_info

    def search_levels(self, query: str) -> List[int]:
        """Search levels by goal or command content"""
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
        
        return sorted(matching_levels)
