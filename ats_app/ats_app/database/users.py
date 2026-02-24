"""
ATS User and RBAC Operations
Manages users, roles, and job ownership
"""
from typing import List, Dict, Optional
from .connection import db_session
from .schema import USER_ROLES


def create_user(email: str, name: str, role: str) -> int:
    """Create a new user with the specified role."""
    if role not in USER_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {USER_ROLES}")
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
            (email, name, role)
        )
        return cursor.lastrowid


def get_users(role: str = None, active_only: bool = True) -> List[Dict]:
    """Get all users, optionally filtered by role."""
    with db_session() as conn:
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        if active_only:
            query += " AND is_active = 1"
        if role:
            query += " AND role = ?"
            params.append(role)
        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_user(user_id: int) -> Optional[Dict]:
    """Get a user by ID."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by email address."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def update_user(user_id: int, **kwargs):
    """Update user fields."""
    ALLOWED_COLUMNS = {'email', 'name', 'role', 'is_active'}
    filtered = {k: v for k, v in kwargs.items() if k in ALLOWED_COLUMNS}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in filtered.keys())
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", (*filtered.values(), user_id))


def deactivate_user(user_id: int):
    """Deactivate a user (soft delete)."""
    update_user(user_id, is_active=0)


def activate_user(user_id: int):
    """Activate a user."""
    update_user(user_id, is_active=1)


# ============ JOB OWNERSHIP OPERATIONS ============
def assign_job_owner(job_id: int, user_id: int, role: str = 'hiring_manager'):
    """Assign a user as an owner of a job."""
    with db_session() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO job_owners (job_id, user_id, role, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (job_id, user_id, role))


def remove_job_owner(job_id: int, user_id: int):
    """Remove a user from job ownership."""
    with db_session() as conn:
        conn.execute("DELETE FROM job_owners WHERE job_id = ? AND user_id = ?", (job_id, user_id))


def get_job_owners(job_id: int) -> List[Dict]:
    """Get all owners of a job."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT jo.*, u.email, u.name, u.role as user_role
            FROM job_owners jo
            JOIN users u ON jo.user_id = u.id
            WHERE jo.job_id = ? AND u.is_active = 1
            ORDER BY u.name
        """, (job_id,)).fetchall()
        return [dict(r) for r in rows]


def get_user_jobs(user_id: int) -> List[Dict]:
    """Get all jobs owned by a user."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT j.*, jo.role as ownership_role
            FROM jobs j
            JOIN job_owners jo ON j.id = jo.job_id
            WHERE jo.user_id = ?
            ORDER BY j.created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_user_job_ids(user_id: int) -> List[int]:
    """Get list of job IDs owned by a user."""
    jobs = get_user_jobs(user_id)
    return [j['id'] for j in jobs]


def is_job_owner(user_id: int, job_id: int) -> bool:
    """Check if a user is an owner of a specific job."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT 1 FROM job_owners WHERE job_id = ? AND user_id = ?",
            (job_id, user_id)
        ).fetchone()
        return row is not None


def get_candidates_for_user_jobs(user_id: int, stage: str = None, status: str = 'Active') -> List[Dict]:
    """Get candidates for jobs owned by a user."""
    job_ids = get_user_job_ids(user_id)
    if not job_ids:
        return []

    with db_session() as conn:
        placeholders = ','.join('?' * len(job_ids))
        query = f"""
            SELECT c.*, j.title as job_title, v.name as vendor_name
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE c.job_id IN ({placeholders})
        """
        params = list(job_ids)
        if stage:
            query += " AND c.current_stage = ?"
            params.append(stage)
        if status:
            query += " AND c.status = ?"
            params.append(status)
        query += " ORDER BY c.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def seed_admin_user():
    """Seed initial admin user if no users exist."""
    with db_session() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        if row['count'] == 0:
            conn.execute("""
                INSERT INTO users (email, name, role, is_active)
                VALUES ('admin@agentic.com', 'System Admin', 'admin', 1)
            """)
            # Also add sample users for testing
            conn.execute("""
                INSERT INTO users (email, name, role, is_active)
                VALUES
                    ('recruiter@agentic.com', 'Main Recruiter', 'recruiter', 1),
                    ('hiring.manager@agentic.com', 'John Smith (HM)', 'hiring_manager', 1),
                    ('interviewer@agentic.com', 'Jane Doe (Interviewer)', 'interviewer', 1)
            """)
