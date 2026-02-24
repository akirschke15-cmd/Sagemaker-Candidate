"""
Mobile Scorecard Module - Token-based access for interviewers
Provides secure, mobile-friendly scorecard submission without login
"""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from config import settings
from database import db_session, get_candidate, get_job, get_scoring_criteria, score_candidate, add_stage_notes

logger = logging.getLogger(__name__)


def generate_scorecard_token(interview_id: int, interviewer_email: str, expires_hours: int = None) -> str:
    """
    Generate a secure token for mobile scorecard access.

    Args:
        interview_id: The interview ID this token is for
        interviewer_email: Email of the interviewer
        expires_hours: Token validity in hours (default from settings)

    Returns:
        The generated token string
    """
    if expires_hours is None:
        expires_hours = settings.SCORECARD_TOKEN_EXPIRY_HOURS

    # Generate a cryptographically secure random token
    token = secrets.token_urlsafe(32)

    expires_at = datetime.now() + timedelta(hours=expires_hours)

    with db_session() as conn:
        conn.execute("""
            INSERT INTO scorecard_tokens
            (interview_id, token, interviewer_email, expires_at, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (interview_id, token, interviewer_email, expires_at.isoformat()))

    return token


def validate_scorecard_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate a scorecard token and return interview data if valid.

    Args:
        token: The token string to validate

    Returns:
        Dictionary with interview/candidate/job data if valid, None otherwise
    """
    if not token:
        return None

    with db_session() as conn:
        # Get token record with interview and candidate data
        row = conn.execute("""
            SELECT st.*, i.candidate_id, i.stage, i.scheduled_time,
                   i.interviewer_name, i.interviewer_email as interview_interviewer_email,
                   c.name as candidate_name, c.email as candidate_email,
                   c.job_id, c.resume_text, c.ai_resume_analysis,
                   j.title as job_title, j.description as job_description
            FROM scorecard_tokens st
            JOIN interviews i ON st.interview_id = i.id
            JOIN candidates c ON i.candidate_id = c.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE st.token = ? AND st.is_active = 1
        """, (token,)).fetchone()

        if not row:
            return None

        token_data = dict(row)

        # Check expiry
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            # Token expired, mark as inactive
            conn.execute(
                "UPDATE scorecard_tokens SET is_active = 0 WHERE token = ?",
                (token,)
            )
            return None

        # Check if already used
        if token_data.get('used_at'):
            return None

        # Get scoring criteria for this stage and job
        criteria = []
        if token_data.get('job_id'):
            criteria = get_scoring_criteria(token_data['job_id'], token_data['stage'])

        return {
            'token_id': token_data['id'],
            'interview_id': token_data['interview_id'],
            'candidate_id': token_data['candidate_id'],
            'candidate_name': token_data['candidate_name'],
            'candidate_email': token_data['candidate_email'],
            'job_id': token_data['job_id'],
            'job_title': token_data['job_title'] or 'Unassigned',
            'job_description': token_data['job_description'],
            'stage': token_data['stage'],
            'scheduled_time': token_data['scheduled_time'],
            'interviewer_name': token_data['interviewer_name'],
            'interviewer_email': token_data['interviewer_email'],
            'ai_resume_analysis': token_data['ai_resume_analysis'],
            'criteria': criteria,
            'expires_at': token_data['expires_at']
        }


def submit_mobile_scorecard(
    token: str,
    scores: Dict[int, int],
    notes: str,
    recommendation: str,
    interviewer_name: str = None
) -> Tuple[bool, str]:
    """
    Submit a mobile scorecard with scores, notes, and recommendation.

    Args:
        token: The scorecard access token
        scores: Dictionary mapping criteria_id to score value
        notes: Interview notes text
        recommendation: One of: Strong Yes, Yes, Maybe, No, Strong No
        interviewer_name: Optional interviewer name override

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Validate token first
    interview_data = validate_scorecard_token(token)
    if not interview_data:
        return False, "Invalid or expired scorecard link"

    try:
        with db_session() as conn:
            candidate_id = interview_data['candidate_id']
            stage = interview_data['stage']
            evaluator = interviewer_name or interview_data.get('interviewer_name', 'Mobile Scorecard')

            # Save scores
            for criteria_id, score_value in scores.items():
                score_candidate(candidate_id, criteria_id, score_value, evaluator)

            # Build notes with recommendation
            full_notes = f"Recommendation: {recommendation}\n\n{notes}"

            # Add stage notes
            add_stage_notes(
                candidate_id=candidate_id,
                stage=stage,
                notes=full_notes,
                interviewer=evaluator,
                interview_date=datetime.now().isoformat()
            )

            # Mark token as used
            conn.execute("""
                UPDATE scorecard_tokens
                SET used_at = ?, is_active = 0
                WHERE token = ?
            """, (datetime.now().isoformat(), token))

            return True, "Scorecard submitted successfully"

    except KeyError as e:
        logger.error(f"Missing required field when submitting scorecard with token: {e}")
        return False, "Error submitting scorecard: a required field is missing"
    except Exception as e:
        logger.exception("Unexpected error submitting scorecard with token")
        return False, "An unexpected error occurred. Please try again or contact support."


def invalidate_token(token: str) -> bool:
    """
    Manually invalidate a scorecard token.

    Args:
        token: The token to invalidate

    Returns:
        True if token was found and invalidated, False otherwise
    """
    with db_session() as conn:
        cursor = conn.execute(
            "UPDATE scorecard_tokens SET is_active = 0 WHERE token = ?",
            (token,)
        )
        return cursor.rowcount > 0


def get_scorecard_tokens_for_interview(interview_id: int) -> list:
    """
    Get all scorecard tokens for an interview.

    Args:
        interview_id: The interview ID

    Returns:
        List of token records
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT * FROM scorecard_tokens
            WHERE interview_id = ?
            ORDER BY created_at DESC
        """, (interview_id,)).fetchall()
        return [dict(r) for r in rows]


def cleanup_expired_tokens() -> int:
    """
    Clean up expired tokens by marking them as inactive.

    Returns:
        Number of tokens cleaned up
    """
    with db_session() as conn:
        cursor = conn.execute("""
            UPDATE scorecard_tokens
            SET is_active = 0
            WHERE is_active = 1 AND expires_at < ?
        """, (datetime.now().isoformat(),))
        return cursor.rowcount


# Recommendation options for the mobile UI
RECOMMENDATIONS = [
    ("Strong Yes", "strong-yes", "#2E7D32"),   # Green
    ("Yes", "yes", "#4CAF50"),                  # Light green
    ("Maybe", "maybe", "#FF9800"),              # Orange
    ("No", "no", "#f44336"),                    # Red
    ("Strong No", "strong-no", "#b71c1c"),      # Dark red
]


def get_recommendation_options() -> list:
    """Get the list of recommendation options with their display info."""
    return RECOMMENDATIONS
