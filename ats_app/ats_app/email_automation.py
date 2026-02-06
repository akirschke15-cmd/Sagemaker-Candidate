"""
Email Automation Module - Auto-send emails on stage changes

This module provides:
- Automatic email triggering when candidates change stages
- Configurable rules per job or globally
- Email queue with retry logic
- Template rendering with context variables
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import logging

from config import settings
from database import (
    get_candidate, get_job, get_matching_automation_rules,
    queue_email, get_pending_emails, mark_email_sent, mark_email_failed,
    log_email, get_email_automation_stats, STAGES
)
from email_utils import render_template, build_email_context, send_email, validate_email

logger = logging.getLogger(__name__)


def check_automation_rules(candidate_id: int, job_id: int, from_stage: str, to_stage: str) -> List[Dict]:
    """
    Check if any automation rules match the stage transition.

    Args:
        candidate_id: Candidate ID
        job_id: Job ID
        from_stage: Previous stage
        to_stage: New stage

    Returns:
        List of matching automation rules
    """
    if not job_id:
        return []

    # Find matching rules (job-specific first, then global)
    rules = get_matching_automation_rules(job_id, from_stage, to_stage)
    return rules


def trigger_stage_change_email(candidate_id: int, job_id: int, from_stage: str, to_stage: str) -> Dict:
    """
    Trigger automated email for a stage change.

    This is the main entry point called when a candidate advances stages.
    It finds matching rules and queues emails accordingly.

    Args:
        candidate_id: Candidate ID
        job_id: Job ID
        from_stage: Previous stage
        to_stage: New stage

    Returns:
        Dict with:
            - triggered: bool - whether any emails were queued
            - count: int - number of emails queued
            - rules: list - list of rules that matched
            - errors: list - any errors encountered
    """
    result = {
        'triggered': False,
        'count': 0,
        'rules': [],
        'errors': []
    }

    # Get matching rules
    rules = check_automation_rules(candidate_id, job_id, from_stage, to_stage)

    if not rules:
        return result

    # Get candidate and job info for template rendering
    candidate = get_candidate(candidate_id)
    if not candidate:
        result['errors'].append(f"Candidate {candidate_id} not found")
        return result

    job = get_job(job_id)
    if not job:
        result['errors'].append(f"Job {job_id} not found")
        return result

    # Check if candidate has a valid email
    candidate_email = candidate.get('email')
    if not candidate_email or not validate_email(candidate_email):
        result['errors'].append(f"Candidate has no valid email address")
        return result

    # Build email context
    context = build_email_context(candidate, job)
    context['from_stage'] = from_stage
    context['to_stage'] = to_stage

    # Process each matching rule (typically just use the first one, job-specific takes precedence)
    # For now, we'll only process the first matching rule to avoid duplicate emails
    rule = rules[0]

    try:
        # Render template
        subject = render_template(rule['template_subject'], context)
        body = render_template(rule['template_body'], context)

        # Calculate scheduled time based on delay
        delay_minutes = rule.get('delay_minutes', 0)
        scheduled_at = datetime.now() + timedelta(minutes=delay_minutes)

        # Queue the email
        queue_id = queue_email(
            candidate_id=candidate_id,
            template_id=rule['template_id'],
            to_email=candidate_email,
            subject=subject,
            body=body,
            scheduled_at=scheduled_at.isoformat()
        )

        result['triggered'] = True
        result['count'] = 1
        result['rules'].append({
            'rule_id': rule['id'],
            'template_name': rule['template_name'],
            'queue_id': queue_id,
            'scheduled_at': scheduled_at.isoformat()
        })

    except KeyError as e:
        logger.exception(f"Missing required field in rule {rule['id']} for candidate {candidate_id}: {e}")
        result['errors'].append(f"Error processing rule {rule['id']}: Missing field {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error processing rule {rule['id']} for candidate {candidate_id}")
        result['errors'].append(f"Error processing rule {rule['id']}: {str(e)}")

    return result


def process_email_queue() -> Dict:
    """
    Process pending emails in the queue.

    This function should be called periodically (e.g., every minute)
    to send emails that are due.

    Returns:
        Dict with:
            - processed: int - number of emails processed
            - sent: int - number successfully sent
            - failed: int - number that failed
            - errors: list - error details
    """
    result = {
        'processed': 0,
        'sent': 0,
        'failed': 0,
        'errors': []
    }

    # Get pending emails that are due
    pending = get_pending_emails(limit=50)

    if not pending:
        return result

    # Get SMTP config from settings
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD
    smtp_from = settings.SMTP_FROM

    for email in pending:
        result['processed'] += 1

        try:
            # Send the email
            send_result = send_email(
                to_email=email['to_email'],
                subject=email['subject'],
                body=email['body'],
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_email=smtp_from
            )

            if send_result.get('success'):
                mark_email_sent(email['id'])
                result['sent'] += 1

                # Also log to email_log table
                log_email(
                    candidate_id=email['candidate_id'],
                    recipient=email['to_email'],
                    subject=email['subject'],
                    body=email['body'],
                    status='sent'
                )
            else:
                error_msg = send_result.get('message', 'Unknown error')
                mark_email_failed(email['id'], error_msg)
                result['failed'] += 1
                result['errors'].append({
                    'queue_id': email['id'],
                    'candidate': email.get('candidate_name', 'Unknown'),
                    'error': error_msg
                })

        except KeyError as e:
            logger.error(f"Missing required field in email queue item {email['id']}: {e}")
            error_msg = f"Missing field: {str(e)}"
            mark_email_failed(email['id'], error_msg)
            result['failed'] += 1
            result['errors'].append({
                'queue_id': email['id'],
                'candidate': email.get('candidate_name', 'Unknown'),
                'error': error_msg
            })
        except Exception as e:
            logger.exception(f"Unexpected error processing email queue item {email['id']}")
            error_msg = str(e)
            mark_email_failed(email['id'], error_msg)
            result['failed'] += 1
            result['errors'].append({
                'queue_id': email['id'],
                'candidate': email.get('candidate_name', 'Unknown'),
                'error': error_msg
            })

    return result


def get_automation_summary() -> Dict:
    """
    Get summary statistics on email automation.

    Returns:
        Dict with:
            - stats: email queue statistics
            - recent_sent: list of recently sent emails
            - pending: list of pending emails
            - failed: list of failed emails
    """
    from database import get_email_queue

    stats = get_email_automation_stats()

    # Get recent activity
    recent_sent = get_email_queue(status='sent', limit=10)
    pending = get_email_queue(status='pending', limit=10)
    failed = get_email_queue(status='failed', limit=10)

    return {
        'stats': stats,
        'recent_sent': recent_sent,
        'pending': pending,
        'failed': failed
    }


def validate_automation_rule(from_stage: str, to_stage: str, template_id: int) -> Tuple[bool, str]:
    """
    Validate an automation rule before creation.

    Args:
        from_stage: Source stage
        to_stage: Target stage
        template_id: Email template ID

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check stages are valid
    if from_stage not in STAGES:
        return False, f"Invalid from_stage: {from_stage}"

    if to_stage not in STAGES:
        return False, f"Invalid to_stage: {to_stage}"

    # Check stages are in correct order (can't go backward)
    from_idx = STAGES.index(from_stage)
    to_idx = STAGES.index(to_stage)

    if to_idx <= from_idx:
        return False, "to_stage must be after from_stage in the pipeline"

    # Check template exists
    from database import get_email_template
    template = get_email_template(template_id)
    if not template:
        return False, f"Email template {template_id} not found"

    return True, ""


def get_stage_transitions() -> List[Dict]:
    """
    Get all valid stage transitions for automation rules.

    Returns:
        List of dicts with from_stage and to_stage
    """
    transitions = []

    for i, from_stage in enumerate(STAGES[:-1]):  # Exclude last stages
        if from_stage == 'Rejected':
            continue

        for to_stage in STAGES[i + 1:]:
            transitions.append({
                'from_stage': from_stage,
                'to_stage': to_stage,
                'label': f"{from_stage} -> {to_stage}"
            })

    return transitions
