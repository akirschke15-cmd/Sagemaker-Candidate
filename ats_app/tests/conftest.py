"""
Pytest configuration and shared fixtures for ATS test suite
"""
import pytest
import tempfile
import sqlite3
from pathlib import Path
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# Add ats_app to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ats_app'))


@pytest.fixture(scope='function')
def test_db(tmp_path, monkeypatch):
    """
    Create a temporary test database for each test.
    Patches the DB_PATH before importing database module.
    """
    test_db_path = tmp_path / "test_ats.db"

    # Patch DB_PATH before importing database
    import database
    original_path = database.DB_PATH
    monkeypatch.setattr(database, 'DB_PATH', test_db_path)

    # Initialize schema
    database.init_db()

    yield test_db_path

    # Restore original path
    monkeypatch.setattr(database, 'DB_PATH', original_path)


@pytest.fixture(scope='function')
def db_connection(test_db):
    """
    Provide a database connection for testing.
    """
    import database
    conn = database.get_connection()
    yield conn
    conn.close()


@pytest.fixture
def mock_anthropic():
    """
    Mock Anthropic API client for testing AI features.
    """
    mock_client = MagicMock()
    mock_response = Mock()
    mock_response.content = [Mock(
        text='{"score": 85, "analysis": "Strong candidate with relevant experience", '
             '"strengths": ["Python", "AWS", "AI/ML"], '
             '"gaps": ["Limited management experience"], '
             '"recommendation": "Advance to technical interview"}'
    )]
    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client(monkeypatch, mock_anthropic):
    """
    Patch the get_anthropic_client function to return mock client.
    """
    with patch('genai.get_anthropic_client', return_value=mock_anthropic):
        with patch('genai.ANTHROPIC_AVAILABLE', True):
            yield mock_anthropic


@pytest.fixture
def sample_candidate():
    """
    Sample candidate data for testing.
    """
    return {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '555-0100',
        'resume_text': 'Experienced Python developer with 5 years in AWS and AI/ML',
        'current_stage': 'Resume Screen',
        'status': 'Active'
    }


@pytest.fixture
def sample_job():
    """
    Sample job data for testing.
    """
    return {
        'title': 'Senior Python Developer',
        'description': 'We are seeking an experienced Python developer for our AI team',
        'requirements': 'Python, AWS, Machine Learning, API development',
        'department': 'Engineering',
        'status': 'Open',
        'slots': 2
    }


@pytest.fixture
def sample_vendor():
    """
    Sample vendor data for testing.
    """
    return {
        'name': 'Tech Recruiters Inc',
        'contact_email': 'contact@techrecruiters.com',
        'contact_phone': '555-0200',
        'notes': 'Reliable staffing partner'
    }


@pytest.fixture
def sample_user():
    """
    Sample user data for testing.
    """
    return {
        'name': 'Test Admin',
        'email': 'admin@example.com',
        'role': 'admin',
        'is_active': 1
    }


@pytest.fixture
def mock_session_state():
    """
    Mock Streamlit session state for auth testing.
    """
    class MockSessionState:
        def __init__(self):
            self.data = {}

        def __contains__(self, key):
            return key in self.data

        def __getattr__(self, key):
            return self.data.get(key)

        def __setattr__(self, key, value):
            if key == 'data':
                super().__setattr__(key, value)
            else:
                self.data[key] = value

    return MockSessionState()


@pytest.fixture
def sample_resume_text():
    """
    Sample resume text for parsing tests.
    """
    return """
John Doe
Senior Software Engineer
Email: john@example.com | Phone: 555-0100

EXPERIENCE
Senior Python Developer, Tech Corp (2020-Present)
- Developed microservices using Python and FastAPI
- Implemented ML models with scikit-learn and TensorFlow
- Managed AWS infrastructure with Terraform

Software Engineer, StartUp Inc (2018-2020)
- Built REST APIs with Flask
- Automated deployment pipelines
- Collaborated with cross-functional teams

EDUCATION
BS Computer Science, State University (2018)

SKILLS
Python, AWS, Docker, Kubernetes, Machine Learning, API Development
"""


@pytest.fixture
def sample_pdf_bytes():
    """
    Mock PDF file bytes for testing.
    """
    # Simple PDF header for testing file type detection
    return b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'


@pytest.fixture
def sample_docx_bytes():
    """
    Mock DOCX file bytes for testing.
    """
    # DOCX files are ZIP archives with specific structure
    # This is a minimal ZIP header
    return b'PK\x03\x04'


@pytest.fixture
def sample_txt_bytes():
    """
    Sample text file bytes for testing.
    """
    return b'This is a sample resume in plain text format.\n\nJohn Doe\nPython Developer'


@pytest.fixture
def temp_upload_dir(tmp_path, monkeypatch):
    """
    Create temporary upload directory for file testing.
    """
    upload_dir = tmp_path / "test_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Patch UPLOAD_DIR in resume_parser
    import resume_parser
    original_dir = resume_parser.UPLOAD_DIR
    monkeypatch.setattr(resume_parser, 'UPLOAD_DIR', upload_dir)

    yield upload_dir

    # Cleanup
    monkeypatch.setattr(resume_parser, 'UPLOAD_DIR', original_dir)
