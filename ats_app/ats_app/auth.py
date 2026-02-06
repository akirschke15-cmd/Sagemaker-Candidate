"""
Feature 7: Authentication and Role-Based Access Control (RBAC)

This module provides simple session-based authentication using Streamlit session state.
For MVP, login is by email selection only (no password).
"""
import streamlit as st
from typing import Optional, Dict, List, Callable, Tuple
from functools import wraps
import logging
from datetime import datetime, timedelta
import hmac
import secrets
import hashlib

# Try to import bcrypt, fallback to hashlib+secrets
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

from database import (
    get_user, get_user_by_email, get_users, get_user_jobs,
    get_user_job_ids, is_job_owner, USER_ROLES
)
from config import settings

# Constants
SESSION_TIMEOUT_HOURS = 2
logger = logging.getLogger(__name__)

# Initialize session secret key
_SESSION_SECRET_KEY = None


def _get_session_secret_key() -> bytes:
    """
    Get or generate the session secret key.

    Returns:
        Session secret key as bytes
    """
    global _SESSION_SECRET_KEY

    if _SESSION_SECRET_KEY is None:
        # Try to get from config
        key_str = settings.SESSION_SECRET_KEY

        if key_str:
            _SESSION_SECRET_KEY = key_str.encode('utf-8')
        else:
            # Generate a random key for this session
            _SESSION_SECRET_KEY = secrets.token_bytes(32)
            logger.warning("SESSION_SECRET_KEY not configured, using random key (sessions will not persist across restarts)")

    return _SESSION_SECRET_KEY


def generate_session_token(user_id: int) -> str:
    """
    Generate an HMAC-signed session token.

    Format: {user_id}:{timestamp}:{hmac_signature}

    Args:
        user_id: User ID to encode in the token

    Returns:
        Signed session token string
    """
    timestamp = str(int(datetime.now().timestamp()))
    message = f"{user_id}:{timestamp}"

    signature = hmac.new(
        _get_session_secret_key(),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"{message}:{signature}"


def validate_session_token(token: str) -> Optional[int]:
    """
    Validate an HMAC-signed session token and extract user_id.

    Args:
        token: Session token string

    Returns:
        User ID if valid, None if invalid or expired
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            logger.warning("Invalid session token format")
            return None

        user_id_str, timestamp_str, signature = parts

        # Verify signature
        message = f"{user_id_str}:{timestamp_str}"
        expected_signature = hmac.new(
            _get_session_secret_key(),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Session token signature verification failed")
            return None

        # Check token age (prevent replay attacks with very old tokens)
        timestamp = int(timestamp_str)
        token_age_hours = (datetime.now().timestamp() - timestamp) / 3600

        # Allow tokens up to 30 days old (as long as session hasn't expired)
        if token_age_hours > 720:  # 30 days
            logger.warning(f"Session token too old: {token_age_hours:.1f} hours")
            return None

        return int(user_id_str)

    except (ValueError, TypeError) as e:
        logger.error(f"Error validating session token: {e}")
        return None

# Permission definitions for role-based access
# Format: resource -> action -> list of allowed roles
PERMISSIONS = {
    'dashboard': {
        'view': ['admin', 'recruiter', 'hiring_manager', 'interviewer'],
    },
    'candidates': {
        'view': ['admin', 'recruiter', 'hiring_manager', 'interviewer'],
        'create': ['admin', 'recruiter'],
        'edit': ['admin', 'recruiter', 'hiring_manager'],
        'delete': ['admin'],
        'advance': ['admin', 'recruiter', 'hiring_manager'],
        'reject': ['admin', 'recruiter', 'hiring_manager'],
    },
    'jobs': {
        'view': ['admin', 'recruiter', 'hiring_manager'],
        'create': ['admin', 'recruiter'],
        'edit': ['admin', 'recruiter'],
        'delete': ['admin'],
        'assign_owner': ['admin', 'recruiter'],
    },
    'vendors': {
        'view': ['admin', 'recruiter'],
        'create': ['admin', 'recruiter'],
        'edit': ['admin', 'recruiter'],
        'delete': ['admin'],
    },
    'scheduling': {
        'view': ['admin', 'recruiter', 'hiring_manager', 'interviewer'],
        'create': ['admin', 'recruiter', 'hiring_manager'],
        'edit': ['admin', 'recruiter', 'hiring_manager'],
    },
    'analytics': {
        'view': ['admin', 'recruiter', 'hiring_manager'],
    },
    'settings': {
        'view': ['admin'],
        'edit': ['admin'],
    },
    'users': {
        'view': ['admin'],
        'create': ['admin'],
        'edit': ['admin'],
        'delete': ['admin'],
    },
}

# Navigation items with their required permissions
NAV_ITEMS = {
    'dashboard': {'label': 'Dashboard', 'icon': 'bar-chart', 'resource': 'dashboard', 'action': 'view'},
    'candidates': {'label': 'Candidates', 'icon': 'users', 'resource': 'candidates', 'action': 'view'},
    'jobs': {'label': 'Jobs', 'icon': 'briefcase', 'resource': 'jobs', 'action': 'view'},
    'vendors': {'label': 'Vendors', 'icon': 'building', 'resource': 'vendors', 'action': 'view'},
    'scheduling': {'label': 'Scheduling', 'icon': 'calendar', 'resource': 'scheduling', 'action': 'view'},
    'analytics': {'label': 'Analytics', 'icon': 'trending-up', 'resource': 'analytics', 'action': 'view'},
    'settings': {'label': 'Settings', 'icon': 'settings', 'resource': 'settings', 'action': 'view'},
}


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt if available, otherwise PBKDF2-SHA256.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string with algorithm prefix
    """
    if BCRYPT_AVAILABLE:
        # Use bcrypt (recommended)
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt)
        return f"bcrypt:{password_hash.decode('utf-8')}"
    else:
        # Fallback to PBKDF2-SHA256
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"pbkdf2:{salt}:{password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain text password to verify
        password_hash: Hashed password string with algorithm prefix

    Returns:
        True if password matches, False otherwise
    """
    try:
        if password_hash.startswith("bcrypt:"):
            if not BCRYPT_AVAILABLE:
                logger.error("Bcrypt hash found but bcrypt not available")
                return False
            stored_hash = password_hash[7:]  # Remove "bcrypt:" prefix
            password_bytes = password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, stored_hash.encode('utf-8'))
        elif password_hash.startswith("pbkdf2:"):
            parts = password_hash.split(":")
            if len(parts) != 3:
                logger.error("Invalid PBKDF2 hash format")
                return False
            salt = parts[1]
            stored_hash = parts[2]
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return new_hash.hex() == stored_hash
        else:
            logger.error(f"Unknown password hash format: {password_hash[:10]}")
            return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, ""


def login_with_password(email: str, password: str) -> bool:
    """
    Login with email and password.

    Args:
        email: User email address
        password: Plain text password

    Returns:
        True if login successful, False otherwise
    """
    try:
        user = get_user_by_email(email)
        if not user:
            logger.warning(f"AUTH_FAILURE: Login attempt for non-existent user: {email}, timestamp: {datetime.now().isoformat()}")
            return False

        if not user.get('is_active'):
            logger.warning(f"AUTH_FAILURE: Login attempt for inactive user: {email}, timestamp: {datetime.now().isoformat()}")
            return False

        password_hash = user.get('password_hash')
        if not password_hash:
            logger.warning(f"AUTH_FAILURE: User {email} has no password hash, timestamp: {datetime.now().isoformat()}")
            return False

        if not verify_password(password, password_hash):
            logger.warning(f"AUTH_FAILURE: Invalid password for user: {email}, timestamp: {datetime.now().isoformat()}")
            return False

        # Set user session with HMAC token
        init_auth_session()
        st.session_state.current_user_id = user['id']
        st.session_state.current_user = user
        st.session_state.session_token = generate_session_token(user['id'])
        st.session_state.session_created_at = datetime.now()
        st.session_state.session_last_activity = datetime.now()
        st.session_state.session_expires_at = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)

        logger.info(f"AUTH_SUCCESS: User logged in: {email}, user_id: {user['id']}, timestamp: {datetime.now().isoformat()}")
        return True

    except Exception as e:
        logger.error(f"AUTH_ERROR: Error during login for {email}: {e}, timestamp: {datetime.now().isoformat()}")
        return False


def check_session_expired() -> bool:
    """
    Check if the current session has expired.

    Returns:
        True if session is expired, False otherwise
    """
    if 'session_expires_at' not in st.session_state:
        return True

    expires_at = st.session_state.session_expires_at
    if not expires_at:
        return True

    return datetime.now() > expires_at


def init_auth_session():
    """Initialize authentication session state."""
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'current_user_id' not in st.session_state:
        st.session_state.current_user_id = None
    if 'session_expires_at' not in st.session_state:
        st.session_state.session_expires_at = None
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None
    if 'session_created_at' not in st.session_state:
        st.session_state.session_created_at = None
    if 'session_last_activity' not in st.session_state:
        st.session_state.session_last_activity = None


def get_current_user() -> Optional[Dict]:
    """Get the currently logged in user from session state."""
    init_auth_session()

    # Check session expiry
    if check_session_expired():
        if st.session_state.current_user_id:
            user_id = st.session_state.current_user_id
            logger.info(f"Session expired for user ID: {user_id}")
            logout_user()
        return None

    # Validate session token if present
    if st.session_state.session_token:
        validated_user_id = validate_session_token(st.session_state.session_token)
        if validated_user_id is None:
            logger.warning("Session token validation failed, logging out")
            logout_user()
            return None

        # Ensure token matches stored user_id
        if st.session_state.current_user_id and validated_user_id != st.session_state.current_user_id:
            logger.warning(f"Session token mismatch: token={validated_user_id}, session={st.session_state.current_user_id}")
            logout_user()
            return None

    if st.session_state.current_user_id:
        # Refresh user data from database
        user = get_user(st.session_state.current_user_id)
        if user and user.get('is_active'):
            st.session_state.current_user = user

            # Update session activity timestamp
            st.session_state.session_last_activity = datetime.now()

            return user
        else:
            # User no longer exists or is inactive
            logger.warning(f"User ID {st.session_state.current_user_id} no longer active")
            logout_user()
            return None
    return None


def set_current_user(user_id: int) -> bool:
    """
    Set the current user by ID.
    DEPRECATED: Only works in DEV_MODE.
    Returns True if successful, False if user not found or inactive.
    """
    # Only allow in dev mode
    if not settings.DEV_MODE:
        logger.error("set_current_user() called but DEV_MODE is disabled")
        return False

    init_auth_session()

    user = get_user(user_id)
    if user and user.get('is_active'):
        st.session_state.current_user_id = user_id
        st.session_state.current_user = user

        # Generate session token
        st.session_state.session_token = generate_session_token(user_id)
        st.session_state.session_created_at = datetime.now()
        st.session_state.session_last_activity = datetime.now()
        st.session_state.session_expires_at = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)

        logger.warning(f"DEV MODE: User {user.get('email')} logged in via set_current_user()")
        return True
    return False


def login_by_email(email: str) -> bool:
    """
    Login by email address (no password for MVP).
    DEPRECATED: Use login_with_password() for secure authentication.
    Only works in DEV_MODE.
    Returns True if successful, False if user not found or inactive.
    """
    # Only allow in dev mode
    if not settings.DEV_MODE:
        logger.error(f"login_by_email() called for {email} but DEV_MODE is disabled")
        return False

    logger.warning(f"DEV MODE: login_by_email() called for {email}. Use login_with_password() instead.")
    user = get_user_by_email(email)
    if user and user.get('is_active'):
        init_auth_session()
        st.session_state.session_expires_at = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)
        return set_current_user(user['id'])
    return False


def logout_user():
    """Log out the current user."""
    init_auth_session()

    # Log logout event before clearing session
    if st.session_state.current_user:
        email = st.session_state.current_user.get('email', 'unknown')
        user_id = st.session_state.current_user_id
        logger.info(f"AUTH_LOGOUT: User logged out: {email}, user_id: {user_id}, timestamp: {datetime.now().isoformat()}")

    # Clear all session data
    st.session_state.current_user_id = None
    st.session_state.current_user = None
    st.session_state.session_expires_at = None
    st.session_state.session_token = None
    st.session_state.session_created_at = None
    st.session_state.session_last_activity = None


def is_logged_in() -> bool:
    """Check if a user is currently logged in."""
    return get_current_user() is not None


def check_permission(user: Optional[Dict], resource: str, action: str) -> bool:
    """
    Check if a user has permission to perform an action on a resource.

    Args:
        user: User dict or None
        resource: Resource name (e.g., 'candidates', 'jobs')
        action: Action name (e.g., 'view', 'create', 'edit')

    Returns:
        True if permitted, False otherwise
    """
    if not user:
        return False

    role = user.get('role')
    if not role:
        return False

    # Get permission config for resource
    resource_perms = PERMISSIONS.get(resource, {})
    action_roles = resource_perms.get(action, [])

    return role in action_roles


def has_permission(resource: str, action: str) -> bool:
    """Check if the current user has permission for a resource/action."""
    user = get_current_user()
    return check_permission(user, resource, action)


def get_user_role() -> Optional[str]:
    """Get the role of the current user."""
    user = get_current_user()
    return user.get('role') if user else None


def is_admin() -> bool:
    """Check if the current user is an admin."""
    return get_user_role() == 'admin'


def is_recruiter() -> bool:
    """Check if the current user is a recruiter."""
    return get_user_role() == 'recruiter'


def is_hiring_manager() -> bool:
    """Check if the current user is a hiring manager."""
    return get_user_role() == 'hiring_manager'


def is_interviewer() -> bool:
    """Check if the current user is an interviewer."""
    return get_user_role() == 'interviewer'


def can_view_all_jobs() -> bool:
    """Check if the current user can view all jobs (admin/recruiter)."""
    role = get_user_role()
    return role in ['admin', 'recruiter']


def can_view_all_candidates() -> bool:
    """Check if the current user can view all candidates (admin/recruiter)."""
    role = get_user_role()
    return role in ['admin', 'recruiter']


def get_visible_job_ids() -> Optional[List[int]]:
    """
    Get the list of job IDs visible to the current user.
    Returns None if user can see all jobs, or a list of job IDs otherwise.
    """
    user = get_current_user()
    if not user:
        return []

    if can_view_all_jobs():
        return None  # None means "all jobs"

    # Hiring managers and interviewers only see their assigned jobs
    return get_user_job_ids(user['id'])


def can_access_job(job_id: int) -> bool:
    """Check if the current user can access a specific job."""
    user = get_current_user()
    if not user:
        return False

    if can_view_all_jobs():
        return True

    return is_job_owner(user['id'], job_id)


def can_access_candidate(candidate: Dict) -> bool:
    """
    Check if the current user can access a candidate.
    Candidates are accessible if:
    - User can view all candidates (admin/recruiter)
    - Candidate is assigned to a job the user owns
    """
    user = get_current_user()
    if not user:
        return False

    if can_view_all_candidates():
        return True

    job_id = candidate.get('job_id')
    if not job_id:
        # Unassigned candidates - only visible to admin/recruiter
        return False

    return is_job_owner(user['id'], job_id)


def get_allowed_nav_items() -> Dict:
    """Get navigation items that the current user is allowed to see."""
    user = get_current_user()
    allowed = {}

    for key, item in NAV_ITEMS.items():
        if check_permission(user, item['resource'], item['action']):
            allowed[key] = item

    return allowed


def require_login(func: Callable) -> Callable:
    """
    Decorator that requires a user to be logged in.
    If not logged in, shows a warning and returns None.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            st.warning("Please log in to access this feature.")
            return None
        return func(*args, **kwargs)
    return wrapper


def require_permission(resource: str, action: str) -> Callable:
    """
    Decorator factory that requires a specific permission.
    Shows an error if user doesn't have permission.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_permission(resource, action):
                st.error("You don't have permission to access this feature.")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


def render_user_selector():
    """
    Render a user login form in the sidebar.
    In DEV_MODE: Shows dropdown selector (no password).
    In production: Shows email + password form.
    """
    init_auth_session()

    current_user = get_current_user()

    st.sidebar.divider()

    if current_user:
        st.sidebar.markdown(f"**Logged in as:**")
        st.sidebar.markdown(f"{current_user['name']}")
        st.sidebar.caption(f"Role: {current_user['role'].replace('_', ' ').title()}")

        # Show session info in dev mode
        if settings.DEV_MODE and st.session_state.session_created_at:
            st.sidebar.caption(f"Session created: {st.session_state.session_created_at.strftime('%H:%M:%S')}")

        if st.sidebar.button("Logout", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        st.sidebar.markdown("**Login:**")

        # DEV_MODE: Show dropdown selector (insecure, for testing only)
        if settings.DEV_MODE:
            st.sidebar.warning("⚠️ DEV MODE: Passwordless login")

            users = get_users(active_only=True)
            if users:
                # Create options for selectbox
                user_options = {0: "Select user..."}
                user_options.update({u['id']: f"{u['name']} ({u['role'].replace('_', ' ').title()})" for u in users})

                selected_user_id = st.sidebar.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    format_func=lambda x: user_options[x],
                    key="login_user_select",
                    label_visibility="collapsed"
                )

                if selected_user_id and st.sidebar.button("Login", type="primary", use_container_width=True):
                    if set_current_user(selected_user_id):
                        st.rerun()
                    else:
                        st.sidebar.error("Login failed")
            else:
                st.sidebar.info("No users available. Please check database.")

        # Production mode: Show password login form
        else:
            with st.sidebar.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", type="primary", use_container_width=True)

                if submit:
                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        if login_with_password(email, password):
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password")


def get_role_display_name(role: str) -> str:
    """Convert role code to display name."""
    return role.replace('_', ' ').title()


def get_role_badge_color(role: str) -> str:
    """Get the color for a role badge."""
    colors = {
        'admin': '#C8102E',        # Southwest Red
        'recruiter': '#304CB2',     # Southwest Blue
        'hiring_manager': '#F9B612', # Southwest Yellow
        'interviewer': '#2E7D32',   # Green
    }
    return colors.get(role, '#666666')
