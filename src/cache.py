"""Caching utilities for the Bandit CLI application."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class Cache:
    """A simple file-based cache with expiration support and statistics tracking."""

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 3600):
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files. If None, uses default location.
            default_ttl: Default time-to-live in seconds for cached items.
        """
        if cache_dir is None:
            cache_dir_path = Path.home() / ".bandit_cli" / "cache"
        else:
            cache_dir_path = Path(cache_dir)

        self.cache_dir = cache_dir_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

        self.stats_file = self.cache_dir / "cache_stats.json"
        self.stats = self._load_stats()
        self.stats.setdefault("hits", 0)
        self.stats.setdefault("misses", 0)
        self.stats.setdefault("sets", 0)
        self.stats.setdefault("clears", 0)

    def _load_stats(self) -> dict[str, Any]:
        """Load cache statistics from file."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_stats(self) -> None:
        """Save cache statistics to file."""
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def _get_cache_file_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_.").strip() or "default"
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        cache_file = self._get_cache_file_path(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            if time.time() > data.get("expires", 0):
                cache_file.unlink()
                self.stats["misses"] += 1
                self._save_stats()
                return None

            self.stats["hits"] += 1
            self._save_stats()
            return data.get("value")
        except Exception:
            if cache_file.exists():
                cache_file.unlink()
            self.stats["misses"] += 1
            self._save_stats()
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds. If None, uses default_ttl.
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_file = self._get_cache_file_path(key)

        try:
            data = {"value": value, "expires": time.time() + ttl}
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

        Args:
            key: The cache key to clear.
        """
        cache_file = self._get_cache_file_path(key)
        if cache_file.exists():
            cache_file.unlink()

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, sets, clears, hit_rate_percent,
            total_requests, and cache_size.
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
