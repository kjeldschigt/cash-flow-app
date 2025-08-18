"""
Cache utility functions and manager.
"""

import time
import threading
from typing import Any, Optional, Dict, Callable
from functools import wraps
from datetime import datetime, timedelta


class CacheManager:
    """Thread-safe in-memory cache manager."""

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return None

            entry["last_accessed"] = time.time()
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        with self._lock:
            ttl = ttl or self.default_ttl
            self._cache[key] = {
                "value": value,
                "created_at": time.time(),
                "ttl": ttl,
                "last_accessed": time.time(),
            }

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(
                1 for entry in self._cache.values() if self._is_expired(entry)
            )

            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_count,
                "expired_entries": expired_count,
                "memory_usage_bytes": self._estimate_memory_usage(),
            }

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() - entry["created_at"] > entry["ttl"]

    def _estimate_memory_usage(self) -> int:
        """Rough estimate of memory usage."""
        import sys

        total_size = 0
        for key, entry in self._cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(entry["value"])
            total_size += sys.getsizeof(entry)
        return total_size


# Global cache instance
_global_cache = CacheManager()


def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """Decorator for caching function results."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (
                    f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                )

            # Try to get from cache
            result = _global_cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            _global_cache.set(cache_key, result, ttl)
            return result

        # Add cache management methods to function
        wrapper.cache_clear = lambda: _global_cache.clear()
        wrapper.cache_delete = lambda key: _global_cache.delete(key)
        wrapper.cache_stats = lambda: _global_cache.get_stats()

        return wrapper

    return decorator


def cache_key_for_user_data(user_id: str, data_type: str) -> str:
    """Generate cache key for user-specific data."""
    return f"user:{user_id}:{data_type}"


def cache_key_for_date_range(start_date: str, end_date: str, data_type: str) -> str:
    """Generate cache key for date range queries."""
    return f"date_range:{data_type}:{start_date}:{end_date}"
