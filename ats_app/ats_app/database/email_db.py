"""
ATS Email Operations
Manages email templates, automation rules, and email queue
"""
from typing import List, Dict, Optional
from .connection import db_session


# ============ EMAIL TEMPLATE OPERATIONS ============
def get_email_templates(template_type: str = None) -> List[Dict]:
    with db_session() as conn:
        if template_type:
            rows = conn.execute("SELECT * FROM email_templates WHERE template_type = ?", (template_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM email_templates").fetchall()
        return [dict(r) for r in rows]


def get_email_template(template_id: int) -> Optional[Dict]:
    """Get a single email template by ID."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,)).fetchone()
        return dict(row) if row else None


def log_email(candidate_id: int, recipient: str, subject: str, body: str, status: str = 'sent'):
    with db_session() as conn:
        conn.execute("""
            INSERT INTO email_log (candidate_id, recipient, subject, body, status)
            VALUES (?, ?, ?, ?, ?)
        """, (candidate_id, recipient, subject, body, status))


# ============ EMAIL AUTOMATION OPERATIONS ============
def create_automation_rule(job_id: int, from_stage: str, to_stage: str,
                           template_id: int, delay_minutes: int = 0, is_enabled: int = 1) -> int:
    """
    Create a new email automation rule.

    Args:
        job_id: Job ID (None for global rule)
        from_stage: Source stage that triggers the rule
        to_stage: Target stage that triggers the rule
        template_id: Email template to use
        delay_minutes: Minutes to delay before sending (default 0)
        is_enabled: Whether rule is active (default 1)

    Returns:
        The new rule ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO email_automation_rules (job_id, from_stage, to_stage, template_id, delay_minutes, is_enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, from_stage, to_stage, template_id, delay_minutes, is_enabled))
        return cursor.lastrowid


def get_automation_rules(job_id: int = None, include_global: bool = True) -> List[Dict]:
    """
    Get email automation rules.

    Args:
        job_id: Filter by job ID (None for all rules)
        include_global: Include global rules (job_id IS NULL) when filtering by job

    Returns:
        List of automation rules with template details
    """
    with db_session() as conn:
        query = """
            SELECT ear.*, et.name as template_name, et.subject as template_subject,
                   j.title as job_title
            FROM email_automation_rules ear
            JOIN email_templates et ON ear.template_id = et.id
            LEFT JOIN jobs j ON ear.job_id = j.id
            WHERE 1=1
        """
        params = []

        if job_id is not None:
            if include_global:
                query += " AND (ear.job_id = ? OR ear.job_id IS NULL)"
            else:
                query += " AND ear.job_id = ?"
            params.append(job_id)

        query += " ORDER BY ear.job_id IS NULL DESC, j.title, ear.from_stage, ear.to_stage"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_automation_rule(rule_id: int) -> Optional[Dict]:
    """Get a single automation rule by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT ear.*, et.name as template_name, et.subject as template_subject,
                   j.title as job_title
            FROM email_automation_rules ear
            JOIN email_templates et ON ear.template_id = et.id
            LEFT JOIN jobs j ON ear.job_id = j.id
            WHERE ear.id = ?
        """, (rule_id,)).fetchone()
        return dict(row) if row else None


def update_automation_rule(rule_id: int, **kwargs) -> bool:
    """
    Update an automation rule.

    Args:
        rule_id: Rule ID to update
        **kwargs: Fields to update (job_id, from_stage, to_stage, template_id, delay_minutes, is_enabled)

    Returns:
        True if updated successfully
    """
    ALLOWED_COLUMNS = {'job_id', 'from_stage', 'to_stage', 'template_id', 'is_enabled', 'delay_minutes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE email_automation_rules SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), rule_id))
        return True


def delete_automation_rule(rule_id: int) -> bool:
    """Delete an automation rule."""
    with db_session() as conn:
        conn.execute("DELETE FROM email_automation_rules WHERE id = ?", (rule_id,))
        return True


def get_matching_automation_rules(job_id: int, from_stage: str, to_stage: str) -> List[Dict]:
    """
    Find automation rules matching a stage transition.

    Args:
        job_id: Job ID of the candidate
        from_stage: Previous stage
        to_stage: New stage

    Returns:
        List of matching enabled rules (job-specific first, then global)
    """
    with db_session() as conn:
        # Get matching rules - job-specific rules take precedence
        rows = conn.execute("""
            SELECT ear.*, et.name as template_name, et.subject as template_subject, et.body as template_body
            FROM email_automation_rules ear
            JOIN email_templates et ON ear.template_id = et.id
            WHERE ear.is_enabled = 1
            AND ear.from_stage = ?
            AND ear.to_stage = ?
            AND (ear.job_id = ? OR ear.job_id IS NULL)
            ORDER BY ear.job_id IS NOT NULL DESC
        """, (from_stage, to_stage, job_id)).fetchall()
        return [dict(r) for r in rows]


# ============ EMAIL QUEUE OPERATIONS ============
def queue_email(candidate_id: int, template_id: int, to_email: str,
                subject: str, body: str, scheduled_at: str) -> int:
    """
    Add an email to the send queue.

    Args:
        candidate_id: Candidate ID
        template_id: Template ID used (for reference)
        to_email: Recipient email address
        subject: Rendered email subject
        body: Rendered email body
        scheduled_at: When to send the email (ISO format timestamp)

    Returns:
        Queue entry ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO email_queue (candidate_id, template_id, to_email, subject, body, scheduled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (candidate_id, template_id, to_email, subject, body, scheduled_at))
        return cursor.lastrowid


def get_pending_emails(limit: int = 50) -> List[Dict]:
    """
    Get emails that are pending and ready to be sent.

    Args:
        limit: Maximum number of emails to return

    Returns:
        List of pending emails where scheduled_at <= now
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT eq.*, c.name as candidate_name
            FROM email_queue eq
            JOIN candidates c ON eq.candidate_id = c.id
            WHERE eq.status = 'pending'
            AND eq.scheduled_at <= datetime('now')
            AND eq.retry_count < 3
            ORDER BY eq.scheduled_at ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def mark_email_sent(queue_id: int) -> bool:
    """Mark an email as successfully sent."""
    with db_session() as conn:
        conn.execute("""
            UPDATE email_queue
            SET status = 'sent', sent_at = CURRENT_TIMESTAMP, error_message = NULL
            WHERE id = ?
        """, (queue_id,))
        return True


def mark_email_failed(queue_id: int, error_message: str) -> bool:
    """Mark an email as failed and increment retry count."""
    with db_session() as conn:
        conn.execute("""
            UPDATE email_queue
            SET status = 'failed', error_message = ?, retry_count = retry_count + 1
            WHERE id = ?
        """, (error_message, queue_id))
        return True


def reset_failed_email(queue_id: int) -> bool:
    """Reset a failed email to pending for retry."""
    with db_session() as conn:
        conn.execute("""
            UPDATE email_queue
            SET status = 'pending', error_message = NULL
            WHERE id = ? AND status = 'failed'
        """, (queue_id,))
        return True


def get_email_queue(status: str = None, candidate_id: int = None, limit: int = 100) -> List[Dict]:
    """
    Get email queue entries with optional filtering.

    Args:
        status: Filter by status ('pending', 'sent', 'failed')
        candidate_id: Filter by candidate
        limit: Maximum entries to return

    Returns:
        List of queue entries
    """
    with db_session() as conn:
        query = """
            SELECT eq.*, c.name as candidate_name, et.name as template_name
            FROM email_queue eq
            JOIN candidates c ON eq.candidate_id = c.id
            LEFT JOIN email_templates et ON eq.template_id = et.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND eq.status = ?"
            params.append(status)

        if candidate_id:
            query += " AND eq.candidate_id = ?"
            params.append(candidate_id)

        query += " ORDER BY eq.created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_email_automation_stats() -> Dict:
    """
    Get statistics on email automation.

    Returns:
        Dict with counts of pending, sent, failed emails and active rules
    """
    with db_session() as conn:
        # Queue stats
        stats_row = conn.execute("""
            SELECT
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                COUNT(*) as total
            FROM email_queue
        """).fetchone()

        # Rule count
        rule_count = conn.execute("""
            SELECT COUNT(*) as count FROM email_automation_rules WHERE is_enabled = 1
        """).fetchone()

        # Today's sent count
        today_sent = conn.execute("""
            SELECT COUNT(*) as count FROM email_queue
            WHERE status = 'sent' AND date(sent_at) = date('now')
        """).fetchone()

        return {
            'pending': stats_row['pending'] or 0,
            'sent': stats_row['sent'] or 0,
            'failed': stats_row['failed'] or 0,
            'total': stats_row['total'] or 0,
            'active_rules': rule_count['count'] or 0,
            'sent_today': today_sent['count'] or 0
        }


def cancel_pending_email(queue_id: int) -> bool:
    """Cancel a pending email (removes from queue)."""
    with db_session() as conn:
        conn.execute("""
            DELETE FROM email_queue WHERE id = ? AND status = 'pending'
        """, (queue_id,))
        return True
