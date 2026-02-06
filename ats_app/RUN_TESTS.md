# Quick Test Reference Guide

## Setup (First Time Only)

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Run Tests

```bash
# Navigate to ats_app directory
cd C:\Users\Akirs\Sagemaker-Candidate\ats_app

# Run all tests (default)
pytest

# Run with detailed output
pytest -v

# Run with coverage report
pytest --cov=ats_app --cov-report=term-missing
```

## Test Categories

```bash
# Unit tests only (fast - 92 tests in ~5 seconds)
pytest tests/unit/

# Integration tests only (28 tests in ~8 seconds)
pytest tests/integration/

# Specific module tests
pytest tests/unit/test_auth.py          # 48 auth tests
pytest tests/unit/test_scoring.py       # 25 scoring tests
pytest tests/unit/test_resume_parser.py # 39 parser tests
pytest tests/integration/test_database.py # 28 database tests
```

## Expected Results

```
120 passed in 13.13s
```

## Test Files

| File | Tests | Focus Area |
|------|-------|------------|
| `tests/unit/test_auth.py` | 48 | Password hashing, RBAC, sessions |
| `tests/unit/test_resume_parser.py` | 39 | File parsing, validation |
| `tests/unit/test_scoring.py` | 25 | AI scoring, questions |
| `tests/integration/test_database.py` | 28 | Database CRUD operations |

## Common Issues

### Import Errors
```bash
# Ensure you're in the ats_app directory
cd C:\Users\Akirs\Sagemaker-Candidate\ats_app
```

### Database Locked
```bash
# Close any other processes accessing the database
# Tests use temporary databases to avoid conflicts
```

### Slow Test
```bash
# Skip slow tests if needed
pytest -m "not slow"
```

## Documentation

- Full documentation: `tests/README.md`
- Test summary: `TEST_SUMMARY.md`
- Configuration: `pytest.ini`
