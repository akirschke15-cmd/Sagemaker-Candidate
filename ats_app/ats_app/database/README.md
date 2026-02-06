# Database Abstraction Layer

This module provides a unified database abstraction layer that supports both SQLite and PostgreSQL backends.

## Features

- **Dual Backend Support**: Seamlessly switch between SQLite and PostgreSQL
- **Connection Pooling**: Automatic connection pooling for PostgreSQL
- **Query Adaptation**: Automatic conversion of SQLite queries to PostgreSQL-compatible syntax
- **Backward Compatible**: All existing code continues to work without modification

## Configuration

Configure the database backend via environment variables or `config.py`:

### SQLite (Default)

```python
# No DATABASE_URL or empty string uses SQLite
DATABASE_URL = ""
DB_PATH = "ats_data.db"
```

### PostgreSQL

```python
# Set DATABASE_URL to use PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost:5432/ats_db"
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
```

Or via environment variables:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/ats_db"
export DB_POOL_SIZE=5
export DB_MAX_OVERFLOW=10
export DB_POOL_TIMEOUT=30
```

## Installation

### SQLite
No additional dependencies required (built into Python).

### PostgreSQL
Install psycopg2:

```bash
pip install psycopg2-binary
```

## Usage

The API is identical regardless of the backend:

```python
from database import get_connection, db_session, get_db_type

# Check which database is being used
print(f"Using database: {get_db_type()}")  # "sqlite" or "postgresql"

# Use context manager (recommended)
with db_session() as conn:
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Software Engineer",))
    result = conn.execute("SELECT * FROM jobs WHERE id = ?", (1,))
    job = result.fetchone()
    print(job['title'])

# Or get a connection manually
conn = get_connection()
try:
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Data Scientist",))
    conn.commit()
except Exception:
    conn.rollback()
finally:
    conn.close()
```

## Query Compatibility

The abstraction layer automatically adapts SQLite queries for PostgreSQL:

### Parameter Placeholders

```python
# SQLite style (works with both backends)
conn.execute("SELECT * FROM jobs WHERE id = ?", (1,))

# Automatically converted to PostgreSQL:
# SELECT * FROM jobs WHERE id = %s
```

### Auto-increment Columns

```sql
-- SQLite style (works with both backends)
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
);

-- Automatically converted to PostgreSQL:
-- CREATE TABLE jobs (
--     id SERIAL PRIMARY KEY,
--     title TEXT NOT NULL
-- );
```

## Database-Specific Features

Some features are database-specific:

### SQLite
- WAL mode enabled by default
- Foreign keys enforced
- PRAGMA statements work only with SQLite

### PostgreSQL
- Connection pooling enabled
- Thread-safe connection handling
- Better concurrency support

## API Reference

### Functions

#### `get_db_type() -> str`
Returns the current database type: "sqlite" or "postgresql".

```python
db_type = get_db_type()
print(f"Using {db_type}")
```

#### `get_connection() -> ConnectionWrapper`
Get a database connection. Must be closed manually.

```python
conn = get_connection()
try:
    # Use connection
    conn.execute("SELECT * FROM jobs")
finally:
    conn.close()
```

#### `db_session() -> ContextManager[ConnectionWrapper]`
Context manager for database sessions. Auto-commits on success, auto-rolls back on error.

```python
with db_session() as conn:
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Engineer",))
    # Auto-committed here
```

#### `adapt_query(sql: str, db_type: str = None) -> str`
Manually adapt a SQL query for the target database type.

```python
sql = "SELECT * FROM jobs WHERE id = ?"
adapted = adapt_query(sql, "postgresql")
# Returns: "SELECT * FROM jobs WHERE id = %s"
```

#### `init_db()`
Initialize the database schema. Creates all tables and indexes.

```python
from database import init_db
init_db()
```

#### `migrate_db()`
Run database migrations. Safe to call multiple times.

```python
from database import migrate_db
migrate_db()
```

#### `explain_query(sql: str, params=None) -> list`
Analyze query performance (EXPLAIN QUERY PLAN for SQLite, EXPLAIN for PostgreSQL).

```python
from database import explain_query

plan = explain_query("SELECT * FROM jobs WHERE title = ?", ("Engineer",))
print(plan)
```

## Migration Guide

### Existing SQLite Applications

No code changes required! The abstraction layer is fully backward compatible:

1. Add PostgreSQL configuration to `config.py` or `.env`
2. Install `psycopg2-binary`
3. Set `DATABASE_URL` to your PostgreSQL connection string
4. Run `init_db()` to create schema in PostgreSQL
5. Migrate data (if needed)

### Query Compatibility Notes

Most SQLite queries work without modification. Exceptions:

- **PRAGMA statements**: SQLite-only, will be skipped on PostgreSQL
- **SQLite-specific functions**: Use standard SQL functions
- **BLOB types**: Use BYTEA in PostgreSQL DDL if creating new tables

### Connection Pooling

PostgreSQL connections are pooled automatically. Pool settings:

- `DB_POOL_SIZE`: Maximum number of connections (default: 5)
- `DB_MAX_OVERFLOW`: Additional connections when pool is full (default: 10)
- `DB_POOL_TIMEOUT`: Connection timeout in seconds (default: 30)

### Performance Considerations

#### SQLite
- Best for: Development, testing, small-scale deployments
- Single-writer limitation
- File-based (no network overhead)

#### PostgreSQL
- Best for: Production, multi-user, high concurrency
- Multiple writers supported
- Advanced features (JSON, full-text search, etc.)
- Requires separate database server

## Troubleshooting

### psycopg2 not found

```
RuntimeError: psycopg2 is not installed. Install it with: pip install psycopg2-binary
```

**Solution**: Install psycopg2:
```bash
pip install psycopg2-binary
```

### Connection pool exhausted

If you see timeout errors with PostgreSQL, increase pool size:

```python
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
```

### Query syntax errors

Most errors indicate database-specific SQL:

- Check for SQLite-specific functions
- Verify column types are compatible
- Use `adapt_query()` to preview adapted SQL

## Examples

### Switching Between Backends

```python
import os
from database import init_db, db_session, get_db_type

# Use SQLite
os.environ['DATABASE_URL'] = ''
init_db()
print(f"Created SQLite database: {get_db_type()}")

# Use PostgreSQL
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/ats'
init_db()
print(f"Created PostgreSQL database: {get_db_type()}")
```

### Transactions

```python
from database import db_session

with db_session() as conn:
    # Start transaction (automatic)
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Job 1",))
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Job 2",))
    # Both committed together
```

### Error Handling

```python
from database import db_session

try:
    with db_session() as conn:
        conn.execute("INSERT INTO jobs (title) VALUES (?)", ("New Job",))
        raise ValueError("Something went wrong")
except ValueError:
    print("Transaction rolled back automatically")
```

## Testing

Test your application with both backends:

```python
import pytest
from database import init_db, db_session, get_db_type

@pytest.fixture(params=['sqlite', 'postgresql'])
def db_backend(request):
    if request.param == 'sqlite':
        os.environ['DATABASE_URL'] = ''
    else:
        os.environ['DATABASE_URL'] = 'postgresql://localhost/test_db'

    init_db()
    yield request.param

def test_create_job(db_backend):
    with db_session() as conn:
        conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Test Job",))
        result = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
        assert result[0] > 0
```

## Best Practices

1. **Always use context managers**: Use `db_session()` instead of manual connection management
2. **Use parameterized queries**: Always use `?` placeholders, never string formatting
3. **Test with both backends**: Ensure compatibility before deploying
4. **Monitor connection pools**: Watch PostgreSQL connection pool usage in production
5. **Use transactions**: Wrap related operations in a single `db_session()` context

## Architecture

```
┌─────────────────────────────────────┐
│        Application Code             │
│  (Uses ? placeholders, standard SQL)│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│     Database Abstraction Layer      │
│  - get_connection()                 │
│  - db_session()                     │
│  - adapt_query()                    │
└─────────────────┬───────────────────┘
                  │
          ┌───────┴────────┐
          ▼                ▼
    ┌──────────┐    ┌──────────────┐
    │  SQLite  │    │  PostgreSQL  │
    │  (file)  │    │ (connection  │
    │          │    │    pool)     │
    └──────────┘    └──────────────┘
```

## License

Part of the ATS application.
