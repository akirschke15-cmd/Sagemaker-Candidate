# Rate Limiter Integration Guide

## Overview

The `rate_limiter.py` module provides thread-safe, in-memory rate limiting for the ATS application using a sliding window algorithm. It's designed specifically for Streamlit applications with no external dependencies.

## Features

- **Thread-safe**: Uses `threading.Lock` for concurrent access
- **Sliding window**: More accurate than fixed window, prevents burst at window boundaries
- **Memory efficient**: Automatic cleanup of expired entries
- **Configurable**: Environment variables via `config.py`
- **Multiple patterns**: Decorator, helper functions, and pre-configured limiters
- **Integrated logging**: All actions logged for monitoring

## Configuration

All rate limit settings are in `config.py` and can be overridden via environment variables:

```python
# .env file example
LOGIN_RATE_LIMIT=5
LOGIN_RATE_WINDOW=900         # 15 minutes in seconds
SCORECARD_RATE_LIMIT=10
SCORECARD_RATE_WINDOW=3600    # 1 hour in seconds
API_RATE_LIMIT=60
API_RATE_WINDOW=60            # 1 minute in seconds
```

## Usage Examples

### 1. Login Rate Limiting

Protect authentication endpoints from brute force attacks:

```python
from rate_limiter import login_limiter
import streamlit as st

def login_page():
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Check rate limit (5 attempts per 15 minutes)
        allowed, retry_after = login_limiter.check(email)

        if not allowed:
            st.error(f"Too many login attempts. Try again in {retry_after} seconds.")
            return

        # Proceed with authentication
        if authenticate(email, password):
            login_limiter.reset(email)  # Reset on successful login
            st.success("Login successful!")
        else:
            remaining = login_limiter.get_remaining(email)
            st.warning(f"Invalid credentials. {remaining} attempts remaining.")
```

### 2. Scorecard Submission Rate Limiting

Prevent abuse of scorecard submission endpoints:

```python
from rate_limiter import scorecard_limiter

def submit_scorecard(token: str, scorecard_data: dict):
    # Check rate limit (10 submissions per hour)
    allowed, retry_after = scorecard_limiter.check(token)

    if not allowed:
        raise ValueError(f"Rate limit exceeded. Retry in {retry_after} seconds.")

    # Process scorecard submission
    save_scorecard(token, scorecard_data)
    return {"status": "success"}
```

### 3. Generic API Rate Limiting

For any API-like operations:

```python
from rate_limiter import api_limiter

def process_api_request(api_key: str, request_data: dict):
    # Check rate limit (60 requests per minute)
    allowed, retry_after = api_limiter.check(api_key)

    if not allowed:
        return {
            "error": "Rate limit exceeded",
            "retry_after": retry_after
        }

    # Process request
    result = handle_request(request_data)
    remaining = api_limiter.get_remaining(api_key)

    return {
        "result": result,
        "rate_limit_remaining": remaining
    }
```

### 4. Custom Rate Limiting

Use the low-level API for custom scenarios:

```python
from rate_limiter import check_rate_limit, get_remaining_requests, reset_rate_limit

# Custom rate limit: 100 requests per 5 minutes per IP
def handle_request(ip_address: str):
    key = f"custom:{ip_address}"
    allowed, retry_after = check_rate_limit(key, max_requests=100, window_seconds=300)

    if not allowed:
        return {"error": f"Rate limited. Retry in {retry_after}s"}

    # Process request
    result = process()

    # Show remaining quota
    remaining = get_remaining_requests(key, max_requests=100, window_seconds=300)
    return {"result": result, "quota_remaining": remaining}
```

### 5. Decorator Pattern

Apply rate limiting to functions:

```python
from rate_limiter import rate_limit

@rate_limit(
    key_func=lambda user_id, action: f"user_action:{user_id}:{action}",
    max_requests=10,
    window_seconds=60
)
def perform_user_action(user_id: str, action: str):
    # This function is automatically rate-limited
    return execute_action(user_id, action)

# Usage
result = perform_user_action("user123", "delete")
if result is None:
    print("Rate limited!")
```

## Integration with Streamlit Session State

For Streamlit apps, integrate with session state for IP tracking:

```python
import streamlit as st
from rate_limiter import login_limiter

# Get client IP (requires reverse proxy headers)
def get_client_ip():
    # In production with reverse proxy:
    # return st.context.headers.get("X-Forwarded-For", "unknown")
    # For development:
    return st.session_state.get("client_ip", "dev")

def login_form():
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Rate limit by email AND IP for extra security
        ip = get_client_ip()
        identifier = f"{email}:{ip}"

        allowed, retry_after = login_limiter.check(identifier)

        if not allowed:
            st.error(f"Too many attempts. Wait {retry_after} seconds.")
            return

        # Authenticate
        if auth.login(email, password):
            login_limiter.reset(identifier)
            st.success("Logged in!")
        else:
            remaining = login_limiter.get_remaining(identifier)
            st.error(f"Invalid credentials ({remaining} attempts left)")
```

## Security Best Practices

### 1. Use Multiple Identifiers

Combine multiple identifiers for robust rate limiting:

```python
# Rate limit by BOTH email AND IP
identifier = f"{email}:{ip_address}"
allowed, retry_after = login_limiter.check(identifier)
```

### 2. Reset on Success

Reset rate limits after successful authentication:

```python
if authenticate_success:
    login_limiter.reset(identifier)
```

### 3. Log Rate Limit Violations

The module automatically logs violations, but add application-level logging:

```python
if not allowed:
    logger.warning(
        "Rate limit exceeded: user=%s, action=%s, retry_after=%d",
        user_email, action, retry_after
    )
    # Optional: trigger alert for repeated violations
    if check_repeated_violations(user_email):
        alert_security_team(user_email)
```

### 4. Progressive Delays

Implement progressive delays for repeated violations:

```python
violation_count = get_violation_count(user_id)
base_delay = retry_after

if violation_count > 3:
    # Exponential backoff
    actual_delay = base_delay * (2 ** (violation_count - 3))
    st.error(f"Multiple violations. Wait {actual_delay} seconds.")
```

### 5. Monitor Memory Usage

The rate limiter auto-cleans every 5 minutes, but for high-traffic scenarios:

```python
from rate_limiter import _rate_limiter

# Force cleanup manually if needed
_rate_limiter._cleanup_expired_entries(max_window=3600)
```

## Testing

Run the test suite:

```bash
cd C:\Users\Akirs\Sagemaker-Candidate\ats_app\ats_app
python test_rate_limiter.py
```

Expected output demonstrates:
- Basic rate limiting behavior
- Pre-configured limiter functionality
- Sliding window behavior
- Decorator pattern
- Cleanup mechanisms

## Monitoring & Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger('rate_limiter').setLevel(logging.DEBUG)
```

### Check Current State

```python
from rate_limiter import login_limiter

# Check without incrementing count
remaining = login_limiter.get_remaining("user@example.com")
print(f"User has {remaining} login attempts remaining")
```

### Manual Reset

```python
# Reset rate limit for testing or support
login_limiter.reset("user@example.com")
```

## Performance Considerations

### Memory Usage

- Each request stores one timestamp (8 bytes) + overhead
- Auto-cleanup runs every 5 minutes
- Example: 1000 users × 5 attempts = ~40 KB

### Thread Safety

- All operations are thread-safe via `threading.Lock`
- Lock contention is minimal (only during check/cleanup)
- Safe for concurrent Streamlit sessions

### Scalability

For single-instance deployments (Streamlit Cloud, single EC2):
- Handles 10,000+ requests/minute easily
- Memory usage stays under 10 MB for typical loads

For multi-instance deployments:
- Consider Redis-based rate limiting (external dependency)
- Or use AWS API Gateway rate limiting

## Troubleshooting

### Issue: Rate limits not working

**Cause**: Config not loaded
**Solution**: Ensure `from config import settings` succeeds

### Issue: Rate limits too strict

**Cause**: Default configuration
**Solution**: Adjust in `.env`:
```
LOGIN_RATE_LIMIT=10
LOGIN_RATE_WINDOW=600
```

### Issue: Memory growing

**Cause**: Large window sizes or high traffic
**Solution**: Reduce cleanup interval:
```python
from rate_limiter import RateLimiter
limiter = RateLimiter(cleanup_interval=60)  # Clean every minute
```

### Issue: False positives (legitimate users blocked)

**Cause**: Shared IP addresses (corporate NAT)
**Solution**: Use email-only or session-based keys:
```python
# Instead of IP-based
allowed, _ = login_limiter.check(ip_address)

# Use email-based
allowed, _ = login_limiter.check(email)
```

## API Reference

### Classes

#### `RateLimiter`
Main rate limiter class with sliding window implementation.

#### `LoginRateLimiter`
Pre-configured for login attempts (5 per 15 min).

#### `ScorecardRateLimiter`
Pre-configured for scorecard submissions (10 per hour).

#### `APIRateLimiter`
Pre-configured for API requests (60 per minute).

### Functions

#### `check_rate_limit(key, max_requests, window_seconds) -> (allowed, retry_after)`
Check if request is allowed.

#### `reset_rate_limit(key)`
Reset rate limit for a key.

#### `get_remaining_requests(key, max_requests, window_seconds) -> int`
Get remaining requests in window.

#### `@rate_limit(key_func, max_requests, window_seconds, on_limit_exceeded)`
Decorator to apply rate limiting.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGIN_RATE_LIMIT` | 5 | Max login attempts |
| `LOGIN_RATE_WINDOW` | 900 | Login window (seconds) |
| `SCORECARD_RATE_LIMIT` | 10 | Max scorecard submissions |
| `SCORECARD_RATE_WINDOW` | 3600 | Scorecard window (seconds) |
| `API_RATE_LIMIT` | 60 | Max API requests |
| `API_RATE_WINDOW` | 60 | API window (seconds) |

## Next Steps

1. Integrate into authentication flow (`auth.py`)
2. Add to scorecard submission endpoints
3. Monitor logs for rate limit violations
4. Adjust limits based on production traffic
5. Consider Redis backend for multi-instance deployments
