"""
ATS Database Connection and Schema Management
Supports both SQLite and PostgreSQL with automatic backend detection
"""
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Union

# Try to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Import settings
try:
    from config import settings
    DB_PATH = Path(settings.DB_PATH)
    DATABASE_URL = settings.DATABASE_URL
    DB_POOL_SIZE = settings.DB_POOL_SIZE
    DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
    DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
except ImportError:
    # Fallback if settings not available
    DB_PATH = Path(__file__).parent.parent / "ats_data.db"
    DATABASE_URL = ""
    DB_POOL_SIZE = 5
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30

# Global connection pool for PostgreSQL
_pg_pool: Optional['psycopg2.pool.ThreadedConnectionPool'] = None


def get_db_type() -> str:
    """
    Returns the database type being used.

    Returns:
        str: "sqlite" or "postgresql"
    """
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        return "postgresql"
    return "sqlite"


def _get_pg_pool():
    """Get or create the PostgreSQL connection pool."""
    global _pg_pool

    if not PSYCOPG2_AVAILABLE:
        raise RuntimeError("psycopg2 is not installed. Install it with: pip install psycopg2-binary")

    if _pg_pool is None:
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=DB_POOL_SIZE + DB_MAX_OVERFLOW,
            dsn=DATABASE_URL,
            connect_timeout=DB_POOL_TIMEOUT
        )

    return _pg_pool


def adapt_query(sql: str, db_type: str = None) -> str:
    """
    Adapt SQL query for the target database type.

    Converts SQLite-specific syntax to PostgreSQL-compatible syntax:
    - ? -> %s for parameter placeholders
    - INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY
    - AUTOINCREMENT -> SERIAL

    Args:
        sql: The SQL query string
        db_type: Target database type ("sqlite" or "postgresql"). Auto-detected if None.

    Returns:
        str: Adapted SQL query
    """
    if db_type is None:
        db_type = get_db_type()

    if db_type != "postgresql":
        return sql

    # Convert ? to %s for parameter placeholders
    adapted = sql.replace("?", "%s")

    # Convert INTEGER PRIMARY KEY AUTOINCREMENT to SERIAL PRIMARY KEY
    adapted = re.sub(
        r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT',
        'SERIAL PRIMARY KEY',
        adapted,
        flags=re.IGNORECASE
    )

    # Convert remaining AUTOINCREMENT to SERIAL
    adapted = re.sub(
        r'AUTOINCREMENT',
        'SERIAL',
        adapted,
        flags=re.IGNORECASE
    )

    return adapted


class RowProxy:
    """
    Wrapper to provide dict-like and attribute access to database rows.
    Compatible with both SQLite Row and psycopg2 DictRow.
    """
    def __init__(self, data: Union[sqlite3.Row, dict]):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __getattr__(self, name):
        try:
            return self._data[name]
        except (KeyError, IndexError):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def keys(self):
        if isinstance(self._data, sqlite3.Row):
            return self._data.keys()
        return self._data.keys()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class ConnectionWrapper:
    """
    Wrapper around database connection to provide unified interface.
    Handles query adaptation for PostgreSQL.
    """
    def __init__(self, conn, db_type: str):
        self._conn = conn
        self._db_type = db_type

    def execute(self, sql: str, parameters=None):
        """Execute a SQL query with automatic adaptation."""
        adapted_sql = adapt_query(sql, self._db_type)

        if parameters:
            return self._conn.execute(adapted_sql, parameters)
        return self._conn.execute(adapted_sql)

    def executescript(self, sql: str):
        """Execute a SQL script with automatic adaptation."""
        adapted_sql = adapt_query(sql, self._db_type)

        if self._db_type == "postgresql":
            # PostgreSQL doesn't have executescript, use execute for DDL
            cursor = self._conn.cursor()
            cursor.execute(adapted_sql)
            return cursor
        return self._conn.executescript(adapted_sql)

    def executemany(self, sql: str, parameters):
        """Execute a SQL query with many parameter sets."""
        adapted_sql = adapt_query(sql, self._db_type)
        return self._conn.executemany(adapted_sql, parameters)

    def commit(self):
        """Commit the current transaction."""
        return self._conn.commit()

    def rollback(self):
        """Roll back the current transaction."""
        return self._conn.rollback()

    def close(self):
        """Close the connection."""
        if self._db_type == "postgresql":
            # Return connection to pool instead of closing
            pool = _get_pg_pool()
            pool.putconn(self._conn)
        else:
            self._conn.close()

    def cursor(self):
        """Get a cursor for the connection."""
        return self._conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_connection():
    """
    Get a database connection based on configuration.

    Returns:
        ConnectionWrapper: A wrapped database connection with unified interface
    """
    db_type = get_db_type()

    if db_type == "postgresql":
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 is not installed. Install it with: pip install psycopg2-binary")

        pool = _get_pg_pool()
        conn = pool.getconn()

        # Set up DictCursor for dict-like row access
        conn.cursor_factory = psycopg2.extras.DictCursor

        return ConnectionWrapper(conn, db_type)

    else:  # SQLite
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # SQLite-specific PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")

        return ConnectionWrapper(conn, db_type)


@contextmanager
def db_session():
    """
    Context manager for database sessions.
    Handles automatic commit/rollback and connection cleanup.

    Usage:
        with db_session() as conn:
            conn.execute("INSERT INTO ...", (values,))
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def explain_query(sql, params=None):
    """
    Run EXPLAIN QUERY PLAN on a query for debugging slow queries.
    Works with both SQLite and PostgreSQL.
    """
    db_type = get_db_type()

    with db_session() as conn:
        if db_type == "postgresql":
            # PostgreSQL uses EXPLAIN
            adapted_sql = adapt_query(sql, db_type)
            result = conn.execute(f"EXPLAIN {adapted_sql}", params or []).fetchall()
        else:
            # SQLite uses EXPLAIN QUERY PLAN
            result = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params or []).fetchall()

        return [dict(r) for r in result]


def init_db():
    """Initialize the database schema for the appropriate backend."""
    db_type = get_db_type()

    with db_session() as conn:
        # Base schema adapted for the target database
        schema = """
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
            status TEXT DEFAULT 'active',
            extension_of INTEGER,
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
            doc_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            received_date DATE,
            expiry_date DATE,
            file_path TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        );

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

        -- Feature 7: Users table for RBAC
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Feature 7: Job owners linking users to jobs
        CREATE TABLE IF NOT EXISTS job_owners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'hiring_manager',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(job_id, user_id)
        );

        -- Saved interview questions for reuse
        CREATE TABLE IF NOT EXISTS saved_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            stage TEXT,
            question TEXT NOT NULL,
            category TEXT,
            probing_area TEXT,
            is_standard INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        -- Calendar integrations for OAuth providers
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

        -- Email automation rules table
        CREATE TABLE IF NOT EXISTS email_automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            template_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            delay_minutes INTEGER DEFAULT 0,
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
            status TEXT DEFAULT 'pending',
            scheduled_at TIMESTAMP NOT NULL,
            sent_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE SET NULL
        );
        """

        # Execute the schema creation
        conn.executescript(schema)

        # Create indexes
        index_sql = """
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
        CREATE INDEX IF NOT EXISTS idx_contractor_roles_active ON contractor_roles(is_active);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        CREATE INDEX IF NOT EXISTS idx_job_owners_job ON job_owners(job_id);
        CREATE INDEX IF NOT EXISTS idx_job_owners_user ON job_owners(user_id);
        CREATE INDEX IF NOT EXISTS idx_saved_questions_job ON saved_questions(job_id);
        CREATE INDEX IF NOT EXISTS idx_saved_questions_stage ON saved_questions(stage);
        CREATE INDEX IF NOT EXISTS idx_saved_questions_category ON saved_questions(category);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_interview ON calendar_events(interview_id);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_ics_uid ON calendar_events(ics_uid);
        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_job ON email_automation_rules(job_id);
        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_stages ON email_automation_rules(from_stage, to_stage);
        CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled ON email_queue(scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_email_queue_candidate ON email_queue(candidate_id);

        -- Composite indexes for common query patterns
        CREATE INDEX IF NOT EXISTS idx_candidates_status_stage ON candidates(status, current_stage);
        CREATE INDEX IF NOT EXISTS idx_candidates_job_status ON candidates(job_id, status);
        CREATE INDEX IF NOT EXISTS idx_candidate_jobs_status_stage ON candidate_jobs(status, current_stage);
        CREATE INDEX IF NOT EXISTS idx_interviews_status_time ON interviews(status, scheduled_time);
        CREATE INDEX IF NOT EXISTS idx_stage_scores_candidate_stage ON stage_scores(candidate_id, stage);
        CREATE INDEX IF NOT EXISTS idx_stage_notes_candidate_stage ON stage_notes(candidate_id, stage);
        CREATE INDEX IF NOT EXISTS idx_email_queue_status_scheduled ON email_queue(status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_contracts_candidate_status ON contracts(candidate_id, status);
        CREATE INDEX IF NOT EXISTS idx_compliance_documents_candidate_type ON compliance_documents(candidate_id, doc_type);
        """

        conn.executescript(index_sql)

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
    """Run database migrations for schema updates."""
    db_type = get_db_type()

    with db_session() as conn:
        if db_type == "sqlite":
            # SQLite-specific migrations using PRAGMA
            _migrate_sqlite(conn)
        else:
            # PostgreSQL-specific migrations using information_schema
            _migrate_postgresql(conn)


def _migrate_sqlite(conn):
    """SQLite-specific migration logic."""
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
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_jobs'")
    if cursor.fetchone():
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

    # Feature 4: Create calendar integration tables if not exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_integrations'")
    if not cursor.fetchone():
        conn.executescript("""
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

        CREATE INDEX IF NOT EXISTS idx_calendar_events_interview ON calendar_events(interview_id);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_ics_uid ON calendar_events(ics_uid);

        CREATE TABLE IF NOT EXISTS email_automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            template_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            delay_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            template_id INTEGER,
            to_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            scheduled_at TIMESTAMP NOT NULL,
            sent_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_job ON email_automation_rules(job_id);
        CREATE INDEX IF NOT EXISTS idx_email_automation_rules_stages ON email_automation_rules(from_stage, to_stage);
        CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled ON email_queue(scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_email_queue_candidate ON email_queue(candidate_id);
        """)


def _migrate_postgresql(conn):
    """PostgreSQL-specific migration logic."""
    cursor = conn.cursor()

    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, (table_name, column_name))
        return cursor.fetchone() is not None

    # Add resume_original_filename to candidates if not exists
    if not column_exists('candidates', 'resume_original_filename'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_original_filename TEXT")

    # Add job_id to stage_scores if not exists
    if not column_exists('stage_scores', 'job_id'):
        cursor.execute("ALTER TABLE stage_scores ADD COLUMN job_id INTEGER")

    # Add job_id to stage_notes if not exists
    if not column_exists('stage_notes', 'job_id'):
        cursor.execute("ALTER TABLE stage_notes ADD COLUMN job_id INTEGER")

    # Add job_id to interviews if not exists
    if not column_exists('interviews', 'job_id'):
        cursor.execute("ALTER TABLE interviews ADD COLUMN job_id INTEGER")

    # Add contractor_role_id to jobs if not exists
    if not column_exists('jobs', 'contractor_role_id'):
        cursor.execute("ALTER TABLE jobs ADD COLUMN contractor_role_id INTEGER")

    # Add expected_hourly_rate to candidates if not exists
    if not column_exists('candidates', 'expected_hourly_rate'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN expected_hourly_rate REAL")

    # Add expected_hourly_rate to candidate_jobs if not exists
    if not column_exists('candidate_jobs', 'expected_hourly_rate'):
        cursor.execute("ALTER TABLE candidate_jobs ADD COLUMN expected_hourly_rate REAL")

    # Add contractor lifecycle fields to candidates
    if not column_exists('candidates', 'is_past_contractor'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN is_past_contractor INTEGER DEFAULT 0")
    if not column_exists('candidates', 'last_contract_end'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN last_contract_end DATE")
    if not column_exists('candidates', 'rehire_eligible'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN rehire_eligible INTEGER DEFAULT 1")
    if not column_exists('candidates', 'rehire_notes'):
        cursor.execute("ALTER TABLE candidates ADD COLUMN rehire_notes TEXT")

    # Migrate existing candidate.job_id data to candidate_jobs table
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'candidate_jobs'
    """)

    if cursor.fetchone():
        cursor.execute("""
            SELECT c.id, c.job_id, c.current_stage, c.status, c.ai_resume_score, c.ai_resume_analysis
            FROM candidates c
            WHERE c.job_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM candidate_jobs cj WHERE cj.candidate_id = c.id AND cj.job_id = c.job_id)
        """)

        candidates_with_jobs = cursor.fetchall()

        for c in candidates_with_jobs:
            cursor.execute("""
                INSERT INTO candidate_jobs
                (candidate_id, job_id, current_stage, status, ai_resume_score, ai_resume_analysis, is_primary, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT DO NOTHING
            """, (c[0], c[1], c[2], c[3], c[4], c[5]))
