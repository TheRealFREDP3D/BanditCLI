"""Unit tests for the configuration module."""
import pytest
import os
import json
from pathlib import Path
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import ConfigManager


class TestConfigManager:
    """Test cases for the ConfigManager class."""
    
    def test_init_with_default_config(self, tmp_path):
        """Test initialization with default configuration."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        
        # Check that default config is loaded
        assert manager.get("ssh.host") == "bandit.labs.overthewire.org"
        assert manager.get("ssh.port") == 2220
        assert manager.get("ui.theme") == "dark"
    
    def test_load_config_from_file(self, tmp_path):
        """Test loading configuration from file."""
        # Create a config file with custom values
        config_file = tmp_path / "config.json"
        custom_config = {
            "ssh": {
                "host": "custom.host",
                "port": 2222
            },
            "ui": {
                "theme": "light"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(custom_config, f)
        
        # Load config
        manager = ConfigManager(str(config_file))
        
        # Check that custom values are loaded
        assert manager.get("ssh.host") == "custom.host"
        assert manager.get("ssh.port") == 2222
        assert manager.get("ui.theme") == "light"
        
        # Check that default values are still there for unspecified keys
        assert manager.get("ai.fallback") == True
    
    def test_get_with_default(self, tmp_path):
        """Test getting configuration values with default fallback."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        
        # Test existing key
        assert manager.get("ssh.port", 3000) == 2220
        
        # Test non-existing key with default
        assert manager.get("non.existing.key", "default_value") == "default_value"
    
    def test_set_and_save(self, tmp_path):
        """Test setting configuration values and saving to file."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        
        # Set a new value
        manager.set("ssh.port", 3000)
        
        # Check that the value is set
        assert manager.get("ssh.port") == 3000
        
        # Reload from file and check that the value persists
        manager2 = ConfigManager(str(config_file))
        assert manager2.get("ssh.port") == 3000
    
    def test_reset_to_default(self, tmp_path):
        """Test resetting configuration to default values."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        
        # Change a value
        manager.set("ssh.port", 3000)
        assert manager.get("ssh.port") == 3000
        
        # Reset to default
        manager.reset_to_default()
        
        # Check that the value is reset
        assert manager.get("ssh.port") == 2220
        
        # Also test that a new manager instance loads the reset values
        manager2 = ConfigManager(str(config_file))
        assert manager2.get("ssh.port") == 2220