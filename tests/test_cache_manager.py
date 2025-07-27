import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.zenoo_rpc.cache.manager import CacheManager
from src.zenoo_rpc.cache.backends import MemoryCache


@pytest.fixture
def cache_manager():
    """Create a cache manager instance."""
    return CacheManager()


def test_cache_manager_initialization(cache_manager):
    """Test CacheManager initialization."""
    assert cache_manager.backend is None
    assert cache_manager.default_ttl == 300
    assert cache_manager.is_enabled is True
    assert cache_manager._stats == {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}


@pytest.mark.asyncio
async def test_cache_manager_setup_memory_cache(cache_manager):
    """Test setting up memory cache backend."""
    await cache_manager.setup_memory_cache(max_size=100, ttl=600)

    assert isinstance(cache_manager.backend, MemoryCache)
    assert cache_manager.default_ttl == 600


@pytest.mark.asyncio
async def test_cache_manager_get_set(cache_manager):
    """Test basic get/set operations."""
    await cache_manager.setup_memory_cache()

    # Set a value
    await cache_manager.set("test_key", "test_value", ttl=60)

    # Get the value
    value = await cache_manager.get("test_key")
    assert value == "test_value"

    # Check stats
    stats = cache_manager.get_stats()
    assert stats["sets"] == 1
    assert stats["hits"] == 1


@pytest.mark.asyncio
async def test_cache_manager_get_miss(cache_manager):
    """Test cache miss."""
    await cache_manager.setup_memory_cache()

    value = await cache_manager.get("non_existent_key")
    assert value is None

    stats = cache_manager.get_stats()
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_manager_delete(cache_manager):
    """Test delete operation."""
    await cache_manager.setup_memory_cache()

    # Set and then delete
    await cache_manager.set("test_key", "test_value")
    await cache_manager.delete("test_key")

    # Should not exist anymore
    value = await cache_manager.get("test_key")
    assert value is None

    stats = cache_manager.get_stats()
    assert stats["deletes"] == 1


@pytest.mark.asyncio
async def test_cache_manager_clear(cache_manager):
    """Test clearing cache."""
    await cache_manager.setup_memory_cache()

    # Set multiple values
    await cache_manager.set("key1", "value1")
    await cache_manager.set("key2", "value2")

    # Clear all
    await cache_manager.clear()

    # Both should be gone
    assert await cache_manager.get("key1") is None
    assert await cache_manager.get("key2") is None


@pytest.mark.asyncio
async def test_cache_manager_exists(cache_manager):
    """Test checking if key exists."""
    await cache_manager.setup_memory_cache()

    await cache_manager.set("test_key", "test_value")

    assert await cache_manager.exists("test_key") is True
    assert await cache_manager.exists("non_existent") is False


@pytest.mark.asyncio
async def test_cache_manager_get_many(cache_manager):
    """Test getting multiple keys at once."""
    await cache_manager.setup_memory_cache()

    # Set multiple values
    await cache_manager.set("key1", "value1")
    await cache_manager.set("key2", "value2")

    # Get many
    values = await cache_manager.get_many(["key1", "key2", "key3"])

    assert values == {"key1": "value1", "key2": "value2", "key3": None}


@pytest.mark.asyncio
async def test_cache_manager_set_many(cache_manager):
    """Test setting multiple keys at once."""
    await cache_manager.setup_memory_cache()

    # Set many
    await cache_manager.set_many({"key1": "value1", "key2": "value2"})

    # Verify all were set
    assert await cache_manager.get("key1") == "value1"
    assert await cache_manager.get("key2") == "value2"


@pytest.mark.asyncio
async def test_cache_manager_delete_many(cache_manager):
    """Test deleting multiple keys at once."""
    await cache_manager.setup_memory_cache()

    # Set values
    await cache_manager.set_many({"key1": "value1", "key2": "value2", "key3": "value3"})

    # Delete some
    await cache_manager.delete_many(["key1", "key3"])

    # Check what remains
    assert await cache_manager.get("key1") is None
    assert await cache_manager.get("key2") == "value2"
    assert await cache_manager.get("key3") is None


def test_cache_manager_enable_disable(cache_manager):
    """Test enabling/disabling cache."""
    assert cache_manager.is_enabled is True

    cache_manager.disable()
    assert cache_manager.is_enabled is False

    cache_manager.enable()
    assert cache_manager.is_enabled is True


@pytest.mark.asyncio
async def test_cache_manager_disabled_operations(cache_manager):
    """Test operations when cache is disabled."""
    await cache_manager.setup_memory_cache()
    cache_manager.disable()

    # Set should not store when disabled
    await cache_manager.set("test_key", "test_value")

    # Get should return None
    value = await cache_manager.get("test_key")
    assert value is None

    # Stats should not be updated
    stats = cache_manager.get_stats()
    assert stats["sets"] == 0
    assert stats["misses"] == 0


def test_cache_manager_reset_stats(cache_manager):
    """Test resetting statistics."""
    # Manually set some stats
    cache_manager._stats = {"hits": 10, "misses": 5, "sets": 15, "deletes": 3}

    cache_manager.reset_stats()

    stats = cache_manager.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["sets"] == 0
    assert stats["deletes"] == 0


@pytest.mark.asyncio
async def test_cache_manager_no_backend_operations(cache_manager):
    """Test operations without backend setup."""
    # Without backend, operations should handle gracefully

    # Get should return None
    assert await cache_manager.get("key") is None

    # Set should not fail
    await cache_manager.set("key", "value")

    # Exists should return False
    assert await cache_manager.exists("key") is False

    # Delete should not fail
    await cache_manager.delete("key")

    # Clear should not fail
    await cache_manager.clear()


@pytest.mark.asyncio
async def test_cache_manager_hit_rate(cache_manager):
    """Test cache hit rate calculation."""
    await cache_manager.setup_memory_cache()

    # Initial hit rate should be 0
    assert cache_manager.get_hit_rate() == 0.0

    # Create some hits and misses
    await cache_manager.set("key1", "value1")
    await cache_manager.get("key1")  # Hit
    await cache_manager.get("key2")  # Miss
    await cache_manager.get("key1")  # Hit

    # Hit rate should be 2/3 = 0.667
    hit_rate = cache_manager.get_hit_rate()
    assert 0.66 < hit_rate < 0.67
