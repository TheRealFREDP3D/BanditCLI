"""Unit tests for the caching module."""
import pytest
import os
import json
import time
from pathlib import Path
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cache import Cache


class TestCache:
    """Test cases for the Cache class."""
    
    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default values."""
        cache = Cache()
        
        # Check that cache directory was created
        assert cache.cache_dir.exists()
        assert ".bandit_cli" in str(cache.cache_dir)
        assert "cache" in str(cache.cache_dir)
        assert cache.default_ttl == 3600
    
    def test_init_with_custom_values(self, tmp_path):
        """Test initialization with custom values."""
        cache_dir = tmp_path / "custom_cache"
        cache = Cache(cache_dir=str(cache_dir), default_ttl=1800)
        
        assert cache.cache_dir == cache_dir
        assert cache.default_ttl == 1800
    
    def test_set_and_get(self, tmp_path):
        """Test setting and getting values from cache."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set a value
        cache.set("test_key", "test_value")
        
        # Get the value
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_get_nonexistent_key(self, tmp_path):
        """Test getting a nonexistent key from cache."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Get a nonexistent key
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_overwrite_existing_key(self, tmp_path):
        """Test overwriting an existing key in cache."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set initial value
        cache.set("test_key", "initial_value")
        
        # Overwrite with new value
        cache.set("test_key", "new_value")
        
        # Get the value
        result = cache.get("test_key")
        assert result == "new_value"
    
    def test_cache_expiration(self, tmp_path):
        """Test cache expiration."""
        cache = Cache(cache_dir=str(tmp_path), default_ttl=1)  # 1 second TTL
        
        # Set a value
        cache.set("test_key", "test_value")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Try to get the expired value
        result = cache.get("test_key")
        assert result is None
    
    def test_custom_ttl(self, tmp_path):
        """Test custom TTL for specific cache entries."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set a value with custom TTL
        cache.set("test_key", "test_value", ttl=1)  # 1 second TTL
        
        # Value should be available immediately
        result = cache.get("test_key")
        assert result == "test_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Value should be expired
        result = cache.get("test_key")
        assert result is None
    
    def test_clear_cache(self, tmp_path):
        """Test clearing all cache entries."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Verify values are set
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Clear cache
        cache.clear()
        
        # Verify values are cleared
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_clear_specific_key(self, tmp_path):
        """Test clearing a specific cache entry."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Verify values are set
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Clear specific key
        cache.clear_key("key1")
        
        # Verify only the specific key is cleared
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_cache_file_creation(self, tmp_path):
        """Test that cache files are created correctly."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set a value
        cache.set("test_key", "test_value")
        
        # Check that cache file was created
        cache_file = tmp_path / "test_key.cache"
        assert cache_file.exists()
        
        # Check file contents
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        assert data['value'] == "test_value"
        assert 'expires' in data
    
    def test_cache_key_sanitization(self, tmp_path):
        """Test that cache keys are properly sanitized."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Set values with problematic keys
        cache.set("", "empty_key_value")
        cache.set("key/with/slashes", "slash_key_value")
        cache.set("key with spaces", "space_key_value")
        
        # Check that values can be retrieved
        assert cache.get("") == "empty_key_value"
        assert cache.get("key/with/slashes") == "slash_key_value"
        assert cache.get("key with spaces") == "space_key_value"
    
    def test_cache_with_complex_data(self, tmp_path):
        """Test caching complex data structures."""
        cache = Cache(cache_dir=str(tmp_path))
        
        # Complex data structure
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "string": "test",
            "number": 42,
            "boolean": True
        }
        
        # Set and get complex data
        cache.set("complex_key", complex_data)
        result = cache.get("complex_key")
        
        assert result == complex_data
        assert isinstance(result, dict)
        assert result["list"] == [1, 2, 3]
        assert result["dict"] == {"nested": "value"}