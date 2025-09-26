"""Caching utilities for the Bandit CLI application."""
import json
import os
import time
from typing import Any, Optional, Dict
from pathlib import Path


class Cache:
    """A simple file-based cache with expiration support."""
    
    def __init__(self, cache_dir: str = None, default_ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files. If None, uses default location.
            default_ttl: Default time-to-live in seconds for cached items.
        """
        if cache_dir is None:
            # Default cache directory
            cache_dir = Path.home() / ".bandit_cli" / "cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_file_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Sanitize the key to create a valid filename
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_.").strip()
        if not safe_key:
            safe_key = "default"
        return self.cache_dir / f"{safe_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        cache_file = self._get_cache_file_path(key)
        
        if not cache_file.exists():
            return None
        
        try:
            # Load cached data
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if cache is expired
            if time.time() > data.get('expires', 0):
                cache_file.unlink()
                return None
            
            return data.get('value')
        except Exception:
            # If there's any error reading the cache, remove it
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds. If None, uses default_ttl.
        """
        if ttl is None:
            ttl = self.default_ttl
            
        cache_file = self._get_cache_file_path(key)
        
        try:
            # Create cache data with expiration time
            data = {
                'value': value,
                'expires': time.time() + ttl
            }
            
            # Save to file
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: Could not save to cache: {e}")
    
    def clear(self):
        """Clear all cached items."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            print(f"Warning: Could not clear cache: {e}")
    
    def clear_key(self, key: str):
        """Clear a specific cached item."""
        cache_file = self._get_cache_file_path(key)
        if cache_file.exists():
            cache_file.unlink()


# Global cache instance
cache = Cache()