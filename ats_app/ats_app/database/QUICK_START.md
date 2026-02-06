# Database Abstraction Layer - Quick Start

## TL;DR

The database now supports both SQLite (default) and PostgreSQL with zero code changes.

## Use SQLite (Default)

```bash
# Nothing to do! Works out of the box
python app.py
```

## Switch to PostgreSQL

### 1. Install driver
```bash
pip install psycopg2-binary
```

### 2. Set connection string
```bash
# .env file
DATABASE_URL="postgresql://user:password@localhost:5432/ats_db"
```

### 3. Create database
```bash
createdb ats_db
```

### 4. Initialize schema
```bash
python -c "from database import init_db, migrate_db; init_db(); migrate_db()"
```

### 5. Run application
```bash
python app.py
```

Done! Your app now uses PostgreSQL.

## Check Which Database You're Using

```python
from database import get_db_type

print(f"Database: {get_db_type()}")  # "sqlite" or "postgresql"
```

## Key Features

- **No code changes** needed to switch databases
- **Same API** for both backends
- **Automatic query adaptation** (? → %s for PostgreSQL)
- **Connection pooling** for PostgreSQL
- **Full backward compatibility**

## Configuration

### SQLite (Default)
```bash
# .env (or leave empty)
DATABASE_URL=""
DB_PATH="ats_data.db"
```

### PostgreSQL
```bash
# .env
DATABASE_URL="postgresql://user:pass@host:port/database"
DB_POOL_SIZE=5          # Optional: connection pool size
DB_MAX_OVERFLOW=10      # Optional: max extra connections
DB_POOL_TIMEOUT=30      # Optional: connection timeout
```

## Example Usage

```python
from database import db_session

# Works with both SQLite and PostgreSQL
with db_session() as conn:
    # Use ? for parameters (works for both)
    conn.execute("INSERT INTO jobs (title) VALUES (?)", ("Engineer",))

    # Query with parameters
    result = conn.execute("SELECT * FROM jobs WHERE id = ?", (1,))
    job = result.fetchone()

    # Dict-like row access
    print(job['title'])
```

## Testing

Run the test suite:
```bash
python test_db_abstraction.py
```

## Documentation

- **Full API Docs**: [database/README.md](README.md)
- **Migration Guide**: [../DATABASE_MIGRATION_GUIDE.md](../DATABASE_MIGRATION_GUIDE.md)
- **Implementation Summary**: [../IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md)

## Common Commands

### Initialize database
```python
from database import init_db
init_db()
```

### Run migrations
```python
from database import migrate_db
migrate_db()
```

### Check database type
```python
from database import get_db_type
print(get_db_type())
```

### Analyze query performance
```python
from database import explain_query
plan = explain_query("SELECT * FROM jobs WHERE title = ?", ("Engineer",))
print(plan)
```

## Troubleshooting

### "psycopg2 is not installed"
```bash
pip install psycopg2-binary
```

### Connection refused (PostgreSQL)
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql
```

### Pool exhausted errors
```bash
# Increase pool size in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## When to Use Which

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Setup | Easy (built-in) | Moderate (needs server) |
| Performance | Fast for reads | Better for writes |
| Concurrency | Single writer | Multiple writers |
| Best for | Development, testing | Production, multi-user |

## Production Recommendations

- **Development**: SQLite (fast setup, no dependencies)
- **Staging**: PostgreSQL (test production config)
- **Production**: PostgreSQL (better performance, scalability)

---

**Need help?** Check the [full documentation](README.md) or [migration guide](../DATABASE_MIGRATION_GUIDE.md).
