"""Caching utilities for the Bandit CLI application."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class Cache:
    """A simple file-based cache with expiration support and statistics tracking."""

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files. If None, uses default location.
            default_ttl: Default time-to-live in seconds for cached items.
        """
        if cache_dir is None:
            # Default cache directory
            cache_dir_path = Path.home() / ".bandit_cli" / "cache"
        else:
            cache_dir_path = Path(cache_dir)

        self.cache_dir = cache_dir_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

        # Statistics tracking
        self.stats_file = self.cache_dir / "cache_stats.json"
        self.stats = self._load_stats()
        self.stats["hits"] = self.stats.get("hits", 0)
        self.stats["misses"] = self.stats.get("misses", 0)
        self.stats["sets"] = self.stats.get("sets", 0)
        self.stats["clears"] = self.stats.get("clears", 0)

    def _load_stats(self) -> dict[str, Any]:
        """Load cache statistics from file.

        Reads the cache statistics JSON file from disk. If the file doesn't exist
        or cannot be parsed, returns an empty dictionary.

        Returns:
            Dict: Cache statistics dictionary with keys 'hits', 'misses', 'sets', 'clears'.
        """
        if self.stats_file.exists():
            try:
                with open(self.stats_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_stats(self) -> None:
        """Save cache statistics to file.

        Writes the current cache statistics to the JSON file on disk.
        If the write fails, silently continues to avoid disrupting cache operations.
        """
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def _get_cache_file_path(self, key: str) -> Path:
        """Get the file path for a cache key.

        Converts a cache key into a safe filename by removing non-alphanumeric
        characters except for hyphens and underscores. This ensures the filename
        is valid across different filesystems.

        Args:
            key: The cache key to convert to a filename.

        Returns:
            Path: The full path to the cache file for the given key.
        """
        # Sanitize the key to create a valid filename
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_.").strip() or "default"
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
            with open(cache_file) as f:
                data = json.load(f)

            # Check if cache is expired
            if time.time() > data.get("expires", 0):
                cache_file.unlink()
                self.stats["misses"] += 1
                self._save_stats()
                return None

            self.stats["hits"] += 1
            self._save_stats()
            return data.get("value")
        except Exception:
            # If there's any error reading the cache, remove it
            if cache_file.exists():
                cache_file.unlink()
            self.stats["misses"] += 1
            self._save_stats()
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
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
            data = {"value": value, "expires": time.time() + ttl}

            # Save to file
            with open(cache_file, "w") as f:
                json.dump(data, f)

            self.stats["sets"] += 1
            self._save_stats()
        except Exception as e:
            print(f"Warning: Could not save to cache: {e}")

    def clear(self) -> None:
        """Clear all cached items."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            self.stats["clears"] += 1
            self._save_stats()
        except Exception as e:
            print(f"Warning: Could not clear cache: {e}")

    def clear_key(self, key: str) -> None:
        """Clear a specific cached item.

        Removes the cache file associated with the given key. If the file
        doesn't exist, the method completes silently.

        Args:
            key: The cache key to clear.
        """
        cache_file = self._get_cache_file_path(key)
        if cache_file.exists():
            cache_file.unlink()

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns comprehensive cache statistics including hit rate, total requests,
        and current cache size. The hit rate is calculated as a percentage.

        Returns:
            Dict: Dictionary containing:
                - hits (int): Number of cache hits.
                - misses (int): Number of cache misses.
                - sets (int): Number of cache sets.
                - clears (int): Number of cache clears.
                - hit_rate_percent (float): Hit rate as percentage.
                - total_requests (int): Total cache requests.
                - cache_size (int): Number of items currently in cache.
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "clears": self.stats["clears"],
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "cache_size": len(list(self.cache_dir.glob("*.cache"))),
        }

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries.

        Returns:
            int: Number of expired entries removed.
        """
        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                    if time.time() > data.get("expires", 0):
                        cache_file.unlink()
                        removed_count += 1
                except Exception:
                    # Remove corrupted cache files
                    cache_file.unlink()
                    removed_count += 1
        except Exception as e:
            print(f"Warning: Could not cleanup expired cache: {e}")

        return removed_count

    def generate_hash_key(self, level: int, question: str) -> str:
        """Generate a hash key for AI responses based on level and question.

        Args:
            level: The current level number.
            question: The user's question.

        Returns:
            str: A hash key for caching.
        """
        content = f"level_{level}_question_{question.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()


# Global cache instance
cache = Cache()
