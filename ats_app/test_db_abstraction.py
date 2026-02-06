#!/usr/bin/env python3
"""
Test script for database abstraction layer.
Tests both SQLite and PostgreSQL backends (if available).
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import from ats_app
sys.path.insert(0, str(Path(__file__).parent / "ats_app"))

from database.connection import (
    get_db_type,
    get_connection,
    db_session,
    adapt_query,
    init_db,
    migrate_db,
)


def test_sqlite():
    """Test SQLite backend."""
    print("=" * 60)
    print("Testing SQLite Backend")
    print("=" * 60)

    # Ensure we're using SQLite
    os.environ['DATABASE_URL'] = ''

    # Test get_db_type
    db_type = get_db_type()
    assert db_type == "sqlite", f"Expected 'sqlite', got '{db_type}'"
    print(f"[OK] Database type: {db_type}")

    # Test query adaptation (should be no-op for SQLite)
    original_query = "SELECT * FROM jobs WHERE id = ?"
    adapted_query = adapt_query(original_query, "sqlite")
    assert original_query == adapted_query, "SQLite query should not be modified"
    print(f"[OK] Query adaptation (no-op for SQLite)")

    # Test connection
    try:
        conn = get_connection()
        print(f"[OK] Connection created: {type(conn).__name__}")
        conn.close()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False

    # Test db_session context manager
    try:
        with db_session() as conn:
            # This should work even if tables don't exist yet
            pass
        print(f"[OK] db_session() context manager works")
    except Exception as e:
        print(f"[FAIL] db_session() failed: {e}")
        return False

    # Test init_db
    try:
        init_db()
        print(f"[OK] init_db() completed")
    except Exception as e:
        print(f"[FAIL] init_db() failed: {e}")
        return False

    # Test migrate_db
    try:
        migrate_db()
        print(f"[OK] migrate_db() completed")
    except Exception as e:
        print(f"[FAIL] migrate_db() failed: {e}")
        return False

    # Test basic CRUD operations
    try:
        with db_session() as conn:
            # Insert
            conn.execute(
                "INSERT INTO jobs (title, description, status) VALUES (?, ?, ?)",
                ("Test Engineer", "Test job description", "Open")
            )

            # Select
            result = conn.execute(
                "SELECT * FROM jobs WHERE title = ?",
                ("Test Engineer",)
            ).fetchone()

            assert result is not None, "Job not found after insert"
            assert result['title'] == "Test Engineer", "Job title mismatch"

            # Update
            conn.execute(
                "UPDATE jobs SET status = ? WHERE title = ?",
                ("Closed", "Test Engineer")
            )

            # Verify update
            updated = conn.execute(
                "SELECT status FROM jobs WHERE title = ?",
                ("Test Engineer",)
            ).fetchone()
            assert updated['status'] == "Closed", "Job status not updated"

            # Delete
            conn.execute("DELETE FROM jobs WHERE title = ?", ("Test Engineer",))

            # Verify delete
            deleted = conn.execute(
                "SELECT * FROM jobs WHERE title = ?",
                ("Test Engineer",)
            ).fetchone()
            assert deleted is None, "Job not deleted"

        print(f"[OK] CRUD operations work correctly")
    except Exception as e:
        print(f"[FAIL] CRUD operations failed: {e}")
        return False

    print("\n[OK] All SQLite tests passed!\n")
    return True


def test_postgresql():
    """Test PostgreSQL backend (if psycopg2 is available)."""
    print("=" * 60)
    print("Testing PostgreSQL Backend")
    print("=" * 60)

    # Check if psycopg2 is available
    try:
        import psycopg2
    except ImportError:
        print("[SKIP] psycopg2 not installed - skipping PostgreSQL tests")
        print("  Install with: pip install psycopg2-binary")
        return True

    # Set PostgreSQL connection (replace with your actual connection string)
    # For testing, you need a running PostgreSQL instance
    pg_url = os.environ.get('TEST_DATABASE_URL', '')

    if not pg_url:
        print("[SKIP] TEST_DATABASE_URL not set - skipping PostgreSQL tests")
        print("  Set TEST_DATABASE_URL environment variable to test PostgreSQL")
        print("  Example: export TEST_DATABASE_URL='postgresql://user:pass@localhost/test_ats'")
        return True

    os.environ['DATABASE_URL'] = pg_url

    # Test get_db_type
    db_type = get_db_type()
    assert db_type == "postgresql", f"Expected 'postgresql', got '{db_type}'"
    print(f"[OK] Database type: {db_type}")

    # Test query adaptation
    original_query = "SELECT * FROM jobs WHERE id = ?"
    adapted_query = adapt_query(original_query, "postgresql")
    expected = "SELECT * FROM jobs WHERE id = %s"
    assert adapted_query == expected, f"Expected '{expected}', got '{adapted_query}'"
    print(f"[OK] Query adaptation: ? → %s")

    # Test AUTOINCREMENT adaptation
    ddl_query = "CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT)"
    adapted_ddl = adapt_query(ddl_query, "postgresql")
    assert "SERIAL PRIMARY KEY" in adapted_ddl, "AUTOINCREMENT not converted to SERIAL"
    print(f"[OK] DDL adaptation: AUTOINCREMENT → SERIAL")

    # Test connection
    try:
        conn = get_connection()
        print(f"[OK] Connection created: {type(conn).__name__}")
        conn.close()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        print("  Make sure PostgreSQL is running and connection string is correct")
        return False

    # Test db_session context manager
    try:
        with db_session() as conn:
            pass
        print(f"[OK] db_session() context manager works")
    except Exception as e:
        print(f"[FAIL] db_session() failed: {e}")
        return False

    # Test init_db
    try:
        init_db()
        print(f"[OK] init_db() completed")
    except Exception as e:
        print(f"[FAIL] init_db() failed: {e}")
        return False

    # Test migrate_db
    try:
        migrate_db()
        print(f"[OK] migrate_db() completed")
    except Exception as e:
        print(f"[FAIL] migrate_db() failed: {e}")
        return False

    # Test basic CRUD operations with PostgreSQL
    try:
        with db_session() as conn:
            # Insert (using ? which will be adapted to %s)
            conn.execute(
                "INSERT INTO jobs (title, description, status) VALUES (?, ?, ?)",
                ("PG Test Engineer", "PostgreSQL test job", "Open")
            )

            # Select
            result = conn.execute(
                "SELECT * FROM jobs WHERE title = ?",
                ("PG Test Engineer",)
            ).fetchone()

            assert result is not None, "Job not found after insert"
            assert result['title'] == "PG Test Engineer", "Job title mismatch"

            # Update
            conn.execute(
                "UPDATE jobs SET status = ? WHERE title = ?",
                ("Closed", "PG Test Engineer")
            )

            # Verify update
            updated = conn.execute(
                "SELECT status FROM jobs WHERE title = ?",
                ("PG Test Engineer",)
            ).fetchone()
            assert updated['status'] == "Closed", "Job status not updated"

            # Delete
            conn.execute("DELETE FROM jobs WHERE title = ?", ("PG Test Engineer",))

            # Verify delete
            deleted = conn.execute(
                "SELECT * FROM jobs WHERE title = ?",
                ("PG Test Engineer",)
            ).fetchone()
            assert deleted is None, "Job not deleted"

        print(f"[OK] CRUD operations work correctly")
    except Exception as e:
        print(f"[FAIL] CRUD operations failed: {e}")
        return False

    print("\n[OK] All PostgreSQL tests passed!\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Database Abstraction Layer Test Suite")
    print("=" * 60 + "\n")

    results = []

    # Test SQLite
    results.append(("SQLite", test_sqlite()))

    # Test PostgreSQL (if available)
    results.append(("PostgreSQL", test_postgresql()))

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for backend, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{backend:20s} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print("\n[FAIL] Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
