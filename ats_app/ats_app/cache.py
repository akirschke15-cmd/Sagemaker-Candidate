"""
In-memory caching module with TTL support for ATS application.
Provides thread-safe caching with automatic cleanup of expired entries.
"""
import threading
import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
from datetime import datetime

try:
    from config import settings
except ImportError:
    # Fallback if imported from subdirectory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from config import settings


class CacheManager:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 30):
        """
        Initialize cache manager.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'invalidations': 0
        }
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background thread for automatic cleanup of expired entries."""
        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                time.sleep(60)  # Run every 60 seconds
                self._cleanup_expired()

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        now = time.time()
        with self._lock:
            expired_keys = [key for key, (_, expiry) in self._cache.items() if expiry < now]
            for key in expired_keys:
                del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if not settings.CACHE_ENABLED:
            self._stats['misses'] += 1
            return None

        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if expiry < time.time():
                del self._cache[key]
                self._stats['misses'] += 1
                return None

            self._stats['hits'] += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (defaults to instance default)
        """
        if not settings.CACHE_ENABLED:
            return

        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl

        with self._lock:
            self._cache[key] = (value, expiry)
            self._stats['sets'] += 1

    def delete(self, key: str):
        """
        Remove specific key from cache.

        Args:
            key: Cache key to remove
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching a prefix pattern.

        Args:
            pattern: Key prefix pattern to match
        """
        with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if key.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            self._stats['invalidations'] += len(keys_to_delete)

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats['deletes'] += 1

    def stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.

        Returns:
            Dictionary with hits, misses, size, and hit rate
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'invalidations': self._stats['invalidations'],
                'size': len(self._cache),
                'hit_rate': round(hit_rate, 2)
            }

    def stop(self):
        """Stop the cleanup thread (for clean shutdown)."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)


# Pre-configured cache instances
query_cache = CacheManager(default_ttl=settings.CACHE_DEFAULT_TTL)
analytics_cache = CacheManager(default_ttl=settings.CACHE_ANALYTICS_TTL)
ai_cache = CacheManager(default_ttl=settings.CACHE_AI_TTL)


def cached(cache_instance: CacheManager, ttl: int = None, key_prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        cache_instance: CacheManager instance to use
        ttl: Time-to-live in seconds (defaults to cache instance default)
        key_prefix: Prefix for cache keys

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]

            # Add args to key
            for arg in args:
                key_parts.append(str(arg))

            # Add kwargs to key (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")

            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# Cache invalidation helpers
def invalidate_candidate_caches():
    """Call after any candidate write operation."""
    query_cache.invalidate_pattern("candidates:")
    query_cache.invalidate_pattern("pipeline:")
    analytics_cache.invalidate_pattern("analytics:")


def invalidate_job_caches():
    """Call after any job write operation."""
    query_cache.invalidate_pattern("jobs:")
    analytics_cache.invalidate_pattern("analytics:")
