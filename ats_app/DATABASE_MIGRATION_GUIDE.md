# Database Migration Guide: SQLite to PostgreSQL

This guide explains how to migrate the ATS application from SQLite to PostgreSQL using the new database abstraction layer.

## Overview

The ATS application now supports both SQLite and PostgreSQL through a unified database abstraction layer. This allows seamless switching between databases without code changes.

## Quick Start

### Continue Using SQLite (Default)

No changes needed! The application defaults to SQLite:

```bash
# .env file (or leave DATABASE_URL unset)
DATABASE_URL=""
DB_PATH="ats_data.db"
```

### Switch to PostgreSQL

1. **Install PostgreSQL driver**:
```bash
pip install psycopg2-binary
```

2. **Set connection string**:
```bash
# .env file
DATABASE_URL="postgresql://username:password@localhost:5432/ats_db"
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

3. **Create database**:
```bash
createdb ats_db
```

4. **Initialize schema**:
```python
python -c "from ats_app.database import init_db, migrate_db; init_db(); migrate_db()"
```

## Detailed Migration Steps

### Step 1: Install PostgreSQL

#### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### On macOS (with Homebrew):
```bash
brew install postgresql
brew services start postgresql
```

#### On Windows:
Download and install from https://www.postgresql.org/download/windows/

### Step 2: Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE ats_db;
CREATE USER ats_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ats_db TO ats_user;

# Exit psql
\q
```

### Step 3: Install Python Dependencies

```bash
pip install psycopg2-binary
```

### Step 4: Configure Application

Update your `.env` file or `config.py`:

```bash
# PostgreSQL connection string
DATABASE_URL="postgresql://ats_user:your_secure_password@localhost:5432/ats_db"

# Connection pool settings (optional, defaults shown)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### Step 5: Initialize Schema

Run the initialization script:

```python
from ats_app.database import init_db, migrate_db

# Create all tables
init_db()

# Run migrations
migrate_db()
```

Or use the CLI:

```bash
cd ats_app
python -c "from database import init_db, migrate_db; init_db(); migrate_db()"
```

### Step 6: Migrate Data (Optional)

If you have existing SQLite data to migrate:

#### Option A: Use a migration script

```python
import sqlite3
from database import db_session, get_db_type
import os

# Ensure we're targeting PostgreSQL
os.environ['DATABASE_URL'] = 'postgresql://ats_user:password@localhost/ats_db'

# Connect to SQLite
sqlite_conn = sqlite3.connect('ats_data.db')
sqlite_conn.row_factory = sqlite3.Row

# Get all tables
tables = sqlite_conn.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
""").fetchall()

# For each table, copy data
for table_row in tables:
    table = table_row['name']
    print(f"Migrating {table}...")

    # Get data from SQLite
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()

    if not rows:
        continue

    # Get column names
    columns = rows[0].keys()

    # Insert into PostgreSQL
    with db_session() as pg_conn:
        for row in rows:
            values = [row[col] for col in columns]
            placeholders = ', '.join(['?' for _ in columns])
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            try:
                pg_conn.execute(sql, values)
            except Exception as e:
                print(f"Error migrating row in {table}: {e}")

sqlite_conn.close()
print("Migration complete!")
```

#### Option B: Use pgloader

Install pgloader (Ubuntu):
```bash
sudo apt install pgloader
```

Create migration config `migrate.load`:
```
LOAD DATABASE
    FROM sqlite://./ats_data.db
    INTO postgresql://ats_user:password@localhost/ats_db

WITH include drop, create tables, create indexes, reset sequences

SET work_mem to '16MB', maintenance_work_mem to '512 MB';
```

Run migration:
```bash
pgloader migrate.load
```

### Step 7: Verify Migration

Test the application:

```python
from database import db_session, get_db_type

# Verify database type
print(f"Using database: {get_db_type()}")  # Should print "postgresql"

# Test query
with db_session() as conn:
    result = conn.execute("SELECT COUNT(*) as count FROM jobs").fetchone()
    print(f"Jobs in database: {result['count']}")
```

### Step 8: Update Application Startup

Ensure your application initializes the database on first run:

```python
# app.py or main.py
from database import init_db, migrate_db

# On application startup
init_db()  # Creates tables if they don't exist
migrate_db()  # Runs any pending migrations
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `""` | Database connection string. Empty = SQLite |
| `DB_PATH` | `"ats_data.db"` | SQLite database file path |
| `DB_POOL_SIZE` | `5` | PostgreSQL connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max connections beyond pool size |
| `DB_POOL_TIMEOUT` | `30` | Connection timeout in seconds |

### Connection String Formats

**SQLite**:
```
DATABASE_URL=""  # Empty string or not set
```

**PostgreSQL (local)**:
```
DATABASE_URL="postgresql://username:password@localhost:5432/dbname"
```

**PostgreSQL (remote)**:
```
DATABASE_URL="postgresql://user:pass@example.com:5432/ats_db"
```

**PostgreSQL (with SSL)**:
```
DATABASE_URL="postgresql://user:pass@example.com:5432/ats_db?sslmode=require"
```

## Code Compatibility

### No Changes Required

The abstraction layer handles these automatically:

```python
# This works with both SQLite and PostgreSQL
with db_session() as conn:
    # Parameter placeholders (? works for both)
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Engineer",))

    # Queries with placeholders
    result = conn.execute("SELECT * FROM jobs WHERE id = ?", (1,))

    # Row access (dict-like for both)
    job = result.fetchone()
    print(job['title'])
```

### Query Adaptations

The following are automatically converted:

| SQLite | PostgreSQL |
|--------|------------|
| `?` | `%s` |
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| `AUTOINCREMENT` | `SERIAL` |

### Database-Specific Code

If you need database-specific behavior:

```python
from database import get_db_type

db_type = get_db_type()

if db_type == "sqlite":
    # SQLite-specific code
    conn.execute("PRAGMA journal_mode=WAL")
elif db_type == "postgresql":
    # PostgreSQL-specific code
    conn.execute("SET work_mem = '64MB'")
```

## Performance Tuning

### SQLite

```python
# In config.py
DB_PATH = "ats_data.db"

# SQLite is automatically configured with:
# - WAL mode for better concurrency
# - Foreign keys enabled
```

### PostgreSQL

```python
# In .env or config.py
DB_POOL_SIZE=10  # Increase for high concurrency
DB_MAX_OVERFLOW=20  # Allow temporary connections
DB_POOL_TIMEOUT=60  # Increase timeout for slow queries

# PostgreSQL server tuning (postgresql.conf):
# max_connections = 100
# shared_buffers = 256MB
# effective_cache_size = 1GB
# work_mem = 4MB
```

## Monitoring

### Connection Pool (PostgreSQL)

Monitor pool usage:

```python
from database.connection import _pg_pool

if _pg_pool:
    print(f"Pool size: {_pg_pool.minconn} - {_pg_pool.maxconn}")
    # Note: psycopg2.pool doesn't expose current usage
    # Use PostgreSQL's pg_stat_activity for monitoring
```

### Query Performance

Use `explain_query()` to analyze slow queries:

```python
from database import explain_query

sql = "SELECT * FROM candidates WHERE status = ?"
plan = explain_query(sql, ("Active",))
print(plan)
```

## Troubleshooting

### Issue: "psycopg2 is not installed"

**Solution**:
```bash
pip install psycopg2-binary
```

### Issue: "Connection refused" (PostgreSQL)

**Solutions**:
1. Ensure PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Check connection settings in `postgresql.conf`:
   ```
   listen_addresses = 'localhost'
   port = 5432
   ```

3. Verify `pg_hba.conf` allows connections:
   ```
   local   all   all   trust
   host    all   all   127.0.0.1/32   md5
   ```

### Issue: "Pool exhausted" errors

**Solution**: Increase pool size:
```python
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

### Issue: Query syntax errors after migration

**Solutions**:
1. Check for SQLite-specific functions
2. Use `adapt_query()` to preview adapted SQL:
   ```python
   from database import adapt_query
   print(adapt_query("SELECT * FROM jobs WHERE id = ?", "postgresql"))
   ```

### Issue: "Row factory" or attribute access errors

**Solution**: Both backends support dict-like row access:
```python
result = conn.execute("SELECT * FROM jobs WHERE id = ?", (1,))
row = result.fetchone()

# Both of these work:
print(row['title'])  # Dict-style access
print(row[1])        # Index access
```

## Rollback to SQLite

To rollback from PostgreSQL to SQLite:

1. **Backup PostgreSQL data** (optional):
   ```bash
   pg_dump ats_db > ats_backup.sql
   ```

2. **Change configuration**:
   ```bash
   # .env
   DATABASE_URL=""
   ```

3. **Restart application**: The app will automatically use SQLite

4. **Migrate data back** (if needed):
   Use the migration script in reverse direction

## Testing Strategy

Test with both databases:

```python
import pytest
import os

@pytest.fixture(params=['sqlite', 'postgresql'])
def db(request):
    if request.param == 'postgresql':
        os.environ['DATABASE_URL'] = 'postgresql://localhost/test_ats'
    else:
        os.environ['DATABASE_URL'] = ''

    from database import init_db, migrate_db
    init_db()
    migrate_db()

    yield request.param

def test_jobs(db):
    from database import db_session

    with db_session() as conn:
        conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Test",))
        result = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
        assert result[0] > 0
```

## Production Deployment

### Recommended Setup

- **Development**: SQLite (simple, no server required)
- **Staging**: PostgreSQL (test production configuration)
- **Production**: PostgreSQL (better performance, concurrency)

### Production Checklist

- [ ] PostgreSQL server is running and configured
- [ ] Database backups are scheduled
- [ ] Connection pooling is tuned for expected load
- [ ] Monitoring is set up (pg_stat_activity, slow query log)
- [ ] SSL/TLS is enabled for remote connections
- [ ] Database user has minimal required permissions
- [ ] `DATABASE_URL` is stored securely (not in version control)

## Support

For issues or questions:
1. Check the [Database README](ats_app/database/README.md)
2. Review error messages and logs
3. Test with the provided test script: `python test_db_abstraction.py`
4. Consult PostgreSQL documentation: https://www.postgresql.org/docs/

## Summary

The database abstraction layer provides:
- **Zero code changes** to switch databases
- **Automatic query adaptation** for compatibility
- **Connection pooling** for PostgreSQL
- **Unified API** regardless of backend
- **Easy testing** with both databases

Start with SQLite for development, migrate to PostgreSQL for production when needed.
