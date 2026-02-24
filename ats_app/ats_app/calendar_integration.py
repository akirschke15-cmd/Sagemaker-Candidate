"""
Calendar Integration Module - ICS File Generation and Calendar Event Management
Phase 1: ICS file generation for interview events
Future Phases: Google Calendar OAuth, Microsoft 365 OAuth integration
"""
import uuid
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _validate_meeting_link(url: str) -> str:
    """Validate meeting link URL scheme. Returns sanitized URL or empty string."""
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme in ('https', 'http') and parsed.hostname:
        return url
    logger.warning(f"Invalid meeting link scheme rejected: {parsed.scheme}")
    return ""

# ICS file constants following RFC 5545 standard
ICS_VERSION = "2.0"
ICS_PRODID = "-//Agentic Program ATS//Interview Scheduling//EN"
ICS_CALSCALE = "GREGORIAN"
ICS_METHOD = "REQUEST"

# Salt used for PBKDF2 key derivation (fixed so the same secret always produces
# the same Fernet key; this is intentional — the secrecy comes from
# SESSION_SECRET_KEY, not from a random salt).
_KDF_SALT = b"ats_calendar_token_v1"
_KDF_ITERATIONS = 100_000


def _get_fernet():
    """
    Build and return a Fernet instance whose key is derived from
    SESSION_SECRET_KEY via PBKDF2-HMAC-SHA256.

    Fernet requires a 32-byte key that is base64url-encoded (44 chars).
    We derive that 32-byte material from the application secret so no
    additional key-management config is needed.
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from config import settings

    secret = settings.SESSION_SECRET_KEY or "default-insecure-key-set-SESSION_SECRET_KEY"
    secret_bytes = secret.encode("utf-8")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITERATIONS,
        backend=default_backend(),
    )
    key_material = kdf.derive(secret_bytes)
    # Fernet expects a base64url-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


def _encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token string using Fernet symmetric encryption.

    Args:
        plaintext: The raw token string to encrypt.

    Returns:
        A base64-encoded ciphertext string suitable for database storage.
    """
    if not plaintext:
        return plaintext
    fernet = _get_fernet()
    ciphertext_bytes = fernet.encrypt(plaintext.encode("utf-8"))
    # Store as a regular string — Fernet output is already URL-safe base64
    return ciphertext_bytes.decode("utf-8")


def _decrypt_token(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted token string read from the database.

    Handles the migration case where a token was stored in plaintext before
    encryption was introduced: if decryption fails (InvalidToken / ValueError)
    the raw value is returned as-is so the caller can continue using it and
    re-encrypt it on the next write.

    Args:
        ciphertext: The stored token string (may be encrypted or plaintext).

    Returns:
        The decrypted plaintext token, or the original value if it was not
        encrypted.
    """
    if not ciphertext:
        return ciphertext
    try:
        from cryptography.fernet import Fernet, InvalidToken
        fernet = _get_fernet()
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        # Token is likely stored as plaintext (pre-encryption migration).
        # Return as-is; the next save will encrypt it.
        logger.debug(
            "Token decryption failed — treating as plaintext (legacy record)."
        )
        return ciphertext


def escape_ics_text(text: str) -> str:
    """
    Escape special characters for ICS format per RFC 5545.
    Escapes backslash, semicolon, comma, and converts newlines.
    """
    if not text:
        return ""
    # Order matters: escape backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    # Convert newlines to escaped newlines for ICS
    text = text.replace("\r\n", "\\n")
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\n")
    return text


def fold_ics_line(line: str, max_length: int = 75) -> str:
    """
    Fold long lines per RFC 5545 (max 75 octets per line).
    Continuation lines start with a space or tab.
    """
    if len(line.encode('utf-8')) <= max_length:
        return line

    result = []
    current_line = ""

    for char in line:
        # Check if adding this char would exceed limit
        test_line = current_line + char
        if len(test_line.encode('utf-8')) > max_length:
            result.append(current_line)
            current_line = " " + char  # Continuation line starts with space
        else:
            current_line = test_line

    if current_line:
        result.append(current_line)

    return "\r\n".join(result)


def format_ics_datetime(dt: datetime) -> str:
    """
    Format datetime for ICS file in UTC format.
    Returns format: YYYYMMDDTHHMMSSZ
    """
    # Convert to UTC format for ICS
    return dt.strftime("%Y%m%dT%H%M%S")


def format_ics_date(dt: datetime) -> str:
    """
    Format date for ICS file.
    Returns format: YYYYMMDD
    """
    return dt.strftime("%Y%m%d")


def generate_uid() -> str:
    """
    Generate a unique identifier for the calendar event.
    Format: UUID@ats.agentic.program
    """
    return f"{uuid.uuid4()}@ats.agentic.program"


def format_event_description(
    candidate: Dict,
    job: Dict,
    stage: str,
    prep_notes: Optional[str] = None,
    previous_notes: Optional[str] = None
) -> str:
    """
    Format a detailed description for the interview calendar event.
    Includes candidate info, job details, interview prep, and previous notes.

    Args:
        candidate: Candidate data dictionary
        job: Job data dictionary
        stage: Interview stage (e.g., "Technical Interview")
        prep_notes: AI-generated interview prep notes
        previous_notes: Notes from previous interview stages

    Returns:
        Formatted description string for ICS
    """
    parts = []

    # Confidentiality warning
    parts.append("****** DO NOT FORWARD TO CANDIDATE ******")
    parts.append("")

    # Header
    parts.append(f"INTERVIEW: {stage}")
    parts.append("=" * 40)
    parts.append("")

    # Candidate Information
    parts.append("CANDIDATE INFORMATION")
    parts.append("-" * 20)
    parts.append(f"Name: {candidate.get('name', 'N/A')}")
    if candidate.get('email'):
        parts.append(f"Email: {candidate.get('email')}")
    if candidate.get('phone'):
        parts.append(f"Phone: {candidate.get('phone')}")
    if candidate.get('vendor_name'):
        parts.append(f"Vendor: {candidate.get('vendor_name')}")
    parts.append("")

    # Job Information
    parts.append("POSITION")
    parts.append("-" * 20)
    parts.append(f"Title: {job.get('title', 'N/A')}")
    if job.get('department'):
        parts.append(f"Department: {job.get('department')}")
    parts.append("")

    # AI Resume Score if available
    if candidate.get('ai_resume_score'):
        parts.append("RESUME ASSESSMENT")
        parts.append("-" * 20)
        parts.append(f"AI Score: {candidate.get('ai_resume_score', 0):.0f}%")
        if candidate.get('ai_resume_analysis'):
            parts.append(f"Analysis: {candidate['ai_resume_analysis']}")
        parts.append("")

    # Interview Prep Notes (full content, no truncation)
    if prep_notes:
        parts.append("INTERVIEW PREP NOTES")
        parts.append("-" * 20)
        parts.append(prep_notes)
        parts.append("")

    # Previous Interview Notes Summary
    if previous_notes:
        parts.append("PREVIOUS INTERVIEW NOTES")
        parts.append("-" * 20)
        parts.append(previous_notes)
        parts.append("")

    # Footer
    parts.append("=" * 40)
    parts.append("Generated by Agentic Program ATS")
    parts.append("")
    parts.append("****** DO NOT FORWARD TO CANDIDATE ******")

    return "\n".join(parts)


def format_event_description_html(
    candidate: Dict,
    job: Dict,
    stage: str,
    prep_notes: Optional[str] = None,
    previous_notes: Optional[str] = None
) -> str:
    """
    Format an HTML description for calendar clients that support X-ALT-DESC.
    Renders the DO NOT FORWARD warning in large red text.
    """
    import html as html_mod

    warning = ('<p style="color:#FF0000;font-size:24px;font-weight:bold;text-align:center;'
               'border:3px solid #FF0000;padding:12px;margin:12px 0;">'
               '&#9888; DO NOT FORWARD TO CANDIDATE &#9888;</p>')

    sections = [warning]

    sections.append(f'<h2>INTERVIEW: {html_mod.escape(stage)}</h2>')

    # Candidate info
    sections.append('<h3>Candidate Information</h3><ul>')
    sections.append(f'<li><b>Name:</b> {html_mod.escape(candidate.get("name", "N/A"))}</li>')
    if candidate.get('email'):
        sections.append(f'<li><b>Email:</b> {html_mod.escape(candidate["email"])}</li>')
    if candidate.get('phone'):
        sections.append(f'<li><b>Phone:</b> {html_mod.escape(candidate["phone"])}</li>')
    if candidate.get('vendor_name'):
        sections.append(f'<li><b>Vendor:</b> {html_mod.escape(candidate["vendor_name"])}</li>')
    sections.append('</ul>')

    # Job info
    sections.append('<h3>Position</h3><ul>')
    sections.append(f'<li><b>Title:</b> {html_mod.escape(job.get("title", "N/A"))}</li>')
    if job.get('department'):
        sections.append(f'<li><b>Department:</b> {html_mod.escape(job["department"])}</li>')
    sections.append('</ul>')

    # AI Resume Score
    if candidate.get('ai_resume_score'):
        sections.append('<h3>Resume Assessment</h3>')
        sections.append(f'<p><b>AI Score:</b> {candidate.get("ai_resume_score", 0):.0f}%</p>')
        if candidate.get('ai_resume_analysis'):
            sections.append(f'<pre style="white-space:pre-wrap;">{html_mod.escape(candidate["ai_resume_analysis"])}</pre>')

    # Interview Prep Notes (full content)
    if prep_notes:
        sections.append('<h3>Interview Prep Notes</h3>')
        sections.append(f'<pre style="white-space:pre-wrap;">{html_mod.escape(prep_notes)}</pre>')

    # Previous Notes
    if previous_notes:
        sections.append('<h3>Previous Interview Notes</h3>')
        sections.append(f'<pre style="white-space:pre-wrap;">{html_mod.escape(previous_notes)}</pre>')

    sections.append('<hr>')
    sections.append('<p style="color:#888;font-size:12px;">Generated by Agentic Program ATS</p>')
    sections.append(warning)

    return ''.join(sections)


def generate_ics_event(
    interview: Dict,
    candidate: Dict,
    job: Dict,
    duration_minutes: int = 60,
    prep_notes: Optional[str] = None,
    previous_notes: Optional[str] = None,
    alarm_minutes: int = 15
) -> Tuple[str, str]:
    """
    Generate a valid ICS file content for an interview event.
    Follows RFC 5545 iCalendar specification for maximum compatibility.

    Args:
        interview: Interview data dictionary containing scheduled_time, stage, etc.
        candidate: Candidate data dictionary
        job: Job data dictionary
        duration_minutes: Duration of the interview in minutes (default: 60)
        prep_notes: Optional AI-generated interview prep notes
        previous_notes: Optional summary of previous interview notes
        alarm_minutes: Minutes before event to trigger reminder (default: 15)

    Returns:
        Tuple of (ics_content: str, uid: str)
    """
    # Parse scheduled time
    scheduled_time_str = interview.get('scheduled_time', '')
    if isinstance(scheduled_time_str, str):
        # Handle various datetime formats
        try:
            if 'T' in scheduled_time_str:
                start_dt = datetime.fromisoformat(scheduled_time_str.replace('Z', ''))
            else:
                start_dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            logger.warning(f"Failed to parse scheduled_time '{scheduled_time_str}': {e}. Using default time.")
            # Fallback: use current time + 1 hour
            start_dt = datetime.now() + timedelta(hours=1)
    else:
        start_dt = scheduled_time_str if scheduled_time_str else datetime.now() + timedelta(hours=1)

    # Calculate end time
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    # Generate unique ID
    uid = generate_uid()

    # Get current timestamp for DTSTAMP
    now = datetime.utcnow()

    # Build event title
    stage = interview.get('stage', 'Interview')
    candidate_name = candidate.get('name', 'Candidate')
    job_title = job.get('title', 'Position')
    summary = f"{stage}: {candidate_name} - {job_title}"

    # Build location
    location_parts = []
    validated_link = _validate_meeting_link(interview.get('meeting_link', ''))
    if validated_link:
        location_parts.append(validated_link)
    if interview.get('location'):
        location_parts.append(interview['location'])
    location = " | ".join(location_parts) if location_parts else "TBD"

    # Build plain text description
    description = format_event_description(
        candidate=candidate,
        job=job,
        stage=stage,
        prep_notes=prep_notes,
        previous_notes=previous_notes
    )

    # Build HTML description for rich calendar clients
    html_description = format_event_description_html(
        candidate=candidate,
        job=job,
        stage=stage,
        prep_notes=prep_notes,
        previous_notes=previous_notes
    )

    # Build ICS content
    ics_lines = [
        "BEGIN:VCALENDAR",
        f"VERSION:{ICS_VERSION}",
        f"PRODID:{ICS_PRODID}",
        f"CALSCALE:{ICS_CALSCALE}",
        f"METHOD:{ICS_METHOD}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{format_ics_datetime(now)}",
        f"DTSTART:{format_ics_datetime(start_dt)}",
        f"DTEND:{format_ics_datetime(end_dt)}",
        fold_ics_line(f"SUMMARY:{escape_ics_text(summary)}"),
        fold_ics_line(f"DESCRIPTION:{escape_ics_text(description)}"),
        fold_ics_line(f"X-ALT-DESC;FMTTYPE=text/html:{escape_ics_text(html_description)}"),
        fold_ics_line(f"LOCATION:{escape_ics_text(location)}"),
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        f"TRANSP:OPAQUE",
    ]

    # Add organizer if interviewer email is available
    if interview.get('interviewer_email'):
        interviewer_name = interview.get('interviewer_name', '')
        if interviewer_name:
            ics_lines.append(fold_ics_line(
                f"ORGANIZER;CN={escape_ics_text(interviewer_name)}:mailto:{interview['interviewer_email']}"
            ))
        else:
            ics_lines.append(f"ORGANIZER:mailto:{interview['interviewer_email']}")

    # Add attendee (candidate) if email available
    if candidate.get('email'):
        ics_lines.append(fold_ics_line(
            f"ATTENDEE;CN={escape_ics_text(candidate.get('name', ''))};"
            f"RSVP=TRUE;ROLE=REQ-PARTICIPANT:mailto:{candidate['email']}"
        ))

    # Add alarm/reminder
    if alarm_minutes > 0:
        ics_lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT{}M".format(alarm_minutes),
            "ACTION:DISPLAY",
            fold_ics_line(f"DESCRIPTION:Reminder: {escape_ics_text(summary)}"),
            "END:VALARM",
        ])

    # Close event and calendar
    ics_lines.extend([
        "END:VEVENT",
        "END:VCALENDAR",
    ])

    # Join with CRLF as per RFC 5545
    ics_content = "\r\n".join(ics_lines) + "\r\n"

    return ics_content, uid


def generate_ics_filename(candidate_name: str, stage: str, scheduled_time: str) -> str:
    """
    Generate a clean filename for the ICS file.

    Args:
        candidate_name: Name of the candidate
        stage: Interview stage
        scheduled_time: Scheduled datetime string

    Returns:
        Clean filename string (e.g., "interview_john_doe_technical_20250130.ics")
    """
    # Clean candidate name
    clean_name = "".join(c if c.isalnum() or c == ' ' else '' for c in candidate_name)
    clean_name = clean_name.strip().replace(' ', '_').lower()

    # Clean stage
    clean_stage = "".join(c if c.isalnum() or c == ' ' else '' for c in stage)
    clean_stage = clean_stage.strip().replace(' ', '_').lower()

    # Extract date
    try:
        if 'T' in scheduled_time:
            dt = datetime.fromisoformat(scheduled_time.replace('Z', ''))
        else:
            dt = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y%m%d")
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse scheduled_time '{scheduled_time}' for filename: {e}. Using current date.")
        date_str = datetime.now().strftime("%Y%m%d")

    return f"interview_{clean_name}_{clean_stage}_{date_str}.ics"


# ============ DATABASE OPERATIONS FOR CALENDAR INTEGRATION ============
# These functions prepare the database for future OAuth integration

def init_calendar_tables():
    """
    Initialize calendar integration tables in the database.
    Called from database.py init_db or migrate_db.
    """
    from database import db_session

    with db_session() as conn:
        conn.executescript("""
        -- Calendar integrations for OAuth providers (future use)
        CREATE TABLE IF NOT EXISTS calendar_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            calendar_id TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Calendar events tracking
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            integration_id INTEGER,
            external_event_id TEXT,
            ics_uid TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
            FOREIGN KEY (integration_id) REFERENCES calendar_integrations(id) ON DELETE SET NULL
        );

        -- Index for quick lookups
        CREATE INDEX IF NOT EXISTS idx_calendar_events_interview ON calendar_events(interview_id);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_ics_uid ON calendar_events(ics_uid);
        """)


def save_calendar_integration(
    provider: str,
    access_token: str,
    refresh_token: str = None,
    token_expires_at: str = None,
    calendar_id: str = None,
) -> int:
    """
    Persist an OAuth integration record to calendar_integrations.

    access_token and refresh_token are encrypted at rest before storage.

    Args:
        provider: OAuth provider name (e.g. "google", "outlook").
        access_token: Raw OAuth access token — will be encrypted.
        refresh_token: Raw OAuth refresh token — will be encrypted if provided.
        token_expires_at: ISO datetime string for token expiry.
        calendar_id: Provider-specific calendar identifier.

    Returns:
        ID of the inserted calendar_integrations row.
    """
    from database import db_session

    encrypted_access = _encrypt_token(access_token)
    encrypted_refresh = _encrypt_token(refresh_token) if refresh_token else None

    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO calendar_integrations
                (provider, calendar_id, access_token, refresh_token, token_expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (provider, calendar_id, encrypted_access, encrypted_refresh, token_expires_at))
        return cursor.lastrowid


def update_calendar_integration_tokens(
    integration_id: int,
    access_token: str,
    refresh_token: str = None,
    token_expires_at: str = None,
):
    """
    Update OAuth tokens for an existing calendar_integrations row.

    Tokens are re-encrypted before storage, providing an automatic migration
    path for any legacy plaintext tokens: callers that read via
    get_calendar_integration (which decrypts) and then call this function will
    cause the tokens to be stored encrypted.

    Args:
        integration_id: Row ID in calendar_integrations.
        access_token: New raw access token — will be encrypted.
        refresh_token: New raw refresh token — will be encrypted if provided.
        token_expires_at: ISO datetime string for updated token expiry.
    """
    from database import db_session

    encrypted_access = _encrypt_token(access_token)
    encrypted_refresh = _encrypt_token(refresh_token) if refresh_token else None

    with db_session() as conn:
        conn.execute("""
            UPDATE calendar_integrations
            SET access_token = ?,
                refresh_token = ?,
                token_expires_at = ?
            WHERE id = ?
        """, (encrypted_access, encrypted_refresh, token_expires_at, integration_id))


def get_calendar_integration(integration_id: int) -> Optional[Dict]:
    """
    Retrieve a calendar integration record, decrypting the stored tokens.

    If a token was stored as plaintext (before encryption was introduced) the
    _decrypt_token helper transparently returns it as-is, so this function
    always yields usable token values regardless of the storage format.

    Args:
        integration_id: Row ID in calendar_integrations.

    Returns:
        Dict with all columns and decrypted access_token / refresh_token,
        or None if the row does not exist.
    """
    from database import db_session

    with db_session() as conn:
        row = conn.execute("""
            SELECT * FROM calendar_integrations WHERE id = ?
        """, (integration_id,)).fetchone()

    if not row:
        return None

    record = dict(row)
    record["access_token"] = _decrypt_token(record.get("access_token") or "")
    record["refresh_token"] = _decrypt_token(record.get("refresh_token") or "") or None
    return record


def get_active_calendar_integrations() -> list:
    """
    Return all active calendar integration records with decrypted tokens.

    Returns:
        List of dicts with decrypted access_token / refresh_token fields.
    """
    from database import db_session

    with db_session() as conn:
        rows = conn.execute("""
            SELECT * FROM calendar_integrations WHERE is_active = 1
        """).fetchall()

    result = []
    for row in rows:
        record = dict(row)
        record["access_token"] = _decrypt_token(record.get("access_token") or "")
        record["refresh_token"] = _decrypt_token(record.get("refresh_token") or "") or None
        result.append(record)
    return result


def save_calendar_event(interview_id: int, ics_uid: str, integration_id: int = None,
                        external_event_id: str = None) -> int:
    """
    Save a calendar event record to the database.

    Args:
        interview_id: ID of the associated interview
        ics_uid: UID from the generated ICS file
        integration_id: Optional ID of the calendar integration (for OAuth)
        external_event_id: Optional external event ID (for Google/Outlook)

    Returns:
        ID of the created calendar event record
    """
    from database import db_session

    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO calendar_events (interview_id, integration_id, external_event_id, ics_uid)
            VALUES (?, ?, ?, ?)
        """, (interview_id, integration_id, external_event_id, ics_uid))
        return cursor.lastrowid


def get_calendar_event(interview_id: int) -> Optional[Dict]:
    """
    Get calendar event record for an interview.

    Args:
        interview_id: ID of the interview

    Returns:
        Calendar event record dict or None
    """
    from database import db_session

    with db_session() as conn:
        row = conn.execute("""
            SELECT * FROM calendar_events WHERE interview_id = ? ORDER BY created_at DESC LIMIT 1
        """, (interview_id,)).fetchone()
        return dict(row) if row else None


def update_calendar_event_status(event_id: int, status: str):
    """
    Update the status of a calendar event.

    Args:
        event_id: ID of the calendar event record
        status: New status (e.g., 'active', 'cancelled', 'updated')
    """
    from database import db_session

    with db_session() as conn:
        conn.execute("""
            UPDATE calendar_events SET status = ? WHERE id = ?
        """, (status, event_id))


# ============ FUTURE OAUTH INTEGRATION STUBS ============
# These are placeholder functions for future Google/Outlook OAuth integration

def get_google_calendar_auth_url() -> str:
    """
    Get Google Calendar OAuth authorization URL.
    Phase 2 implementation.
    """
    raise NotImplementedError("Google Calendar OAuth not yet implemented. Use ICS download for now.")


def get_outlook_calendar_auth_url() -> str:
    """
    Get Microsoft 365 OAuth authorization URL.
    Phase 3 implementation.
    """
    raise NotImplementedError("Microsoft 365 OAuth not yet implemented. Use ICS download for now.")


def create_google_calendar_event(interview: Dict, candidate: Dict, job: Dict) -> str:
    """
    Create an event in Google Calendar via API.
    Phase 2 implementation.

    Returns:
        External event ID from Google Calendar
    """
    raise NotImplementedError("Google Calendar API integration not yet implemented.")


def create_outlook_calendar_event(interview: Dict, candidate: Dict, job: Dict) -> str:
    """
    Create an event in Microsoft 365 Outlook Calendar via API.
    Phase 3 implementation.

    Returns:
        External event ID from Microsoft Graph API
    """
    raise NotImplementedError("Microsoft 365 API integration not yet implemented.")
