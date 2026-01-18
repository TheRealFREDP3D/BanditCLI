"""Configuration management for the Bandit CLI application."""

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager.

        Sets up the configuration manager with default settings and loads
        the configuration from disk if it exists. Creates the configuration
        directory if it doesn't exist.

        Args:
            config_file: Path to configuration file. If None, uses default location
                at ~/.bandit_cli/config.json.

        Example:
            >>> # Use default config location
            >>> config = ConfigManager()
            >>> # Use custom config file
            >>> config = ConfigManager("/path/to/custom_config.json")
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
            "ssh": {"host": "bandit.labs.overthewire.org", "port": 2220, "timeout": 10},
            "ui": {"theme": "dark", "max_recent_commands": 10},
            "ai": {"model": "gpt-3.5-turbo", "max_context_commands": 3, "fallback": True},
            "history": {"max_commands": 100, "persist": True},
            "cache": {"enable": True, "path": str(Path.home() / ".bandit_cli" / "cache")},
        }

        # Load configuration
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file.

        Loads configuration from the JSON file on disk and merges it with the
        default configuration. If the file doesn't exist or cannot be parsed,
        returns the default configuration.

        Returns:
            Configuration dictionary with all settings merged from defaults
            and file overrides.

        Example:
            >>> config = ConfigManager()
            >>> settings = config.load_config()
            >>> print(settings['ssh']['host'])  # 'bandit.labs.overthewire.org'
        """
        # Start with default config
        config = copy.deepcopy(self.default_config)

        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    file_config = json.load(f)
                # Merge with default config
                config = self._merge_config(config, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")

        return config

    def _merge_config(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries.

        Deep merges the override dictionary into the default dictionary,
        preserving nested structure. Values in override take precedence over
        default values.

        Args:
            default: Default configuration dictionary.
            override: Configuration dictionary with overrides.

        Returns:
            Merged configuration dictionary.

        Example:
            >>> default = {'ssh': {'host': 'default.com', 'port': 22}}
            >>> override = {'ssh': {'port': 2220}}
            >>> result = self._merge_config(default, override)
            >>> # result == {'ssh': {'host': 'default.com', 'port': 2220}}
        """
        merged = default.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged

    def save_config(self) -> None:
        """Save current configuration to file.

        Writes the current configuration to the JSON file on disk. Creates the
        configuration directory if it doesn't exist. If the write fails,
        prints a warning but continues execution.

        Example:
            >>> config = ConfigManager()
            >>> config.set('ssh.port', 2220)
            >>> config.save_config()  # Saves to disk
        """
        try:
            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(exist_ok=True)

            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Retrieves a configuration value using a dot-separated path. If the key
        is not found, returns the provided default value.

        Args:
            key_path: Dot-separated path to configuration value
                (e.g., "ssh.port", "ai.model").
            default: Default value to return if key is not found.

        Returns:
            Configuration value or default if not found.

        Example:
            >>> config = ConfigManager()
            >>> host = config.get('ssh.host', 'localhost')
            >>> port = config.get('ssh.port', 22)
            >>> invalid = config.get('invalid.key', 'default')
        """
        keys = key_path.split(".")
        value = self.config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """Set a configuration value using dot notation.

        Sets a configuration value using a dot-separated path. Creates nested
        dictionaries as needed and saves the configuration to disk.

        Args:
            key_path: Dot-separated path to configuration value
                (e.g., "ssh.port", "ai.model").
            value: Value to set at the specified path.

        Example:
            >>> config = ConfigManager()
            >>> config.set('ssh.host', 'example.com')
            >>> config.set('ai.model', 'gpt-4')
            >>> config.set('new.nested.key', 'value')  # Creates nested structure
        """
        keys = key_path.split(".")
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

    def reset_to_default(self) -> None:
        """Reset configuration to default values.

        Resets all configuration values to their defaults and saves the
        configuration to disk. This overwrites any custom settings.

        Example:
            >>> config = ConfigManager()
            >>> config.set('ssh.port', 9999)  # Custom setting
            >>> config.reset_to_default()  # Resets to default port 2220
        """
        self.config = copy.deepcopy(self.default_config)
        self.save_config()
