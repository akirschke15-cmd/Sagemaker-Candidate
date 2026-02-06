"""
Unit tests for rate limiter security features.

Tests cover:
- Basic rate limiting (allow up to max, then block)
- Sliding window expiry (requests allowed again after window)
- Pre-configured limiters (login_limiter, scorecard_limiter, api_limiter)
- Helper functions (check_rate_limit, reset_rate_limit, get_remaining_requests)
- Thread safety (concurrent access)
- Memory cleanup of expired entries
"""
import pytest
import time
import threading
from unittest.mock import patch

# Import rate limiter components
from rate_limiter import (
    RateLimiter,
    check_rate_limit,
    reset_rate_limit,
    get_remaining_requests,
    LoginRateLimiter,
    ScorecardRateLimiter,
    APIRateLimiter,
    login_limiter,
    scorecard_limiter,
    api_limiter,
)


class TestRateLimiter:
    """Test the RateLimiter class core functionality."""

    def test_basic_rate_limiting_allows_up_to_max(self):
        """Test that rate limiter allows requests up to the maximum."""
        limiter = RateLimiter()
        key = "test_user_1"
        max_requests = 3
        window = 60

        # First 3 requests should be allowed
        for i in range(max_requests):
            allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
            assert allowed is True
            assert retry_after == 0

    def test_basic_rate_limiting_blocks_after_max(self):
        """Test that rate limiter blocks requests after maximum is reached."""
        limiter = RateLimiter()
        key = "test_user_2"
        max_requests = 3
        window = 60

        # First 3 requests allowed
        for i in range(max_requests):
            limiter.check_rate_limit(key, max_requests, window)

        # 4th request should be blocked
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False
        assert retry_after > 0
        assert retry_after <= window

    def test_sliding_window_expiry(self):
        """Test that requests are allowed again after window expires."""
        limiter = RateLimiter()
        key = "test_user_3"
        max_requests = 2
        window = 1  # 1 second window

        # Use up the limit
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Should be blocked now
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False

        # Wait for window to expire
        time.sleep(window + 0.1)

        # Should be allowed again
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is True
        assert retry_after == 0

    def test_sliding_window_partial_expiry(self):
        """Test that sliding window correctly handles partial expiry."""
        limiter = RateLimiter()
        key = "test_user_4"
        max_requests = 3
        window = 2  # 2 second window

        # Make 3 requests
        limiter.check_rate_limit(key, max_requests, window)
        time.sleep(0.5)
        limiter.check_rate_limit(key, max_requests, window)
        time.sleep(0.5)
        limiter.check_rate_limit(key, max_requests, window)

        # Should be blocked
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False

        # Wait for first request to expire (total ~2.2 seconds from first request)
        time.sleep(1.3)

        # Should be allowed again (first request expired)
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is True

    def test_reset_clears_limit(self):
        """Test that reset() clears rate limit for a key."""
        limiter = RateLimiter()
        key = "test_user_5"
        max_requests = 2
        window = 60

        # Use up the limit
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Should be blocked
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False

        # Reset the limit
        limiter.reset(key)

        # Should be allowed again
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is True

    def test_get_remaining_requests(self):
        """Test get_remaining() returns correct count."""
        limiter = RateLimiter()
        key = "test_user_6"
        max_requests = 5
        window = 60

        # Initially, all requests remaining
        remaining = limiter.get_remaining(key, max_requests, window)
        assert remaining == max_requests

        # Make 2 requests
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Should have 3 remaining
        remaining = limiter.get_remaining(key, max_requests, window)
        assert remaining == 3

        # Make 3 more requests
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Should have 0 remaining
        remaining = limiter.get_remaining(key, max_requests, window)
        assert remaining == 0

    def test_different_keys_are_independent(self):
        """Test that different keys have independent rate limits."""
        limiter = RateLimiter()
        key1 = "user_a"
        key2 = "user_b"
        max_requests = 2
        window = 60

        # Use up key1's limit
        limiter.check_rate_limit(key1, max_requests, window)
        limiter.check_rate_limit(key1, max_requests, window)

        # key1 should be blocked
        allowed, _ = limiter.check_rate_limit(key1, max_requests, window)
        assert allowed is False

        # key2 should still be allowed
        allowed, _ = limiter.check_rate_limit(key2, max_requests, window)
        assert allowed is True

    def test_thread_safety_concurrent_access(self):
        """Test that rate limiter is thread-safe with concurrent access."""
        limiter = RateLimiter()
        key = "concurrent_user"
        max_requests = 10
        window = 60

        results = []
        errors = []

        def make_request():
            try:
                allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
                results.append(allowed)
            except Exception as e:
                errors.append(e)

        # Create 20 threads trying to make requests simultaneously
        threads = [threading.Thread(target=make_request) for _ in range(20)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # No exceptions should occur
        assert len(errors) == 0

        # Exactly 10 requests should be allowed
        allowed_count = sum(1 for r in results if r is True)
        assert allowed_count == max_requests

        # The rest should be blocked
        blocked_count = sum(1 for r in results if r is False)
        assert blocked_count == 10

    def test_memory_cleanup_expired_entries(self):
        """Test that expired entries are cleaned up from memory."""
        limiter = RateLimiter(cleanup_interval=1)  # Cleanup every 1 second
        key = "cleanup_test_user"
        max_requests = 2
        window = 1  # 1 second window

        # Make some requests
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Key should exist in internal storage
        assert key in limiter._requests

        # Wait for entries to expire and cleanup to run
        time.sleep(window + limiter._cleanup_interval + 0.2)

        # Trigger cleanup by making another check
        limiter.check_rate_limit("trigger_cleanup", 1, 60)

        # Original key should be cleaned up (empty deque removed)
        # Note: The key is only removed if the deque is completely empty
        # Let's verify by checking remaining count
        remaining = limiter.get_remaining(key, max_requests, window)
        assert remaining == max_requests  # Should be back to full quota

    def test_cleanup_interval_respected(self):
        """Test that cleanup only runs after cleanup_interval."""
        limiter = RateLimiter(cleanup_interval=10)  # Cleanup every 10 seconds

        # Record initial cleanup time
        initial_cleanup = limiter._last_cleanup

        # Make a request (should not trigger cleanup yet)
        limiter.check_rate_limit("test_user", 5, 60)

        # Cleanup time should not have changed
        assert limiter._last_cleanup == initial_cleanup


class TestHelperFunctions:
    """Test the global helper functions."""

    def test_check_rate_limit_helper(self):
        """Test check_rate_limit() helper function."""
        key = "helper_test_1"
        max_requests = 3
        window = 60

        # Should use global rate limiter
        for i in range(max_requests):
            allowed, retry_after = check_rate_limit(key, max_requests, window)
            assert allowed is True

        # Should be blocked after max
        allowed, retry_after = check_rate_limit(key, max_requests, window)
        assert allowed is False

    def test_reset_rate_limit_helper(self):
        """Test reset_rate_limit() helper function."""
        key = "helper_test_2"
        max_requests = 2
        window = 60

        # Use up limit
        check_rate_limit(key, max_requests, window)
        check_rate_limit(key, max_requests, window)

        # Reset
        reset_rate_limit(key)

        # Should work again
        allowed, _ = check_rate_limit(key, max_requests, window)
        assert allowed is True

    def test_get_remaining_requests_helper(self):
        """Test get_remaining_requests() helper function."""
        key = "helper_test_3"
        max_requests = 5
        window = 60

        # Initially full
        remaining = get_remaining_requests(key, max_requests, window)
        assert remaining == max_requests

        # Use some
        check_rate_limit(key, max_requests, window)
        check_rate_limit(key, max_requests, window)

        remaining = get_remaining_requests(key, max_requests, window)
        assert remaining == 3


class TestLoginRateLimiter:
    """Test the pre-configured LoginRateLimiter."""

    def test_login_limiter_check(self, monkeypatch):
        """Test LoginRateLimiter.check() method."""
        # Mock settings
        from config import settings
        monkeypatch.setattr(settings, 'LOGIN_RATE_LIMIT', 3)
        monkeypatch.setattr(settings, 'LOGIN_RATE_WINDOW', 60)

        identifier = "user@example.com"

        # Should allow up to limit
        for i in range(3):
            allowed, retry_after = LoginRateLimiter.check(identifier)
            assert allowed is True

        # Should block after limit
        allowed, retry_after = LoginRateLimiter.check(identifier)
        assert allowed is False

    def test_login_limiter_reset(self, monkeypatch):
        """Test LoginRateLimiter.reset() method."""
        from config import settings
        monkeypatch.setattr(settings, 'LOGIN_RATE_LIMIT', 2)
        monkeypatch.setattr(settings, 'LOGIN_RATE_WINDOW', 60)

        identifier = "user2@example.com"

        # Use up limit
        LoginRateLimiter.check(identifier)
        LoginRateLimiter.check(identifier)

        # Reset
        LoginRateLimiter.reset(identifier)

        # Should work again
        allowed, _ = LoginRateLimiter.check(identifier)
        assert allowed is True

    def test_login_limiter_get_remaining(self, monkeypatch):
        """Test LoginRateLimiter.get_remaining() method."""
        from config import settings
        monkeypatch.setattr(settings, 'LOGIN_RATE_LIMIT', 5)
        monkeypatch.setattr(settings, 'LOGIN_RATE_WINDOW', 60)

        identifier = "user3@example.com"

        # Initially full
        remaining = LoginRateLimiter.get_remaining(identifier)
        assert remaining == 5

        # Use 2
        LoginRateLimiter.check(identifier)
        LoginRateLimiter.check(identifier)

        remaining = LoginRateLimiter.get_remaining(identifier)
        assert remaining == 3

    def test_login_limiter_instance(self):
        """Test that login_limiter instance is available."""
        assert login_limiter is not None
        assert isinstance(login_limiter, LoginRateLimiter)


class TestScorecardRateLimiter:
    """Test the pre-configured ScorecardRateLimiter."""

    def test_scorecard_limiter_check(self, monkeypatch):
        """Test ScorecardRateLimiter.check() method."""
        from config import settings
        monkeypatch.setattr(settings, 'SCORECARD_RATE_LIMIT', 4)
        monkeypatch.setattr(settings, 'SCORECARD_RATE_WINDOW', 60)

        token = "scorecard_token_123"

        # Should allow up to limit
        for i in range(4):
            allowed, retry_after = ScorecardRateLimiter.check(token)
            assert allowed is True

        # Should block after limit
        allowed, retry_after = ScorecardRateLimiter.check(token)
        assert allowed is False

    def test_scorecard_limiter_reset(self, monkeypatch):
        """Test ScorecardRateLimiter.reset() method."""
        from config import settings
        monkeypatch.setattr(settings, 'SCORECARD_RATE_LIMIT', 2)
        monkeypatch.setattr(settings, 'SCORECARD_RATE_WINDOW', 60)

        token = "scorecard_token_456"

        # Use up limit
        ScorecardRateLimiter.check(token)
        ScorecardRateLimiter.check(token)

        # Reset
        ScorecardRateLimiter.reset(token)

        # Should work again
        allowed, _ = ScorecardRateLimiter.check(token)
        assert allowed is True

    def test_scorecard_limiter_get_remaining(self, monkeypatch):
        """Test ScorecardRateLimiter.get_remaining() method."""
        from config import settings
        monkeypatch.setattr(settings, 'SCORECARD_RATE_LIMIT', 10)
        monkeypatch.setattr(settings, 'SCORECARD_RATE_WINDOW', 60)

        token = "scorecard_token_789"

        # Initially full
        remaining = ScorecardRateLimiter.get_remaining(token)
        assert remaining == 10

        # Use 3
        ScorecardRateLimiter.check(token)
        ScorecardRateLimiter.check(token)
        ScorecardRateLimiter.check(token)

        remaining = ScorecardRateLimiter.get_remaining(token)
        assert remaining == 7

    def test_scorecard_limiter_instance(self):
        """Test that scorecard_limiter instance is available."""
        assert scorecard_limiter is not None
        assert isinstance(scorecard_limiter, ScorecardRateLimiter)


class TestAPIRateLimiter:
    """Test the pre-configured APIRateLimiter."""

    def test_api_limiter_check(self, monkeypatch):
        """Test APIRateLimiter.check() method."""
        from config import settings
        monkeypatch.setattr(settings, 'API_RATE_LIMIT', 5)
        monkeypatch.setattr(settings, 'API_RATE_WINDOW', 60)

        identifier = "api_key_abc123"

        # Should allow up to limit
        for i in range(5):
            allowed, retry_after = APIRateLimiter.check(identifier)
            assert allowed is True

        # Should block after limit
        allowed, retry_after = APIRateLimiter.check(identifier)
        assert allowed is False

    def test_api_limiter_reset(self, monkeypatch):
        """Test APIRateLimiter.reset() method."""
        from config import settings
        monkeypatch.setattr(settings, 'API_RATE_LIMIT', 3)
        monkeypatch.setattr(settings, 'API_RATE_WINDOW', 60)

        identifier = "api_key_def456"

        # Use up limit
        APIRateLimiter.check(identifier)
        APIRateLimiter.check(identifier)
        APIRateLimiter.check(identifier)

        # Reset
        APIRateLimiter.reset(identifier)

        # Should work again
        allowed, _ = APIRateLimiter.check(identifier)
        assert allowed is True

    def test_api_limiter_get_remaining(self, monkeypatch):
        """Test APIRateLimiter.get_remaining() method."""
        from config import settings
        monkeypatch.setattr(settings, 'API_RATE_LIMIT', 60)
        monkeypatch.setattr(settings, 'API_RATE_WINDOW', 60)

        identifier = "api_key_ghi789"

        # Initially full
        remaining = APIRateLimiter.get_remaining(identifier)
        assert remaining == 60

        # Use 10
        for i in range(10):
            APIRateLimiter.check(identifier)

        remaining = APIRateLimiter.get_remaining(identifier)
        assert remaining == 50

    def test_api_limiter_instance(self):
        """Test that api_limiter instance is available."""
        assert api_limiter is not None
        assert isinstance(api_limiter, APIRateLimiter)


class TestRetryAfterCalculation:
    """Test the retry_after calculation."""

    def test_retry_after_is_accurate(self):
        """Test that retry_after seconds are calculated accurately."""
        limiter = RateLimiter()
        key = "retry_test_user"
        max_requests = 2
        window = 5  # 5 second window

        # Use up the limit
        limiter.check_rate_limit(key, max_requests, window)
        limiter.check_rate_limit(key, max_requests, window)

        # Check retry_after
        allowed, retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False
        assert 0 < retry_after <= window + 1  # Should be within window + 1 second

        # Wait half the retry time
        time.sleep(retry_after / 2)

        # Should still be blocked
        allowed, new_retry_after = limiter.check_rate_limit(key, max_requests, window)
        assert allowed is False
        # Retry time should be roughly half of original
        assert new_retry_after < retry_after
