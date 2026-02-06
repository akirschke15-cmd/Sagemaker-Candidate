"""
ATS Candidate CRUD Operations
Manages candidates and multi-role matching
"""
from typing import List, Dict, Optional
from datetime import datetime
from .connection import db_session

try:
    from cache import invalidate_candidate_caches
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cache import invalidate_candidate_caches


# ============ BASIC CANDIDATE OPERATIONS ============
def create_candidate(name: str, email: str = None, phone: str = None,
                     vendor_id: int = None, job_id: int = None,
                     resume_text: str = None, resume_path: str = None,
                     resume_original_filename: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO candidates (name, email, phone, vendor_id, job_id, resume_text, resume_path, resume_original_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, vendor_id, job_id, resume_text, resume_path, resume_original_filename))
        candidate_id = cursor.lastrowid
    invalidate_candidate_caches()
    return candidate_id


def get_candidates(job_id: int = None, vendor_id: int = None, stage: str = None, status: str = 'Active') -> List[Dict]:
    with db_session() as conn:
        query = "SELECT c.*, j.title as job_title, v.name as vendor_name FROM candidates c LEFT JOIN jobs j ON c.job_id = j.id LEFT JOIN vendors v ON c.vendor_id = v.id WHERE 1=1"
        params = []
        if job_id:
            query += " AND c.job_id = ?"
            params.append(job_id)
        if vendor_id:
            query += " AND c.vendor_id = ?"
            params.append(vendor_id)
        if stage:
            query += " AND c.current_stage = ?"
            params.append(stage)
        if status:
            query += " AND c.status = ?"
            params.append(status)
        query += " ORDER BY c.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_candidate(candidate_id: int) -> Optional[Dict]:
    with db_session() as conn:
        row = conn.execute("""
            SELECT c.*, j.title as job_title, j.description as job_description,
                   j.requirements as job_requirements, v.name as vendor_name
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE c.id = ?
        """, (candidate_id,)).fetchone()
        return dict(row) if row else None


def update_candidate(candidate_id: int, **kwargs):
    ALLOWED_COLUMNS = {'name', 'email', 'phone', 'vendor_id', 'job_id', 'current_stage', 'status', 'resume_text', 'resume_path', 'resume_original_filename', 'ai_resume_score', 'ai_resume_analysis', 'notes', 'updated_at', 'expected_hourly_rate', 'is_past_contractor', 'last_contract_end', 'rehire_eligible', 'rehire_notes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE candidates SET {set_clause} WHERE id = ?", (*kwargs.values(), candidate_id))
    invalidate_candidate_caches()


def batch_update_candidates(updates: List[Dict]):
    """
    Update multiple candidates in a single transaction.

    Args:
        updates: List of dicts with 'id' and field updates, e.g.:
                 [{'id': 1, 'status': 'Rejected'}, {'id': 2, 'current_stage': 'Offer'}]
    """
    ALLOWED_COLUMNS = {'name', 'email', 'phone', 'vendor_id', 'job_id', 'current_stage', 'status', 'resume_text', 'resume_path', 'resume_original_filename', 'ai_resume_score', 'ai_resume_analysis', 'notes', 'updated_at', 'expected_hourly_rate', 'is_past_contractor', 'last_contract_end', 'rehire_eligible', 'rehire_notes'}

    if not updates:
        return

    now = datetime.now().isoformat()

    with db_session() as conn:
        for update in updates:
            if 'id' not in update:
                raise ValueError("Each update must contain 'id' field")

            candidate_id = update.pop('id')

            # Validate column names
            invalid_cols = set(update.keys()) - ALLOWED_COLUMNS
            if invalid_cols:
                raise ValueError(f"Invalid column names: {invalid_cols}")

            if not update:
                continue  # Skip if no fields to update

            # Add updated_at
            update['updated_at'] = now

            # Build and execute update
            set_clause = ", ".join(f"{k} = ?" for k in update.keys())
            conn.execute(f"UPDATE candidates SET {set_clause} WHERE id = ?", (*update.values(), candidate_id))


def advance_candidate(candidate_id: int, new_stage: str):
    update_candidate(candidate_id, current_stage=new_stage)
    invalidate_candidate_caches()


def reject_candidate(candidate_id: int):
    update_candidate(candidate_id, status='Rejected', current_stage='Rejected')
    invalidate_candidate_caches()


# ============ MULTI-ROLE MATCHING OPERATIONS (Feature 6) ============
def add_candidate_to_job(candidate_id: int, job_id: int, is_primary: int = 0) -> int:
    """Add a candidate to a job role. Returns the candidate_jobs id."""
    with db_session() as conn:
        existing = conn.execute(
            "SELECT id FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        ).fetchone()
        if existing:
            return existing['id']
        cursor = conn.execute("""
            INSERT INTO candidate_jobs (candidate_id, job_id, is_primary, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (candidate_id, job_id, is_primary))
        candidate = conn.execute("SELECT job_id FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if candidate and (is_primary or not candidate['job_id']):
            conn.execute("UPDATE candidates SET job_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (job_id, candidate_id))
        return cursor.lastrowid


def remove_candidate_from_job(candidate_id: int, job_id: int):
    """Remove a candidate from a job role."""
    with db_session() as conn:
        conn.execute(
            "DELETE FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        )
        candidate = conn.execute("SELECT job_id FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if candidate and candidate['job_id'] == job_id:
            other_job = conn.execute(
                "SELECT job_id FROM candidate_jobs WHERE candidate_id = ? ORDER BY is_primary DESC, created_at ASC LIMIT 1",
                (candidate_id,)
            ).fetchone()
            new_job_id = other_job['job_id'] if other_job else None
            conn.execute(
                "UPDATE candidates SET job_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_job_id, candidate_id)
            )


def get_candidate_jobs(candidate_id: int) -> List[Dict]:
    """Get all jobs associated with a candidate, including job details and per-job status."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT cj.*, j.title as job_title, j.description as job_description,
                   j.requirements as job_requirements, j.department, j.status as job_status
            FROM candidate_jobs cj
            JOIN jobs j ON cj.job_id = j.id
            WHERE cj.candidate_id = ?
            ORDER BY cj.is_primary DESC, cj.created_at ASC
        """, (candidate_id,)).fetchall()
        return [dict(r) for r in rows]


def get_candidate_role_status(candidate_id: int, job_id: int) -> Optional[Dict]:
    """Get the status of a candidate for a specific job role."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT cj.*, j.title as job_title, j.description as job_description,
                   j.requirements as job_requirements
            FROM candidate_jobs cj
            JOIN jobs j ON cj.job_id = j.id
            WHERE cj.candidate_id = ? AND cj.job_id = ?
        """, (candidate_id, job_id)).fetchone()
        return dict(row) if row else None


def advance_candidate_in_role(candidate_id: int, job_id: int, new_stage: str):
    """Advance a candidate to a new stage for a specific job role."""
    with db_session() as conn:
        conn.execute("""
            UPDATE candidate_jobs
            SET current_stage = ?, updated_at = CURRENT_TIMESTAMP
            WHERE candidate_id = ? AND job_id = ?
        """, (new_stage, candidate_id, job_id))
        cj = conn.execute(
            "SELECT is_primary FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        ).fetchone()
        if cj and cj['is_primary']:
            conn.execute(
                "UPDATE candidates SET current_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stage, candidate_id)
            )


def reject_candidate_in_role(candidate_id: int, job_id: int):
    """Reject a candidate for a specific job role."""
    with db_session() as conn:
        conn.execute("""
            UPDATE candidate_jobs
            SET current_stage = 'Rejected', status = 'Rejected', updated_at = CURRENT_TIMESTAMP
            WHERE candidate_id = ? AND job_id = ?
        """, (candidate_id, job_id))
        cj = conn.execute(
            "SELECT is_primary FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        ).fetchone()
        other_active = conn.execute("""
            SELECT job_id, current_stage FROM candidate_jobs
            WHERE candidate_id = ? AND status = 'Active' AND job_id != ?
            ORDER BY is_primary DESC, created_at ASC LIMIT 1
        """, (candidate_id, job_id)).fetchone()
        if other_active:
            conn.execute(
                "UPDATE candidate_jobs SET is_primary = 1 WHERE candidate_id = ? AND job_id = ?",
                (candidate_id, other_active['job_id'])
            )
            conn.execute("""
                UPDATE candidates SET job_id = ?, current_stage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (other_active['job_id'], other_active['current_stage'], candidate_id))
        elif cj and cj['is_primary']:
            conn.execute(
                "UPDATE candidates SET current_stage = 'Rejected', status = 'Rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (candidate_id,)
            )


def update_candidate_role_score(candidate_id: int, job_id: int, score: float, analysis: str):
    """Update AI resume score for a specific candidate-job association."""
    with db_session() as conn:
        conn.execute("""
            UPDATE candidate_jobs
            SET ai_resume_score = ?, ai_resume_analysis = ?, updated_at = CURRENT_TIMESTAMP
            WHERE candidate_id = ? AND job_id = ?
        """, (score, analysis, candidate_id, job_id))
        cj = conn.execute(
            "SELECT is_primary FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        ).fetchone()
        if cj and cj['is_primary']:
            conn.execute(
                "UPDATE candidates SET ai_resume_score = ?, ai_resume_analysis = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (score, analysis, candidate_id)
            )


def set_primary_job(candidate_id: int, job_id: int):
    """Set a job as the primary role for a candidate."""
    with db_session() as conn:
        conn.execute(
            "UPDATE candidate_jobs SET is_primary = 0 WHERE candidate_id = ?",
            (candidate_id,)
        )
        conn.execute(
            "UPDATE candidate_jobs SET is_primary = 1, updated_at = CURRENT_TIMESTAMP WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        )
        cj = conn.execute(
            "SELECT current_stage, status, ai_resume_score, ai_resume_analysis FROM candidate_jobs WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job_id)
        ).fetchone()
        if cj:
            conn.execute("""
                UPDATE candidates
                SET job_id = ?, current_stage = ?, status = ?, ai_resume_score = ?, ai_resume_analysis = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (job_id, cj['current_stage'], cj['status'], cj['ai_resume_score'], cj['ai_resume_analysis'], candidate_id))


def get_candidates_for_job_multirole(job_id: int, stage: str = None, status: str = 'Active') -> List[Dict]:
    """Get all candidates associated with a specific job, using the candidate_jobs table."""
    with db_session() as conn:
        query = """
            SELECT c.*, cj.current_stage as role_stage, cj.status as role_status,
                   cj.ai_resume_score as role_ai_score, cj.ai_resume_analysis as role_ai_analysis,
                   cj.is_primary, cj.id as candidate_job_id,
                   j.title as job_title, v.name as vendor_name
            FROM candidates c
            JOIN candidate_jobs cj ON c.id = cj.candidate_id
            JOIN jobs j ON cj.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE cj.job_id = ?
        """
        params = [job_id]
        if stage:
            query += " AND cj.current_stage = ?"
            params.append(stage)
        if status:
            query += " AND cj.status = ?"
            params.append(status)
        query += " ORDER BY cj.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_candidates_for_comparison(candidate_ids: list) -> list:
    """
    Get detailed candidate data for comparison view.

    Args:
        candidate_ids: List of candidate IDs to compare (2-3 candidates)

    Returns:
        List of candidate dicts with: basic info, AI scores, stage scores,
        expected rate, role rate range, strengths, gaps, interview scores
    """
    if not candidate_ids or len(candidate_ids) < 2 or len(candidate_ids) > 3:
        return []

    with db_session() as conn:
        results = []

        for cid in candidate_ids:
            # Get basic candidate info with job details
            row = conn.execute("""
                SELECT c.*,
                       j.title as job_title,
                       j.description as job_description,
                       j.requirements as job_requirements,
                       j.contractor_role_id,
                       v.name as vendor_name,
                       cr.name as role_name,
                       cr.min_hourly_rate as role_min_rate,
                       cr.max_hourly_rate as role_max_rate
                FROM candidates c
                LEFT JOIN jobs j ON c.job_id = j.id
                LEFT JOIN vendors v ON c.vendor_id = v.id
                LEFT JOIN contractor_roles cr ON j.contractor_role_id = cr.id
                WHERE c.id = ?
            """, (cid,)).fetchone()

            if not row:
                continue

            candidate = dict(row)

            # Calculate days in pipeline
            if candidate.get('created_at'):
                try:
                    created = datetime.fromisoformat(candidate['created_at'].replace('Z', '+00:00'))
                    days_in_pipeline = (datetime.now() - created.replace(tzinfo=None)).days
                    candidate['days_in_pipeline'] = days_in_pipeline
                except:
                    candidate['days_in_pipeline'] = 0
            else:
                candidate['days_in_pipeline'] = 0

            # Parse AI analysis for strengths and gaps
            analysis = candidate.get('ai_resume_analysis', '')
            strengths = []
            gaps = []

            if analysis:
                # Parse strengths section
                if 'Strengths:' in analysis:
                    strengths_section = analysis.split('Strengths:')[1]
                    if 'Gaps:' in strengths_section:
                        strengths_section = strengths_section.split('Gaps:')[0]
                    strengths = [s.strip() for s in strengths_section.split(',') if s.strip()]

                # Parse gaps section
                if 'Gaps:' in analysis:
                    gaps_section = analysis.split('Gaps:')[1]
                    gaps = [g.strip() for g in gaps_section.split(',') if g.strip()]

            candidate['strengths'] = strengths[:5]  # Limit to 5 items
            candidate['gaps'] = gaps[:5]

            # Get rate status
            expected_rate = candidate.get('expected_hourly_rate')
            min_rate = candidate.get('role_min_rate')
            max_rate = candidate.get('role_max_rate')

            if expected_rate and (min_rate or max_rate):
                if min_rate and expected_rate < min_rate:
                    candidate['rate_status'] = 'below'
                    candidate['rate_variance'] = ((expected_rate - min_rate) / min_rate) * 100
                elif max_rate and expected_rate > max_rate:
                    candidate['rate_status'] = 'above'
                    candidate['rate_variance'] = ((expected_rate - max_rate) / max_rate) * 100
                else:
                    candidate['rate_status'] = 'in_range'
                    candidate['rate_variance'] = 0
            else:
                candidate['rate_status'] = 'no_data'
                candidate['rate_variance'] = 0

            # Get interview scores by stage
            scores = conn.execute("""
                SELECT ss.stage,
                       SUM(ss.score * sc.weight) as weighted_score,
                       SUM(sc.max_score * sc.weight) as max_possible,
                       ss.evaluator
                FROM stage_scores ss
                JOIN scoring_criteria sc ON ss.criteria_id = sc.id
                WHERE ss.candidate_id = ?
                GROUP BY ss.stage
            """, (cid,)).fetchall()

            interview_scores = {}
            total_weighted = 0
            total_max = 0

            for score_row in scores:
                stage = score_row['stage']
                weighted = score_row['weighted_score'] or 0
                max_poss = score_row['max_possible'] or 1
                pct = (weighted / max_poss * 100) if max_poss > 0 else 0

                interview_scores[stage] = {
                    'score': weighted,
                    'max': max_poss,
                    'percentage': pct,
                    'evaluator': score_row['evaluator']
                }
                total_weighted += weighted
                total_max += max_poss

            candidate['interview_scores'] = interview_scores
            candidate['total_interview_score'] = (total_weighted / total_max * 100) if total_max > 0 else 0

            # Get stage notes count and recommendations
            notes = conn.execute("""
                SELECT stage, notes, ai_summary
                FROM stage_notes
                WHERE candidate_id = ?
                ORDER BY created_at DESC
            """, (cid,)).fetchall()

            candidate['notes_count'] = len(notes)

            # Count recommendations from notes (look for keywords)
            recommendations = 0
            for note in notes:
                note_text = (note['notes'] or '').lower()
                if 'recommend' in note_text or 'proceed' in note_text or 'advance' in note_text:
                    recommendations += 1

            candidate['recommendations'] = recommendations

            results.append(candidate)

        return results


def export_candidates_data(job_id: int = None, vendor_id: int = None) -> List[Dict]:
    """Export full candidate data for CSV/Excel export"""
    with db_session() as conn:
        query = """
            SELECT c.id, c.name, c.email, c.phone, c.current_stage, c.status,
                   c.ai_resume_score, c.created_at, c.updated_at,
                   j.title as job_title, v.name as vendor_name
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE 1=1
        """
        params = []
        if job_id:
            query += " AND c.job_id = ?"
            params.append(job_id)
        if vendor_id:
            query += " AND c.vendor_id = ?"
            params.append(vendor_id)
        query += " ORDER BY c.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
