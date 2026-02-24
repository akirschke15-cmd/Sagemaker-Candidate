"""
ATS Database Layer - SQLite with full lifecycle tracking
Feature 6: Multi-Role Matching - Candidates can be associated with multiple jobs
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from config import settings

DB_PATH = Path(settings.DB_PATH)

STAGES = ["Resume Screen", "Phone Screen", "Technical Interview", "Behavioral Interview", "Offer", "Hired", "Rejected"]
STAGE_ORDER = {stage: i for i, stage in enumerate(STAGES)}

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db_session() as conn:
        conn.executescript("""
        -- Vendors (staffing agencies, recruiters)
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            contact_email TEXT,
            contact_phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Job Descriptions / Roles
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            requirements TEXT,
            department TEXT,
            status TEXT DEFAULT 'Open',
            slots INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Scoring criteria per job per stage
        CREATE TABLE IF NOT EXISTS scoring_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            criteria_name TEXT NOT NULL,
            max_score INTEGER DEFAULT 5,
            weight REAL DEFAULT 1.0,
            description TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(job_id, stage, criteria_name)
        );
        
        -- Candidates
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            vendor_id INTEGER,
            job_id INTEGER,
            current_stage TEXT DEFAULT 'Resume Screen',
            status TEXT DEFAULT 'Active',
            resume_text TEXT,
            resume_path TEXT,
            resume_original_filename TEXT,
            ai_resume_score REAL,
            ai_resume_analysis TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        -- Add resume_original_filename column if it doesn't exist (migration)
        -- This is handled separately in migrate_db function
        
        -- Stage scores (actual evaluations)
        CREATE TABLE IF NOT EXISTS stage_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            criteria_id INTEGER NOT NULL,
            score INTEGER,
            evaluator TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (criteria_id) REFERENCES scoring_criteria(id) ON DELETE CASCADE,
            UNIQUE(candidate_id, criteria_id)
        );
        
        -- Interview notes per stage
        CREATE TABLE IF NOT EXISTS stage_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            notes TEXT,
            ai_summary TEXT,
            interviewer TEXT,
            interview_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        );
        
        -- Scheduling
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            scheduled_time TIMESTAMP,
            interviewer_email TEXT,
            interviewer_name TEXT,
            location TEXT,
            meeting_link TEXT,
            status TEXT DEFAULT 'Scheduled',
            email_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        );
        
        -- Email templates
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            stage TEXT,
            template_type TEXT
        );
        
        -- Email log
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            recipient TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );
        
        -- Scorecard tokens for mobile access
        CREATE TABLE IF NOT EXISTS scorecard_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            interviewer_email TEXT,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
        );

        -- Feature 6: Candidate-Jobs junction table for multi-role matching
        CREATE TABLE IF NOT EXISTS candidate_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            current_stage TEXT DEFAULT 'Resume Screen',
            status TEXT DEFAULT 'Active',
            ai_resume_score REAL,
            ai_resume_analysis TEXT,
            is_primary INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(candidate_id, job_id)
        );

        -- Feature 3: Notification webhooks (Slack/Teams)
        CREATE TABLE IF NOT EXISTS notification_webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('slack', 'teams')),
            webhook_url TEXT NOT NULL,
            channel_name TEXT,
            job_id INTEGER,
            is_active INTEGER DEFAULT 1,
            last_success TIMESTAMP,
            last_failure TIMESTAMP,
            failure_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );

        -- Feature 3: Notification settings per webhook
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (webhook_id) REFERENCES notification_webhooks(id) ON DELETE CASCADE,
            UNIQUE(webhook_id, event_type)
        );

        -- Feature 3: Notification log
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (webhook_id) REFERENCES notification_webhooks(id) ON DELETE CASCADE
        );

        -- Contractor Lifecycle Tracking: Contracts table
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            job_id INTEGER,
            start_date DATE,
            end_date DATE,
            hourly_rate REAL,
            status TEXT DEFAULT 'active',  -- active, completed, terminated, extended
            extension_of INTEGER,  -- FK to previous contract if extension
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
            FOREIGN KEY (extension_of) REFERENCES contracts(id) ON DELETE SET NULL
        );

        -- Contractor Lifecycle Tracking: Compliance documents table
        CREATE TABLE IF NOT EXISTS compliance_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,  -- W9, insurance, NDA, background_check, etc.
            status TEXT DEFAULT 'pending',  -- pending, received, verified, expired
            received_date DATE,
            expiry_date DATE,
            file_path TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_candidates_job ON candidates(job_id);
        CREATE INDEX IF NOT EXISTS idx_candidates_vendor ON candidates(vendor_id);
        CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(current_stage);
        CREATE INDEX IF NOT EXISTS idx_stage_scores_candidate ON stage_scores(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_interviews_candidate ON interviews(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_scorecard_tokens_token ON scorecard_tokens(token);
        CREATE INDEX IF NOT EXISTS idx_scorecard_tokens_interview ON scorecard_tokens(interview_id);
        CREATE INDEX IF NOT EXISTS idx_candidate_jobs_candidate ON candidate_jobs(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_candidate_jobs_job ON candidate_jobs(job_id);
        CREATE INDEX IF NOT EXISTS idx_candidate_jobs_stage ON candidate_jobs(current_stage);
        CREATE INDEX IF NOT EXISTS idx_notification_webhooks_job ON notification_webhooks(job_id);
        CREATE INDEX IF NOT EXISTS idx_notification_log_webhook ON notification_log(webhook_id);
        CREATE INDEX IF NOT EXISTS idx_notification_log_sent ON notification_log(sent_at);
        CREATE INDEX IF NOT EXISTS idx_contracts_candidate ON contracts(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
        CREATE INDEX IF NOT EXISTS idx_contracts_end_date ON contracts(end_date);
        CREATE INDEX IF NOT EXISTS idx_compliance_documents_candidate ON compliance_documents(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_compliance_documents_status ON compliance_documents(status);
        CREATE INDEX IF NOT EXISTS idx_compliance_documents_expiry ON compliance_documents(expiry_date);

        -- Contractor Roles for rate management
        CREATE TABLE IF NOT EXISTS contractor_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            min_hourly_rate REAL,
            max_hourly_rate REAL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_contractor_roles_active ON contractor_roles(is_active);

        -- Feature 7: Users table for RBAC
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            role TEXT NOT NULL,  -- 'admin', 'recruiter', 'hiring_manager', 'interviewer'
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Feature 7: Job owners linking users to jobs
        CREATE TABLE IF NOT EXISTS job_owners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'hiring_manager',  -- could be 'hiring_manager', 'recruiter', etc.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(job_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        CREATE INDEX IF NOT EXISTS idx_job_owners_job ON job_owners(job_id);
        CREATE INDEX IF NOT EXISTS idx_job_owners_user ON job_owners(user_id);

        -- Saved interview questions for reuse
        CREATE TABLE IF NOT EXISTS saved_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            stage TEXT,
            question TEXT NOT NULL,
            category TEXT,  -- technical, behavioral, situational, experience, culture_fit
            probing_area TEXT,  -- what this question aims to validate
            is_standard INTEGER DEFAULT 0,  -- standard question for this job/stage
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_saved_questions_job ON saved_questions(job_id);
        CREATE INDEX IF NOT EXISTS idx_saved_questions_stage ON saved_questions(stage);
        CREATE INDEX IF NOT EXISTS idx_saved_questions_category ON saved_questions(category);
        """)
        
        # Insert default email templates if not exists
        templates = [
            ("Phone Screen Invite", "Interview Invitation - {job_title}", 
             "Hi {candidate_name},\n\nWe'd like to schedule a phone screen for the {job_title} position.\n\nPlease let us know your availability.\n\nBest regards", 
             "Phone Screen", "invite"),
            ("Technical Interview Invite", "Technical Interview - {job_title}",
             "Hi {candidate_name},\n\nCongratulations on passing the phone screen! We'd like to schedule your technical interview.\n\nDetails:\nDate: {interview_date}\nTime: {interview_time}\nInterviewer: {interviewer_name}\n\nBest regards",
             "Technical Interview", "invite"),
            ("Rejection", "Update on your application - {job_title}",
             "Hi {candidate_name},\n\nThank you for your interest in the {job_title} position. After careful consideration, we've decided to move forward with other candidates.\n\nWe appreciate your time and wish you the best.\n\nBest regards",
             None, "rejection"),
            ("Offer", "Offer Letter - {job_title}",
             "Hi {candidate_name},\n\nWe're pleased to extend an offer for the {job_title} position!\n\nPlease review the attached offer letter and let us know if you have any questions.\n\nBest regards",
             "Offer", "offer"),
        ]
        
        for name, subject, body, stage, ttype in templates:
            conn.execute("""
                INSERT OR IGNORE INTO email_templates (name, subject, body, stage, template_type)
                VALUES (?, ?, ?, ?, ?)
            """, (name, subject, body, stage, ttype))

def migrate_db():
    """Run database migrations for schema updates"""
    with db_session() as conn:
        # Check if resume_original_filename column exists
        cursor = conn.execute("PRAGMA table_info(candidates)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'resume_original_filename' not in columns:
            conn.execute("ALTER TABLE candidates ADD COLUMN resume_original_filename TEXT")

        # Feature 6: Add job_id column to stage_scores if not exists
        cursor = conn.execute("PRAGMA table_info(stage_scores)")
        ss_columns = [row[1] for row in cursor.fetchall()]
        if 'job_id' not in ss_columns:
            conn.execute("ALTER TABLE stage_scores ADD COLUMN job_id INTEGER")

        # Feature 6: Add job_id column to stage_notes if not exists
        cursor = conn.execute("PRAGMA table_info(stage_notes)")
        sn_columns = [row[1] for row in cursor.fetchall()]
        if 'job_id' not in sn_columns:
            conn.execute("ALTER TABLE stage_notes ADD COLUMN job_id INTEGER")

        # Feature 6: Add job_id column to interviews if not exists
        cursor = conn.execute("PRAGMA table_info(interviews)")
        int_columns = [row[1] for row in cursor.fetchall()]
        if 'job_id' not in int_columns:
            conn.execute("ALTER TABLE interviews ADD COLUMN job_id INTEGER")

        # Contractor Roles: Add contractor_role_id to jobs table if not exists
        cursor = conn.execute("PRAGMA table_info(jobs)")
        jobs_columns = [row[1] for row in cursor.fetchall()]
        if 'contractor_role_id' not in jobs_columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN contractor_role_id INTEGER")

        # Contractor Roles: Add expected_hourly_rate to candidates table if not exists
        cursor = conn.execute("PRAGMA table_info(candidates)")
        candidates_columns = [row[1] for row in cursor.fetchall()]
        if 'expected_hourly_rate' not in candidates_columns:
            conn.execute("ALTER TABLE candidates ADD COLUMN expected_hourly_rate REAL")

        # Contractor Roles: Add expected_hourly_rate to candidate_jobs table if not exists
        cursor = conn.execute("PRAGMA table_info(candidate_jobs)")
        cj_columns = [row[1] for row in cursor.fetchall()]
        if 'expected_hourly_rate' not in cj_columns:
            conn.execute("ALTER TABLE candidate_jobs ADD COLUMN expected_hourly_rate REAL")

        # Contractor Lifecycle Tracking: Add contractor fields to candidates table
        cursor = conn.execute("PRAGMA table_info(candidates)")
        candidates_cols = [row[1] for row in cursor.fetchall()]

        if 'is_past_contractor' not in candidates_cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN is_past_contractor INTEGER DEFAULT 0")
        if 'last_contract_end' not in candidates_cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN last_contract_end DATE")
        if 'rehire_eligible' not in candidates_cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN rehire_eligible INTEGER DEFAULT 1")
        if 'rehire_notes' not in candidates_cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN rehire_notes TEXT")

        # Feature 6: Migrate existing candidate.job_id data to candidate_jobs table
        # Check if candidate_jobs table exists (it should from init_db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_jobs'")
        if cursor.fetchone():
            # Get all candidates with job_id that are not already in candidate_jobs
            candidates_with_jobs = conn.execute("""
                SELECT c.id, c.job_id, c.current_stage, c.status, c.ai_resume_score, c.ai_resume_analysis
                FROM candidates c
                WHERE c.job_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM candidate_jobs cj WHERE cj.candidate_id = c.id AND cj.job_id = c.job_id)
            """).fetchall()

            for c in candidates_with_jobs:
                conn.execute("""
                    INSERT OR IGNORE INTO candidate_jobs
                    (candidate_id, job_id, current_stage, status, ai_resume_score, ai_resume_analysis, is_primary, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (c['id'], c['job_id'], c['current_stage'], c['status'], c['ai_resume_score'], c['ai_resume_analysis']))

        # Feature 4: Create calendar integration tables
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

        -- Indexes for calendar tables
        CREATE INDEX IF NOT EXISTS idx_calendar_events_interview ON calendar_events(interview_id);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_ics_uid ON calendar_events(ics_uid);

        -- Email automation rules table
        CREATE TABLE IF NOT EXISTS email_automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,  -- NULL for global rules
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            template_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            delay_minutes INTEGER DEFAULT 0,  -- delay before sending
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE CASCADE
        );

        -- Email queue table for pending/sent emails
        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            template_id INTEGER,
            to_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT DEFAULT 'pending',  -- pending, sent, failed
            scheduled_at TIMESTAMP NOT NULL,
            sent_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE SET NULL
        );

        -- Indexes for email automation
        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_job ON email_automation_rules(job_id);
        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_stages ON email_automation_rules(from_stage, to_stage);
        CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled ON email_queue(scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_email_queue_candidate ON email_queue(candidate_id);
        """)

# ============ VENDOR OPERATIONS ============
def create_vendor(name: str, contact_email: str = None, contact_phone: str = None, notes: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO vendors (name, contact_email, contact_phone, notes) VALUES (?, ?, ?, ?)",
            (name, contact_email, contact_phone, notes)
        )
        return cursor.lastrowid

def get_vendors() -> List[Dict]:
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
        return [dict(r) for r in rows]

def get_vendor(vendor_id: int) -> Optional[Dict]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        return dict(row) if row else None

# ============ JOB OPERATIONS ============
def create_job(title: str, description: str = None, requirements: str = None, 
               department: str = None, slots: int = 1) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO jobs (title, description, requirements, department, slots) VALUES (?, ?, ?, ?, ?)",
            (title, description, requirements, department, slots)
        )
        return cursor.lastrowid

def get_jobs(status: str = None) -> List[Dict]:
    with db_session() as conn:
        if status:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def get_job(job_id: int) -> Optional[Dict]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

def update_job(job_id: int, **kwargs):
    ALLOWED_COLUMNS = {'title', 'description', 'requirements', 'department', 'status', 'slots', 'updated_at', 'contractor_role_id'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", (*kwargs.values(), job_id))

# ============ CONTRACTOR ROLE OPERATIONS ============
def create_contractor_role(name: str, description: str = None, min_rate: float = None, max_rate: float = None) -> int:
    """Create a new contractor role with rate range."""
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO contractor_roles (name, description, min_hourly_rate, max_hourly_rate) VALUES (?, ?, ?, ?)",
            (name, description, min_rate, max_rate)
        )
        return cursor.lastrowid

def get_contractor_roles(active_only: bool = True) -> List[Dict]:
    """Get all contractor roles, optionally filtered by active status."""
    with db_session() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM contractor_roles WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contractor_roles ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

def get_contractor_role(role_id: int) -> Optional[Dict]:
    """Get a contractor role by ID."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM contractor_roles WHERE id = ?", (role_id,)
        ).fetchone()
        return dict(row) if row else None

def update_contractor_role(role_id: int, **kwargs) -> bool:
    """Update a contractor role."""
    ALLOWED_COLUMNS = {'name', 'description', 'min_hourly_rate', 'max_hourly_rate', 'is_active'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE contractor_roles SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), role_id))
        return True

def delete_contractor_role(role_id: int) -> bool:
    """Soft delete a contractor role (set is_active = 0)."""
    with db_session() as conn:
        conn.execute("UPDATE contractor_roles SET is_active = 0 WHERE id = ?", (role_id,))
        return True

def activate_contractor_role(role_id: int) -> bool:
    """Reactivate a contractor role."""
    with db_session() as conn:
        conn.execute("UPDATE contractor_roles SET is_active = 1 WHERE id = ?", (role_id,))
        return True

def check_rate_in_range(expected_rate: float, role_id: int) -> tuple:
    """
    Check if an expected rate falls within a role's rate range.

    Returns:
        (in_range: bool, variance: float, message: str)
        - in_range: True if rate is within the range
        - variance: Percentage variance from nearest boundary (positive = over, negative = under)
        - message: Human-readable status message
    """
    if expected_rate is None or role_id is None:
        return (True, 0.0, "No rate specified")

    role = get_contractor_role(role_id)
    if not role:
        return (True, 0.0, "Role not found")

    min_rate = role.get('min_hourly_rate')
    max_rate = role.get('max_hourly_rate')

    if min_rate is None and max_rate is None:
        return (True, 0.0, "No rate range defined")

    # Calculate variance and status
    if min_rate is not None and expected_rate < min_rate:
        variance = ((expected_rate - min_rate) / min_rate) * 100
        return (False, variance, f"Below minimum (${min_rate:.2f}/hr)")

    if max_rate is not None and expected_rate > max_rate:
        variance = ((expected_rate - max_rate) / max_rate) * 100
        return (False, variance, f"Above maximum (${max_rate:.2f}/hr)")

    return (True, 0.0, "Within range")

def get_rate_status(expected_rate: float, role_id: int) -> Dict:
    """
    Get detailed rate status for display purposes.

    Returns dict with:
        - status: 'in_range', 'warning' (within 10%), or 'out_of_range'
        - color: Southwest-themed color for display
        - variance: percentage variance from nearest boundary
        - message: human-readable status
        - min_rate, max_rate: role's rate range
    """
    if expected_rate is None or role_id is None:
        return {
            'status': 'no_data',
            'color': '#6c757d',  # gray
            'variance': 0,
            'message': 'No rate data',
            'min_rate': None,
            'max_rate': None
        }

    role = get_contractor_role(role_id)
    if not role:
        return {
            'status': 'no_data',
            'color': '#6c757d',
            'variance': 0,
            'message': 'Role not found',
            'min_rate': None,
            'max_rate': None
        }

    min_rate = role.get('min_hourly_rate')
    max_rate = role.get('max_hourly_rate')

    if min_rate is None and max_rate is None:
        return {
            'status': 'no_data',
            'color': '#6c757d',
            'variance': 0,
            'message': 'No range defined',
            'min_rate': None,
            'max_rate': None
        }

    # Southwest Airlines colors
    COLOR_IN_RANGE = '#304CB2'   # Southwest Blue - in range
    COLOR_WARNING = '#F9B612'    # Southwest Yellow - within 10%
    COLOR_OUT_OF_RANGE = '#C8102E'  # Southwest Red - out of range

    # Check if within 10% of boundaries (warning zone)
    warning_threshold = 0.10

    if min_rate is not None and expected_rate < min_rate:
        variance = ((expected_rate - min_rate) / min_rate) * 100
        return {
            'status': 'out_of_range',
            'color': COLOR_OUT_OF_RANGE,
            'variance': variance,
            'message': f'${variance:.1f}% below minimum',
            'min_rate': min_rate,
            'max_rate': max_rate
        }

    if max_rate is not None and expected_rate > max_rate:
        variance = ((expected_rate - max_rate) / max_rate) * 100
        return {
            'status': 'out_of_range',
            'color': COLOR_OUT_OF_RANGE,
            'variance': variance,
            'message': f'+{variance:.1f}% above maximum',
            'min_rate': min_rate,
            'max_rate': max_rate
        }

    # Check warning zones (within 10% of min or max)
    if min_rate is not None:
        warning_min = min_rate * (1 + warning_threshold)
        if expected_rate < warning_min:
            variance = ((expected_rate - min_rate) / min_rate) * 100
            return {
                'status': 'warning',
                'color': COLOR_WARNING,
                'variance': variance,
                'message': f'Near minimum (+{variance:.1f}%)',
                'min_rate': min_rate,
                'max_rate': max_rate
            }

    if max_rate is not None:
        warning_max = max_rate * (1 - warning_threshold)
        if expected_rate > warning_max:
            variance = ((expected_rate - max_rate) / max_rate) * 100
            return {
                'status': 'warning',
                'color': COLOR_WARNING,
                'variance': variance,
                'message': f'Near maximum ({variance:.1f}%)',
                'min_rate': min_rate,
                'max_rate': max_rate
            }

    # In range
    return {
        'status': 'in_range',
        'color': COLOR_IN_RANGE,
        'variance': 0,
        'message': 'Within range',
        'min_rate': min_rate,
        'max_rate': max_rate
    }

def get_jobs_by_contractor_role(role_id: int) -> List[Dict]:
    """Get all jobs using a specific contractor role."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE contractor_role_id = ? ORDER BY created_at DESC",
            (role_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_compensation_stats_by_job() -> List[Dict]:
    """Get compensation analysis stats per job for dashboard."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT
                j.id as job_id,
                j.title as job_title,
                cr.name as role_name,
                cr.min_hourly_rate,
                cr.max_hourly_rate,
                COUNT(DISTINCT cj.candidate_id) as total_candidates,
                SUM(CASE
                    WHEN cj.expected_hourly_rate IS NOT NULL
                         AND cr.min_hourly_rate IS NOT NULL
                         AND cr.max_hourly_rate IS NOT NULL
                         AND cj.expected_hourly_rate >= cr.min_hourly_rate
                         AND cj.expected_hourly_rate <= cr.max_hourly_rate
                    THEN 1 ELSE 0 END) as in_range_count,
                SUM(CASE
                    WHEN cj.expected_hourly_rate IS NOT NULL
                         AND ((cr.min_hourly_rate IS NOT NULL AND cj.expected_hourly_rate < cr.min_hourly_rate)
                              OR (cr.max_hourly_rate IS NOT NULL AND cj.expected_hourly_rate > cr.max_hourly_rate))
                    THEN 1 ELSE 0 END) as out_of_range_count,
                SUM(CASE WHEN cj.expected_hourly_rate IS NULL THEN 1 ELSE 0 END) as no_rate_count
            FROM jobs j
            LEFT JOIN contractor_roles cr ON j.contractor_role_id = cr.id
            LEFT JOIN candidate_jobs cj ON j.id = cj.job_id AND cj.status = 'Active'
            WHERE j.status = 'Open'
            GROUP BY j.id, j.title, cr.name, cr.min_hourly_rate, cr.max_hourly_rate
            ORDER BY j.title
        """).fetchall()
        return [dict(r) for r in rows]

# ============ SCORING CRITERIA OPERATIONS ============
def set_scoring_criteria(job_id: int, stage: str, criteria: List[Dict]):
    """Set scoring criteria for a job stage. criteria = [{'name': str, 'max_score': int, 'weight': float, 'description': str}]"""
    with db_session() as conn:
        # Clear existing
        conn.execute("DELETE FROM scoring_criteria WHERE job_id = ? AND stage = ?", (job_id, stage))
        # Insert new
        for c in criteria:
            conn.execute("""
                INSERT INTO scoring_criteria (job_id, stage, criteria_name, max_score, weight, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, stage, c['name'], c.get('max_score', 5), c.get('weight', 1.0), c.get('description', '')))

def get_scoring_criteria(job_id: int, stage: str = None) -> List[Dict]:
    with db_session() as conn:
        if stage:
            rows = conn.execute(
                "SELECT * FROM scoring_criteria WHERE job_id = ? AND stage = ?", (job_id, stage)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scoring_criteria WHERE job_id = ? ORDER BY stage, id", (job_id,)
            ).fetchall()
        return [dict(r) for r in rows]

# ============ CANDIDATE OPERATIONS ============
def create_candidate(name: str, email: str = None, phone: str = None,
                     vendor_id: int = None, job_id: int = None,
                     resume_text: str = None, resume_path: str = None,
                     resume_original_filename: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO candidates (name, email, phone, vendor_id, job_id, resume_text, resume_path, resume_original_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, vendor_id, job_id, resume_text, resume_path, resume_original_filename))
        return cursor.lastrowid

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

def advance_candidate(candidate_id: int, new_stage: str):
    update_candidate(candidate_id, current_stage=new_stage)

def reject_candidate(candidate_id: int):
    update_candidate(candidate_id, status='Rejected', current_stage='Rejected')

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

def schedule_interview_for_role(candidate_id: int, job_id: int, stage: str, scheduled_time: str,
                                interviewer_email: str = None, interviewer_name: str = None,
                                location: str = None, meeting_link: str = None) -> int:
    """Schedule interview with job context for multi-role support."""
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO interviews (candidate_id, job_id, stage, scheduled_time, interviewer_email,
                                   interviewer_name, location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, job_id, stage, scheduled_time, interviewer_email, interviewer_name, location, meeting_link))
        return cursor.lastrowid

def get_interviews_with_role(candidate_id: int = None, job_id: int = None, upcoming_only: bool = False) -> List[Dict]:
    """Get interviews with job context for multi-role support."""
    with db_session() as conn:
        query = """
            SELECT i.*, c.name as candidate_name, c.email as candidate_email,
                   COALESCE(j2.title, j.title) as job_title
            FROM interviews i
            JOIN candidates c ON i.candidate_id = c.id
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN jobs j2 ON i.job_id = j2.id
            WHERE 1=1
        """
        params = []
        if candidate_id:
            query += " AND i.candidate_id = ?"
            params.append(candidate_id)
        if job_id:
            query += " AND (i.job_id = ? OR (i.job_id IS NULL AND c.job_id = ?))"
            params.extend([job_id, job_id])
        if upcoming_only:
            query += " AND i.scheduled_time >= datetime('now', 'localtime') AND i.status = 'Scheduled'"
        query += " ORDER BY i.scheduled_time"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

# ============ SCORING OPERATIONS ============
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

# ============ NOTES OPERATIONS ============
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

def get_saved_question(question_id: int) -> Optional[Dict]:
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

# ============ INTERVIEW SCHEDULING ============
def schedule_interview(candidate_id: int, stage: str, scheduled_time: str, 
                       interviewer_email: str = None, interviewer_name: str = None,
                       location: str = None, meeting_link: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO interviews (candidate_id, stage, scheduled_time, interviewer_email, 
                                   interviewer_name, location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, stage, scheduled_time, interviewer_email, interviewer_name, location, meeting_link))
        return cursor.lastrowid

def get_interviews(candidate_id: int = None, upcoming_only: bool = False) -> List[Dict]:
    with db_session() as conn:
        query = """
            SELECT i.*, c.name as candidate_name, c.email as candidate_email, j.title as job_title
            FROM interviews i
            JOIN candidates c ON i.candidate_id = c.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE 1=1
        """
        params = []
        if candidate_id:
            query += " AND i.candidate_id = ?"
            params.append(candidate_id)
        if upcoming_only:
            query += " AND i.scheduled_time >= datetime('now', 'localtime') AND i.status = 'Scheduled'"
        query += " ORDER BY i.scheduled_time"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

# ============ EMAIL OPERATIONS ============
def get_email_templates(template_type: str = None) -> List[Dict]:
    with db_session() as conn:
        if template_type:
            rows = conn.execute("SELECT * FROM email_templates WHERE template_type = ?", (template_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM email_templates").fetchall()
        return [dict(r) for r in rows]

def log_email(candidate_id: int, recipient: str, subject: str, body: str, status: str = 'sent'):
    with db_session() as conn:
        conn.execute("""
            INSERT INTO email_log (candidate_id, recipient, subject, body, status)
            VALUES (?, ?, ?, ?, ?)
        """, (candidate_id, recipient, subject, body, status))

# ============ ANALYTICS ============
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

# ============ USER OPERATIONS (Feature 7: RBAC) ============
USER_ROLES = ['admin', 'recruiter', 'hiring_manager', 'interviewer']

def create_user(email: str, name: str, role: str) -> int:
    """Create a new user with the specified role."""
    if role not in USER_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {USER_ROLES}")
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
            (email, name, role)
        )
        return cursor.lastrowid

def get_users(role: str = None, active_only: bool = True) -> List[Dict]:
    """Get all users, optionally filtered by role."""
    with db_session() as conn:
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        if active_only:
            query += " AND is_active = 1"
        if role:
            query += " AND role = ?"
            params.append(role)
        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_user(user_id: int) -> Optional[Dict]:
    """Get a user by ID."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by email address."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

def update_user(user_id: int, **kwargs):
    """Update user fields."""
    ALLOWED_COLUMNS = {'email', 'name', 'role', 'is_active'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", (*kwargs.values(), user_id))

def deactivate_user(user_id: int):
    """Deactivate a user (soft delete)."""
    update_user(user_id, is_active=0)

def activate_user(user_id: int):
    """Activate a user."""
    update_user(user_id, is_active=1)

# ============ JOB OWNERSHIP OPERATIONS (Feature 7: RBAC) ============
def assign_job_owner(job_id: int, user_id: int, role: str = 'hiring_manager'):
    """Assign a user as an owner of a job."""
    with db_session() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO job_owners (job_id, user_id, role, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (job_id, user_id, role))

def remove_job_owner(job_id: int, user_id: int):
    """Remove a user from job ownership."""
    with db_session() as conn:
        conn.execute("DELETE FROM job_owners WHERE job_id = ? AND user_id = ?", (job_id, user_id))

def get_job_owners(job_id: int) -> List[Dict]:
    """Get all owners of a job."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT jo.*, u.email, u.name, u.role as user_role
            FROM job_owners jo
            JOIN users u ON jo.user_id = u.id
            WHERE jo.job_id = ? AND u.is_active = 1
            ORDER BY u.name
        """, (job_id,)).fetchall()
        return [dict(r) for r in rows]

def get_user_jobs(user_id: int) -> List[Dict]:
    """Get all jobs owned by a user."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT j.*, jo.role as ownership_role
            FROM jobs j
            JOIN job_owners jo ON j.id = jo.job_id
            WHERE jo.user_id = ?
            ORDER BY j.created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def get_user_job_ids(user_id: int) -> List[int]:
    """Get list of job IDs owned by a user."""
    jobs = get_user_jobs(user_id)
    return [j['id'] for j in jobs]

def is_job_owner(user_id: int, job_id: int) -> bool:
    """Check if a user is an owner of a specific job."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT 1 FROM job_owners WHERE job_id = ? AND user_id = ?",
            (job_id, user_id)
        ).fetchone()
        return row is not None

def get_candidates_for_user_jobs(user_id: int, stage: str = None, status: str = 'Active') -> List[Dict]:
    """Get candidates for jobs owned by a user."""
    job_ids = get_user_job_ids(user_id)
    if not job_ids:
        return []

    with db_session() as conn:
        placeholders = ','.join('?' * len(job_ids))
        query = f"""
            SELECT c.*, j.title as job_title, v.name as vendor_name
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE c.job_id IN ({placeholders})
        """
        params = list(job_ids)
        if stage:
            query += " AND c.current_stage = ?"
            params.append(stage)
        if status:
            query += " AND c.status = ?"
            params.append(status)
        query += " ORDER BY c.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def seed_admin_user():
    """Seed initial admin user if no users exist."""
    with db_session() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        if row['count'] == 0:
            conn.execute("""
                INSERT INTO users (email, name, role, is_active)
                VALUES ('admin@agentic.com', 'System Admin', 'admin', 1)
            """)
            # Also add sample users for testing
            conn.execute("""
                INSERT INTO users (email, name, role, is_active)
                VALUES
                    ('recruiter@agentic.com', 'Main Recruiter', 'recruiter', 1),
                    ('hiring.manager@agentic.com', 'John Smith (HM)', 'hiring_manager', 1),
                    ('interviewer@agentic.com', 'Jane Doe (Interviewer)', 'interviewer', 1)
            """)

# ============ NOTIFICATION WEBHOOK OPERATIONS (Feature 3) ============
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
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE notification_webhooks SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), webhook_id))
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

# ============ CANDIDATE COMPARISON OPERATIONS ============
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
                    candidate['days_in_pipeline'] = max(days_in_pipeline, 0)
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

def get_email_template(template_id: int) -> Optional[Dict]:
    """Get a single email template by ID."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,)).fetchone()
        return dict(row) if row else None


# ============ CONTRACT LIFECYCLE TRACKING OPERATIONS ============
COMPLIANCE_DOC_TYPES = ['W9', 'insurance', 'NDA', 'background_check', 'I9', 'direct_deposit', 'other']
CONTRACT_STATUSES = ['active', 'completed', 'terminated', 'extended']

def create_contract(candidate_id: int, job_id: int = None, start_date: str = None,
                   end_date: str = None, hourly_rate: float = None, notes: str = None,
                   extension_of: int = None) -> int:
    """
    Create a new contract for a candidate.

    Args:
        candidate_id: Candidate ID
        job_id: Optional job ID
        start_date: Contract start date (YYYY-MM-DD)
        end_date: Contract end date (YYYY-MM-DD)
        hourly_rate: Hourly rate for the contract
        notes: Additional notes
        extension_of: ID of previous contract if this is an extension

    Returns:
        New contract ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO contracts (candidate_id, job_id, start_date, end_date, hourly_rate, notes, extension_of)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, job_id, start_date, end_date, hourly_rate, notes, extension_of))
        return cursor.lastrowid

def get_contracts(candidate_id: int = None, status: str = None, job_id: int = None) -> List[Dict]:
    """
    Get contracts with optional filtering.

    Args:
        candidate_id: Filter by candidate ID
        status: Filter by status (active, completed, terminated, extended)
        job_id: Filter by job ID

    Returns:
        List of contract dictionaries
    """
    with db_session() as conn:
        query = """
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE 1=1
        """
        params = []

        if candidate_id:
            query += " AND c.candidate_id = ?"
            params.append(candidate_id)
        if status:
            query += " AND c.status = ?"
            params.append(status)
        if job_id:
            query += " AND c.job_id = ?"
            params.append(job_id)

        query += " ORDER BY c.end_date ASC, c.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_contract(contract_id: int) -> Optional[Dict]:
    """Get a single contract by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.id = ?
        """, (contract_id,)).fetchone()
        return dict(row) if row else None

def update_contract(contract_id: int, **kwargs) -> bool:
    """Update contract fields."""
    ALLOWED_COLUMNS = {'candidate_id', 'job_id', 'start_date', 'end_date', 'hourly_rate', 'status', 'extension_of', 'notes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE contracts SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), contract_id))
        return True

def get_expiring_contracts(days: int = 30) -> List[Dict]:
    """
    Get contracts ending within N days.

    Args:
        days: Number of days to look ahead

    Returns:
        List of contracts ending soon, sorted by end date
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title,
                   julianday(c.end_date) - julianday('now') as days_remaining
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.status = 'active'
            AND c.end_date IS NOT NULL
            AND date(c.end_date) <= date('now', '+' || ? || ' days')
            AND date(c.end_date) >= date('now')
            ORDER BY c.end_date ASC
        """, (days,)).fetchall()
        return [dict(r) for r in rows]

def extend_contract(contract_id: int, new_end_date: str, new_rate: float = None,
                   notes: str = None) -> int:
    """
    Extend a contract by creating a new contract linked to the original.

    Args:
        contract_id: Original contract ID
        new_end_date: New end date for the extension
        new_rate: New hourly rate (optional, uses original if not provided)
        notes: Notes for the extension

    Returns:
        New contract ID
    """
    original = get_contract(contract_id)
    if not original:
        raise ValueError(f"Contract {contract_id} not found")

    # Mark original as extended
    update_contract(contract_id, status='extended')

    # Create extension contract
    return create_contract(
        candidate_id=original['candidate_id'],
        job_id=original['job_id'],
        start_date=original['end_date'],  # Extension starts when original ends
        end_date=new_end_date,
        hourly_rate=new_rate if new_rate else original['hourly_rate'],
        notes=notes,
        extension_of=contract_id
    )

def complete_contract(contract_id: int, notes: str = None) -> bool:
    """
    Mark a contract as completed and update candidate as past contractor.

    Args:
        contract_id: Contract ID
        notes: Optional completion notes

    Returns:
        True if successful
    """
    contract = get_contract(contract_id)
    if not contract:
        return False

    with db_session() as conn:
        # Update contract status
        conn.execute("""
            UPDATE contracts SET status = 'completed', notes = COALESCE(?, notes)
            WHERE id = ?
        """, (notes, contract_id))

        # Mark candidate as past contractor
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                last_contract_end = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contract['end_date'], contract['candidate_id']))

        return True

def terminate_contract(contract_id: int, notes: str = None) -> bool:
    """
    Terminate a contract early.

    Args:
        contract_id: Contract ID
        notes: Termination notes

    Returns:
        True if successful
    """
    contract = get_contract(contract_id)
    if not contract:
        return False

    with db_session() as conn:
        # Update contract status
        conn.execute("""
            UPDATE contracts SET status = 'terminated', notes = COALESCE(?, notes)
            WHERE id = ?
        """, (notes, contract_id))

        # Mark candidate as past contractor with today's date
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                last_contract_end = date('now'),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contract['candidate_id'],))

        return True

# ============ COMPLIANCE DOCUMENT OPERATIONS ============
def add_compliance_doc(candidate_id: int, doc_type: str, status: str = 'pending',
                       received_date: str = None, expiry_date: str = None,
                       file_path: str = None, notes: str = None) -> int:
    """
    Add a compliance document record for a candidate.

    Args:
        candidate_id: Candidate ID
        doc_type: Document type (W9, insurance, NDA, etc.)
        status: Document status (pending, received, verified, expired)
        received_date: Date document was received
        expiry_date: Document expiration date
        file_path: Path to uploaded document
        notes: Additional notes

    Returns:
        New document ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO compliance_documents
            (candidate_id, doc_type, status, received_date, expiry_date, file_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, doc_type, status, received_date, expiry_date, file_path, notes))
        return cursor.lastrowid

def get_compliance_docs(candidate_id: int = None, doc_type: str = None,
                       status: str = None) -> List[Dict]:
    """
    Get compliance documents with optional filtering.

    Args:
        candidate_id: Filter by candidate ID
        doc_type: Filter by document type
        status: Filter by status

    Returns:
        List of compliance document dictionaries
    """
    with db_session() as conn:
        query = """
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            WHERE 1=1
        """
        params = []

        if candidate_id:
            query += " AND cd.candidate_id = ?"
            params.append(candidate_id)
        if doc_type:
            query += " AND cd.doc_type = ?"
            params.append(doc_type)
        if status:
            query += " AND cd.status = ?"
            params.append(status)

        query += " ORDER BY cd.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_compliance_doc(doc_id: int) -> Optional[Dict]:
    """Get a single compliance document by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            WHERE cd.id = ?
        """, (doc_id,)).fetchone()
        return dict(row) if row else None

def update_compliance_doc(doc_id: int, **kwargs) -> bool:
    """Update compliance document fields."""
    ALLOWED_COLUMNS = {'candidate_id', 'doc_type', 'status', 'received_date', 'expiry_date', 'file_path', 'notes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE compliance_documents SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), doc_id))
        return True

def delete_compliance_doc(doc_id: int) -> bool:
    """Delete a compliance document."""
    with db_session() as conn:
        conn.execute("DELETE FROM compliance_documents WHERE id = ?", (doc_id,))
        return True

def get_compliance_alerts() -> List[Dict]:
    """
    Get compliance documents that need attention (expired or expiring soon).

    Returns:
        List of documents with issues, sorted by urgency
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email,
                   CASE
                       WHEN cd.status = 'expired' THEN 'expired'
                       WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) < date('now') THEN 'expired'
                       WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days') THEN 'expiring_soon'
                       WHEN cd.status = 'pending' THEN 'pending'
                       ELSE 'ok'
                   END as alert_type,
                   julianday(cd.expiry_date) - julianday('now') as days_until_expiry
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            JOIN contracts con ON cd.candidate_id = con.candidate_id AND con.status = 'active'
            WHERE cd.status IN ('pending', 'expired')
               OR (cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days'))
            ORDER BY
                CASE
                    WHEN cd.status = 'expired' OR (cd.expiry_date IS NOT NULL AND date(cd.expiry_date) < date('now')) THEN 1
                    WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days') THEN 2
                    WHEN cd.status = 'pending' THEN 3
                    ELSE 4
                END,
                cd.expiry_date ASC
        """).fetchall()
        return [dict(r) for r in rows]

def get_compliance_matrix() -> List[Dict]:
    """
    Get compliance status matrix for all active contractors.

    Returns:
        List of candidates with their compliance document statuses
    """
    with db_session() as conn:
        # Get all candidates with active contracts
        candidates = conn.execute("""
            SELECT DISTINCT c.id, c.name, c.email
            FROM candidates c
            JOIN contracts con ON c.id = con.candidate_id
            WHERE con.status = 'active'
            ORDER BY c.name
        """).fetchall()

        result = []
        for cand in candidates:
            cand_dict = dict(cand)
            # Get all compliance docs for this candidate
            docs = conn.execute("""
                SELECT doc_type, status, expiry_date
                FROM compliance_documents
                WHERE candidate_id = ?
            """, (cand['id'],)).fetchall()

            doc_status = {}
            for doc_type in COMPLIANCE_DOC_TYPES:
                doc_status[doc_type] = 'missing'

            for doc in docs:
                doc_type = doc['doc_type']
                status = doc['status']
                expiry = doc['expiry_date']

                # Check if expired
                if expiry and status == 'verified':
                    try:
                        exp_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                        if exp_date < datetime.now().date():
                            status = 'expired'
                    except ValueError:
                        pass

                doc_status[doc_type] = status

            cand_dict['documents'] = doc_status
            result.append(cand_dict)

        return result

# ============ PAST CONTRACTOR / REHIRE OPERATIONS ============
def mark_as_past_contractor(candidate_id: int, rehire_eligible: bool = True,
                           notes: str = None) -> bool:
    """
    Mark a candidate as a past contractor.

    Args:
        candidate_id: Candidate ID
        rehire_eligible: Whether the candidate is eligible for rehire
        notes: Rehire notes/reasons

    Returns:
        True if successful
    """
    with db_session() as conn:
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                rehire_eligible = ?,
                rehire_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if rehire_eligible else 0, notes, candidate_id))
        return True

def get_past_contractors(rehire_eligible: bool = None) -> List[Dict]:
    """
    Get all past contractors with optional rehire eligibility filter.

    Args:
        rehire_eligible: Filter by rehire eligibility (None for all)

    Returns:
        List of past contractor candidates
    """
    with db_session() as conn:
        query = """
            SELECT c.*, j.title as job_title, v.name as vendor_name,
                   (SELECT MAX(end_date) FROM contracts WHERE candidate_id = c.id) as last_contract_end_date,
                   (SELECT COUNT(*) FROM contracts WHERE candidate_id = c.id) as total_contracts
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE c.is_past_contractor = 1
        """
        params = []

        if rehire_eligible is not None:
            query += " AND c.rehire_eligible = ?"
            params.append(1 if rehire_eligible else 0)

        query += " ORDER BY c.last_contract_end DESC, c.name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def update_rehire_status(candidate_id: int, rehire_eligible: bool, notes: str = None) -> bool:
    """Update a candidate's rehire eligibility status."""
    with db_session() as conn:
        conn.execute("""
            UPDATE candidates
            SET rehire_eligible = ?,
                rehire_notes = COALESCE(?, rehire_notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if rehire_eligible else 0, notes, candidate_id))
        return True

def get_contract_history(candidate_id: int) -> List[Dict]:
    """
    Get full contract history for a candidate including extensions.

    Args:
        candidate_id: Candidate ID

    Returns:
        List of contracts ordered by date
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, j.title as job_title,
                   ec.id as extended_to_id
            FROM contracts c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN contracts ec ON ec.extension_of = c.id
            WHERE c.candidate_id = ?
            ORDER BY c.start_date DESC
        """, (candidate_id,)).fetchall()
        return [dict(r) for r in rows]

def get_active_contractors_count() -> int:
    """Get count of candidates with active contracts."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT COUNT(DISTINCT candidate_id) as count
            FROM contracts
            WHERE status = 'active'
        """).fetchone()
        return row['count'] if row else 0

def get_contracts_expiring_this_month() -> List[Dict]:
    """Get contracts expiring within the current month."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title,
                   julianday(c.end_date) - julianday('now') as days_remaining
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.status = 'active'
            AND c.end_date IS NOT NULL
            AND strftime('%Y-%m', c.end_date) = strftime('%Y-%m', 'now')
            ORDER BY c.end_date ASC
        """).fetchall()
        return [dict(r) for r in rows]


# ============ ANALYTICS FUNCTIONS ============
def get_pipeline_velocity(job_id: int = None) -> List[Dict]:
    """
    Calculate average days spent in each stage.
    Uses stage_notes and interviews to track time in stages.
    Returns list of {stage, avg_days, min_days, max_days, candidate_count}.
    """
    with db_session() as conn:
        # Calculate time between stage transitions using candidate_jobs updated_at
        query = """
            WITH stage_times AS (
                SELECT
                    cj.current_stage as stage,
                    cj.candidate_id,
                    cj.job_id,
                    JULIANDAY(cj.updated_at) - JULIANDAY(cj.created_at) as days_in_stage
                FROM candidate_jobs cj
                WHERE cj.status IN ('Active', 'Rejected')
        """
        params = []
        if job_id:
            query += " AND cj.job_id = ?"
            params.append(job_id)

        query += """
            )
            SELECT
                stage,
                ROUND(AVG(days_in_stage), 1) as avg_days,
                ROUND(MIN(days_in_stage), 1) as min_days,
                ROUND(MAX(days_in_stage), 1) as max_days,
                COUNT(*) as candidate_count
            FROM stage_times
            WHERE days_in_stage >= 0
            GROUP BY stage
            ORDER BY
                CASE stage
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


def get_stage_conversion_rates(job_id: int = None) -> List[Dict]:
    """
    Calculate conversion rates between stages.
    Returns list of {from_stage, to_stage, total_entered, advanced, rejected, conversion_rate}.
    """
    with db_session() as conn:
        # Get counts per stage
        query = """
            SELECT
                current_stage as stage,
                COUNT(*) as count
            FROM candidate_jobs
            WHERE 1=1
        """
        params = []
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        query += " GROUP BY current_stage"

        stage_counts = {r['stage']: r['count'] for r in conn.execute(query, params).fetchall()}

        # Get rejected count per stage
        reject_query = """
            SELECT
                current_stage as stage,
                COUNT(*) as rejected_count
            FROM candidate_jobs
            WHERE status = 'Rejected'
        """
        if job_id:
            reject_query += " AND job_id = ?"
        reject_query += " GROUP BY current_stage"

        rejected_counts = {r['stage']: r['rejected_count'] for r in conn.execute(reject_query, params).fetchall()}

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


def get_jobs_dict(status: str = None) -> dict:
    """Pre-fetch all jobs as a dict keyed by job ID. Use to avoid N+1 queries."""
    with db_session() as conn:
        if status:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ?", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs").fetchall()
        return {row['id']: dict(row) for row in rows}

def get_contractor_roles_dict() -> dict:
    """Pre-fetch all contractor roles as a dict keyed by role ID."""
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM contractor_roles").fetchall()
        return {row['id']: dict(row) for row in rows}


# Initialize on import
init_db()
migrate_db()
seed_admin_user()
