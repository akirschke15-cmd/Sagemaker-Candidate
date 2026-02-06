# ATS Application Test Suite

This directory contains the comprehensive test suite for the ATS (Applicant Tracking System) application.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests (70% of test pyramid)
│   ├── test_auth.py     # Authentication and RBAC tests
│   ├── test_scoring.py  # AI scoring and analysis tests
│   └── test_resume_parser.py  # File parsing tests
└── integration/          # Integration tests (20% of test pyramid)
    └── test_database.py # Database CRUD operation tests
```

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# From ats_app directory
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=ats_app --cov-report=term-missing --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_auth.py

# Specific test class
pytest tests/unit/test_auth.py::TestPasswordHashing

# Specific test function
pytest tests/unit/test_auth.py::TestPasswordHashing::test_hash_password_returns_non_empty_string
```

### Run Tests with Markers

```bash
# Run only authentication tests
pytest -m auth

# Run only database tests
pytest -m database

# Run everything except slow tests
pytest -m "not slow"
```

## Test Coverage

### Unit Tests (tests/unit/)

#### test_auth.py (48 tests)
- Password hashing (bcrypt and PBKDF2 fallback)
- Password verification
- Password strength validation
- Session management and expiry
- Permission checking (RBAC)
- Role-based access control
- Helper functions

**Coverage:**
- `hash_password()` - Complete
- `verify_password()` - Complete with edge cases
- `validate_password_strength()` - All validation rules
- `check_session_expired()` - All scenarios
- `check_permission()` - All roles and resources
- Role helper functions

#### test_resume_parser.py (30+ tests)
- File size validation
- Text cleaning and normalization
- File format support (PDF, DOCX, TXT)
- File save and retrieval
- Path sanitization (security)
- Error handling

**Coverage:**
- `validate_file_size()` - All edge cases
- `clean_extracted_text()` - Text normalization
- `parse_resume()` - All supported formats
- `parse_txt()` - Multiple encodings
- `save_resume_file()` - File operations
- `get_resume_file()` - Retrieval
- `delete_resume_file()` - Cleanup

#### test_scoring.py (25+ tests)
- AI client initialization
- Resume scoring against job descriptions
- Mock scoring (fallback)
- Interview note summarization
- Interview question generation
- Candidate comparison
- JSON parsing from AI responses
- Error handling

**Coverage:**
- `smart_score_resume()` - With and without AI
- `score_resume_against_jd()` - JSON parsing
- `mock_score_resume()` - Keyword matching
- `smart_summarize_notes()` - Summarization
- `generate_interview_questions()` - Stage-specific
- `compare_candidates()` - Multi-candidate analysis

### Integration Tests (tests/integration/)

#### test_database.py (35+ tests)
- Database initialization and schema
- Vendor CRUD operations
- Job CRUD operations
- Candidate CRUD operations
- Candidate filtering and search
- SQL injection protection
- Scoring criteria management
- Stage progression
- Interview scheduling
- Multi-role matching (candidate_jobs)
- User management (RBAC)
- Contract lifecycle
- Foreign key constraints
- Cascade delete operations

**Coverage:**
- All CRUD operations with REAL database
- Foreign key relationships
- Data integrity constraints
- Index creation
- Transaction handling

## Test Fixtures

### conftest.py Fixtures

- `test_db` - Temporary SQLite database for each test
- `db_connection` - Database connection with automatic cleanup
- `mock_anthropic` - Mocked Anthropic API client
- `mock_anthropic_client` - Patched AI client for testing
- `sample_candidate` - Sample candidate data
- `sample_job` - Sample job data
- `sample_vendor` - Sample vendor data
- `sample_user` - Sample user data
- `sample_resume_text` - Sample resume text
- `temp_upload_dir` - Temporary upload directory

## Test Philosophy

### Testing Pyramid

- **70% Unit Tests**: Fast, isolated tests of individual functions
- **20% Integration Tests**: Real database operations, API integrations
- **10% E2E Tests**: (Future) Full user workflow tests with Streamlit

### Integration Testing Principles

✅ **DO:**
- Test against REAL SQLite database (using Testcontainers pattern)
- Test actual SQL operations and constraints
- Test foreign key relationships
- Test data integrity

❌ **DON'T:**
- Create mock database implementations
- Skip SQL constraint testing
- Test only happy paths

### Mock Usage Guidelines

✅ **Mock external services:**
- Anthropic API (third-party, costly)
- AWS Bedrock (third-party, AWS account required)
- Email services (external)

❌ **Never mock your own services:**
- Database operations
- File system operations
- Business logic

## Writing New Tests

### Unit Test Template

```python
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import module_to_test


class TestFeatureName:
    """Test description"""

    def test_function_returns_expected_value(self):
        """function should return expected value for valid input"""
        result = module_to_test.function(valid_input)

        assert result == expected_value
        assert isinstance(result, expected_type)

    def test_function_handles_edge_case(self):
        """function should handle edge case gracefully"""
        result = module_to_test.function(edge_case_input)

        assert result is not None
```

### Integration Test Template

```python
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import database


class TestDatabaseFeature:
    """Test database operations"""

    def test_create_and_retrieve(self, test_db):
        """Should create and retrieve entity"""
        entity_id = database.create_entity(name="Test")

        retrieved = database.get_entity(entity_id)

        assert retrieved is not None
        assert retrieved['id'] == entity_id
        assert retrieved['name'] == "Test"
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest --cov=ats_app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running pytest from the `ats_app` directory:

```bash
cd ats_app
pytest
```

### Database Locked Errors

If you see "database is locked" errors, ensure:
- No other processes are accessing the test database
- Tests are properly cleaning up connections
- Use the `db_connection` fixture for proper cleanup

### Mock Not Working

If mocks aren't being applied:
- Check that patches are in the correct scope
- Verify import paths match actual module structure
- Use `mock_anthropic_client` fixture for AI tests

## Test Metrics

Current test statistics:
- **Total Tests**: 100+
- **Unit Tests**: ~75
- **Integration Tests**: ~35
- **Execution Time**: ~5-10 seconds (unit), ~10-15 seconds (integration)
- **Target Coverage**: 70%+ overall

## Future Enhancements

- [ ] Add E2E tests with Streamlit UI testing
- [ ] Add performance benchmarking tests
- [ ] Add security testing (OWASP top 10)
- [ ] Add load testing for database operations
- [ ] Add mutation testing with mutmut
- [ ] Add contract testing for API endpoints
