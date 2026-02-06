#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Utility for ATS Application

This script migrates the ATS application database from SQLite to PostgreSQL,
handling schema translation, data migration, and verification.

Usage:
  python migrate_to_postgres.py --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  python migrate_to_postgres.py --dry-run --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  python migrate_to_postgres.py --verify --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  python migrate_to_postgres.py --drop-existing --postgres-url "postgresql://user:pass@localhost:5432/ats_db"

Requirements:
  pip install psycopg2-binary

Author: ATS Migration Tool
Version: 1.0.0
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 is required. Install with: pip install psycopg2-binary")
    sys.exit(1)


# Table migration order (respects foreign key dependencies)
TABLE_ORDER = [
    'vendors',
    'jobs',
    'contractor_roles',
    'candidates',
    'candidate_jobs',
    'scoring_criteria',
    'stage_scores',
    'stage_notes',
    'interviews',
    'scorecard_tokens',
    'email_templates',
    'email_log',
    'email_queue',
    'email_automation_rules',
    'notification_webhooks',
    'notification_settings',
    'notification_log',
    'contracts',
    'compliance_documents',
    'users',
    'job_owners',
    'saved_questions',
    'calendar_integrations',
    'calendar_events',
]


# PostgreSQL schema definitions with proper type translations
POSTGRES_SCHEMAS = {
    'vendors': """
        CREATE TABLE vendors (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            contact_email TEXT,
            contact_phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,

    'jobs': """
        CREATE TABLE jobs (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            requirements TEXT,
            department TEXT,
            status TEXT DEFAULT 'Open',
            slots INTEGER DEFAULT 1,
            contractor_role_id INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,

    'contractor_roles': """
        CREATE TABLE contractor_roles (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            min_hourly_rate DOUBLE PRECISION,
            max_hourly_rate DOUBLE PRECISION,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,

    'candidates': """
        CREATE TABLE candidates (
            id SERIAL PRIMARY KEY,
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
            ai_resume_score DOUBLE PRECISION,
            ai_resume_analysis TEXT,
            notes TEXT,
            expected_hourly_rate DOUBLE PRECISION,
            is_past_contractor BOOLEAN DEFAULT FALSE,
            last_contract_end DATE,
            rehire_eligible BOOLEAN DEFAULT TRUE,
            rehire_notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (vendor_id) REFERENCES vendors(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """,

    'candidate_jobs': """
        CREATE TABLE candidate_jobs (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            current_stage TEXT DEFAULT 'Resume Screen',
            status TEXT DEFAULT 'Active',
            ai_resume_score DOUBLE PRECISION,
            ai_resume_analysis TEXT,
            is_primary BOOLEAN DEFAULT FALSE,
            expected_hourly_rate DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(candidate_id, job_id)
        )
    """,

    'scoring_criteria': """
        CREATE TABLE scoring_criteria (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            criteria_name TEXT NOT NULL,
            max_score INTEGER DEFAULT 5,
            weight DOUBLE PRECISION DEFAULT 1.0,
            description TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(job_id, stage, criteria_name)
        )
    """,

    'stage_scores': """
        CREATE TABLE stage_scores (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            criteria_id INTEGER NOT NULL,
            score INTEGER,
            evaluator TEXT,
            job_id INTEGER,
            scored_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (criteria_id) REFERENCES scoring_criteria(id) ON DELETE CASCADE,
            UNIQUE(candidate_id, criteria_id)
        )
    """,

    'stage_notes': """
        CREATE TABLE stage_notes (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            notes TEXT,
            ai_summary TEXT,
            interviewer TEXT,
            interview_date TIMESTAMP,
            job_id INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        )
    """,

    'interviews': """
        CREATE TABLE interviews (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            scheduled_time TIMESTAMP,
            interviewer_email TEXT,
            interviewer_name TEXT,
            location TEXT,
            meeting_link TEXT,
            status TEXT DEFAULT 'Scheduled',
            email_sent BOOLEAN DEFAULT FALSE,
            job_id INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        )
    """,

    'scorecard_tokens': """
        CREATE TABLE scorecard_tokens (
            id SERIAL PRIMARY KEY,
            interview_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            interviewer_email TEXT,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
        )
    """,

    'email_templates': """
        CREATE TABLE email_templates (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            stage TEXT,
            template_type TEXT
        )
    """,

    'email_log': """
        CREATE TABLE email_log (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER,
            recipient TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            sent_at TIMESTAMP DEFAULT NOW(),
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """,

    'email_queue': """
        CREATE TABLE email_queue (
            id SERIAL PRIMARY KEY,
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
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE SET NULL
        )
    """,

    'email_automation_rules': """
        CREATE TABLE email_automation_rules (
            id SERIAL PRIMARY KEY,
            job_id INTEGER,
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            template_id INTEGER NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            delay_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE CASCADE
        )
    """,

    'notification_webhooks': """
        CREATE TABLE notification_webhooks (
            id SERIAL PRIMARY KEY,
            platform TEXT NOT NULL CHECK(platform IN ('slack', 'teams')),
            webhook_url TEXT NOT NULL,
            channel_name TEXT,
            job_id INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            last_success TIMESTAMP,
            last_failure TIMESTAMP,
            failure_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
        )
    """,

    'notification_settings': """
        CREATE TABLE notification_settings (
            id SERIAL PRIMARY KEY,
            webhook_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (webhook_id) REFERENCES notification_webhooks(id) ON DELETE CASCADE,
            UNIQUE(webhook_id, event_type)
        )
    """,

    'notification_log': """
        CREATE TABLE notification_log (
            id SERIAL PRIMARY KEY,
            webhook_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (webhook_id) REFERENCES notification_webhooks(id) ON DELETE CASCADE
        )
    """,

    'contracts': """
        CREATE TABLE contracts (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            job_id INTEGER,
            start_date DATE,
            end_date DATE,
            hourly_rate DOUBLE PRECISION,
            status TEXT DEFAULT 'active',
            extension_of INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
            FOREIGN KEY (extension_of) REFERENCES contracts(id) ON DELETE SET NULL
        )
    """,

    'compliance_documents': """
        CREATE TABLE compliance_documents (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            received_date DATE,
            expiry_date DATE,
            file_path TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        )
    """,

    'users': """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,

    'job_owners': """
        CREATE TABLE job_owners (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'hiring_manager',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(job_id, user_id)
        )
    """,

    'saved_questions': """
        CREATE TABLE saved_questions (
            id SERIAL PRIMARY KEY,
            job_id INTEGER,
            stage TEXT,
            question TEXT NOT NULL,
            category TEXT,
            probing_area TEXT,
            is_standard BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """,

    'calendar_integrations': """
        CREATE TABLE calendar_integrations (
            id SERIAL PRIMARY KEY,
            provider TEXT NOT NULL,
            calendar_id TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,

    'calendar_events': """
        CREATE TABLE calendar_events (
            id SERIAL PRIMARY KEY,
            interview_id INTEGER NOT NULL,
            integration_id INTEGER,
            external_event_id TEXT,
            ics_uid TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
            FOREIGN KEY (integration_id) REFERENCES calendar_integrations(id) ON DELETE SET NULL
        )
    """,
}


# PostgreSQL indexes matching SQLite schema
POSTGRES_INDEXES = [
    'CREATE INDEX idx_candidates_job ON candidates(job_id)',
    'CREATE INDEX idx_candidates_vendor ON candidates(vendor_id)',
    'CREATE INDEX idx_candidates_stage ON candidates(current_stage)',
    'CREATE INDEX idx_stage_scores_candidate ON stage_scores(candidate_id)',
    'CREATE INDEX idx_interviews_candidate ON interviews(candidate_id)',
    'CREATE INDEX idx_scorecard_tokens_token ON scorecard_tokens(token)',
    'CREATE INDEX idx_scorecard_tokens_interview ON scorecard_tokens(interview_id)',
    'CREATE INDEX idx_candidate_jobs_candidate ON candidate_jobs(candidate_id)',
    'CREATE INDEX idx_candidate_jobs_job ON candidate_jobs(job_id)',
    'CREATE INDEX idx_candidate_jobs_stage ON candidate_jobs(current_stage)',
    'CREATE INDEX idx_notification_webhooks_job ON notification_webhooks(job_id)',
    'CREATE INDEX idx_notification_log_webhook ON notification_log(webhook_id)',
    'CREATE INDEX idx_notification_log_sent ON notification_log(sent_at)',
    'CREATE INDEX idx_contracts_candidate ON contracts(candidate_id)',
    'CREATE INDEX idx_contracts_status ON contracts(status)',
    'CREATE INDEX idx_contracts_end_date ON contracts(end_date)',
    'CREATE INDEX idx_compliance_documents_candidate ON compliance_documents(candidate_id)',
    'CREATE INDEX idx_compliance_documents_status ON compliance_documents(status)',
    'CREATE INDEX idx_compliance_documents_expiry ON compliance_documents(expiry_date)',
    'CREATE INDEX idx_candidates_status_stage ON candidates(status, current_stage)',
    'CREATE INDEX idx_candidates_job_status ON candidates(job_id, status)',
    'CREATE INDEX idx_candidate_jobs_status_stage ON candidate_jobs(status, current_stage)',
    'CREATE INDEX idx_interviews_status_time ON interviews(status, scheduled_time)',
    'CREATE INDEX idx_stage_scores_candidate_stage ON stage_scores(candidate_id, stage)',
    'CREATE INDEX idx_stage_notes_candidate_stage ON stage_notes(candidate_id, stage)',
    'CREATE INDEX idx_email_queue_status_scheduled ON email_queue(status, scheduled_at)',
    'CREATE INDEX idx_contracts_candidate_status ON contracts(candidate_id, status)',
    'CREATE INDEX idx_compliance_documents_candidate_type ON compliance_documents(candidate_id, doc_type)',
    'CREATE INDEX idx_contractor_roles_active ON contractor_roles(is_active)',
    'CREATE INDEX idx_users_email ON users(email)',
    'CREATE INDEX idx_users_role ON users(role)',
    'CREATE INDEX idx_job_owners_job ON job_owners(job_id)',
    'CREATE INDEX idx_job_owners_user ON job_owners(user_id)',
    'CREATE INDEX idx_saved_questions_job ON saved_questions(job_id)',
    'CREATE INDEX idx_saved_questions_stage ON saved_questions(stage)',
    'CREATE INDEX idx_saved_questions_category ON saved_questions(category)',
    'CREATE INDEX idx_calendar_events_interview ON calendar_events(interview_id)',
    'CREATE INDEX idx_calendar_events_ics_uid ON calendar_events(ics_uid)',
    'CREATE INDEX idx_email_automation_rules_job ON email_automation_rules(job_id)',
    'CREATE INDEX idx_email_automation_rules_stages ON email_automation_rules(from_stage, to_stage)',
    'CREATE INDEX idx_email_queue_status ON email_queue(status)',
    'CREATE INDEX idx_email_queue_scheduled ON email_queue(scheduled_at)',
    'CREATE INDEX idx_email_queue_candidate ON email_queue(candidate_id)',
]


class MigrationLogger:
    """Simple logger for migration operations"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def info(self, message: str):
        if self.verbose:
            print(f"[INFO] {message}")

    def success(self, message: str):
        if self.verbose:
            print(f"[SUCCESS] {message}")

    def warning(self, message: str):
        print(f"[WARNING] {message}")

    def error(self, message: str):
        print(f"[ERROR] {message}", file=sys.stderr)


class PostgreSQLMigrator:
    """Handles SQLite to PostgreSQL migration"""

    def __init__(
        self,
        sqlite_path: str,
        postgres_url: str,
        dry_run: bool = False,
        drop_existing: bool = False,
        logger: Optional[MigrationLogger] = None
    ):
        self.sqlite_path = Path(sqlite_path)
        self.postgres_url = postgres_url
        self.dry_run = dry_run
        self.drop_existing = drop_existing
        self.logger = logger or MigrationLogger()

        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.pg_conn: Optional[Any] = None

    def connect(self):
        """Establish connections to both databases"""
        self.logger.info("Connecting to SQLite database...")
        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

        self.sqlite_conn = sqlite3.connect(str(self.sqlite_path))
        self.sqlite_conn.row_factory = sqlite3.Row
        self.logger.success(f"Connected to SQLite: {self.sqlite_path}")

        if not self.dry_run:
            self.logger.info("Connecting to PostgreSQL database...")
            self.pg_conn = psycopg2.connect(self.postgres_url)
            self.logger.success("Connected to PostgreSQL")

    def disconnect(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            self.logger.info("Disconnected from SQLite")

        if self.pg_conn:
            self.pg_conn.close()
            self.logger.info("Disconnected from PostgreSQL")

    def drop_tables(self):
        """Drop all existing PostgreSQL tables"""
        if self.dry_run:
            self.logger.info("[DRY RUN] Would drop all existing tables")
            return

        self.logger.info("Dropping existing PostgreSQL tables...")
        cursor = self.pg_conn.cursor()

        # Reverse order for safe deletion
        for table in reversed(TABLE_ORDER):
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                self.logger.info(f"Dropped table: {table}")
            except Exception as e:
                self.logger.warning(f"Could not drop table {table}: {e}")

        self.pg_conn.commit()
        cursor.close()
        self.logger.success("Dropped all existing tables")

    def create_schema(self):
        """Create PostgreSQL schema"""
        if self.dry_run:
            self.logger.info("[DRY RUN] Would create PostgreSQL schema")
            for table in TABLE_ORDER:
                self.logger.info(f"[DRY RUN] Would create table: {table}")
            return

        self.logger.info("Creating PostgreSQL schema...")
        cursor = self.pg_conn.cursor()

        for table in TABLE_ORDER:
            if table not in POSTGRES_SCHEMAS:
                self.logger.warning(f"No schema definition for table: {table}")
                continue

            try:
                cursor.execute(POSTGRES_SCHEMAS[table])
                self.logger.success(f"Created table: {table}")
            except Exception as e:
                self.logger.error(f"Failed to create table {table}: {e}")
                raise

        self.pg_conn.commit()
        cursor.close()
        self.logger.success("Created all tables")

    def create_indexes(self):
        """Create PostgreSQL indexes"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create {len(POSTGRES_INDEXES)} indexes")
            return

        self.logger.info(f"Creating {len(POSTGRES_INDEXES)} indexes...")
        cursor = self.pg_conn.cursor()

        for idx, index_sql in enumerate(POSTGRES_INDEXES, 1):
            try:
                cursor.execute(index_sql)
                if idx % 10 == 0:
                    self.logger.info(f"Created {idx}/{len(POSTGRES_INDEXES)} indexes")
            except Exception as e:
                self.logger.warning(f"Failed to create index: {e}")

        self.pg_conn.commit()
        cursor.close()
        self.logger.success(f"Created all indexes")

    def get_table_columns(self, table: str) -> List[str]:
        """Get column names from SQLite table"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'id']
        cursor.close()
        return columns

    def convert_value(self, value: Any, column: str, table: str) -> Any:
        """Convert SQLite value to PostgreSQL-compatible value"""
        if value is None:
            return None

        # Convert SQLite INTEGER booleans to PostgreSQL BOOLEAN
        boolean_columns = {
            'is_active', 'is_primary', 'email_sent', 'is_enabled',
            'is_past_contractor', 'rehire_eligible', 'is_standard'
        }

        if column in boolean_columns:
            return bool(value)

        return value

    def migrate_table_data(self, table: str):
        """Migrate data from SQLite table to PostgreSQL"""
        # Check if table exists in SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if not cursor.fetchone():
            self.logger.warning(f"Table {table} does not exist in SQLite, skipping")
            cursor.close()
            return
        cursor.close()

        # Get row count
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total_rows = cursor.fetchone()[0]
        cursor.close()

        if total_rows == 0:
            self.logger.info(f"Table {table}: 0 rows, skipping")
            return

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would migrate {total_rows} rows from {table}")
            return

        self.logger.info(f"Migrating {total_rows} rows from {table}...")

        # Get columns (excluding id which is auto-generated)
        columns = self.get_table_columns(table)

        # Read all rows from SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        cursor.close()

        # Batch insert into PostgreSQL
        pg_cursor = self.pg_conn.cursor()
        batch_size = 100
        migrated = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]

            for row in batch:
                row_dict = dict(row)

                # Prepare values (excluding id)
                values = []
                for col in columns:
                    val = row_dict.get(col)
                    converted_val = self.convert_value(val, col, table)
                    values.append(converted_val)

                # Build INSERT statement
                cols_str = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"

                try:
                    pg_cursor.execute(insert_sql, values)
                    migrated += 1
                except Exception as e:
                    self.logger.error(f"Failed to insert row {migrated + 1} in {table}: {e}")
                    self.logger.error(f"Values: {values}")
                    raise

            # Commit batch
            self.pg_conn.commit()

            if migrated % 100 == 0 or migrated == total_rows:
                self.logger.info(f"  Migrated {migrated}/{total_rows} rows from {table}")

        pg_cursor.close()

        # Reset sequence to match max ID
        self.reset_sequence(table)

        self.logger.success(f"Migrated {migrated} rows from {table}")

    def reset_sequence(self, table: str):
        """Reset PostgreSQL sequence to match max ID from SQLite"""
        if self.dry_run:
            return

        cursor = self.pg_conn.cursor()

        try:
            # Get max ID from PostgreSQL table
            cursor.execute(f"SELECT MAX(id) FROM {table}")
            max_id = cursor.fetchone()[0]

            if max_id is not None:
                # Reset sequence
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), %s, true)",
                    (max_id,)
                )
                self.logger.info(f"Reset sequence for {table} to {max_id}")
        except Exception as e:
            self.logger.warning(f"Could not reset sequence for {table}: {e}")

        cursor.close()

    def verify_migration(self):
        """Verify data integrity after migration"""
        if self.dry_run:
            self.logger.info("[DRY RUN] Would verify migration")
            return

        self.logger.info("Verifying migration...")

        all_match = True

        for table in TABLE_ORDER:
            # Check if table exists in SQLite
            cursor = self.sqlite_conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor.fetchone():
                cursor.close()
                continue
            cursor.close()

            # Get row counts
            sqlite_cursor = self.sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sqlite_cursor.fetchone()[0]
            sqlite_cursor.close()

            pg_cursor = self.pg_conn.cursor()
            pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = pg_cursor.fetchone()[0]
            pg_cursor.close()

            if sqlite_count == pg_count:
                self.logger.success(f"{table}: {sqlite_count} rows (match)")
            else:
                self.logger.error(
                    f"{table}: SQLite={sqlite_count}, PostgreSQL={pg_count} (MISMATCH)"
                )
                all_match = False

        if all_match:
            self.logger.success("All table row counts match!")
        else:
            self.logger.error("Some tables have mismatched row counts")
            return False

        return True

    def run(self, verify: bool = False):
        """Execute the full migration process"""
        try:
            self.connect()

            if self.drop_existing:
                self.drop_tables()

            self.create_schema()

            if not self.dry_run:
                # Begin transaction
                cursor = self.pg_conn.cursor()
                cursor.execute("BEGIN")
                cursor.close()

            # Migrate data for each table in dependency order
            for table in TABLE_ORDER:
                self.migrate_table_data(table)

            if not self.dry_run:
                # Commit transaction
                self.pg_conn.commit()
                self.logger.success("All data committed to PostgreSQL")

            self.create_indexes()

            if verify and not self.dry_run:
                verification_passed = self.verify_migration()
                if not verification_passed:
                    self.logger.error("Verification failed")
                    return False

            if self.dry_run:
                self.logger.success("Dry run completed successfully")
            else:
                self.logger.success("Migration completed successfully!")

            return True

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            if self.pg_conn and not self.dry_run:
                self.pg_conn.rollback()
                self.logger.info("Rolled back PostgreSQL transaction")
            raise

        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='Migrate ATS database from SQLite to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  %(prog)s --dry-run --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  %(prog)s --verify --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
  %(prog)s --drop-existing --postgres-url "postgresql://user:pass@localhost:5432/ats_db"
        """
    )

    parser.add_argument(
        '--sqlite-path',
        default='ats_data.db',
        help='Path to SQLite database file (default: ats_data.db)'
    )

    parser.add_argument(
        '--postgres-url',
        required=True,
        help='PostgreSQL connection URL (e.g., postgresql://user:pass@localhost:5432/dbname)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without executing'
    )

    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing PostgreSQL tables before migration'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify data integrity after migration'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )

    args = parser.parse_args()

    # Create logger
    logger = MigrationLogger(verbose=not args.quiet)

    # Create migrator
    migrator = PostgreSQLMigrator(
        sqlite_path=args.sqlite_path,
        postgres_url=args.postgres_url,
        dry_run=args.dry_run,
        drop_existing=args.drop_existing,
        logger=logger
    )

    # Run migration
    try:
        success = migrator.run(verify=args.verify)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Migration failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
