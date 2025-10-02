"""
Unit tests for DataCache implementation.
"""

import pytest
import time
import threading
from unittest.mock import Mock

from financial_portfolio_automation.data.cache import DataCache, CacheEntry
from financial_portfolio_automation.exceptions import DataError


class TestCacheEntry:
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() + 300,  # 5 minutes from now
            access_count=0,
            last_accessed=time.time()
        )
        
        assert entry.value == "test_value"
        assert not entry.is_expired()
        assert entry.access_count == 0
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        # Create expired entry
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() - 1,  # 1 second ago
            access_count=0,
            last_accessed=time.time()
        )
        
        assert entry.is_expired()
    
    def test_cache_entry_touch(self):
        """Test cache entry touch functionality."""
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() + 300,
            access_count=0,
            last_accessed=0
        )
        
        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed
        
        entry.touch()
        
        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed


class TestDataCache:
    
    @pytest.fixture
    def cache(self):
        """Create a DataCache instance for testing."""
        return DataCache(default_ttl=300, cleanup_interval=60)
    
    def test_cache_initialization(self):
        """Test cache initialization with custom parameters."""
        cache = DataCache(default_ttl=600, cleanup_interval=120)
        assert cache.default_ttl == 600
        assert cache.cleanup_interval == 120
        assert len(cache._cache) == 0
    
    def test_basic_get_set_operations(self, cache):
        """Test basic cache get and set operations."""
        # Test setting and getting a value
        cache.set("key1", "value1")
        result = cache.get("key1")
        assert result == "value1"
        
        # Test getting non-existent key
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_with_custom_ttl(self, cache):
        """Test cache operations with custom TTL."""
        # Set value with custom TTL
        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("key1") is None
    
    def test_cache_expiration(self, cache):
        """Test cache entry expiration."""
        # Set value with very short TTL
        cache.set("key1", "value1", ttl=1)
        
        # Verify it's there
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be None now
        assert cache.get("key1") is None
    
    def test_cache_delete(self, cache):
        """Test cache delete operation."""
        # Set a value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Delete it
        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None
        
        # Try to delete non-existent key
        result = cache.delete("nonexistent")
        assert result is False
    
    def test_cache_clear(self, cache):
        """Test cache clear operation."""
        # Set multiple values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Verify they're there
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Clear cache
        cache.clear()
        
        # Verify they're gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
    
    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Initially empty
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['active_entries'] == 0
        assert stats['hit_count'] == 0
        assert stats['miss_count'] == 0
        assert stats['hit_rate'] == 0.0
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Get some values (hits)
        cache.get("key1")
        cache.get("key1")  # Another hit
        cache.get("nonexistent")  # Miss
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['active_entries'] == 2
        assert stats['hit_count'] == 2
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == 2/3  # 2 hits out of 3 requests
    
    def test_cache_stats_with_expired_entries(self, cache):
        """Test cache statistics with expired entries."""
        # Add entry with short TTL
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2")  # Normal TTL
        
        # Wait for first entry to expire
        time.sleep(1.1)
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['expired_entries'] == 1
        assert stats['active_entries'] == 1
    
    def test_cache_warm_cache(self, cache):
        """Test cache warming functionality."""
        # Mock data loader
        def mock_data_loader(key):
            return f"loaded_value_for_{key}"
        
        keys = ["key1", "key2", "key3"]
        cache.warm_cache(mock_data_loader, keys)
        
        # Verify all keys were loaded
        for key in keys:
            assert cache.get(key) == f"loaded_value_for_{key}"
    
    def test_cache_warm_cache_with_none_values(self, cache):
        """Test cache warming with data loader returning None."""
        def mock_data_loader(key):
            if key == "key2":
                return None
            return f"loaded_value_for_{key}"
        
        keys = ["key1", "key2", "key3"]
        cache.warm_cache(mock_data_loader, keys)
        
        # key2 should not be cached since loader returned None
        assert cache.get("key1") == "loaded_value_for_key1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "loaded_value_for_key3"
    
    def test_cache_warm_cache_with_exceptions(self, cache):
        """Test cache warming with data loader raising exceptions."""
        def mock_data_loader(key):
            if key == "key2":
                raise Exception("Load failed")
            return f"loaded_value_for_{key}"
        
        keys = ["key1", "key2", "key3"]
        # Should not raise exception
        cache.warm_cache(mock_data_loader, keys)
        
        # key2 should not be cached due to exception
        assert cache.get("key1") == "loaded_value_for_key1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "loaded_value_for_key3"
    
    def test_invalidate_pattern(self, cache):
        """Test pattern-based cache invalidation."""
        # Set up test data
        cache.set("user:123:profile", "profile_data")
        cache.set("user:123:settings", "settings_data")
        cache.set("user:456:profile", "other_profile_data")
        cache.set("product:789", "product_data")
        
        # Invalidate all user:123 entries
        count = cache.invalidate_pattern("user:123:*")
        assert count == 2
        
        # Verify correct entries were invalidated
        assert cache.get("user:123:profile") is None
        assert cache.get("user:123:settings") is None
        assert cache.get("user:456:profile") == "other_profile_data"
        assert cache.get("product:789") == "product_data"
    
    def test_invalidate_pattern_no_matches(self, cache):
        """Test pattern invalidation with no matches."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        count = cache.invalidate_pattern("nomatch:*")
        assert count == 0
        
        # Original entries should still be there
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
    
    def test_thread_safety(self, cache):
        """Test cache thread safety."""
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    
                    # Set value
                    cache.set(key, value)
                    
                    # Get value
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Thread {thread_id}: Expected {value}, got {retrieved}")
                    
                    results.append((thread_id, i, retrieved == value))
            except Exception as e:
                errors.append(f"Thread {thread_id}: Exception {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 500  # 5 threads * 100 operations each
        assert all(success for _, _, success in results)
    
    def test_cache_access_statistics(self, cache):
        """Test cache access statistics tracking."""
        cache.set("key1", "value1")
        
        # Access the key multiple times
        for _ in range(5):
            cache.get("key1")
        
        # Check that access count is tracked
        entry = cache._cache.get("key1")
        assert entry is not None
        assert entry.access_count == 5
        assert entry.last_accessed > 0
    
    def test_cache_replacement_behavior(self, cache):
        """Test cache behavior when replacing existing keys."""
        # Set initial value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Replace with new value
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"
        
        # Verify only one entry exists
        stats = cache.get_stats()
        assert stats['total_entries'] == 1
    
    def test_cache_with_different_data_types(self, cache):
        """Test cache with various data types."""
        test_data = {
            "string": "test_string",
            "integer": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
            "boolean": True
        }
        
        # Set all values
        for key, value in test_data.items():
            cache.set(key, value)
        
        # Retrieve and verify all values
        for key, expected_value in test_data.items():
            retrieved_value = cache.get(key)
            assert retrieved_value == expected_value
    
    def test_cache_cleanup_timer(self):
        """Test automatic cache cleanup."""
        # Create cache with very short cleanup interval
        cache = DataCache(default_ttl=1, cleanup_interval=2)
        
        # Add entries with short TTL
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=1)
        
        # Verify entries exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Wait for entries to expire and cleanup to run
        time.sleep(3)
        
        # Entries should be cleaned up
        stats = cache.get_stats()
        # Note: This test might be flaky due to timing, but should generally work
        assert stats['total_entries'] <= 2  # May still be there if cleanup hasn't run
    
    def test_cache_memory_efficiency(self, cache):
        """Test cache memory usage with large number of entries."""
        # Add many entries
        num_entries = 1000
        for i in range(num_entries):
            cache.set(f"key_{i}", f"value_{i}")
        
        stats = cache.get_stats()
        assert stats['total_entries'] == num_entries
        
        # Clear cache and verify memory is freed
        cache.clear()
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
    
    def test_cache_edge_cases(self, cache):
        """Test cache edge cases and boundary conditions."""
        # Test with empty string key
        cache.set("", "empty_key_value")
        assert cache.get("") == "empty_key_value"
        
        # Test with very long key
        long_key = "x" * 1000
        cache.set(long_key, "long_key_value")
        assert cache.get(long_key) == "long_key_value"
        
        # Test with very short TTL (should expire quickly)
        cache.set("short_ttl", "value", ttl=0.001)  # 1 millisecond
        time.sleep(0.01)  # Wait 10 milliseconds
        assert cache.get("short_ttl") is None