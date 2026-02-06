"""
ATS Analytics Operations
Pipeline stats, conversion rates, vendor performance, and reporting
"""
from typing import List, Dict
from .connection import db_session

try:
    from cache import analytics_cache, cached
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cache import analytics_cache, cached


def get_pipeline_stats(job_id: int = None) -> Dict:
    """Get candidate counts by stage"""
    with db_session() as conn:
        query = "SELECT current_stage, COUNT(*) as count FROM candidates WHERE status = 'Active'"
        params = []
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        query += " GROUP BY current_stage"
        rows = conn.execute(query, params).fetchall()
        return {r['current_stage']: r['count'] for r in rows}


@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_pipeline_stats_multirole(job_id: int = None) -> Dict:
    """Get candidate counts by stage using candidate_jobs table for multi-role support (AC5)."""
    with db_session() as conn:
        if job_id:
            query = """
                SELECT current_stage, COUNT(*) as count
                FROM candidate_jobs
                WHERE status = 'Active' AND job_id = ?
                GROUP BY current_stage
            """
            rows = conn.execute(query, (job_id,)).fetchall()
        else:
            query = """
                SELECT current_stage, COUNT(DISTINCT candidate_id) as count
                FROM candidate_jobs
                WHERE status = 'Active'
                GROUP BY current_stage
            """
            rows = conn.execute(query).fetchall()
        return {r['current_stage']: r['count'] for r in rows}


def get_vendor_stats() -> List[Dict]:
    """Get stats per vendor"""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT v.id, v.name,
                   COUNT(c.id) as total_candidates,
                   SUM(CASE WHEN c.status = 'Active' THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN c.current_stage = 'Hired' THEN 1 ELSE 0 END) as hired,
                   SUM(CASE WHEN c.status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                   AVG(c.ai_resume_score) as avg_resume_score
            FROM vendors v
            LEFT JOIN candidates c ON v.id = c.vendor_id
            GROUP BY v.id, v.name
            ORDER BY total_candidates DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_job_stats() -> List[Dict]:
    """Get stats per job"""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT j.id, j.title, j.slots,
                   COUNT(c.id) as total_candidates,
                   SUM(CASE WHEN c.status = 'Active' THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN c.current_stage = 'Hired' THEN 1 ELSE 0 END) as filled,
                   j.slots - COALESCE(SUM(CASE WHEN c.current_stage = 'Hired' THEN 1 ELSE 0 END), 0) as remaining_slots
            FROM jobs j
            LEFT JOIN candidates c ON j.id = c.job_id
            WHERE j.status = 'Open'
            GROUP BY j.id, j.title, j.slots
            ORDER BY j.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_job_stats_multirole() -> List[Dict]:
    """Get stats per job using candidate_jobs table for multi-role support."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT j.id, j.title, j.slots,
                   COUNT(cj.id) as total_candidates,
                   SUM(CASE WHEN cj.status = 'Active' THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END) as filled,
                   j.slots - COALESCE(SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END), 0) as remaining_slots
            FROM jobs j
            LEFT JOIN candidate_jobs cj ON j.id = cj.job_id
            WHERE j.status = 'Open'
            GROUP BY j.id, j.title, j.slots
            ORDER BY j.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_pipeline_velocity(job_id: int = None) -> List[Dict]:
    """
    Calculate average days spent in each stage.
    Uses stage_notes and interviews to track time in stages.
    Returns list of {stage, avg_days, min_days, max_days, candidate_count}.
    """
    with db_session() as conn:
        # Optimized: Single query without CTE, uses composite index on (status, current_stage)
        query = """
            SELECT
                cj.current_stage as stage,
                ROUND(AVG(JULIANDAY(cj.updated_at) - JULIANDAY(cj.created_at)), 1) as avg_days,
                ROUND(MIN(JULIANDAY(cj.updated_at) - JULIANDAY(cj.created_at)), 1) as min_days,
                ROUND(MAX(JULIANDAY(cj.updated_at) - JULIANDAY(cj.created_at)), 1) as max_days,
                COUNT(*) as candidate_count
            FROM candidate_jobs cj
            WHERE cj.status IN ('Active', 'Rejected')
        """
        params = []
        if job_id:
            query += " AND cj.job_id = ?"
            params.append(job_id)

        query += """
            GROUP BY cj.current_stage
            HAVING avg_days >= 0
            ORDER BY
                CASE cj.current_stage
                    WHEN 'Resume Screen' THEN 1
                    WHEN 'Phone Screen' THEN 2
                    WHEN 'Technical Interview' THEN 3
                    WHEN 'Behavioral Interview' THEN 4
                    WHEN 'Offer' THEN 5
                    WHEN 'Hired' THEN 6
                    WHEN 'Rejected' THEN 7
                    ELSE 99
                END
        """
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_time_to_hire_stats(job_id: int = None) -> Dict:
    """
    Calculate time-to-hire statistics (from application to hired).
    Returns {avg_days, min_days, max_days, median_days, total_hires, by_job: []}.
    """
    with db_session() as conn:
        query = """
            SELECT
                cj.job_id,
                j.title as job_title,
                JULIANDAY(cj.updated_at) - JULIANDAY(c.created_at) as days_to_hire
            FROM candidate_jobs cj
            JOIN candidates c ON cj.candidate_id = c.id
            JOIN jobs j ON cj.job_id = j.id
            WHERE cj.current_stage = 'Hired'
        """
        params = []
        if job_id:
            query += " AND cj.job_id = ?"
            params.append(job_id)

        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                'avg_days': 0,
                'min_days': 0,
                'max_days': 0,
                'median_days': 0,
                'total_hires': 0,
                'by_job': []
            }

        days_list = [r['days_to_hire'] for r in rows if r['days_to_hire'] is not None]

        if not days_list:
            return {
                'avg_days': 0,
                'min_days': 0,
                'max_days': 0,
                'median_days': 0,
                'total_hires': 0,
                'by_job': []
            }

        days_list.sort()
        n = len(days_list)
        median = days_list[n // 2] if n % 2 == 1 else (days_list[n // 2 - 1] + days_list[n // 2]) / 2

        # Group by job
        by_job_query = """
            SELECT
                j.id as job_id,
                j.title as job_title,
                COUNT(*) as hire_count,
                ROUND(AVG(JULIANDAY(cj.updated_at) - JULIANDAY(c.created_at)), 1) as avg_days
            FROM candidate_jobs cj
            JOIN candidates c ON cj.candidate_id = c.id
            JOIN jobs j ON cj.job_id = j.id
            WHERE cj.current_stage = 'Hired'
        """
        if job_id:
            by_job_query += " AND cj.job_id = ?"
        by_job_query += " GROUP BY j.id, j.title ORDER BY avg_days"

        by_job_rows = conn.execute(by_job_query, params).fetchall()

        return {
            'avg_days': round(sum(days_list) / len(days_list), 1),
            'min_days': round(min(days_list), 1),
            'max_days': round(max(days_list), 1),
            'median_days': round(median, 1),
            'total_hires': len(days_list),
            'by_job': [dict(r) for r in by_job_rows]
        }


@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_stage_conversion_rates(job_id: int = None) -> List[Dict]:
    """
    Calculate conversion rates between stages.
    Returns list of {from_stage, to_stage, total_entered, advanced, rejected, conversion_rate}.
    """
    with db_session() as conn:
        # Optimized: Single query to get both counts and rejected counts using CASE
        query = """
            SELECT
                current_stage as stage,
                COUNT(*) as count,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected_count
            FROM candidate_jobs
            WHERE 1=1
        """
        params = []
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        query += " GROUP BY current_stage"

        rows = conn.execute(query, params).fetchall()
        stage_counts = {r['stage']: r['count'] for r in rows}
        rejected_counts = {r['stage']: r['rejected_count'] for r in rows}

        # Define stage progression order
        stage_order = ['Resume Screen', 'Phone Screen', 'Technical Interview',
                       'Behavioral Interview', 'Offer', 'Hired']

        results = []
        for i, stage in enumerate(stage_order[:-1]):
            next_stage = stage_order[i + 1]

            total_at_or_past = sum(stage_counts.get(s, 0) for s in stage_order[i:])
            total_rejected_here = rejected_counts.get(stage, 0)

            total_entered = total_at_or_past + total_rejected_here
            advanced = sum(stage_counts.get(s, 0) for s in stage_order[i+1:])
            rejected = total_rejected_here

            conversion_rate = (advanced / total_entered * 100) if total_entered > 0 else 0

            results.append({
                'from_stage': stage,
                'to_stage': next_stage,
                'total_entered': total_entered,
                'advanced': advanced,
                'rejected': rejected,
                'still_in_stage': stage_counts.get(stage, 0),
                'conversion_rate': round(conversion_rate, 1)
            })

        return results


def get_vendor_performance() -> List[Dict]:
    """
    Get detailed vendor performance metrics.
    Returns list of {vendor_id, vendor_name, submitted, hired, rejected,
                     pass_rate, avg_ai_score, avg_days_to_hire}.
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT
                v.id as vendor_id,
                v.name as vendor_name,
                COUNT(DISTINCT c.id) as submitted,
                SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END) as hired,
                SUM(CASE WHEN cj.status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                ROUND(AVG(cj.ai_resume_score), 1) as avg_ai_score,
                ROUND(AVG(CASE
                    WHEN cj.current_stage = 'Hired'
                    THEN JULIANDAY(cj.updated_at) - JULIANDAY(c.created_at)
                    ELSE NULL
                END), 1) as avg_days_to_hire
            FROM vendors v
            LEFT JOIN candidates c ON v.id = c.vendor_id
            LEFT JOIN candidate_jobs cj ON c.id = cj.candidate_id
            GROUP BY v.id, v.name
            HAVING submitted > 0
            ORDER BY hired DESC, submitted DESC
        """).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d['pass_rate'] = round((d['hired'] / d['submitted'] * 100), 1) if d['submitted'] > 0 else 0
            results.append(d)

        return results


def get_hiring_trends(days: int = 90) -> List[Dict]:
    """
    Get hiring trends over time.
    Returns list of {date, hires, applications}.
    """
    with db_session() as conn:
        # Hires by date
        hires_query = """
            SELECT
                DATE(cj.updated_at) as date,
                COUNT(*) as hires
            FROM candidate_jobs cj
            WHERE cj.current_stage = 'Hired'
            AND cj.updated_at >= DATE('now', ?)
            GROUP BY DATE(cj.updated_at)
            ORDER BY date
        """
        hires = {r['date']: r['hires'] for r in conn.execute(hires_query, (f'-{days} days',)).fetchall()}

        # Applications by date
        apps_query = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as applications
            FROM candidates
            WHERE created_at >= DATE('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        apps = {r['date']: r['applications'] for r in conn.execute(apps_query, (f'-{days} days',)).fetchall()}

        # Combine all dates
        all_dates = sorted(set(list(hires.keys()) + list(apps.keys())))

        return [{
            'date': d,
            'hires': hires.get(d, 0),
            'applications': apps.get(d, 0)
        } for d in all_dates]


def get_rejection_reasons() -> List[Dict]:
    """
    Analyze where candidates are rejected most (which stages).
    Returns list of {stage, rejection_count, percentage}.
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT
                current_stage as stage,
                COUNT(*) as rejection_count
            FROM candidate_jobs
            WHERE status = 'Rejected' AND current_stage = 'Rejected'
            GROUP BY current_stage
            UNION ALL
            SELECT
                current_stage as stage,
                COUNT(*) as rejection_count
            FROM candidate_jobs
            WHERE status = 'Rejected' AND current_stage != 'Rejected'
            GROUP BY current_stage
            ORDER BY rejection_count DESC
        """).fetchall()

        total = sum(r['rejection_count'] for r in rows)

        results = []
        for r in rows:
            d = dict(r)
            d['percentage'] = round((d['rejection_count'] / total * 100), 1) if total > 0 else 0
            results.append(d)

        return results


def get_ai_score_accuracy() -> Dict:
    """
    Compare AI resume scores to actual hiring outcomes.
    Returns {avg_score_hired, avg_score_rejected, score_correlation,
             hired_by_score_range: [], rejected_by_score_range: []}.
    """
    with db_session() as conn:
        # Average scores by outcome
        avg_query = """
            SELECT
                CASE
                    WHEN cj.current_stage = 'Hired' THEN 'hired'
                    WHEN cj.status = 'Rejected' THEN 'rejected'
                    ELSE 'active'
                END as outcome,
                ROUND(AVG(cj.ai_resume_score), 1) as avg_score,
                COUNT(*) as count
            FROM candidate_jobs cj
            WHERE cj.ai_resume_score IS NOT NULL
            GROUP BY outcome
        """
        avg_rows = conn.execute(avg_query).fetchall()

        outcomes = {r['outcome']: {'avg_score': r['avg_score'], 'count': r['count']} for r in avg_rows}

        # Score distribution for hired vs rejected
        score_ranges = [(0, 40), (40, 60), (60, 80), (80, 100)]

        hired_by_range = []
        rejected_by_range = []

        for low, high in score_ranges:
            range_query = """
                SELECT
                    SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END) as hired,
                    SUM(CASE WHEN cj.status = 'Rejected' THEN 1 ELSE 0 END) as rejected
                FROM candidate_jobs cj
                WHERE cj.ai_resume_score >= ? AND cj.ai_resume_score < ?
            """
            row = conn.execute(range_query, (low, high)).fetchone()

            hired_by_range.append({
                'range': f'{low}-{high}',
                'count': row['hired'] or 0
            })
            rejected_by_range.append({
                'range': f'{low}-{high}',
                'count': row['rejected'] or 0
            })

        # Calculate predictive accuracy (what % of high scorers got hired)
        high_score_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END) as hired
            FROM candidate_jobs cj
            WHERE cj.ai_resume_score >= 70
            AND (cj.current_stage = 'Hired' OR cj.status = 'Rejected')
        """
        high_score = conn.execute(high_score_query).fetchone()

        predictive_accuracy = 0
        if high_score and high_score['total'] > 0:
            predictive_accuracy = round((high_score['hired'] / high_score['total'] * 100), 1)

        return {
            'avg_score_hired': outcomes.get('hired', {}).get('avg_score', 0),
            'avg_score_rejected': outcomes.get('rejected', {}).get('avg_score', 0),
            'avg_score_active': outcomes.get('active', {}).get('avg_score', 0),
            'hired_count': outcomes.get('hired', {}).get('count', 0),
            'rejected_count': outcomes.get('rejected', {}).get('count', 0),
            'predictive_accuracy': predictive_accuracy,
            'hired_by_score_range': hired_by_range,
            'rejected_by_score_range': rejected_by_range
        }


def get_source_effectiveness() -> List[Dict]:
    """
    Analyze effectiveness of different candidate sources (vendors).
    Returns list with funnel metrics per source.
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT
                COALESCE(v.name, 'Direct/Unknown') as source,
                COUNT(DISTINCT c.id) as total_candidates,
                SUM(CASE WHEN cj.current_stage IN ('Phone Screen', 'Technical Interview', 'Behavioral Interview', 'Offer', 'Hired') THEN 1 ELSE 0 END) as passed_screen,
                SUM(CASE WHEN cj.current_stage IN ('Technical Interview', 'Behavioral Interview', 'Offer', 'Hired') THEN 1 ELSE 0 END) as passed_phone,
                SUM(CASE WHEN cj.current_stage IN ('Behavioral Interview', 'Offer', 'Hired') THEN 1 ELSE 0 END) as passed_technical,
                SUM(CASE WHEN cj.current_stage IN ('Offer', 'Hired') THEN 1 ELSE 0 END) as reached_offer,
                SUM(CASE WHEN cj.current_stage = 'Hired' THEN 1 ELSE 0 END) as hired,
                ROUND(AVG(cj.ai_resume_score), 1) as avg_ai_score
            FROM candidates c
            LEFT JOIN vendors v ON c.vendor_id = v.id
            LEFT JOIN candidate_jobs cj ON c.id = cj.candidate_id
            GROUP BY COALESCE(v.name, 'Direct/Unknown')
            HAVING total_candidates > 0
            ORDER BY hired DESC, total_candidates DESC
        """).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d['screen_rate'] = round((d['passed_screen'] / d['total_candidates'] * 100), 1) if d['total_candidates'] > 0 else 0
            d['hire_rate'] = round((d['hired'] / d['total_candidates'] * 100), 1) if d['total_candidates'] > 0 else 0
            results.append(d)

        return results
