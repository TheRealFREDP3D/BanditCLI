import json
import os
from typing import Dict, List, Optional

class BanditLevelInfo:
    def __init__(self, levels_file_path: str = "bandit_levels.json"):
        self.levels_file_path = levels_file_path
        self.levels_data = self._load_levels_data()
    
    def _load_levels_data(self) -> Dict:
        """Load level data from JSON file"""
        try:
            # First try to load from the current directory
            if os.path.exists(self.levels_file_path):
                with open(self.levels_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # If not found, try to load from the same directory as this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            levels_file = os.path.join(current_dir, "..", "bandit_levels.json")
            if os.path.exists(levels_file):
                with open(levels_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            print("Warning: Could not find bandit_levels.json file")
            return {}
        except Exception as e:
            print(f"Error loading level data: {e}")
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