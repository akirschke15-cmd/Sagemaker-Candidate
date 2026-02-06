"""Test script for rate_limiter module.

Run this to verify rate limiting functionality.
Usage: python test_rate_limiter.py
"""
import time
from rate_limiter import (
    check_rate_limit,
    login_limiter,
    scorecard_limiter,
    api_limiter,
    rate_limit
)


def test_basic_rate_limiting():
    """Test basic rate limit checking."""
    print("\n=== Test 1: Basic Rate Limiting ===")

    # Allow 3 requests per 5 seconds
    for i in range(5):
        allowed, retry_after = check_rate_limit("test-key", max_requests=3, window_seconds=5)
        print(f"Request {i+1}: {'ALLOWED' if allowed else f'BLOCKED (retry in {retry_after}s)'}")

        if not allowed:
            print(f"Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            allowed, retry_after = check_rate_limit("test-key", max_requests=3, window_seconds=5)
            print(f"After wait: {'ALLOWED' if allowed else 'BLOCKED'}")


def test_login_limiter():
    """Test login rate limiter."""
    print("\n=== Test 2: Login Rate Limiter ===")
    print(f"Config: {login_limiter.get_remaining('test@example.com')} attempts allowed")

    email = "test@example.com"

    for i in range(7):
        allowed, retry_after = login_limiter.check(email)
        remaining = login_limiter.get_remaining(email)

        print(f"Login attempt {i+1}: {'ALLOWED' if allowed else f'BLOCKED (retry in {retry_after}s)'} "
              f"- Remaining: {remaining}")

        if i == 3:
            print(f"Resetting rate limit for {email}")
            login_limiter.reset(email)


def test_scorecard_limiter():
    """Test scorecard submission limiter."""
    print("\n=== Test 3: Scorecard Rate Limiter ===")

    token = "test-token-123"

    for i in range(3):
        allowed, retry_after = scorecard_limiter.check(token)
        remaining = scorecard_limiter.get_remaining(token)

        print(f"Scorecard submission {i+1}: {'ALLOWED' if allowed else f'BLOCKED'} "
              f"- Remaining: {remaining}")


def test_api_limiter():
    """Test generic API limiter."""
    print("\n=== Test 4: API Rate Limiter ===")

    api_key = "api-key-456"

    # Simulate rapid requests
    for i in range(5):
        allowed, retry_after = api_limiter.check(api_key)
        remaining = api_limiter.get_remaining(api_key)

        print(f"API request {i+1}: {'ALLOWED' if allowed else f'BLOCKED'} "
              f"- Remaining: {remaining}")


def test_decorator():
    """Test rate limit decorator."""
    print("\n=== Test 5: Decorator Pattern ===")

    @rate_limit(
        key_func=lambda user_id: f"custom:{user_id}",
        max_requests=3,
        window_seconds=10
    )
    def protected_function(user_id: str):
        return f"Success for user {user_id}"

    for i in range(5):
        result = protected_function("user123")
        print(f"Call {i+1}: {result if result else 'RATE LIMITED'}")


def test_sliding_window():
    """Test sliding window behavior."""
    print("\n=== Test 6: Sliding Window Behavior ===")

    key = "sliding-test"
    max_requests = 3
    window = 5  # 5 seconds

    print(f"Config: {max_requests} requests per {window} seconds")

    # Make 3 requests immediately
    for i in range(3):
        allowed, _ = check_rate_limit(key, max_requests, window)
        print(f"Request {i+1}: {'ALLOWED' if allowed else 'BLOCKED'}")

    # Try 4th request (should be blocked)
    allowed, retry_after = check_rate_limit(key, max_requests, window)
    print(f"Request 4: {'ALLOWED' if allowed else f'BLOCKED (retry in {retry_after}s)'}")

    # Wait for first request to expire
    print(f"Waiting {retry_after + 1} seconds for sliding window...")
    time.sleep(retry_after + 1)

    # Now 1 request should be available
    allowed, _ = check_rate_limit(key, max_requests, window)
    print(f"Request 5 (after wait): {'ALLOWED' if allowed else 'BLOCKED'}")


if __name__ == "__main__":
    print("=" * 60)
    print("RATE LIMITER TEST SUITE")
    print("=" * 60)

    try:
        # Run all tests
        test_basic_rate_limiting()
        test_login_limiter()
        test_scorecard_limiter()
        test_api_limiter()
        test_decorator()
        test_sliding_window()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
