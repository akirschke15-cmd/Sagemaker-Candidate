# Cache Module Usage Guide

## Overview

The ATS application includes an in-memory caching module (`cache.py`) that provides TTL-based caching with automatic cleanup and thread-safe operations. This module significantly improves performance by caching expensive database queries and AI operations.

## Features

- Thread-safe operations with `threading.Lock`
- TTL (Time-To-Live) support for automatic expiration
- Pattern-based cache invalidation
- Cache statistics (hits, misses, hit rate)
- Automatic cleanup of expired entries every 60 seconds
- Pre-configured cache instances for different use cases

## Pre-configured Cache Instances

The module provides three pre-configured cache instances:

```python
from cache import query_cache, analytics_cache, ai_cache

# query_cache - For database query results (TTL: 30 seconds)
# analytics_cache - For analytics/reports (TTL: 5 minutes)
# ai_cache - For AI scoring results (TTL: 1 hour)
```

## Basic Usage

### Manual Caching

```python
from cache import query_cache

# Set a cached value
query_cache.set("user:123", {"name": "John", "email": "john@example.com"})

# Get a cached value
user = query_cache.get("user:123")
if user:
    print(f"Cache hit: {user}")
else:
    print("Cache miss - fetch from database")

# Set with custom TTL
query_cache.set("temp:data", "value", ttl_seconds=60)

# Delete specific key
query_cache.delete("user:123")

# Clear all cache
query_cache.clear()
```

### Using the @cached Decorator

The most convenient way to cache function results:

```python
from cache import analytics_cache, cached

@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_pipeline_stats_multirole(job_id: int = None):
    """Expensive analytics query - will be cached for 5 minutes"""
    with db_session() as conn:
        # ... expensive database query ...
        return results

# First call - executes query and caches result
stats1 = get_pipeline_stats_multirole(job_id=1)

# Second call with same args - returns cached result
stats2 = get_pipeline_stats_multirole(job_id=1)

# Different args - executes query again
stats3 = get_pipeline_stats_multirole(job_id=2)
```

## Cache Invalidation

### Pattern-Based Invalidation

Invalidate all keys matching a prefix pattern:

```python
from cache import query_cache

# Set some related cache entries
query_cache.set("candidates:list", [1, 2, 3])
query_cache.set("candidates:123", {...})
query_cache.set("candidates:456", {...})

# Invalidate all candidate-related caches
query_cache.invalidate_pattern("candidates:")
```

### Helper Functions

Use the provided invalidation helpers after write operations:

```python
from cache import invalidate_candidate_caches, invalidate_job_caches

def create_candidate(...):
    # ... create candidate in database ...
    invalidate_candidate_caches()  # Clear all candidate-related caches
    return candidate_id

def update_job(...):
    # ... update job in database ...
    invalidate_job_caches()  # Clear all job-related caches
```

The helper functions invalidate multiple cache patterns:

- `invalidate_candidate_caches()` - Clears:
  - `candidates:*`
  - `pipeline:*`
  - `analytics:*`

- `invalidate_job_caches()` - Clears:
  - `jobs:*`
  - `analytics:*`

## Cache Statistics

Monitor cache performance:

```python
from cache import query_cache

stats = query_cache.stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Current size: {stats['size']}")
```

Example output:
```
{
  'hits': 150,
  'misses': 50,
  'sets': 75,
  'deletes': 10,
  'invalidations': 25,
  'size': 45,
  'hit_rate': 75.0
}
```

## Configuration

Cache settings can be configured in `config.py` or via environment variables:

```python
# config.py
CACHE_DEFAULT_TTL: int = 30        # Default TTL in seconds
CACHE_ANALYTICS_TTL: int = 300     # Analytics cache TTL (5 minutes)
CACHE_AI_TTL: int = 3600           # AI cache TTL (1 hour)
CACHE_ENABLED: bool = True         # Enable/disable caching
```

Environment variables:
```bash
export CACHE_DEFAULT_TTL=30
export CACHE_ANALYTICS_TTL=300
export CACHE_AI_TTL=3600
export CACHE_ENABLED=true
```

## Custom Cache Instances

Create custom cache instances for specific use cases:

```python
from cache import CacheManager

# Create a cache with 2-minute TTL
short_cache = CacheManager(default_ttl=120)

short_cache.set("temp:data", "value")
result = short_cache.get("temp:data")

# Clean up when done
short_cache.stop()
```

## Integration Examples

### Analytics Functions

```python
from cache import analytics_cache, cached

@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_pipeline_velocity(job_id: int = None):
    """Cache pipeline velocity for 5 minutes"""
    # ... expensive query ...
    return results

@cached(analytics_cache, ttl=300, key_prefix="analytics")
def get_stage_conversion_rates(job_id: int = None):
    """Cache conversion rates for 5 minutes"""
    # ... expensive query ...
    return results
```

### Database Write Operations

```python
from cache import invalidate_candidate_caches

def create_candidate(...):
    with db_session() as conn:
        cursor = conn.execute(...)
        candidate_id = cursor.lastrowid
    invalidate_candidate_caches()  # Clear related caches
    return candidate_id

def update_candidate(candidate_id: int, **kwargs):
    with db_session() as conn:
        conn.execute(...)
    invalidate_candidate_caches()  # Clear related caches
```

## Best Practices

1. **Choose appropriate TTLs**:
   - Short-lived data (30s): Real-time queries, user sessions
   - Medium-lived data (5min): Analytics, reports, dashboard stats
   - Long-lived data (1hr): AI scores, expensive computations

2. **Always invalidate on writes**:
   ```python
   def update_data():
       # ... database write ...
       invalidate_related_caches()  # IMPORTANT!
   ```

3. **Use pattern-based invalidation**:
   ```python
   # Good: Clear all related caches at once
   cache.invalidate_pattern("users:")

   # Bad: Manual deletion of individual keys
   cache.delete("users:1")
   cache.delete("users:2")
   # ... might miss some keys
   ```

4. **Monitor cache performance**:
   ```python
   stats = cache.stats()
   if stats['hit_rate'] < 50:
       print("Warning: Low cache hit rate!")
   ```

5. **Disable caching for debugging**:
   ```bash
   export CACHE_ENABLED=false
   ```

## Testing

Run the test suite to verify cache functionality:

```bash
cd ats_app
python test_cache.py
```

## Performance Impact

Expected performance improvements with caching:

- **Analytics queries**: 80-95% faster (5+ seconds → <500ms)
- **Pipeline stats**: 70-90% faster (2+ seconds → <200ms)
- **AI scoring lookups**: 90-99% faster (10+ seconds → <100ms)
- **Dashboard loads**: 50-80% faster (aggregate effect)

## Troubleshooting

### Cache not working

1. Check if caching is enabled:
   ```python
   from config import settings
   print(settings.CACHE_ENABLED)
   ```

2. Verify cache statistics:
   ```python
   stats = query_cache.stats()
   print(stats)
   ```

### High memory usage

Monitor cache size:
```python
stats = query_cache.stats()
if stats['size'] > 1000:
    query_cache.clear()  # Clear if too large
```

### Stale data

Reduce TTL or invalidate more aggressively:
```python
# Option 1: Shorter TTL
@cached(cache, ttl=10)  # 10 seconds instead of 30

# Option 2: Invalidate after related changes
def update_anything():
    # ... changes ...
    query_cache.invalidate_pattern("related:")
```

## Advanced Usage

### Custom cache key generation

```python
@cached(cache, ttl=60, key_prefix="custom")
def complex_function(user_id, filters):
    # Cache key will be: "custom:complex_function:123:{'status':'active'}"
    pass
```

### Conditional caching

```python
from cache import query_cache

def get_user(user_id: int):
    cache_key = f"user:{user_id}"

    # Try cache first
    if settings.CACHE_ENABLED:
        cached_user = query_cache.get(cache_key)
        if cached_user:
            return cached_user

    # Fetch from database
    user = fetch_from_db(user_id)

    # Cache if enabled
    if settings.CACHE_ENABLED:
        query_cache.set(cache_key, user)

    return user
```

### Multi-level caching strategy

```python
# Level 1: Short-term cache for hot data
@cached(query_cache, ttl=30, key_prefix="hot")
def get_hot_data():
    pass

# Level 2: Long-term cache for expensive operations
@cached(ai_cache, ttl=3600, key_prefix="cold")
def get_cold_data():
    pass
```
