"""
ATS Job CRUD Operations
Manages job postings and positions
"""
from typing import List, Dict, Optional
from datetime import datetime
from .connection import db_session

try:
    from cache import invalidate_job_caches
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cache import invalidate_job_caches


def create_job(title: str, description: str = None, requirements: str = None,
               department: str = None, slots: int = 1) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO jobs (title, description, requirements, department, slots) VALUES (?, ?, ?, ?, ?)",
            (title, description, requirements, department, slots)
        )
        job_id = cursor.lastrowid
    invalidate_job_caches()
    return job_id


def get_jobs(status: str = None) -> List[Dict]:
    with db_session() as conn:
        if status:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_job(job_id: int) -> Optional[Dict]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def update_job(job_id: int, **kwargs):
    ALLOWED_COLUMNS = {'title', 'description', 'requirements', 'department', 'status', 'slots', 'updated_at', 'contractor_role_id'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", (*kwargs.values(), job_id))
    invalidate_job_caches()


def get_jobs_by_contractor_role(role_id: int) -> List[Dict]:
    """Get all jobs using a specific contractor role."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE contractor_role_id = ? ORDER BY created_at DESC",
            (role_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def set_scoring_criteria(job_id: int, stage: str, criteria: List[Dict]):
    """Set scoring criteria for a job stage. criteria = [{'name': str, 'max_score': int, 'weight': float, 'description': str}]"""
    with db_session() as conn:
        # Clear existing
        conn.execute("DELETE FROM scoring_criteria WHERE job_id = ? AND stage = ?", (job_id, stage))
        # Insert new
        for c in criteria:
            conn.execute("""
                INSERT INTO scoring_criteria (job_id, stage, criteria_name, max_score, weight, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, stage, c['name'], c.get('max_score', 5), c.get('weight', 1.0), c.get('description', '')))


def get_scoring_criteria(job_id: int, stage: str = None) -> List[Dict]:
    with db_session() as conn:
        if stage:
            rows = conn.execute(
                "SELECT * FROM scoring_criteria WHERE job_id = ? AND stage = ?", (job_id, stage)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scoring_criteria WHERE job_id = ? ORDER BY stage, id", (job_id,)
            ).fetchall()
        return [dict(r) for r in rows]
