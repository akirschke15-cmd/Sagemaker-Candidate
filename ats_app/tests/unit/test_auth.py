"""
Unit tests for authentication module (auth.py)

Tests password hashing, validation, session management, and permission checking.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import auth


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_returns_non_empty_string(self):
        """hash_password should return a non-empty string"""
        password = "TestPassword123"
        hashed = auth.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_includes_algorithm_prefix(self):
        """hash_password should include algorithm prefix (bcrypt: or pbkdf2:)"""
        password = "TestPassword123"
        hashed = auth.hash_password(password)

        assert hashed.startswith("bcrypt:") or hashed.startswith("pbkdf2:")

    def test_hash_password_produces_different_hashes_for_same_password(self):
        """hash_password should produce different hashes for same password (salting)"""
        password = "TestPassword123"
        hash1 = auth.hash_password(password)
        hash2 = auth.hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_returns_true_for_correct_password(self):
        """verify_password should return True for correct password"""
        password = "TestPassword123"
        hashed = auth.hash_password(password)

        assert auth.verify_password(password, hashed) is True

    def test_verify_password_returns_false_for_wrong_password(self):
        """verify_password should return False for incorrect password"""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = auth.hash_password(password)

        assert auth.verify_password(wrong_password, hashed) is False

    def test_verify_password_handles_bcrypt_format(self):
        """verify_password should handle bcrypt format correctly"""
        if auth.BCRYPT_AVAILABLE:
            password = "TestPassword123"
            # Force bcrypt
            with patch.object(auth, 'BCRYPT_AVAILABLE', True):
                hashed = auth.hash_password(password)
                assert hashed.startswith("bcrypt:")
                assert auth.verify_password(password, hashed) is True

    def test_verify_password_handles_pbkdf2_format(self):
        """verify_password should handle pbkdf2 format correctly"""
        password = "TestPassword123"
        # Force pbkdf2
        with patch.object(auth, 'BCRYPT_AVAILABLE', False):
            hashed = auth.hash_password(password)
            assert hashed.startswith("pbkdf2:")
            assert auth.verify_password(password, hashed) is True

    def test_verify_password_returns_false_for_invalid_format(self):
        """verify_password should return False for invalid hash format"""
        password = "TestPassword123"
        invalid_hash = "invalid:format:hash"

        assert auth.verify_password(password, invalid_hash) is False

    def test_verify_password_handles_corrupted_bcrypt_hash(self):
        """verify_password should handle corrupted bcrypt hash gracefully"""
        password = "TestPassword123"
        corrupted_hash = "bcrypt:corrupted_hash_data"

        assert auth.verify_password(password, corrupted_hash) is False

    def test_verify_password_handles_corrupted_pbkdf2_hash(self):
        """verify_password should handle corrupted pbkdf2 hash gracefully"""
        password = "TestPassword123"
        corrupted_hash = "pbkdf2:salt"  # Missing hash part

        assert auth.verify_password(password, corrupted_hash) is False


class TestPasswordValidation:
    """Test password strength validation"""

    def test_validate_password_accepts_valid_password(self):
        """validate_password_strength should accept valid password"""
        valid_password = "ValidPass123"
        is_valid, error_msg = auth.validate_password_strength(valid_password)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_password_rejects_short_password(self):
        """validate_password_strength should reject passwords shorter than 8 characters"""
        short_password = "Short1"
        is_valid, error_msg = auth.validate_password_strength(short_password)

        assert is_valid is False
        assert "at least 8 characters" in error_msg.lower()

    def test_validate_password_rejects_missing_uppercase(self):
        """validate_password_strength should reject password without uppercase letter"""
        no_upper = "lowercase123"
        is_valid, error_msg = auth.validate_password_strength(no_upper)

        assert is_valid is False
        assert "uppercase" in error_msg.lower()

    def test_validate_password_rejects_missing_lowercase(self):
        """validate_password_strength should reject password without lowercase letter"""
        no_lower = "UPPERCASE123"
        is_valid, error_msg = auth.validate_password_strength(no_lower)

        assert is_valid is False
        assert "lowercase" in error_msg.lower()

    def test_validate_password_rejects_missing_digit(self):
        """validate_password_strength should reject password without digit"""
        no_digit = "NoDigitsHere"
        is_valid, error_msg = auth.validate_password_strength(no_digit)

        assert is_valid is False
        assert "digit" in error_msg.lower()

    def test_validate_password_accepts_minimum_length(self):
        """validate_password_strength should accept exactly 8 character password"""
        min_length = "Valid123"  # Exactly 8 characters
        is_valid, error_msg = auth.validate_password_strength(min_length)

        assert is_valid is True

    def test_validate_password_accepts_long_password(self):
        """validate_password_strength should accept long passwords"""
        long_password = "ThisIsAVeryLongPassword123WithManyCharacters"
        is_valid, error_msg = auth.validate_password_strength(long_password)

        assert is_valid is True


class TestSessionManagement:
    """Test session management functions"""

    def test_check_session_expired_returns_true_when_no_expiry(self):
        """check_session_expired should return True when no expiry set"""
        mock_st = Mock()
        mock_st.session_state = {}

        with patch('auth.st', mock_st):
            assert auth.check_session_expired() is True

    def test_check_session_expired_returns_true_when_expiry_none(self):
        """check_session_expired should return True when expiry is None"""
        mock_st = Mock()
        mock_session_state = Mock()
        mock_session_state.session_expires_at = None
        mock_session_state.__contains__ = Mock(side_effect=lambda x: x == 'session_expires_at')
        mock_st.session_state = mock_session_state

        with patch('auth.st', mock_st):
            assert auth.check_session_expired() is True

    def test_check_session_expired_returns_false_when_not_expired(self):
        """check_session_expired should return False when session not expired"""
        mock_st = Mock()
        mock_session_state = Mock()
        future_time = datetime.now() + timedelta(hours=1)
        mock_session_state.session_expires_at = future_time
        mock_session_state.__contains__ = Mock(side_effect=lambda x: x == 'session_expires_at')
        mock_st.session_state = mock_session_state

        with patch('auth.st', mock_st):
            assert auth.check_session_expired() is False

    def test_check_session_expired_returns_true_when_expired(self):
        """check_session_expired should return True when session expired"""
        mock_st = Mock()
        mock_session_state = Mock()
        past_time = datetime.now() - timedelta(hours=1)
        mock_session_state.session_expires_at = past_time
        mock_session_state.__contains__ = Mock(side_effect=lambda x: x == 'session_expires_at')
        mock_st.session_state = mock_session_state

        with patch('auth.st', mock_st):
            assert auth.check_session_expired() is True

    def test_init_auth_session_initializes_state(self):
        """init_auth_session should initialize session state variables"""
        mock_st = Mock()
        mock_session_state = Mock()
        # Set up __contains__ to return False initially (simulating empty state)
        mock_session_state.__contains__ = Mock(return_value=False)
        mock_st.session_state = mock_session_state

        with patch('auth.st', mock_st):
            auth.init_auth_session()

            # Verify attributes were set
            assert hasattr(mock_session_state, 'current_user')
            assert hasattr(mock_session_state, 'current_user_id')
            assert hasattr(mock_session_state, 'session_expires_at')


class TestPermissions:
    """Test permission checking functions"""

    def test_check_permission_returns_false_for_no_user(self):
        """check_permission should return False when user is None"""
        assert auth.check_permission(None, 'candidates', 'view') is False

    def test_check_permission_returns_false_for_user_without_role(self):
        """check_permission should return False when user has no role"""
        user = {'name': 'Test User'}
        assert auth.check_permission(user, 'candidates', 'view') is False

    def test_check_permission_returns_true_for_admin_all_resources(self):
        """check_permission should return True for admin on any resource"""
        admin_user = {'name': 'Admin', 'role': 'admin'}

        # Admin should have access to all resources/actions in PERMISSIONS
        assert auth.check_permission(admin_user, 'candidates', 'view') is True
        assert auth.check_permission(admin_user, 'candidates', 'create') is True
        assert auth.check_permission(admin_user, 'candidates', 'delete') is True
        assert auth.check_permission(admin_user, 'jobs', 'delete') is True
        assert auth.check_permission(admin_user, 'users', 'view') is True

    def test_check_permission_respects_recruiter_permissions(self):
        """check_permission should respect recruiter role permissions"""
        recruiter = {'name': 'Recruiter', 'role': 'recruiter'}

        # Recruiter can view/create candidates
        assert auth.check_permission(recruiter, 'candidates', 'view') is True
        assert auth.check_permission(recruiter, 'candidates', 'create') is True

        # Recruiter cannot delete candidates
        assert auth.check_permission(recruiter, 'candidates', 'delete') is False

        # Recruiter cannot manage users
        assert auth.check_permission(recruiter, 'users', 'view') is False

    def test_check_permission_respects_hiring_manager_permissions(self):
        """check_permission should respect hiring_manager role permissions"""
        hiring_manager = {'name': 'Manager', 'role': 'hiring_manager'}

        # Hiring manager can view candidates
        assert auth.check_permission(hiring_manager, 'candidates', 'view') is True

        # Hiring manager cannot create candidates
        assert auth.check_permission(hiring_manager, 'candidates', 'create') is False

        # Hiring manager can view jobs
        assert auth.check_permission(hiring_manager, 'jobs', 'view') is True

        # Hiring manager cannot view vendors
        assert auth.check_permission(hiring_manager, 'vendors', 'view') is False

    def test_check_permission_respects_interviewer_permissions(self):
        """check_permission should respect interviewer role permissions"""
        interviewer = {'name': 'Interviewer', 'role': 'interviewer'}

        # Interviewer can view dashboard
        assert auth.check_permission(interviewer, 'dashboard', 'view') is True

        # Interviewer can view candidates
        assert auth.check_permission(interviewer, 'candidates', 'view') is True

        # Interviewer cannot edit candidates
        assert auth.check_permission(interviewer, 'candidates', 'edit') is False

        # Interviewer cannot view jobs
        assert auth.check_permission(interviewer, 'jobs', 'view') is False

    def test_check_permission_returns_false_for_nonexistent_resource(self):
        """check_permission should return False for non-existent resource"""
        admin_user = {'name': 'Admin', 'role': 'admin'}
        assert auth.check_permission(admin_user, 'nonexistent_resource', 'view') is False

    def test_check_permission_returns_false_for_nonexistent_action(self):
        """check_permission should return False for non-existent action"""
        admin_user = {'name': 'Admin', 'role': 'admin'}
        assert auth.check_permission(admin_user, 'candidates', 'nonexistent_action') is False


class TestRoleHelpers:
    """Test role helper functions"""

    def test_get_role_display_name_converts_underscores(self):
        """get_role_display_name should convert underscores to spaces and title case"""
        assert auth.get_role_display_name('admin') == 'Admin'
        assert auth.get_role_display_name('recruiter') == 'Recruiter'
        assert auth.get_role_display_name('hiring_manager') == 'Hiring Manager'
        assert auth.get_role_display_name('interviewer') == 'Interviewer'

    def test_get_role_badge_color_returns_colors_for_all_roles(self):
        """get_role_badge_color should return color for each role"""
        assert isinstance(auth.get_role_badge_color('admin'), str)
        assert isinstance(auth.get_role_badge_color('recruiter'), str)
        assert isinstance(auth.get_role_badge_color('hiring_manager'), str)
        assert isinstance(auth.get_role_badge_color('interviewer'), str)

    def test_get_role_badge_color_returns_default_for_unknown_role(self):
        """get_role_badge_color should return default color for unknown role"""
        color = auth.get_role_badge_color('unknown_role')
        assert color == '#666666'
