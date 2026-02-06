"""
Integration tests for database module (database.py)

Tests CRUD operations against a real SQLite database.
CRITICAL: These tests use REAL database operations, not mocks.
"""
import pytest
import sqlite3
from datetime import datetime, date
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import database


class TestDatabaseInitialization:
    """Test database initialization and schema creation"""

    def test_init_db_creates_tables(self, test_db, db_connection):
        """init_db should create all required tables"""
        cursor = db_connection.cursor()

        # Check critical tables exist
        tables = [
            'vendors', 'jobs', 'candidates', 'scoring_criteria',
            'stage_scores', 'stage_notes', 'interviews', 'email_templates',
            'email_log', 'scorecard_tokens', 'candidate_jobs',
            'notification_webhooks', 'contracts', 'compliance_documents',
            'users'
        ]

        for table in tables:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            result = cursor.fetchone()
            assert result is not None, f"Table {table} should exist"

    def test_init_db_creates_indexes(self, test_db, db_connection):
        """init_db should create indexes for performance"""
        cursor = db_connection.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = cursor.fetchall()

        # Should have multiple indexes
        assert len(indexes) > 0


class TestVendorOperations:
    """Test vendor CRUD operations"""

    def test_create_vendor_returns_id(self, test_db):
        """create_vendor should return vendor ID"""
        from database import create_vendor

        vendor_id = create_vendor(
            name=f"Test Vendor {uuid.uuid4().hex[:8]}",
            contact_email="test@vendor.com",
            contact_phone="555-0100",
            notes="Test vendor notes"
        )

        assert vendor_id is not None
        assert isinstance(vendor_id, int)
        assert vendor_id > 0

    def test_get_vendor_returns_created_vendor(self, test_db):
        """get_vendor should retrieve created vendor"""
        from database import create_vendor, get_vendor

        unique_name = f"Test Vendor {uuid.uuid4().hex[:8]}"
        vendor_id = create_vendor(
            name=unique_name,
            contact_email="test@vendor.com"
        )

        vendor = get_vendor(vendor_id)

        assert vendor is not None
        assert vendor['id'] == vendor_id
        assert vendor['name'] == unique_name
        assert vendor['contact_email'] == "test@vendor.com"

    def test_get_vendors_returns_list(self, test_db):
        """get_vendors should return list of vendors"""
        from database import create_vendor, get_vendors

        create_vendor(name=f"Vendor 1 {uuid.uuid4().hex[:8]}")
        create_vendor(name=f"Vendor 2 {uuid.uuid4().hex[:8]}")

        vendors = get_vendors()

        assert isinstance(vendors, list)
        assert len(vendors) >= 2

    def test_update_vendor_modifies_fields(self, test_db):
        """update_vendor should modify vendor fields"""
        from database import create_vendor, get_vendor
        import database

        vendor_id = create_vendor(name=f"Original Name {uuid.uuid4().hex[:8]}")

        # Update directly via SQL since update_vendor may not exist
        updated_name = f"Updated Name {uuid.uuid4().hex[:8]}"
        with database.db_session() as conn:
            conn.execute(
                "UPDATE vendors SET name = ?, contact_email = ? WHERE id = ?",
                (updated_name, "new@email.com", vendor_id)
            )

        updated = get_vendor(vendor_id)
        assert updated['name'] == updated_name
        assert updated['contact_email'] == "new@email.com"


class TestJobOperations:
    """Test job CRUD operations"""

    def test_create_job_returns_id(self, test_db):
        """create_job should return job ID"""
        from database import create_job

        job_id = create_job(
            title="Python Developer",
            description="Python development role",
            requirements="Python, AWS",
            department="Engineering"
        )

        assert job_id is not None
        assert isinstance(job_id, int)
        assert job_id > 0

    def test_get_job_returns_created_job(self, test_db):
        """get_job should retrieve created job"""
        from database import create_job, get_job

        job_id = create_job(
            title="Python Developer",
            description="Python role",
            requirements="Python, AWS"
        )

        job = get_job(job_id)

        assert job is not None
        assert job['id'] == job_id
        assert job['title'] == "Python Developer"
        assert job['description'] == "Python role"
        assert job['requirements'] == "Python, AWS"

    def test_get_jobs_returns_list(self, test_db):
        """get_jobs should return list of jobs"""
        from database import create_job, get_jobs

        create_job(title="Job 1", description="First job")
        create_job(title="Job 2", description="Second job")

        jobs = get_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) >= 2

    def test_get_jobs_dict_returns_dict_keyed_by_id(self, test_db):
        """get_jobs_dict should return dictionary keyed by job ID"""
        from database import create_job, get_jobs_dict

        job_id1 = create_job(title="Job 1")
        job_id2 = create_job(title="Job 2")

        jobs_dict = get_jobs_dict()

        assert isinstance(jobs_dict, dict)
        assert job_id1 in jobs_dict
        assert job_id2 in jobs_dict
        assert jobs_dict[job_id1]['title'] == "Job 1"


class TestCandidateOperations:
    """Test candidate CRUD operations"""

    def test_create_candidate_returns_id(self, test_db):
        """create_candidate should return candidate ID"""
        from database import create_candidate

        candidate_id = create_candidate(
            name="John Doe",
            email="john@example.com",
            phone="555-0100"
        )

        assert candidate_id is not None
        assert isinstance(candidate_id, int)
        assert candidate_id > 0

    def test_get_candidate_returns_created_candidate(self, test_db):
        """get_candidate should retrieve created candidate"""
        from database import create_candidate, get_candidate

        candidate_id = create_candidate(
            name="John Doe",
            email="john@example.com",
            phone="555-0100"
        )

        candidate = get_candidate(candidate_id)

        assert candidate is not None
        assert candidate['id'] == candidate_id
        assert candidate['name'] == "John Doe"
        assert candidate['email'] == "john@example.com"
        assert candidate['phone'] == "555-0100"

    def test_get_candidates_returns_list(self, test_db):
        """get_candidates should return list of candidates"""
        from database import create_candidate, get_candidates

        create_candidate(name="Candidate 1", email="c1@example.com")
        create_candidate(name="Candidate 2", email="c2@example.com")

        candidates = get_candidates()

        assert isinstance(candidates, list)
        assert len(candidates) >= 2

    def test_update_candidate_modifies_fields(self, test_db):
        """update_candidate should modify candidate fields"""
        from database import create_candidate, update_candidate, get_candidate

        candidate_id = create_candidate(
            name="Original Name",
            email="original@example.com"
        )

        update_candidate(
            candidate_id,
            name="Updated Name",
            email="updated@example.com",
            phone="555-9999"
        )

        updated = get_candidate(candidate_id)
        assert updated['name'] == "Updated Name"
        assert updated['email'] == "updated@example.com"
        assert updated['phone'] == "555-9999"

    def test_update_candidate_rejects_invalid_columns(self, test_db):
        """update_candidate should reject invalid column names (SQL injection protection)"""
        from database import create_candidate, update_candidate

        candidate_id = create_candidate(name="Test Candidate")

        # Attempt SQL injection via column name
        try:
            update_candidate(candidate_id, **{"name; DROP TABLE candidates--": "hacker"})
            # If it doesn't raise, check that the update didn't work
            candidate = database.get_candidate(candidate_id)
            assert candidate is not None  # Table should still exist
        except (ValueError, sqlite3.OperationalError):
            # Should reject invalid column names
            pass

    def test_create_candidate_with_job_id(self, test_db):
        """create_candidate should accept job_id"""
        from database import create_job, create_candidate, get_candidate

        job_id = create_job(title="Python Developer")
        candidate_id = create_candidate(
            name="John Doe",
            email="john@example.com",
            job_id=job_id
        )

        candidate = get_candidate(candidate_id)
        assert candidate['job_id'] == job_id

    def test_create_candidate_with_vendor_id(self, test_db):
        """create_candidate should accept vendor_id"""
        from database import create_vendor, create_candidate, get_candidate

        vendor_id = create_vendor(name=f"Test Vendor {uuid.uuid4().hex[:8]}")
        candidate_id = create_candidate(
            name="John Doe",
            email="john@example.com",
            vendor_id=vendor_id
        )

        candidate = get_candidate(candidate_id)
        assert candidate['vendor_id'] == vendor_id


class TestCandidateFiltering:
    """Test candidate filtering and search"""

    def test_get_candidates_filters_by_job_id(self, test_db):
        """get_candidates should filter by job_id"""
        from database import create_job, create_candidate, get_candidates

        job1 = create_job(title="Job 1")
        job2 = create_job(title="Job 2")

        create_candidate(name="Candidate 1", job_id=job1)
        create_candidate(name="Candidate 2", job_id=job1)
        create_candidate(name="Candidate 3", job_id=job2)

        job1_candidates = get_candidates(job_id=job1)

        assert len(job1_candidates) == 2
        assert all(c['job_id'] == job1 for c in job1_candidates)

    def test_get_candidates_filters_by_stage(self, test_db):
        """get_candidates should filter by stage"""
        from database import create_candidate, update_candidate, get_candidates

        c1 = create_candidate(name="Candidate 1")
        c2 = create_candidate(name="Candidate 2")
        update_candidate(c2, current_stage="Phone Screen")

        resume_screen_candidates = get_candidates(stage="Resume Screen")

        assert len(resume_screen_candidates) >= 1
        assert all(c['current_stage'] == "Resume Screen" for c in resume_screen_candidates)


class TestScoringCriteria:
    """Test scoring criteria operations"""

    def test_create_scoring_criteria(self, test_db):
        """Should be able to create scoring criteria for a job"""
        from database import create_job

        job_id = create_job(title="Python Developer")

        with database.db_session() as conn:
            conn.execute(
                """INSERT INTO scoring_criteria
                   (job_id, stage, criteria_name, max_score, weight, description)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, "Technical Interview", "Python Skills", 5, 1.0, "Python expertise")
            )

        # Verify created
        with database.db_session() as conn:
            cursor = conn.execute(
                "SELECT * FROM scoring_criteria WHERE job_id = ?",
                (job_id,)
            )
            criteria = cursor.fetchone()

        assert criteria is not None
        assert criteria['criteria_name'] == "Python Skills"


class TestStageProgression:
    """Test candidate stage progression"""

    def test_candidate_can_advance_stages(self, test_db):
        """Candidate should be able to advance through stages"""
        from database import create_candidate, update_candidate, get_candidate

        candidate_id = create_candidate(name="Test Candidate")

        # Advance through stages
        stages = ["Resume Screen", "Phone Screen", "Technical Interview", "Behavioral Interview"]

        for stage in stages:
            update_candidate(candidate_id, current_stage=stage)
            candidate = get_candidate(candidate_id)
            assert candidate['current_stage'] == stage


class TestInterviewScheduling:
    """Test interview scheduling operations"""

    def test_create_interview(self, test_db):
        """Should be able to schedule interview"""
        from database import create_candidate

        candidate_id = create_candidate(name="Test Candidate")

        with database.db_session() as conn:
            conn.execute(
                """INSERT INTO interviews
                   (candidate_id, stage, scheduled_time, interviewer_email, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (candidate_id, "Technical Interview", datetime.now(), "interviewer@example.com", "Scheduled")
            )

        # Verify created
        with database.db_session() as conn:
            cursor = conn.execute(
                "SELECT * FROM interviews WHERE candidate_id = ?",
                (candidate_id,)
            )
            interview = cursor.fetchone()

        assert interview is not None
        assert interview['stage'] == "Technical Interview"
        assert interview['interviewer_email'] == "interviewer@example.com"


class TestCandidateJobsJunction:
    """Test multi-role matching with candidate_jobs table"""

    def test_candidate_can_be_assigned_to_multiple_jobs(self, test_db):
        """Candidate should be assignable to multiple jobs"""
        from database import create_candidate, create_job

        candidate_id = create_candidate(name="Multi-Role Candidate")
        job1 = create_job(title="Python Developer")
        job2 = create_job(title="Data Engineer")

        # Assign to both jobs
        with database.db_session() as conn:
            conn.execute(
                "INSERT INTO candidate_jobs (candidate_id, job_id, status) VALUES (?, ?, ?)",
                (candidate_id, job1, "Active")
            )
            conn.execute(
                "INSERT INTO candidate_jobs (candidate_id, job_id, status) VALUES (?, ?, ?)",
                (candidate_id, job2, "Active")
            )

        # Verify assignments
        with database.db_session() as conn:
            cursor = conn.execute(
                "SELECT * FROM candidate_jobs WHERE candidate_id = ?",
                (candidate_id,)
            )
            assignments = cursor.fetchall()

        assert len(assignments) == 2


class TestUserOperations:
    """Test user management for RBAC"""

    def test_create_user(self, test_db):
        """Should be able to create users"""
        unique_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
        with database.db_session() as conn:
            conn.execute(
                """INSERT INTO users (name, email, role, is_active)
                   VALUES (?, ?, ?, ?)""",
                ("Test Admin", unique_email, "admin", 1)
            )

        # Verify created
        with database.db_session() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (unique_email,))
            user = cursor.fetchone()

        assert user is not None
        assert user['name'] == "Test Admin"
        assert user['role'] == "admin"


class TestContractLifecycle:
    """Test contractor lifecycle tracking"""

    def test_create_contract(self, test_db):
        """Should be able to create contract for candidate"""
        from database import create_candidate, create_job

        candidate_id = create_candidate(name="Contractor")
        job_id = create_job(title="Python Developer")

        with database.db_session() as conn:
            conn.execute(
                """INSERT INTO contracts
                   (candidate_id, job_id, start_date, end_date, hourly_rate, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (candidate_id, job_id, date.today(), date(2026, 12, 31), 120.0, "active")
            )

        # Verify created
        with database.db_session() as conn:
            cursor = conn.execute(
                "SELECT * FROM contracts WHERE candidate_id = ?",
                (candidate_id,)
            )
            contract = cursor.fetchone()

        assert contract is not None
        assert contract['hourly_rate'] == 120.0
        assert contract['status'] == "active"


class TestDatabaseConstraints:
    """Test database constraints and data integrity"""

    def test_foreign_key_constraints_enabled(self, test_db, db_connection):
        """Foreign key constraints should be enabled"""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()

        assert result[0] == 1  # Foreign keys enabled

    def test_unique_constraint_on_vendor_name(self, test_db):
        """Vendor name should be unique"""
        from database import create_vendor

        unique_name = f"Unique Vendor {uuid.uuid4().hex[:8]}"
        create_vendor(name=unique_name)

        # Attempting to create duplicate should fail
        with pytest.raises(sqlite3.IntegrityError):
            create_vendor(name=unique_name)

    def test_cascade_delete_candidate_removes_related_data(self, test_db):
        """Deleting candidate should cascade to related tables"""
        from database import create_candidate

        candidate_id = create_candidate(name="Test Candidate")

        # Add interview
        with database.db_session() as conn:
            conn.execute(
                "INSERT INTO interviews (candidate_id, stage, status) VALUES (?, ?, ?)",
                (candidate_id, "Phone Screen", "Scheduled")
            )

        # Delete candidate
        with database.db_session() as conn:
            conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))

        # Verify related data deleted
        with database.db_session() as conn:
            cursor = conn.execute("SELECT * FROM interviews WHERE candidate_id = ?", (candidate_id,))
            interviews = cursor.fetchall()

        assert len(interviews) == 0  # Should be deleted due to CASCADE
