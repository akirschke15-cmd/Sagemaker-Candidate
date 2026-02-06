"""
ATS Scoring Operations
Manages candidate scoring and evaluation
"""
from typing import List, Dict
from .connection import db_session


def score_candidate(candidate_id: int, criteria_id: int, score: int, evaluator: str = None):
    with db_session() as conn:
        conn.execute("""
            INSERT INTO stage_scores (candidate_id, criteria_id, score, evaluator, stage)
            VALUES (?, ?, ?, ?, (SELECT stage FROM scoring_criteria WHERE id = ?))
            ON CONFLICT(candidate_id, criteria_id) DO UPDATE SET score = ?, evaluator = ?, scored_at = CURRENT_TIMESTAMP
        """, (candidate_id, criteria_id, score, evaluator, criteria_id, score, evaluator))


def get_candidate_scores(candidate_id: int, stage: str = None) -> List[Dict]:
    with db_session() as conn:
        query = """
            SELECT ss.*, sc.criteria_name, sc.max_score, sc.weight, sc.description
            FROM stage_scores ss
            JOIN scoring_criteria sc ON ss.criteria_id = sc.id
            WHERE ss.candidate_id = ?
        """
        params = [candidate_id]
        if stage:
            query += " AND ss.stage = ?"
            params.append(stage)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_stage_total_score(candidate_id: int, stage: str) -> Dict:
    """Get weighted total score for a stage"""
    scores = get_candidate_scores(candidate_id, stage)
    if not scores:
        return {'total': 0, 'max_possible': 0, 'percentage': 0}

    total = sum(s['score'] * s['weight'] for s in scores if s['score'] is not None)
    max_possible = sum(s['max_score'] * s['weight'] for s in scores)
    return {
        'total': total,
        'max_possible': max_possible,
        'percentage': (total / max_possible * 100) if max_possible > 0 else 0
    }


# ============ STAGE NOTES OPERATIONS ============
def add_stage_notes(candidate_id: int, stage: str, notes: str, interviewer: str = None, interview_date: str = None):
    with db_session() as conn:
        conn.execute("""
            INSERT INTO stage_notes (candidate_id, stage, notes, interviewer, interview_date)
            VALUES (?, ?, ?, ?, ?)
        """, (candidate_id, stage, notes, interviewer, interview_date))


def get_stage_notes(candidate_id: int, stage: str = None) -> List[Dict]:
    with db_session() as conn:
        if stage:
            rows = conn.execute(
                "SELECT * FROM stage_notes WHERE candidate_id = ? AND stage = ? ORDER BY created_at DESC",
                (candidate_id, stage)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stage_notes WHERE candidate_id = ? ORDER BY created_at DESC",
                (candidate_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def update_note_ai_summary(note_id: int, summary: str):
    with db_session() as conn:
        conn.execute("UPDATE stage_notes SET ai_summary = ? WHERE id = ?", (summary, note_id))


def add_stage_notes_for_role(candidate_id: int, job_id: int, stage: str, notes: str,
                             interviewer: str = None, interview_date: str = None):
    """Add stage notes with job context for multi-role support (AC4)."""
    with db_session() as conn:
        conn.execute("""
            INSERT INTO stage_notes (candidate_id, job_id, stage, notes, interviewer, interview_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (candidate_id, job_id, stage, notes, interviewer, interview_date))


def get_stage_notes_with_role(candidate_id: int, job_id: int = None, stage: str = None) -> List[Dict]:
    """Get stage notes with job context for multi-role support (AC4)."""
    with db_session() as conn:
        query = """
            SELECT sn.*, j.title as job_title
            FROM stage_notes sn
            LEFT JOIN jobs j ON sn.job_id = j.id
            WHERE sn.candidate_id = ?
        """
        params = [candidate_id]
        if job_id:
            query += " AND (sn.job_id = ? OR sn.job_id IS NULL)"
            params.append(job_id)
        if stage:
            query += " AND sn.stage = ?"
            params.append(stage)
        query += " ORDER BY sn.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ============ SAVED QUESTIONS OPERATIONS ============
def save_interview_question(job_id: int, stage: str, question: str, category: str = None,
                           probing_area: str = None, is_standard: int = 0) -> int:
    """Save an interview question for future reuse."""
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO saved_questions (job_id, stage, question, category, probing_area, is_standard)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, stage, question, category, probing_area, is_standard))
        return cursor.lastrowid


def get_saved_questions(job_id: int = None, stage: str = None, category: str = None) -> List[Dict]:
    """Get saved interview questions with optional filtering."""
    with db_session() as conn:
        query = """
            SELECT sq.*, j.title as job_title
            FROM saved_questions sq
            LEFT JOIN jobs j ON sq.job_id = j.id
            WHERE 1=1
        """
        params = []
        if job_id:
            query += " AND sq.job_id = ?"
            params.append(job_id)
        if stage:
            query += " AND sq.stage = ?"
            params.append(stage)
        if category:
            query += " AND sq.category = ?"
            params.append(category)
        query += " ORDER BY sq.is_standard DESC, sq.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_saved_question(question_id: int) -> Dict:
    """Get a single saved question by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT sq.*, j.title as job_title
            FROM saved_questions sq
            LEFT JOIN jobs j ON sq.job_id = j.id
            WHERE sq.id = ?
        """, (question_id,)).fetchone()
        return dict(row) if row else None


def update_saved_question(question_id: int, **kwargs):
    """Update a saved question."""
    ALLOWED_COLUMNS = {'job_id', 'stage', 'question', 'category', 'probing_area', 'is_standard'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE saved_questions SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), question_id))


def delete_saved_question(question_id: int):
    """Delete a saved question."""
    with db_session() as conn:
        conn.execute("DELETE FROM saved_questions WHERE id = ?", (question_id,))


def toggle_question_standard(question_id: int) -> bool:
    """Toggle a question's standard status. Returns new status."""
    with db_session() as conn:
        current = conn.execute(
            "SELECT is_standard FROM saved_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if current:
            new_status = 0 if current['is_standard'] else 1
            conn.execute(
                "UPDATE saved_questions SET is_standard = ? WHERE id = ?",
                (new_status, question_id)
            )
            return bool(new_status)
        return False


def get_question_bank_stats(job_id: int = None) -> Dict:
    """Get statistics about saved questions."""
    with db_session() as conn:
        query = "SELECT COUNT(*) as total, category FROM saved_questions WHERE 1=1"
        params = []
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        query += " GROUP BY category"
        rows = conn.execute(query, params).fetchall()

        stats = {'total': 0, 'by_category': {}}
        for row in rows:
            stats['by_category'][row['category'] or 'uncategorized'] = row['total']
            stats['total'] += row['total']
        return stats
