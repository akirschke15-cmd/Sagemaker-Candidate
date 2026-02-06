"""
ATS Database Helper Functions
Utility functions for avoiding N+1 queries and other common patterns
"""
from typing import Dict
from .connection import db_session


def get_jobs_dict(status: str = None) -> Dict:
    """Pre-fetch all jobs as a dict keyed by job ID. Use to avoid N+1 queries."""
    with db_session() as conn:
        if status:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ?", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs").fetchall()
        return {row['id']: dict(row) for row in rows}


def get_contractor_roles_dict() -> Dict:
    """Pre-fetch all contractor roles as a dict keyed by role ID."""
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM contractor_roles").fetchall()
        return {row['id']: dict(row) for row in rows}
