"""
Advanced tests for cache backends to improve coverage.

This test file focuses on testing edge cases and advanced scenarios
for cache backends to increase overall coverage.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from zenoo_rpc.cache.backends import (
    MemoryCache,
    RedisCache,
    CacheBackend
)
from zenoo_rpc.cache.exceptions import CacheError, CacheBackendError


class TestCacheBackendBase:
    """Test base CacheBackend functionality."""

    def test_cache_backend_abstract_methods(self):
        """Test that CacheBackend is abstract."""
        with pytest.raises(TypeError):
            CacheBackend()


class TestMemoryCacheAdvanced:
    """Advanced test cases for MemoryCache."""

    @pytest.mark.asyncio
    async def test_memory_cache_initialization_with_params(self):
        """Test MemoryCache initialization with various parameters."""
        cache = MemoryCache(max_size=100, default_ttl=300)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 300
        assert cache._cache == {}
        assert cache._access_times == {}

    @pytest.mark.asyncio
    async def test_memory_cache_set_with_ttl(self):
        """Test setting values with TTL."""
        cache = MemoryCache(default_ttl=1)
        
        await cache.set("key1", "value1", ttl=2)
        await cache.set("key2", "value2")  # Uses default TTL
        
        # Both should exist initially
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        
        # Wait for default TTL to expire
        await asyncio.sleep(1.1)
        
        # key2 should be expired, key1 should still exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_memory_cache_lru_eviction(self):
        """Test LRU eviction when max_size is reached."""
        cache = MemoryCache(max_size=3)
        
        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add another item, should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still exists
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still exists
        assert await cache.get("key4") == "value4"  # New item

    @pytest.mark.asyncio
    async def test_memory_cache_delete_operations(self):
        """Test delete operations."""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Test single delete
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None
        
        # Test delete non-existent key
        result = await cache.delete("nonexistent")
        assert result is False
        
        # Test delete multiple keys
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")
        
        result = await cache.delete_many(["key2", "key3", "nonexistent"])
        assert result == 2  # Only 2 keys actually deleted

    @pytest.mark.asyncio
    async def test_memory_cache_exists_operation(self):
        """Test exists operation."""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False
        
        # Test with expired key
        await cache.set("expired_key", "value", ttl=0.1)
        await asyncio.sleep(0.2)
        
        assert await cache.exists("expired_key") is False

    @pytest.mark.asyncio
    async def test_memory_cache_clear_operation(self):
        """Test clear operation."""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.clear()
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0

    @pytest.mark.asyncio
    async def test_memory_cache_get_many_operation(self):
        """Test get_many operation."""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        result = await cache.get_many(["key1", "key3", "nonexistent"])
        
        assert result == {
            "key1": "value1",
            "key3": "value3",
            "nonexistent": None
        }

    @pytest.mark.asyncio
    async def test_memory_cache_set_many_operation(self):
        """Test set_many operation."""
        cache = MemoryCache()
        
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        await cache.set_many(data, ttl=300)
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_memory_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache()
        
        # Perform some operations
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.get("key1")  # Hit
        await cache.get("nonexistent")  # Miss
        
        stats = await cache.get_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert stats["size"] == 2

    @pytest.mark.asyncio
    async def test_memory_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = MemoryCache()
        
        # Set entries with short TTL
        await cache.set("key1", "value1", ttl=0.1)
        await cache.set("key2", "value2", ttl=0.1)
        await cache.set("key3", "value3", ttl=10)  # Long TTL
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Trigger cleanup by accessing cache
        await cache.get("key3")
        
        # Expired entries should be cleaned up
        assert "key1" not in cache._cache
        assert "key2" not in cache._cache
        assert "key3" in cache._cache


class TestRedisCacheAdvanced:
    """Advanced test cases for RedisCache."""

    @pytest.mark.asyncio
    async def test_redis_cache_initialization(self):
        """Test RedisCache initialization."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            cache = RedisCache(
                redis_url="redis://localhost:6379/1",
                default_ttl=300,
                key_prefix="test:"
            )
            
            assert cache.redis_url == "redis://localhost:6379/1"
            assert cache.default_ttl == 300
            assert cache.key_prefix == "test:"

    @pytest.mark.asyncio
    async def test_redis_cache_connection_error(self):
        """Test Redis connection error handling."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")
            
            cache = RedisCache()
            
            with pytest.raises(CacheBackendError):
                await cache.connect()

    @pytest.mark.asyncio
    async def test_redis_cache_operations_without_connection(self):
        """Test Redis operations without connection."""
        cache = RedisCache()
        
        # Should raise error when not connected
        with pytest.raises(CacheBackendError):
            await cache.get("key")
        
        with pytest.raises(CacheBackendError):
            await cache.set("key", "value")

    @pytest.mark.asyncio
    async def test_redis_cache_key_prefixing(self):
        """Test Redis key prefixing."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            cache = RedisCache(key_prefix="myapp:")
            await cache.connect()
            
            await cache.set("test_key", "value")
            
            # Should call Redis with prefixed key
            mock_redis_client.set.assert_called_once()
            call_args = mock_redis_client.set.call_args[0]
            assert call_args[0] == "myapp:test_key"

    @pytest.mark.asyncio
    async def test_redis_cache_serialization_error(self):
        """Test Redis serialization error handling."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            cache = RedisCache()
            await cache.connect()
            
            # Mock serialization error
            with patch('json.dumps', side_effect=TypeError("Not serializable")):
                with pytest.raises(CacheBackendError):
                    await cache.set("key", object())  # Non-serializable object

    @pytest.mark.asyncio
    async def test_redis_cache_deserialization_error(self):
        """Test Redis deserialization error handling."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.get.return_value = b"invalid json"
            mock_redis.return_value = mock_redis_client
            
            cache = RedisCache()
            await cache.connect()
            
            # Should handle deserialization error gracefully
            result = await cache.get("key")
            assert result is None

    @pytest.mark.asyncio
    async def test_redis_cache_disconnect(self):
        """Test Redis disconnect."""
        with patch('aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            cache = RedisCache()
            await cache.connect()
            await cache.disconnect()
            
            mock_redis_client.close.assert_called_once()
            assert cache._redis is None
