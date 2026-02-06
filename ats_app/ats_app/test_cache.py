"""
Test script for cache module functionality.
Run this to verify caching works correctly.
"""
import sys
import time
from cache import CacheManager, query_cache, analytics_cache, ai_cache, cached, invalidate_candidate_caches, invalidate_job_caches

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def test_basic_cache_operations():
    """Test basic get/set/delete operations."""
    print("Testing basic cache operations...")

    cache = CacheManager(default_ttl=5)

    # Test set and get
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value", "Get failed"
    print("[OK] Set and get working")

    # Test expiry
    cache.set("expiring_key", "value", ttl_seconds=1)
    time.sleep(1.5)
    assert cache.get("expiring_key") is None, "TTL expiry failed"
    print("[OK] TTL expiry working")

    # Test delete
    cache.set("delete_me", "value")
    cache.delete("delete_me")
    assert cache.get("delete_me") is None, "Delete failed"
    print("[OK] Delete working")

    # Test pattern invalidation
    cache.set("users:1", "user1")
    cache.set("users:2", "user2")
    cache.set("posts:1", "post1")
    cache.invalidate_pattern("users:")
    assert cache.get("users:1") is None, "Pattern invalidation failed"
    assert cache.get("posts:1") == "post1", "Pattern invalidation affected wrong keys"
    print("[OK] Pattern invalidation working")

    # Test clear
    cache.set("a", "1")
    cache.set("b", "2")
    cache.clear()
    assert cache.get("a") is None, "Clear failed"
    print("[OK] Clear working")

    cache.stop()
    print("\nBasic operations: PASSED\n")


def test_cache_stats():
    """Test cache statistics."""
    print("Testing cache statistics...")

    cache = CacheManager(default_ttl=10)

    # Generate some activity
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.get("key1")  # Hit
    cache.get("key1")  # Hit
    cache.get("missing")  # Miss

    stats = cache.stats()

    assert stats['hits'] == 2, f"Expected 2 hits, got {stats['hits']}"
    assert stats['misses'] == 1, f"Expected 1 miss, got {stats['misses']}"
    assert stats['sets'] == 2, f"Expected 2 sets, got {stats['sets']}"
    assert stats['size'] == 2, f"Expected size 2, got {stats['size']}"

    print(f"[OK] Stats: {stats}")

    cache.stop()
    print("\nCache stats: PASSED\n")


def test_decorator():
    """Test cached decorator."""
    print("Testing @cached decorator...")

    call_count = 0

    @cached(query_cache, ttl=5, key_prefix="test")
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y

    # First call - should execute
    result1 = expensive_function(2, 3)
    assert result1 == 5, "Function result incorrect"
    assert call_count == 1, "Function should have been called once"
    print(f"[OK] First call: result={result1}, calls={call_count}")

    # Second call with same args - should use cache
    result2 = expensive_function(2, 3)
    assert result2 == 5, "Cached result incorrect"
    assert call_count == 1, "Function should not have been called again"
    print(f"[OK] Second call (cached): result={result2}, calls={call_count}")

    # Different args - should execute
    result3 = expensive_function(5, 7)
    assert result3 == 12, "Function result incorrect"
    assert call_count == 2, "Function should have been called twice"
    print(f"[OK] Different args: result={result3}, calls={call_count}")

    print("\nDecorator: PASSED\n")


def test_pre_configured_caches():
    """Test pre-configured cache instances."""
    print("Testing pre-configured cache instances...")

    # Test query_cache (30 second TTL)
    query_cache.set("query:1", {"results": [1, 2, 3]})
    assert query_cache.get("query:1") == {"results": [1, 2, 3]}, "Query cache failed"
    print("[OK] query_cache working")

    # Test analytics_cache (300 second TTL)
    analytics_cache.set("analytics:pipeline", {"total": 100})
    assert analytics_cache.get("analytics:pipeline") == {"total": 100}, "Analytics cache failed"
    print("[OK] analytics_cache working")

    # Test ai_cache (3600 second TTL)
    ai_cache.set("ai:score:123", 85.5)
    assert ai_cache.get("ai:score:123") == 85.5, "AI cache failed"
    print("[OK] ai_cache working")

    print("\nPre-configured caches: PASSED\n")


def test_invalidation_helpers():
    """Test cache invalidation helper functions."""
    print("Testing invalidation helpers...")

    # Set up some cache data
    query_cache.set("candidates:list", [1, 2, 3])
    query_cache.set("pipeline:stats", {"total": 50})
    analytics_cache.set("analytics:report", {"data": "test"})
    query_cache.set("jobs:list", [1, 2])

    # Test candidate cache invalidation
    invalidate_candidate_caches()
    assert query_cache.get("candidates:list") is None, "Candidate cache not invalidated"
    assert query_cache.get("pipeline:stats") is None, "Pipeline cache not invalidated"
    assert analytics_cache.get("analytics:report") is None, "Analytics cache not invalidated"
    assert query_cache.get("jobs:list") == [1, 2], "Jobs cache incorrectly invalidated"
    print("[OK] invalidate_candidate_caches working")

    # Test job cache invalidation
    query_cache.set("jobs:list", [1, 2])
    analytics_cache.set("analytics:report", {"data": "test"})
    invalidate_job_caches()
    assert query_cache.get("jobs:list") is None, "Jobs cache not invalidated"
    assert analytics_cache.get("analytics:report") is None, "Analytics cache not invalidated"
    print("[OK] invalidate_job_caches working")

    print("\nInvalidation helpers: PASSED\n")


def test_thread_safety():
    """Test thread safety of cache operations."""
    print("Testing thread safety...")
    import threading

    cache = CacheManager(default_ttl=10)
    results = []

    def worker(thread_id):
        for i in range(100):
            cache.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")
            val = cache.get(f"key_{thread_id}_{i}")
            if val:
                results.append(val)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 500, f"Expected 500 results, got {len(results)}"
    print(f"[OK] Thread safety: {len(results)} operations completed successfully")

    cache.stop()
    print("\nThread safety: PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Cache Module Tests")
    print("=" * 60 + "\n")

    test_basic_cache_operations()
    test_cache_stats()
    test_decorator()
    test_pre_configured_caches()
    test_invalidation_helpers()
    test_thread_safety()

    print("=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
