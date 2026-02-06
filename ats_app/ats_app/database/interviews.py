"""
ATS Interview Scheduling Operations
Manages interview scheduling and calendar events
"""
from typing import List, Dict
from .connection import db_session


def schedule_interview(candidate_id: int, stage: str, scheduled_time: str,
                       interviewer_email: str = None, interviewer_name: str = None,
                       location: str = None, meeting_link: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO interviews (candidate_id, stage, scheduled_time, interviewer_email,
                                   interviewer_name, location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, stage, scheduled_time, interviewer_email, interviewer_name, location, meeting_link))
        return cursor.lastrowid


def get_interviews(candidate_id: int = None, upcoming_only: bool = False) -> List[Dict]:
    with db_session() as conn:
        query = """
            SELECT i.*, c.name as candidate_name, c.email as candidate_email, j.title as job_title
            FROM interviews i
            JOIN candidates c ON i.candidate_id = c.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE 1=1
        """
        params = []
        if candidate_id:
            query += " AND i.candidate_id = ?"
            params.append(candidate_id)
        if upcoming_only:
            query += " AND i.scheduled_time >= datetime('now') AND i.status = 'Scheduled'"
        query += " ORDER BY i.scheduled_time"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def schedule_interview_for_role(candidate_id: int, job_id: int, stage: str, scheduled_time: str,
                                interviewer_email: str = None, interviewer_name: str = None,
                                location: str = None, meeting_link: str = None) -> int:
    """Schedule interview with job context for multi-role support."""
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO interviews (candidate_id, job_id, stage, scheduled_time, interviewer_email,
                                   interviewer_name, location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, job_id, stage, scheduled_time, interviewer_email, interviewer_name, location, meeting_link))
        return cursor.lastrowid


def get_interviews_with_role(candidate_id: int = None, job_id: int = None, upcoming_only: bool = False) -> List[Dict]:
    """Get interviews with job context for multi-role support."""
    with db_session() as conn:
        query = """
            SELECT i.*, c.name as candidate_name, c.email as candidate_email,
                   COALESCE(j2.title, j.title) as job_title
            FROM interviews i
            JOIN candidates c ON i.candidate_id = c.id
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN jobs j2 ON i.job_id = j2.id
            WHERE 1=1
        """
        params = []
        if candidate_id:
            query += " AND i.candidate_id = ?"
            params.append(candidate_id)
        if job_id:
            query += " AND (i.job_id = ? OR (i.job_id IS NULL AND c.job_id = ?))"
            params.extend([job_id, job_id])
        if upcoming_only:
            query += " AND i.scheduled_time >= datetime('now') AND i.status = 'Scheduled'"
        query += " ORDER BY i.scheduled_time"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
