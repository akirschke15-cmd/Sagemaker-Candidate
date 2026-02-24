"""
ATS Notifications Module - Slack and Teams webhook integrations
"""
import json
import logging
import socket
from datetime import datetime
from ipaddress import ip_address, ip_network
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import urllib.request
import urllib.error

from config import settings

logger = logging.getLogger(__name__)

PRIVATE_NETWORKS = [
    ip_network('10.0.0.0/8'),
    ip_network('172.16.0.0/12'),
    ip_network('192.168.0.0/16'),
    ip_network('127.0.0.0/8'),
    ip_network('169.254.0.0/16'),
]

def validate_webhook_url(url: str) -> tuple[bool, str]:
    """Validate webhook URL is safe (not internal/private). Returns (is_valid, error_msg)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != 'https':
            return False, f"Only HTTPS webhooks are allowed. Got: {parsed.scheme}"
        if not parsed.hostname:
            return False, "No hostname in URL"
        # Resolve hostname and check for private IPs
        resolved_ip = socket.gethostbyname(parsed.hostname)
        addr = ip_address(resolved_ip)
        for network in PRIVATE_NETWORKS:
            if addr in network:
                return False, f"Private/internal IP not allowed: {resolved_ip}"
        return True, ""
    except (socket.gaierror, ValueError) as e:
        return False, f"URL validation failed: {e}"


def send_slack_notification(webhook_url: str, message: Dict[str, Any]) -> tuple[bool, str]:
    """
    Send a notification to Slack via webhook.

    Args:
        webhook_url: Slack incoming webhook URL
        message: Slack message payload (can include blocks for rich formatting)

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    if not webhook_url:
        return False, "Webhook URL is required"

    # Validate webhook URL
    is_valid, error_msg = validate_webhook_url(webhook_url)
    if not is_valid:
        logger.warning(f"Invalid Slack webhook URL: {error_msg}")
        return False, error_msg

    try:
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as response:
            if response.status == 200:
                return True, None
            else:
                error_msg = f"HTTP {response.status}: {response.read().decode('utf-8')}"
                logger.error(f"Slack notification failed: {error_msg}")
                return False, error_msg

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(f"Slack notification HTTP error: {error_msg}")
        return False, error_msg
    except urllib.error.URLError as e:
        error_msg = f"URL Error: {str(e.reason)}"
        logger.error(f"Slack notification URL error: {error_msg}")
        return False, error_msg
    except socket.timeout:
        error_msg = "Request timed out after 10 seconds"
        logger.error(f"Slack notification timeout: {error_msg}")
        return False, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"JSON encoding error: {e}"
        logger.error(f"Slack notification JSON error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.exception(f"Unexpected error in Slack notification: {e}")
        return False, error_msg


def send_teams_notification(webhook_url: str, message: Dict[str, Any]) -> tuple[bool, str]:
    """
    Send a notification to Microsoft Teams via webhook.

    Args:
        webhook_url: Teams incoming webhook URL
        message: Teams adaptive card payload

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    if not webhook_url:
        return False, "Webhook URL is required"

    # Validate webhook URL
    is_valid, error_msg = validate_webhook_url(webhook_url)
    if not is_valid:
        logger.warning(f"Invalid Teams webhook URL: {error_msg}")
        return False, error_msg

    try:
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as response:
            # Teams returns 200 with "1" in body on success
            if response.status == 200:
                return True, None
            else:
                error_msg = f"HTTP {response.status}: {response.read().decode('utf-8')}"
                logger.error(f"Teams notification failed: {error_msg}")
                return False, error_msg

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(f"Teams notification HTTP error: {error_msg}")
        return False, error_msg
    except urllib.error.URLError as e:
        error_msg = f"URL Error: {str(e.reason)}"
        logger.error(f"Teams notification URL error: {error_msg}")
        return False, error_msg
    except socket.timeout:
        error_msg = "Request timed out after 10 seconds"
        logger.error(f"Teams notification timeout: {error_msg}")
        return False, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"JSON encoding error: {e}"
        logger.error(f"Teams notification JSON error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.exception(f"Unexpected error in Teams notification: {e}")
        return False, error_msg


def format_slack_candidate_notification(candidate: Dict, event_type: str, job_title: str = None) -> Dict[str, Any]:
    """
    Format a candidate event notification for Slack.

    Args:
        candidate: Candidate data dict
        event_type: Type of event (new_candidate, stage_change)
        job_title: Optional job title

    Returns:
        Slack message payload with blocks
    """
    candidate_name = candidate.get('name', 'Unknown')
    candidate_email = candidate.get('email', 'N/A')
    job = job_title or candidate.get('job_title', 'Unassigned')
    stage = candidate.get('current_stage', 'Resume Screen')

    if event_type == 'new_candidate':
        header_text = f"New Candidate: {candidate_name}"
        color = "#304CB2"  # Southwest Blue
        emoji = ":new:"
    elif event_type == 'stage_change':
        header_text = f"Stage Update: {candidate_name}"
        color = "#F9B612"  # Southwest Yellow
        emoji = ":arrow_forward:"
    else:
        header_text = f"Candidate Update: {candidate_name}"
        color = "#304CB2"
        emoji = ":bell:"

    message = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {header_text}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Name:*\n{candidate_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Email:*\n{candidate_email}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Role:*\n{job}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Stage:*\n{stage}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Add AI score if available
    ai_score = candidate.get('ai_resume_score')
    if ai_score is not None:
        message["attachments"][0]["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Resume Score:* {ai_score:.0f}%"
            }
        })

    # Add vendor info if available
    vendor = candidate.get('vendor_name')
    if vendor:
        message["attachments"][0]["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Source: {vendor}"
                }
            ]
        })

    return message


def format_teams_candidate_notification(candidate: Dict, event_type: str, job_title: str = None) -> Dict[str, Any]:
    """
    Format a candidate event notification for Microsoft Teams (Adaptive Card).

    Args:
        candidate: Candidate data dict
        event_type: Type of event (new_candidate, stage_change)
        job_title: Optional job title

    Returns:
        Teams adaptive card payload
    """
    candidate_name = candidate.get('name', 'Unknown')
    candidate_email = candidate.get('email', 'N/A')
    job = job_title or candidate.get('job_title', 'Unassigned')
    stage = candidate.get('current_stage', 'Resume Screen')

    if event_type == 'new_candidate':
        header_text = f"New Candidate: {candidate_name}"
        accent_color = "accent"
    elif event_type == 'stage_change':
        header_text = f"Stage Update: {candidate_name}"
        accent_color = "warning"
    else:
        header_text = f"Candidate Update: {candidate_name}"
        accent_color = "default"

    facts = [
        {"title": "Name", "value": candidate_name},
        {"title": "Email", "value": candidate_email},
        {"title": "Role", "value": job},
        {"title": "Stage", "value": stage}
    ]

    # Add AI score if available
    ai_score = candidate.get('ai_resume_score')
    if ai_score is not None:
        facts.append({"title": "AI Score", "value": f"{ai_score:.0f}%"})

    # Add vendor info if available
    vendor = candidate.get('vendor_name')
    if vendor:
        facts.append({"title": "Source", "value": vendor})

    message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": header_text,
                            "style": "heading",
                            "color": accent_color
                        },
                        {
                            "type": "FactSet",
                            "facts": facts
                        }
                    ]
                }
            }
        ]
    }

    return message


def format_slack_interview_notification(interview: Dict, candidate: Dict) -> Dict[str, Any]:
    """
    Format an interview scheduled notification for Slack.

    Args:
        interview: Interview data dict
        candidate: Candidate data dict

    Returns:
        Slack message payload with blocks
    """
    candidate_name = candidate.get('name', 'Unknown')
    job_title = candidate.get('job_title', 'Unassigned')
    stage = interview.get('stage', 'Interview')
    scheduled_time = interview.get('scheduled_time', 'TBD')
    interviewer = interview.get('interviewer_name', 'TBD')
    location = interview.get('location', '')
    _raw_link = interview.get('meeting_link', '')
    meeting_link = _raw_link if _raw_link and urlparse(_raw_link).scheme in ('https', 'http') else ''

    message = {
        "attachments": [
            {
                "color": "#2E7D32",  # Green for scheduled
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":calendar: Interview Scheduled: {candidate_name}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Candidate:*\n{candidate_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Role:*\n{job_title}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Stage:*\n{stage}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Time:*\n{scheduled_time}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Interviewer:*\n{interviewer}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Add location/meeting link if available
    location_text = []
    if location:
        location_text.append(f"Location: {location}")
    if meeting_link:
        location_text.append(f"Meeting Link: {meeting_link}")

    if location_text:
        message["attachments"][0]["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": " | ".join(location_text)
                }
            ]
        })

    return message


def format_teams_interview_notification(interview: Dict, candidate: Dict) -> Dict[str, Any]:
    """
    Format an interview scheduled notification for Microsoft Teams (Adaptive Card).

    Args:
        interview: Interview data dict
        candidate: Candidate data dict

    Returns:
        Teams adaptive card payload
    """
    candidate_name = candidate.get('name', 'Unknown')
    job_title = candidate.get('job_title', 'Unassigned')
    stage = interview.get('stage', 'Interview')
    scheduled_time = interview.get('scheduled_time', 'TBD')
    interviewer = interview.get('interviewer_name', 'TBD')
    location = interview.get('location', '')
    _raw_link = interview.get('meeting_link', '')
    meeting_link = _raw_link if _raw_link and urlparse(_raw_link).scheme in ('https', 'http') else ''

    facts = [
        {"title": "Candidate", "value": candidate_name},
        {"title": "Role", "value": job_title},
        {"title": "Stage", "value": stage},
        {"title": "Time", "value": scheduled_time},
        {"title": "Interviewer", "value": interviewer}
    ]

    if location:
        facts.append({"title": "Location", "value": location})

    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": f"Interview Scheduled: {candidate_name}",
            "style": "heading",
            "color": "good"
        },
        {
            "type": "FactSet",
            "facts": facts
        }
    ]

    # Add meeting link as action button if available
    actions = []
    if meeting_link:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "Join Meeting",
            "url": meeting_link
        })

    message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                    "actions": actions if actions else None
                }
            }
        ]
    }

    return message


def format_test_notification(platform: str, channel_name: str = None) -> Dict[str, Any]:
    """
    Format a test notification message.

    Args:
        platform: 'slack' or 'teams'
        channel_name: Optional channel name for context

    Returns:
        Platform-specific test message payload
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if platform == 'slack':
        return {
            "attachments": [
                {
                    "color": "#304CB2",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": ":white_check_mark: ATS Notification Test",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"This is a test notification from the Agentic Program ATS.\n\n*Timestamp:* {timestamp}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Channel: {channel_name or 'Default'}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    else:  # teams
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": "ATS Notification Test",
                                "style": "heading",
                                "color": "good"
                            },
                            {
                                "type": "TextBlock",
                                "text": "This is a test notification from the Agentic Program ATS.",
                                "wrap": True
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Timestamp", "value": timestamp},
                                    {"title": "Channel", "value": channel_name or "Default"}
                                ]
                            }
                        ]
                    }
                }
            ]
        }


class NotificationService:
    """
    Service class for managing and sending notifications.
    Provides methods for triggering notifications and managing webhooks.
    """

    def __init__(self, db_module):
        """
        Initialize the notification service.

        Args:
            db_module: Reference to the database module for webhook/logging operations
        """
        self.db = db_module

    def get_webhooks_for_job(self, job_id: int, event_type: str = None) -> List[Dict]:
        """
        Get all active webhooks configured for a specific job.

        Args:
            job_id: Job ID to get webhooks for
            event_type: Optional filter for event type

        Returns:
            List of webhook configurations
        """
        return self.db.get_webhooks_for_job(job_id, event_type)

    def trigger_notification(self, event_type: str, payload: Dict[str, Any]) -> List[Dict]:
        """
        Trigger notifications for a specific event.

        Args:
            event_type: Type of event (new_candidate, stage_change, interview_scheduled)
            payload: Event payload containing relevant data

        Returns:
            List of notification results
        """
        results = []
        job_id = payload.get('job_id')

        if not job_id:
            logger.warning(f"No job_id in payload for event {event_type}")
            return results

        webhooks = self.get_webhooks_for_job(job_id, event_type)

        for webhook in webhooks:
            webhook_id = webhook['id']
            platform = webhook['platform']
            webhook_url = webhook['webhook_url']

            try:
                # Format message based on event type and platform
                message = self._format_message(event_type, payload, platform)

                # Send notification
                if platform == 'slack':
                    success, error = send_slack_notification(webhook_url, message)
                elif platform == 'teams':
                    success, error = send_teams_notification(webhook_url, message)
                else:
                    success, error = False, f"Unknown platform: {platform}"

                # Log the notification
                self.db.log_notification_event(
                    webhook_id=webhook_id,
                    event_type=event_type,
                    payload=json.dumps(payload),
                    status='success' if success else 'failed',
                    error_message=error
                )

                # Update webhook status
                self.db.update_webhook_status(webhook_id, success, error)

                results.append({
                    'webhook_id': webhook_id,
                    'platform': platform,
                    'success': success,
                    'error': error
                })

            except Exception as e:
                logger.exception(f"Error sending notification via webhook {webhook_id}")
                self.db.log_notification_event(
                    webhook_id=webhook_id,
                    event_type=event_type,
                    payload=json.dumps(payload),
                    status='failed',
                    error_message=str(e)
                )
                results.append({
                    'webhook_id': webhook_id,
                    'platform': platform,
                    'success': False,
                    'error': str(e)
                })

        return results

    def _format_message(self, event_type: str, payload: Dict, platform: str) -> Dict[str, Any]:
        """
        Format a notification message based on event type and platform.

        Args:
            event_type: Type of event
            payload: Event payload
            platform: Target platform (slack/teams)

        Returns:
            Formatted message payload
        """
        if event_type in ('new_candidate', 'stage_change'):
            candidate = payload.get('candidate', {})
            job_title = payload.get('job_title')

            if platform == 'slack':
                return format_slack_candidate_notification(candidate, event_type, job_title)
            else:
                return format_teams_candidate_notification(candidate, event_type, job_title)

        elif event_type == 'interview_scheduled':
            interview = payload.get('interview', {})
            candidate = payload.get('candidate', {})

            if platform == 'slack':
                return format_slack_interview_notification(interview, candidate)
            else:
                return format_teams_interview_notification(interview, candidate)

        else:
            # Generic notification
            return format_test_notification(platform)

    def send_test_notification(self, webhook_id: int) -> tuple[bool, str]:
        """
        Send a test notification to verify webhook configuration.

        Args:
            webhook_id: ID of the webhook to test

        Returns:
            Tuple of (success, error_message)
        """
        webhook = self.db.get_webhook(webhook_id)
        if not webhook:
            return False, "Webhook not found"

        platform = webhook['platform']
        webhook_url = webhook['webhook_url']
        channel_name = webhook.get('channel_name', 'Default')

        message = format_test_notification(platform, channel_name)

        if platform == 'slack':
            success, error = send_slack_notification(webhook_url, message)
        elif platform == 'teams':
            success, error = send_teams_notification(webhook_url, message)
        else:
            success, error = False, f"Unknown platform: {platform}"

        # Log the test
        self.db.log_notification_event(
            webhook_id=webhook_id,
            event_type='test',
            payload=json.dumps({'test': True}),
            status='success' if success else 'failed',
            error_message=error
        )

        # Update webhook status
        self.db.update_webhook_status(webhook_id, success, error)

        return success, error


# Singleton instance (will be initialized with db module in app.py)
notification_service: Optional[NotificationService] = None


def init_notification_service(db_module) -> NotificationService:
    """
    Initialize the notification service singleton.

    Args:
        db_module: Reference to the database module

    Returns:
        NotificationService instance
    """
    global notification_service
    notification_service = NotificationService(db_module)
    return notification_service


def get_notification_service() -> Optional[NotificationService]:
    """
    Get the notification service singleton.

    Returns:
        NotificationService instance or None if not initialized
    """
    return notification_service
