"""
ATS Notification Webhook Operations
Manages Slack/Teams webhooks and notification events
"""
from typing import List, Dict, Optional
from datetime import datetime
from .connection import db_session


def create_webhook(platform: str, webhook_url: str, channel_name: str = None,
                   job_id: int = None, event_types: List[str] = None) -> int:
    """
    Create a new notification webhook.

    Args:
        platform: 'slack' or 'teams'
        webhook_url: The webhook URL
        channel_name: Optional channel name for reference
        job_id: Optional job ID to associate with (None for all jobs)
        event_types: List of event types to enable (default: all)

    Returns:
        The new webhook ID
    """
    if event_types is None:
        event_types = ['new_candidate', 'stage_change', 'interview_scheduled']

    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO notification_webhooks (platform, webhook_url, channel_name, job_id)
            VALUES (?, ?, ?, ?)
        """, (platform, webhook_url, channel_name, job_id))
        webhook_id = cursor.lastrowid

        # Create notification settings for each event type
        for event_type in event_types:
            conn.execute("""
                INSERT INTO notification_settings (webhook_id, event_type, is_enabled)
                VALUES (?, ?, 1)
            """, (webhook_id, event_type))

        return webhook_id


def get_webhooks(job_id: int = None, is_active: bool = None) -> List[Dict]:
    """
    Get notification webhooks with optional filtering.

    Args:
        job_id: Filter by job ID (None for all)
        is_active: Filter by active status

    Returns:
        List of webhook configurations
    """
    with db_session() as conn:
        query = """
            SELECT w.*, j.title as job_title
            FROM notification_webhooks w
            LEFT JOIN jobs j ON w.job_id = j.id
            WHERE 1=1
        """
        params = []

        if job_id is not None:
            query += " AND (w.job_id = ? OR w.job_id IS NULL)"
            params.append(job_id)

        if is_active is not None:
            query += " AND w.is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY w.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_webhook(webhook_id: int) -> Optional[Dict]:
    """Get a single webhook by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT w.*, j.title as job_title
            FROM notification_webhooks w
            LEFT JOIN jobs j ON w.job_id = j.id
            WHERE w.id = ?
        """, (webhook_id,)).fetchone()
        return dict(row) if row else None


def update_webhook(webhook_id: int, **kwargs) -> bool:
    """
    Update a webhook configuration.

    Args:
        webhook_id: Webhook ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    ALLOWED_COLUMNS = {'platform', 'webhook_url', 'channel_name', 'job_id', 'is_active', 'last_success', 'last_failure', 'failure_count', 'updated_at'}
    kwargs['updated_at'] = datetime.now().isoformat()
    filtered = {k: v for k, v in kwargs.items() if k in ALLOWED_COLUMNS}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in filtered.keys())
        conn.execute(f"UPDATE notification_webhooks SET {set_clause} WHERE id = ?",
                    (*filtered.values(), webhook_id))
        return True


def delete_webhook(webhook_id: int) -> bool:
    """Delete a webhook and its settings."""
    with db_session() as conn:
        conn.execute("DELETE FROM notification_webhooks WHERE id = ?", (webhook_id,))
        return True


def get_notification_settings(webhook_id: int) -> List[Dict]:
    """Get notification settings for a webhook."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT * FROM notification_settings WHERE webhook_id = ?
        """, (webhook_id,)).fetchall()
        return [dict(r) for r in rows]


def update_notification_setting(webhook_id: int, event_type: str, is_enabled: bool) -> bool:
    """Update a specific notification setting."""
    with db_session() as conn:
        conn.execute("""
            INSERT INTO notification_settings (webhook_id, event_type, is_enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(webhook_id, event_type) DO UPDATE SET is_enabled = ?
        """, (webhook_id, event_type, 1 if is_enabled else 0, 1 if is_enabled else 0))
        return True


def get_webhooks_for_job(job_id: int, event_type: str = None) -> List[Dict]:
    """
    Get active webhooks configured for a specific job and event type.

    Args:
        job_id: Job ID
        event_type: Optional event type filter

    Returns:
        List of active webhooks with their settings
    """
    with db_session() as conn:
        query = """
            SELECT DISTINCT w.*
            FROM notification_webhooks w
            JOIN notification_settings ns ON w.id = ns.webhook_id
            WHERE w.is_active = 1
            AND (w.job_id = ? OR w.job_id IS NULL)
            AND ns.is_enabled = 1
        """
        params = [job_id]

        if event_type:
            query += " AND ns.event_type = ?"
            params.append(event_type)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def log_notification_event(webhook_id: int, event_type: str, payload: str,
                           status: str, error_message: str = None) -> int:
    """
    Log a notification event.

    Args:
        webhook_id: Webhook ID
        event_type: Type of event
        payload: JSON payload that was sent
        status: 'success' or 'failed'
        error_message: Error message if failed

    Returns:
        Log entry ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO notification_log (webhook_id, event_type, payload, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (webhook_id, event_type, payload, status, error_message))
        return cursor.lastrowid


def update_webhook_status(webhook_id: int, success: bool, error_message: str = None):
    """
    Update webhook status after a notification attempt.

    Args:
        webhook_id: Webhook ID
        success: Whether the notification was successful
        error_message: Error message if failed
    """
    with db_session() as conn:
        if success:
            conn.execute("""
                UPDATE notification_webhooks
                SET last_success = CURRENT_TIMESTAMP, failure_count = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (webhook_id,))
        else:
            conn.execute("""
                UPDATE notification_webhooks
                SET last_failure = CURRENT_TIMESTAMP, failure_count = failure_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (webhook_id,))


def get_notification_log(webhook_id: int = None, limit: int = 50) -> List[Dict]:
    """
    Get notification log entries.

    Args:
        webhook_id: Optional filter by webhook ID
        limit: Maximum number of entries to return

    Returns:
        List of log entries
    """
    with db_session() as conn:
        query = """
            SELECT nl.*, w.platform, w.channel_name
            FROM notification_log nl
            JOIN notification_webhooks w ON nl.webhook_id = w.id
            WHERE 1=1
        """
        params = []

        if webhook_id:
            query += " AND nl.webhook_id = ?"
            params.append(webhook_id)

        query += " ORDER BY nl.sent_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
