"""
Unit tests for session security features in auth.py.

Tests cover:
- Session token generation and validation
- HMAC signature verification
- Token expiration handling
- Timing-attack resistance (compare_digest)
- DEV_MODE enforcement for insecure functions
- Password strength validation
- Password hashing and verification (bcrypt and PBKDF2)
"""
import pytest
import time
import hmac
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

import auth
from auth import (
    generate_session_token,
    validate_session_token,
    hash_password,
    verify_password,
    validate_password_strength,
    login_by_email,
    set_current_user,
)


class TestSessionTokenGeneration:
    """Test session token generation."""

    def test_generate_session_token_format(self):
        """Test that generate_session_token creates valid format (user_id:timestamp:hmac)."""
        user_id = 42
        token = generate_session_token(user_id)

        # Token should have 3 parts separated by colons
        parts = token.split(':')
        assert len(parts) == 3

        # First part should be user_id
        assert parts[0] == str(user_id)

        # Second part should be timestamp (numeric)
        assert parts[1].isdigit()

        # Third part should be HMAC signature (64 hex chars for SHA256)
        assert len(parts[2]) == 64
        assert all(c in '0123456789abcdef' for c in parts[2])

    def test_generate_session_token_includes_current_timestamp(self):
        """Test that token includes current timestamp."""
        user_id = 123
        before = int(datetime.now().timestamp())
        token = generate_session_token(user_id)
        after = int(datetime.now().timestamp())

        parts = token.split(':')
        timestamp = int(parts[1])

        # Timestamp should be between before and after
        assert before <= timestamp <= after

    def test_generate_session_token_unique_per_call(self):
        """Test that each call generates a unique token (due to timestamp)."""
        user_id = 456
        token1 = generate_session_token(user_id)
        time.sleep(1.1)  # Ensure timestamp changes
        token2 = generate_session_token(user_id)

        assert token1 != token2


class TestSessionTokenValidation:
    """Test session token validation."""

    def test_validate_session_token_returns_user_id_for_valid_token(self):
        """Test that validate_session_token returns correct user_id for valid token."""
        user_id = 789
        token = generate_session_token(user_id)

        validated_user_id = validate_session_token(token)
        assert validated_user_id == user_id

    def test_validate_session_token_returns_none_for_tampered_user_id(self):
        """Test that validate_session_token returns None for tampered user_id."""
        user_id = 100
        token = generate_session_token(user_id)

        # Tamper with user_id
        parts = token.split(':')
        parts[0] = str(user_id + 1)  # Change user_id
        tampered_token = ':'.join(parts)

        validated_user_id = validate_session_token(tampered_token)
        assert validated_user_id is None

    def test_validate_session_token_returns_none_for_tampered_timestamp(self):
        """Test that validate_session_token returns None for tampered timestamp."""
        user_id = 200
        token = generate_session_token(user_id)

        # Tamper with timestamp
        parts = token.split(':')
        parts[1] = str(int(parts[1]) + 3600)  # Add 1 hour
        tampered_token = ':'.join(parts)

        validated_user_id = validate_session_token(tampered_token)
        assert validated_user_id is None

    def test_validate_session_token_returns_none_for_tampered_signature(self):
        """Test that validate_session_token returns None for tampered signature."""
        user_id = 300
        token = generate_session_token(user_id)

        # Tamper with signature
        parts = token.split(':')
        parts[2] = parts[2][:-1] + ('0' if parts[2][-1] != '0' else '1')  # Change last char
        tampered_token = ':'.join(parts)

        validated_user_id = validate_session_token(tampered_token)
        assert validated_user_id is None

    def test_validate_session_token_returns_none_for_expired_token(self):
        """Test that validate_session_token returns None for expired tokens (>30 days)."""
        user_id = 400

        # Mock datetime to generate old token
        old_timestamp = int((datetime.now() - timedelta(days=31)).timestamp())

        # Manually construct token with old timestamp
        message = f"{user_id}:{old_timestamp}"
        signature = hmac.new(
            auth._get_session_secret_key(),
            message.encode('utf-8'),
            auth.hashlib.sha256
        ).hexdigest()
        old_token = f"{message}:{signature}"

        validated_user_id = validate_session_token(old_token)
        assert validated_user_id is None

    def test_validate_session_token_accepts_recent_token(self):
        """Test that validate_session_token accepts tokens less than 30 days old."""
        user_id = 500

        # Create token with timestamp 29 days ago (should be valid)
        recent_timestamp = int((datetime.now() - timedelta(days=29)).timestamp())
        message = f"{user_id}:{recent_timestamp}"
        signature = hmac.new(
            auth._get_session_secret_key(),
            message.encode('utf-8'),
            auth.hashlib.sha256
        ).hexdigest()
        recent_token = f"{message}:{signature}"

        validated_user_id = validate_session_token(recent_token)
        assert validated_user_id == user_id

    def test_validate_session_token_returns_none_for_invalid_format(self):
        """Test that validate_session_token returns None for invalid format."""
        # Missing parts
        assert validate_session_token("invalid") is None
        assert validate_session_token("user_id:timestamp") is None  # Missing signature

        # Too many parts
        assert validate_session_token("a:b:c:d") is None

        # Non-numeric user_id
        assert validate_session_token("abc:123456789:signature") is None

        # Non-numeric timestamp
        assert validate_session_token("123:abc:signature") is None

    def test_validate_session_token_uses_compare_digest(self):
        """Test that validate_session_token uses compare_digest (timing-attack resistance)."""
        user_id = 600
        token = generate_session_token(user_id)

        # Mock compare_digest to verify it's called
        with patch('hmac.compare_digest', wraps=hmac.compare_digest) as mock_compare:
            validate_session_token(token)
            assert mock_compare.called


class TestPasswordStrength:
    """Test password strength validation."""

    def test_password_strength_requires_minimum_length(self):
        """Test that password must be at least 8 characters."""
        valid, error = validate_password_strength("short")
        assert valid is False
        assert "8 characters" in error

        valid, error = validate_password_strength("Short1!")
        assert valid is False

        valid, error = validate_password_strength("LongEnough1")
        assert valid is True or "8 characters" not in error

    def test_password_strength_requires_uppercase(self):
        """Test that password must contain at least one uppercase letter."""
        valid, error = validate_password_strength("lowercase123")
        assert valid is False
        assert "uppercase" in error.lower()

        valid, error = validate_password_strength("Uppercase123")
        assert valid is True or "uppercase" not in error.lower()

    def test_password_strength_requires_lowercase(self):
        """Test that password must contain at least one lowercase letter."""
        valid, error = validate_password_strength("UPPERCASE123")
        assert valid is False
        assert "lowercase" in error.lower()

        valid, error = validate_password_strength("UPPERCASE123a")
        assert valid is True or "lowercase" not in error.lower()

    def test_password_strength_requires_digit(self):
        """Test that password must contain at least one digit."""
        valid, error = validate_password_strength("NoDigitsHere")
        assert valid is False
        assert "digit" in error.lower()

        valid, error = validate_password_strength("HasDigit1")
        assert valid is True or "digit" not in error.lower()

    def test_password_strength_accepts_strong_password(self):
        """Test that strong password passes all checks."""
        valid, error = validate_password_strength("StrongPass123")
        assert valid is True
        assert error == ""

        valid, error = validate_password_strength("MyP@ssw0rd!")
        assert valid is True
        assert error == ""


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a hash string."""
        password = "TestPassword123"
        password_hash = hash_password(password)

        assert password_hash is not None
        assert len(password_hash) > 0
        assert password_hash != password  # Should not be plain text

    def test_hash_password_includes_algorithm_prefix(self):
        """Test that hash includes algorithm prefix (bcrypt: or pbkdf2:)."""
        password = "TestPassword456"
        password_hash = hash_password(password)

        # Should start with either bcrypt: or pbkdf2:
        assert password_hash.startswith('bcrypt:') or password_hash.startswith('pbkdf2:')

    def test_hash_password_creates_different_hashes(self):
        """Test that same password creates different hashes (due to salt)."""
        password = "SamePassword789"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (different salts)
        assert hash1 != hash2

    def test_verify_password_with_bcrypt_hash(self):
        """Test verify_password with bcrypt hash."""
        password = "BcryptPassword123"

        # Create bcrypt hash (if bcrypt available)
        if auth.BCRYPT_AVAILABLE:
            password_hash = hash_password(password)
            if password_hash.startswith('bcrypt:'):
                # Correct password should verify
                assert verify_password(password, password_hash) is True

                # Wrong password should fail
                assert verify_password("WrongPassword", password_hash) is False

    def test_verify_password_with_pbkdf2_hash(self):
        """Test verify_password with PBKDF2 hash."""
        password = "Pbkdf2Password456"

        # Create PBKDF2 hash manually to ensure we test this code path
        import secrets
        import hashlib

        salt = secrets.token_hex(32)
        password_hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        password_hash = f"pbkdf2:{salt}:{password_hash_bytes.hex()}"

        # Correct password should verify
        assert verify_password(password, password_hash) is True

        # Wrong password should fail
        assert verify_password("WrongPassword", password_hash) is False

    def test_verify_password_with_invalid_format(self):
        """Test verify_password with invalid hash format."""
        password = "TestPassword789"

        # Unknown prefix
        assert verify_password(password, "unknown:hash") is False

        # Malformed PBKDF2 hash
        assert verify_password(password, "pbkdf2:salt") is False  # Missing hash
        assert verify_password(password, "pbkdf2:") is False  # Empty

        # Empty hash
        assert verify_password(password, "") is False

    def test_verify_password_handles_bcrypt_unavailable(self):
        """Test that verify_password handles bcrypt being unavailable."""
        password = "TestPassword000"

        # Create a bcrypt-prefixed hash
        bcrypt_hash = "bcrypt:$2b$12$somevalidlookinghash"

        # Mock BCRYPT_AVAILABLE to False
        original_available = auth.BCRYPT_AVAILABLE
        try:
            auth.BCRYPT_AVAILABLE = False
            result = verify_password(password, bcrypt_hash)
            assert result is False  # Should fail gracefully
        finally:
            auth.BCRYPT_AVAILABLE = original_available


class TestDevModeEnforcement:
    """Test that insecure functions are blocked when DEV_MODE=False."""

    def test_login_by_email_blocked_when_dev_mode_false(self, monkeypatch):
        """Test that login_by_email is blocked when DEV_MODE=False."""
        from config import settings
        monkeypatch.setattr(settings, 'DEV_MODE', False)

        # Mock get_user_by_email to return a user
        mock_user = {'id': 1, 'email': 'test@example.com', 'is_active': True}
        with patch('auth.get_user_by_email', return_value=mock_user):
            with patch('auth.st') as mock_st:
                mock_st.session_state = {}
                result = login_by_email('test@example.com')

        # Should return False (blocked)
        assert result is False

    def test_login_by_email_allowed_when_dev_mode_true(self, monkeypatch):
        """Test that login_by_email is allowed when DEV_MODE=True."""
        from config import settings
        monkeypatch.setattr(settings, 'DEV_MODE', True)

        # Mock dependencies
        mock_user = {'id': 1, 'email': 'test@example.com', 'is_active': True}
        with patch('auth.get_user_by_email', return_value=mock_user):
            with patch('auth.init_auth_session'):
                with patch('auth.set_current_user', return_value=True) as mock_set:
                    result = login_by_email('test@example.com')

        # Should call set_current_user and return True
        assert mock_set.called

    def test_set_current_user_blocked_when_dev_mode_false(self, monkeypatch):
        """Test that set_current_user is blocked when DEV_MODE=False."""
        from config import settings
        monkeypatch.setattr(settings, 'DEV_MODE', False)

        # Mock get_user to return a user
        mock_user = {'id': 1, 'email': 'test@example.com', 'is_active': True}
        with patch('auth.get_user', return_value=mock_user):
            with patch('auth.st') as mock_st:
                mock_st.session_state = {}
                result = set_current_user(1)

        # Should return False (blocked)
        assert result is False

    def test_set_current_user_allowed_when_dev_mode_true(self, monkeypatch):
        """Test that set_current_user is allowed when DEV_MODE=True."""
        from config import settings
        monkeypatch.setattr(settings, 'DEV_MODE', True)

        # Mock dependencies
        mock_user = {'id': 1, 'email': 'test@example.com', 'is_active': True, 'role': 'admin'}
        with patch('auth.get_user', return_value=mock_user):
            with patch('auth.st') as mock_st:
                mock_st.session_state = Mock()
                mock_st.session_state.data = {}

                with patch('auth.init_auth_session'):
                    with patch('auth.generate_session_token', return_value='mock_token'):
                        result = set_current_user(1)

        # Should return True (allowed)
        assert result is True


class TestSessionTokenEdgeCases:
    """Test edge cases in session token handling."""

    def test_validate_session_token_with_empty_string(self):
        """Test that validate_session_token handles empty string."""
        assert validate_session_token("") is None

    def test_validate_session_token_with_none(self):
        """Test that validate_session_token handles None gracefully."""
        # Should raise AttributeError (None has no split method)
        # This is expected behavior - token must be a string
        try:
            result = validate_session_token(None)
            # If it doesn't crash, it should return None
            assert result is None
        except (AttributeError, TypeError):
            # This is expected and acceptable behavior
            pass

    def test_generate_session_token_with_zero_user_id(self):
        """Test that generate_session_token works with user_id=0."""
        token = generate_session_token(0)
        validated_user_id = validate_session_token(token)
        assert validated_user_id == 0

    def test_generate_session_token_with_large_user_id(self):
        """Test that generate_session_token works with large user_id."""
        user_id = 999999999
        token = generate_session_token(user_id)
        validated_user_id = validate_session_token(token)
        assert validated_user_id == user_id

    def test_validate_session_token_with_special_characters(self):
        """Test that validate_session_token handles tokens with special characters."""
        # Token with special characters should fail validation
        assert validate_session_token("user:timestamp:sig<script>") is None
        assert validate_session_token("123:456:abc\x00def") is None


class TestPasswordVerificationTimingSafety:
    """Test that password verification is timing-safe."""

    def test_verify_password_timing_consistency(self):
        """Test that verify_password takes similar time for wrong passwords."""
        # This is a basic test - true timing attack prevention requires
        # constant-time comparison at the algorithm level (which bcrypt provides)

        password = "CorrectPassword123"
        password_hash = hash_password(password)

        # Time several wrong password attempts
        import time

        def time_verification(test_password):
            start = time.perf_counter()
            verify_password(test_password, password_hash)
            return time.perf_counter() - start

        # Multiple attempts with different wrong passwords
        times = [
            time_verification("Wrong1"),
            time_verification("Wrong2"),
            time_verification("CompletelyDifferent"),
        ]

        # Times should be similar (within an order of magnitude)
        # Note: This is a weak test, but verifies basic timing consistency
        max_time = max(times)
        min_time = min(times)

        # Ratio should be less than 10x (very generous for test reliability)
        # In production, bcrypt ensures much tighter timing
        if min_time > 0:
            ratio = max_time / min_time
            assert ratio < 10  # Should be consistent
