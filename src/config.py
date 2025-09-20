"""Configuration management for the Bandit CLI application."""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import copy


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            # Default config file location
            config_dir = Path.home() / ".bandit_cli"
            config_dir.mkdir(exist_ok=True)
            self.config_file = config_dir / "config.json"
        else:
            self.config_file = Path(config_file)
            
        # Default configuration
        self.default_config = {
            "ssh": {
                "host": "bandit.labs.overthewire.org",
                "port": 2220,
                "timeout": 10
            },
            "ui": {
                "theme": "dark",
                "max_recent_commands": 10
            },
            "ai": {
                "model": "gpt-3.5-turbo",
                "max_context_commands": 3,
                "fallback": True
            },
            "history": {
                "max_commands": 100,
                "persist": True
            },
            "cache": {
                "enable": True,
                "path": str(Path.home() / ".bandit_cli" / "cache")
            }
        }
        
        # Load configuration
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        # Start with default config
        config = copy.deepcopy(self.default_config)
        
        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                # Merge with default config
                config = self._merge_config(config, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        
        return config
    
    def _merge_config(self, default: Dict, override: Dict) -> Dict:
        """
        Recursively merge two configuration dictionaries.
        
        Args:
            default: Default configuration
            override: Configuration to override defaults
            
        Returns:
            Merged configuration
        """
        merged = default.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., "ssh.port")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., "ssh.port")
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save to file
        self.save_config()
    
    def reset_to_default(self):
        """Reset configuration to default values."""
        self.config = copy.deepcopy(self.default_config)
        self.save_config()