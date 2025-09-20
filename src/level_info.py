import json
import os
from typing import Dict, List, Optional, Callable
import importlib.resources

from textual.app import Notify
class BanditLevelInfo:
    def __init__(self, levels_file_path: str = "bandit_levels.json", notify_callback: Callable[[str, str], None] = None):
        self.levels_file_path = levels_file_path
        self.notify = notify_callback
        self.levels_data = self._load_levels_data()
    
    def _load_levels_data(self) -> Dict:
        """Load level data from JSON file"""
        try:
            with importlib.resources.open_text("src", self.levels_file_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            if self.notify:
                self.notify(f"Error loading level data: {e}", "error")
            return {}
    
    def get_level_info(self, level_num: int) -> Optional[Dict]:
        """Get information for a specific level"""
        level_key = str(level_num)
        return self.levels_data.get(level_key)
    
    def get_all_levels(self) -> Dict:
        """Get information for all levels"""
        return self.levels_data
    
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
            return f"Level {level_num} information not available"
        
        formatted_info = f"# Bandit Level {level_num}\n\n"
        
        # Add goal
        goal = level_info.get("goal", "")
        if goal:
            formatted_info += f"## Goal\n{goal}\n\n"
        
        # Add recommended commands
        commands = level_info.get("commands", [])
        if commands:
            formatted_info += f"## Recommended Commands\n"
            for command in commands:
                formatted_info += f"- {command}\n"
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
        
        return formatted_info