"""
Email Utilities - Template rendering and sending
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime
import re
import logging

from config import settings

logger = logging.getLogger(__name__)

def render_template(template: str, context: Dict) -> str:
    """
    Render an email template with context variables.
    Variables are in {variable_name} format.
    """
    result = template
    for key, value in context.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value) if value else "")
    return result

def build_email_context(candidate: Dict, job: Dict = None, interview: Dict = None) -> Dict:
    """Build context dict for email templates"""
    context = {
        'candidate_name': candidate.get('name', ''),
        'candidate_email': candidate.get('email', ''),
        'candidate_phone': candidate.get('phone', ''),
        'current_stage': candidate.get('current_stage', ''),
    }
    
    if job:
        context.update({
            'job_title': job.get('title', ''),
            'job_description': job.get('description', ''),
            'department': job.get('department', ''),
        })
    elif candidate.get('job_title'):
        context['job_title'] = candidate.get('job_title', '')
    
    if interview:
        scheduled = interview.get('scheduled_time')
        if scheduled:
            try:
                dt = datetime.fromisoformat(scheduled)
                context['interview_date'] = dt.strftime('%B %d, %Y')
                context['interview_time'] = dt.strftime('%I:%M %p')
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse scheduled_time '{scheduled}': {e}")
                context['interview_date'] = scheduled
                context['interview_time'] = ''
        
        context.update({
            'interviewer_name': interview.get('interviewer_name', ''),
            'interviewer_email': interview.get('interviewer_email', ''),
            'meeting_link': interview.get('meeting_link', ''),
            'location': interview.get('location', ''),
        })
    
    return context

def send_email(
    to_email: str,
    subject: str,
    body: str,
    smtp_host: str = None,
    smtp_port: int = 587,
    smtp_user: str = None,
    smtp_password: str = None,
    from_email: str = None
) -> Dict:
    """
    Send an email via SMTP.
    Returns {'success': bool, 'message': str}
    
    If SMTP credentials not provided, returns a preview instead of sending.
    """
    if not smtp_host or not smtp_user:
        # Return preview for testing
        return {
            'success': True,
            'message': 'Preview mode (SMTP not configured)',
            'preview': {
                'to': to_email,
                'subject': subject,
                'body': body
            }
        }
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email or smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_host, smtp_port, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        return {'success': True, 'message': 'Email sent successfully'}
    
    except (smtplib.SMTPException, ConnectionError, OSError) as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {'success': False, 'message': f'Failed to send email: {str(e)}'}

def generate_calendar_invite(
    candidate_name: str,
    interview_stage: str,
    scheduled_time: datetime,
    duration_minutes: int = 60,
    interviewer_name: str = None,
    meeting_link: str = None,
    location: str = None
) -> str:
    """
    Generate an ICS calendar invite string.
    """
    import uuid
    from datetime import timedelta
    
    end_time = scheduled_time + timedelta(minutes=duration_minutes)
    
    # Format dates for ICS
    start_str = scheduled_time.strftime('%Y%m%dT%H%M%S')
    end_str = end_time.strftime('%Y%m%dT%H%M%S')
    now_str = datetime.now().strftime('%Y%m%dT%H%M%S')
    
    description = f"{interview_stage} Interview with {candidate_name}"
    if interviewer_name:
        description += f"\\nInterviewer: {interviewer_name}"
    if meeting_link:
        description += f"\\nMeeting Link: {meeting_link}"
    
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ATS System//Interview Scheduler//EN
BEGIN:VEVENT
UID:{uuid.uuid4()}
DTSTAMP:{now_str}
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:{interview_stage} - {candidate_name}
DESCRIPTION:{description}
LOCATION:{location or meeting_link or 'TBD'}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return ics

def validate_email(email: str) -> bool:
    """Basic email validation"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def format_email_list(candidates: list) -> str:
    """Format candidate emails for bulk operations"""
    emails = [c.get('email') for c in candidates if c.get('email') and validate_email(c['email'])]
    return '; '.join(emails)
