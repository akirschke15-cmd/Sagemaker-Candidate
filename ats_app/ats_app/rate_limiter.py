"""Rate limiting module for ATS application.

Provides in-memory, thread-safe rate limiting using sliding window pattern.
Designed for Streamlit applications without external dependencies.
"""
import logging
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Tuple, Dict, Deque

from config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe in-memory rate limiter using sliding window pattern.

    Attributes:
        _requests: Dictionary mapping keys to deques of request timestamps
        _lock: Thread lock for synchronization
        _last_cleanup: Timestamp of last cleanup operation
        _cleanup_interval: Seconds between automatic cleanup operations
    """

    def __init__(self, cleanup_interval: int = 300):
        """Initialize rate limiter.

        Args:
            cleanup_interval: Seconds between automatic cleanup of expired entries (default: 5 minutes)
        """
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval
        logger.info("RateLimiter initialized with cleanup_interval=%d seconds", cleanup_interval)

    def _cleanup_expired_entries(self, max_window: int = 3600) -> None:
        """Remove expired entries to prevent memory leaks.

        Args:
            max_window: Maximum window size to consider (default: 1 hour)
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        with self._lock:
            cutoff_time = now - max_window
            keys_to_remove = []

            for key, timestamps in self._requests.items():
                # Remove timestamps older than max_window
                while timestamps and timestamps[0] < cutoff_time:
                    timestamps.popleft()

                # Remove empty keys
                if not timestamps:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]

            self._last_cleanup = now
            if keys_to_remove:
                logger.debug("Cleaned up %d expired rate limit entries", len(keys_to_remove))

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """Check if a request should be allowed under rate limit.

        Uses sliding window: counts requests within the last window_seconds.

        Args:
            key: Unique identifier for the rate limit bucket (e.g., IP address, email, token)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, retry_after_seconds):
                - allowed: True if request is allowed, False if rate limited
                - retry_after_seconds: Seconds to wait before retrying (0 if allowed)
        """
        now = time.time()
        cutoff_time = now - window_seconds

        # Periodic cleanup
        self._cleanup_expired_entries(max_window=window_seconds)

        with self._lock:
            timestamps = self._requests[key]

            # Remove timestamps outside the current window
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()

            # Check if under limit
            if len(timestamps) < max_requests:
                timestamps.append(now)
                logger.debug("Rate limit check passed: key=%s, count=%d/%d", key, len(timestamps), max_requests)
                return True, 0

            # Calculate retry time (when oldest request falls outside window)
            oldest_timestamp = timestamps[0]
            retry_after = int(oldest_timestamp + window_seconds - now) + 1

            logger.warning(
                "Rate limit exceeded: key=%s, count=%d/%d, retry_after=%ds",
                key, len(timestamps), max_requests, retry_after
            )
            return False, retry_after

    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key.

        Useful for testing or manual intervention.

        Args:
            key: Rate limit key to reset
        """
        with self._lock:
            if key in self._requests:
                del self._requests[key]
                logger.info("Rate limit reset for key=%s", key)

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests allowed in current window.

        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Number of remaining requests (0 if rate limited)
        """
        now = time.time()
        cutoff_time = now - window_seconds

        with self._lock:
            timestamps = self._requests.get(key, deque())

            # Remove timestamps outside the current window
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()

            remaining = max(0, max_requests - len(timestamps))
            return remaining


# Global rate limiter instance
_rate_limiter = RateLimiter()


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
    """Helper function to check rate limit using global limiter.

    Args:
        key: Unique identifier for the rate limit bucket
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Returns:
        Tuple of (allowed, retry_after_seconds)
    """
    return _rate_limiter.check_rate_limit(key, max_requests, window_seconds)


def reset_rate_limit(key: str) -> None:
    """Helper function to reset rate limit for a key.

    Args:
        key: Rate limit key to reset
    """
    _rate_limiter.reset(key)


def get_remaining_requests(key: str, max_requests: int, window_seconds: int) -> int:
    """Helper function to get remaining requests for a key.

    Args:
        key: Rate limit key
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds

    Returns:
        Number of remaining requests
    """
    return _rate_limiter.get_remaining(key, max_requests, window_seconds)


def rate_limit(
    key_func: Callable[..., str],
    max_requests: int,
    window_seconds: int,
    on_limit_exceeded: Callable[[int], None] = None
):
    """Decorator to apply rate limiting to functions.

    Args:
        key_func: Function to extract rate limit key from function arguments
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        on_limit_exceeded: Optional callback when rate limit is exceeded (receives retry_after)

    Returns:
        Decorated function that enforces rate limiting

    Example:
        @rate_limit(
            key_func=lambda email, password: f"login:{email}",
            max_requests=5,
            window_seconds=900
        )
        def authenticate_user(email: str, password: str):
            # Authentication logic
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract rate limit key
            key = key_func(*args, **kwargs)

            # Check rate limit
            allowed, retry_after = _rate_limiter.check_rate_limit(
                key, max_requests, window_seconds
            )

            if not allowed:
                logger.warning(
                    "Rate limit exceeded for %s: key=%s, retry_after=%ds",
                    func.__name__, key, retry_after
                )
                if on_limit_exceeded:
                    on_limit_exceeded(retry_after)
                return None

            # Execute function
            return func(*args, **kwargs)

        return wrapper
    return decorator


# Pre-configured rate limiters for common operations

class LoginRateLimiter:
    """Rate limiter for login attempts."""

    @staticmethod
    def check(identifier: str) -> Tuple[bool, int]:
        """Check if login attempt is allowed.

        Args:
            identifier: IP address, email, or combined identifier

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        key = f"login:{identifier}"
        return check_rate_limit(
            key,
            settings.LOGIN_RATE_LIMIT,
            settings.LOGIN_RATE_WINDOW
        )

    @staticmethod
    def reset(identifier: str) -> None:
        """Reset login rate limit for identifier.

        Args:
            identifier: IP address or email to reset
        """
        key = f"login:{identifier}"
        reset_rate_limit(key)

    @staticmethod
    def get_remaining(identifier: str) -> int:
        """Get remaining login attempts.

        Args:
            identifier: IP address or email

        Returns:
            Number of remaining attempts
        """
        key = f"login:{identifier}"
        return get_remaining_requests(
            key,
            settings.LOGIN_RATE_LIMIT,
            settings.LOGIN_RATE_WINDOW
        )


class ScorecardRateLimiter:
    """Rate limiter for scorecard submissions."""

    @staticmethod
    def check(token: str) -> Tuple[bool, int]:
        """Check if scorecard submission is allowed.

        Args:
            token: Scorecard token

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        key = f"scorecard:{token}"
        return check_rate_limit(
            key,
            settings.SCORECARD_RATE_LIMIT,
            settings.SCORECARD_RATE_WINDOW
        )

    @staticmethod
    def reset(token: str) -> None:
        """Reset scorecard rate limit for token.

        Args:
            token: Scorecard token to reset
        """
        key = f"scorecard:{token}"
        reset_rate_limit(key)

    @staticmethod
    def get_remaining(token: str) -> int:
        """Get remaining scorecard submissions.

        Args:
            token: Scorecard token

        Returns:
            Number of remaining submissions
        """
        key = f"scorecard:{token}"
        return get_remaining_requests(
            key,
            settings.SCORECARD_RATE_LIMIT,
            settings.SCORECARD_RATE_WINDOW
        )


class APIRateLimiter:
    """Rate limiter for generic API operations."""

    @staticmethod
    def check(identifier: str) -> Tuple[bool, int]:
        """Check if API request is allowed.

        Args:
            identifier: API key, user ID, or IP address

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        key = f"api:{identifier}"
        return check_rate_limit(
            key,
            settings.API_RATE_LIMIT,
            settings.API_RATE_WINDOW
        )

    @staticmethod
    def reset(identifier: str) -> None:
        """Reset API rate limit for identifier.

        Args:
            identifier: API key or user ID to reset
        """
        key = f"api:{identifier}"
        reset_rate_limit(key)

    @staticmethod
    def get_remaining(identifier: str) -> int:
        """Get remaining API requests.

        Args:
            identifier: API key or user ID

        Returns:
            Number of remaining requests
        """
        key = f"api:{identifier}"
        return get_remaining_requests(
            key,
            settings.API_RATE_LIMIT,
            settings.API_RATE_WINDOW
        )


# Convenience instances
login_limiter = LoginRateLimiter()
scorecard_limiter = ScorecardRateLimiter()
api_limiter = APIRateLimiter()
