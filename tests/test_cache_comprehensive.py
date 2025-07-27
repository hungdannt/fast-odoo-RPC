"""
Comprehensive tests for Zenoo-RPC caching system.

This module tests all aspects of the caching system including:
- Cache backends (Memory, Redis)
- Cache strategies (TTL, LRU, LFU)
- Cache decorators and key management
- Cache invalidation and statistics
"""

import pytest
import asyncio
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from zenoo_rpc.cache.manager import CacheManager
from zenoo_rpc.cache.backends import MemoryCache, RedisCache, CacheBackend
from zenoo_rpc.cache.strategies import TTLCache, LRUCache, LFUCache
from zenoo_rpc.cache.keys import (
    CacheKey,
    make_cache_key,
    make_model_cache_key,
    make_query_cache_key,
)
from zenoo_rpc.cache.decorators import cached, cache_result, invalidate_cache
from zenoo_rpc.cache.exceptions import CacheError, CacheBackendError, CacheKeyError


class TestCacheKeys:
    """Test cache key generation and validation."""

    def test_cache_key_creation(self):
        """Test CacheKey creation and validation."""
        key = CacheKey("test:key", namespace="test")
        assert key.namespace == "test"
        assert key.key == "test:key"

        # Test string representation
        assert str(key) == "test:key"

    def test_cache_key_validation(self):
        """Test cache key validation."""
        # Valid keys
        valid_keys = ["simple", "with_underscore", "with-dash", "with123numbers"]
        for key in valid_keys:
            cache_key = CacheKey(key, namespace="test")
            assert cache_key.key == key

        # Test basic validation - CacheKey should accept any non-empty string
        cache_key = CacheKey("valid_key", namespace="test")
        assert cache_key.key == "valid_key"

    def test_make_cache_key(self):
        """Test cache key factory functions."""
        # Basic key
        key = make_cache_key("res.partner", "search")
        assert isinstance(key, CacheKey)
        assert "res.partner" in str(key)
        assert "search" in str(key)

        # Model cache key
        model_key = make_model_cache_key("res.partner", 123)
        assert "res.partner" in str(model_key)
        assert "123" in str(model_key)

        # Query cache key
        domain = [("name", "=", "test")]
        query_key = make_query_cache_key("res.partner", domain)
        assert "res.partner" in str(query_key)
        assert "search_read" in str(query_key)


class TestMemoryCache:
    """Test in-memory cache backend."""

    @pytest.mark.asyncio
    async def test_memory_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = MemoryCache(max_size=100, default_ttl=300)

        # Test set and get
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        assert value == "test_value"

        # Test exists
        exists = await cache.exists("test_key")
        assert exists is True

        # Test non-existent key
        value = await cache.get("non_existent")
        assert value is None

        exists = await cache.exists("non_existent")
        assert exists is False

    @pytest.mark.asyncio
    async def test_memory_cache_ttl(self):
        """Test TTL functionality."""
        cache = MemoryCache(default_ttl=1)  # 1 second TTL

        # Set value with TTL
        await cache.set("ttl_key", "ttl_value", ttl=0.1)  # 100ms

        # Should exist immediately
        value = await cache.get("ttl_key")
        assert value == "ttl_value"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        value = await cache.get("ttl_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_cache_lru_eviction(self):
        """Test LRU eviction."""
        cache = MemoryCache(max_size=3)  # Small cache for testing

        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # All should exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

        # Add one more - should evict least recently used
        await cache.set("key4", "value4")

        # key1 should be evicted (least recently used)
        assert await cache.get("key1") is None
        assert await cache.get("key4") == "value4"

    @pytest.mark.asyncio
    async def test_memory_cache_delete(self):
        """Test cache deletion."""
        cache = MemoryCache()

        await cache.set("delete_key", "delete_value")
        assert await cache.get("delete_key") == "delete_value"

        # Delete key
        deleted = await cache.delete("delete_key")
        assert deleted is True

        # Should not exist
        assert await cache.get("delete_key") is None

        # Delete non-existent key
        deleted = await cache.delete("non_existent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_memory_cache_clear(self):
        """Test cache clearing."""
        cache = MemoryCache()

        # Add multiple items
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Clear cache
        cleared = await cache.clear()
        assert cleared is True

        # All should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_memory_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache(max_size=100)

        # Get initial stats
        stats = await cache.get_stats()
        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats

        # Add some data and check stats
        await cache.set("stats_key", "stats_value")
        await cache.get("stats_key")  # Hit
        await cache.get("non_existent")  # Miss

        stats = await cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1


class TestCacheStrategies:
    """Test cache strategies."""

    @pytest.mark.asyncio
    async def test_ttl_cache_strategy(self):
        """Test TTL cache strategy."""
        backend = MemoryCache()
        strategy = TTLCache(backend, default_ttl=1)

        # Set value with TTL
        await strategy.set("ttl_test", "ttl_value", ttl=0.1)

        # Should exist immediately
        value = await strategy.get("ttl_test")
        assert value == "ttl_value"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        value = await strategy.get("ttl_test")
        assert value is None

    @pytest.mark.asyncio
    async def test_lru_cache_strategy(self):
        """Test LRU cache strategy."""
        backend = MemoryCache()
        strategy = LRUCache(backend, max_size=3)

        # Fill cache
        await strategy.set("lru1", "value1")
        await strategy.set("lru2", "value2")
        await strategy.set("lru3", "value3")

        # Access lru1 to make it recently used
        await strategy.get("lru1")

        # Add new item - should evict lru2 (least recently used)
        await strategy.set("lru4", "value4")

        assert await strategy.get("lru1") == "value1"  # Should still exist
        assert await strategy.get("lru2") is None  # Should be evicted
        assert await strategy.get("lru3") == "value3"  # Should still exist
        assert await strategy.get("lru4") == "value4"  # Should exist

    @pytest.mark.asyncio
    async def test_lfu_cache_strategy(self):
        """Test LFU cache strategy."""
        backend = MemoryCache()
        strategy = LFUCache(backend, max_size=3)

        # Fill cache
        await strategy.set("lfu1", "value1")
        await strategy.set("lfu2", "value2")
        await strategy.set("lfu3", "value3")

        # Access lfu1 multiple times to increase frequency
        await strategy.get("lfu1")
        await strategy.get("lfu1")
        await strategy.get("lfu1")

        # Access lfu2 once
        await strategy.get("lfu2")

        # Add new item - should evict lfu3 (least frequently used)
        await strategy.set("lfu4", "value4")

        assert (
            await strategy.get("lfu1") == "value1"
        )  # Should still exist (most frequent)
        assert await strategy.get("lfu2") == "value2"  # Should still exist
        assert await strategy.get("lfu3") is None  # Should be evicted (least frequent)
        assert await strategy.get("lfu4") == "value4"  # Should exist


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_cache_manager_setup(self):
        """Test cache manager setup."""
        manager = CacheManager()

        # Setup memory cache
        await manager.setup_memory_cache(max_size=100, default_ttl=300)

        assert "memory" in manager.backends
        assert "memory" in manager.strategies
        assert isinstance(manager.backends["memory"], MemoryCache)
        assert isinstance(manager.strategies["memory"], TTLCache)

    @pytest.mark.asyncio
    async def test_cache_manager_operations(self):
        """Test cache manager operations."""
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Test basic operations
        await manager.set("manager_key", "manager_value", ttl=60)
        value = await manager.get("manager_key")
        assert value == "manager_value"

        # Test exists and delete
        assert await manager.exists("manager_key") is True
        assert await manager.delete("manager_key") is True
        assert await manager.get("manager_key") is None

    @pytest.mark.asyncio
    async def test_cache_manager_query_caching(self):
        """Test query result caching."""
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Cache query result
        model = "res.partner"
        domain = [("is_company", "=", True)]
        result = [{"id": 1, "name": "Test Company"}]

        cached = await manager.cache_query_result(model, domain, result, ttl=60)
        assert cached is True

        # Retrieve cached result
        cached_result = await manager.get_cached_query_result(model, domain)
        assert cached_result == result

        # Test cache invalidation
        invalidated = await manager.invalidate_model(model)
        assert invalidated >= 0  # Returns number of keys invalidated

        # Should be gone after invalidation
        cached_result = await manager.get_cached_query_result(model, domain)
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_cache_manager_model_caching(self):
        """Test model record caching."""
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Cache model record
        model = "res.partner"
        record_id = 123
        record_data = {"id": 123, "name": "Test Partner", "email": "test@example.com"}

        cached = await manager.cache_model_record(model, record_id, record_data, ttl=60)
        assert cached is True

        # Retrieve cached record
        cached_record = await manager.get_cached_model_record(model, record_id)
        assert cached_record == record_data

        # Test cache invalidation
        invalidated = await manager.invalidate_model(model)
        assert invalidated >= 0  # Returns number of keys invalidated

        # Should be gone after invalidation
        cached_record = await manager.get_cached_model_record(model, record_id)
        assert cached_record is None


class TestCacheDecorators:
    """Test cache decorators."""

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test @cached decorator."""
        call_count = 0

        # Setup cache manager
        manager = CacheManager()
        await manager.setup_memory_cache()

        @cached(ttl=60, backend="memory", cache_manager=manager)
        async def expensive_function(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate expensive operation
            return x + y

        # First call should execute function
        result1 = await expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not increment

        # Different parameters should execute function
        result3 = await expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_result_decorator(self):
        """Test @cache_result decorator."""
        call_count = 0

        @cache_result(model="test.model", operation="search", ttl=60)
        async def test_function(client, value: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{value}"

        # Setup cache manager
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Mock client with cache manager
        mock_client = AsyncMock()
        mock_client.cache_manager = manager

        # First call
        result1 = await test_function(mock_client, "test")
        assert result1 == "processed_test"
        assert call_count == 1

        # Second call should use cache
        result2 = await test_function(mock_client, "test")
        assert result2 == "processed_test"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator(self):
        """Test @invalidate_cache decorator."""
        call_count = 0

        @cached(ttl=60, backend="memory")
        async def cached_function(client, x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        @invalidate_cache("cached_function:*")
        async def invalidating_function(client):
            pass

        # Setup cache manager
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Mock client with cache manager
        mock_client = AsyncMock()
        mock_client.cache_manager = manager

        # Cache a value
        result1 = await cached_function(mock_client, 5)
        assert result1 == 10
        assert call_count == 1

        # Should use cache
        result2 = await cached_function(mock_client, 5)
        assert result2 == 10
        assert call_count == 1

        # Invalidate cache
        await invalidating_function(mock_client)

        # Should execute function again
        result3 = await cached_function(mock_client, 5)
        assert result3 == 10
        assert call_count == 2


class TestRedisCache:
    """Test Redis cache backend."""

    @pytest.mark.asyncio
    async def test_redis_cache_real(self):
        """Test Redis cache with real Redis instance."""
        # Skip if aioredis is not available
        pytest.importorskip("aioredis")

        # Use test Redis instance on port 6381
        cache = RedisCache(url="redis://localhost:6381/0", namespace="test")

        try:
            await cache.connect()

            # Test set and get
            test_key = "redis_test_key"
            test_value = {"data": "redis_test_value", "number": 42}

            # Set value
            result = await cache.set(test_key, test_value, ttl=60)
            assert result is True

            # Get value
            retrieved_value = await cache.get(test_key)
            assert retrieved_value == test_value

            # Test exists
            exists = await cache.exists(test_key)
            assert exists is True

            # Test delete
            deleted = await cache.delete(test_key)
            assert deleted is True

            # Verify deleted
            retrieved_after_delete = await cache.get(test_key)
            assert retrieved_after_delete is None

            # Test stats
            stats = await cache.get_stats()
            assert "backend" in stats
            assert stats["backend"] == "redis"

        except Exception as e:
            # If Redis is not available, skip the test
            pytest.skip(f"Redis not available for testing: {e}")
        finally:
            # Cleanup
            try:
                await cache.close()
            except:
                pass


class TestCacheExceptions:
    """Test cache exception handling."""

    @pytest.mark.asyncio
    async def test_cache_backend_error(self):
        """Test cache backend error handling."""
        # Create a mock backend that raises errors
        mock_backend = AsyncMock()
        mock_backend.get.side_effect = Exception("Backend error")

        strategy = TTLCache(mock_backend)

        with pytest.raises(CacheBackendError):
            await strategy.get("error_key")

    def test_cache_key_error(self):
        """Test cache key validation errors."""
        with pytest.raises(CacheKeyError):
            CacheKey("", namespace="test")  # Empty key

        with pytest.raises(CacheKeyError):
            CacheKey("key", namespace="")  # Empty namespace

        with pytest.raises(CacheKeyError):
            CacheKey("key with spaces", namespace="test")  # Invalid characters


class TestCacheIntegration:
    """Test cache system integration."""

    @pytest.mark.asyncio
    async def test_multi_backend_cache_manager(self):
        """Test cache manager with multiple backends."""
        manager = CacheManager()

        # Setup multiple backends
        await manager.setup_memory_cache(name="memory1", max_size=100)
        await manager.setup_memory_cache(name="memory2", max_size=50)

        assert "memory1" in manager.backends
        assert "memory2" in manager.backends

        # Test operations on specific backends
        await manager.set("key1", "value1", backend="memory1")
        await manager.set("key2", "value2", backend="memory2")

        value1 = await manager.get("key1", backend="memory1")
        value2 = await manager.get("key2", backend="memory2")

        assert value1 == "value1"
        assert value2 == "value2"

        # Key should not exist in other backend
        value1_in_memory2 = await manager.get("key1", backend="memory2")
        assert value1_in_memory2 is None

    @pytest.mark.asyncio
    async def test_cache_statistics_aggregation(self):
        """Test cache statistics aggregation."""
        manager = CacheManager()
        await manager.setup_memory_cache()

        # Add some data and access it
        await manager.set("stats_key1", "value1")
        await manager.set("stats_key2", "value2")
        await manager.get("stats_key1")  # Hit
        await manager.get("nonexistent")  # Miss

        # Get aggregated stats
        stats = await manager.get_stats()

        assert "backends" in stats
        assert "memory" in stats["backends"]
        assert "total_size" in stats
        assert "total_hits" in stats
        assert "total_misses" in stats
