import pytest
from unittest.mock import AsyncMock, MagicMock
from src.zenoo_rpc.query.lazy import LazyLoader, LazyCollection, PrefetchManager


@pytest.mark.asyncio
async def test_lazy_loader_basic():
    """Test basic LazyLoader functionality."""

    # Mock loader function
    async def loader_func(model, id):
        return {"id": id, "model": model, "name": "Test Object"}

    loader = LazyLoader(loader_func, "res.partner", 123)

    # Initially not loaded
    assert not loader.is_loaded()
    assert loader.get_cached_data() is None

    # Load data
    result = await loader.load()
    assert result == {"id": 123, "model": "res.partner", "name": "Test Object"}
    assert loader.is_loaded()
    assert loader.get_cached_data() == result

    # Second load should return cached data
    result2 = await loader.load()
    assert result2 == result


@pytest.mark.asyncio
async def test_lazy_loader_await():
    """Test LazyLoader as awaitable."""

    async def loader_func():
        return "loaded data"

    loader = LazyLoader(loader_func)
    result = await loader  # Use loader as awaitable
    assert result == "loaded data"


@pytest.mark.asyncio
async def test_lazy_loader_invalidate():
    """Test LazyLoader cache invalidation."""
    call_count = 0

    async def loader_func():
        nonlocal call_count
        call_count += 1
        return f"load {call_count}"

    loader = LazyLoader(loader_func)

    # First load
    result1 = await loader.load()
    assert result1 == "load 1"
    assert call_count == 1

    # Second load (cached)
    result2 = await loader.load()
    assert result2 == "load 1"
    assert call_count == 1

    # Invalidate and reload
    loader.invalidate()
    assert not loader.is_loaded()

    result3 = await loader.load()
    assert result3 == "load 2"
    assert call_count == 2


@pytest.mark.asyncio
async def test_lazy_collection_basic():
    """Test basic LazyCollection functionality."""

    async def loader_func():
        return [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]

    collection = LazyCollection(loader_func)

    # Initially not loaded
    assert not collection.is_loaded()
    assert collection.get_cached_items() is None

    # Load all items
    items = await collection.all()
    assert len(items) == 3
    assert items[0]["name"] == "Item 1"
    assert collection.is_loaded()


@pytest.mark.asyncio
async def test_lazy_collection_first():
    """Test LazyCollection first() method."""

    async def loader_func():
        return [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}]

    collection = LazyCollection(loader_func)
    first = await collection.first()
    assert first["name"] == "First"


@pytest.mark.asyncio
async def test_lazy_collection_empty():
    """Test LazyCollection with empty results."""

    async def loader_func():
        return []

    collection = LazyCollection(loader_func)

    items = await collection.all()
    assert items == []

    first = await collection.first()
    assert first is None

    count = await collection.count()
    assert count == 0

    exists = await collection.exists()
    assert exists is False


@pytest.mark.asyncio
async def test_lazy_collection_iteration():
    """Test LazyCollection async iteration."""

    async def loader_func():
        return [{"id": i, "value": i * 10} for i in range(1, 4)]

    collection = LazyCollection(loader_func)

    values = []
    async for item in collection:
        values.append(item["value"])

    assert values == [10, 20, 30]


@pytest.mark.asyncio
async def test_lazy_collection_awaitable():
    """Test LazyCollection as awaitable."""

    async def loader_func():
        return ["a", "b", "c"]

    collection = LazyCollection(loader_func)
    items = await collection  # Use collection as awaitable
    assert items == ["a", "b", "c"]


def test_prefetch_manager_initialization():
    """Test PrefetchManager initialization."""
    client = MagicMock()
    manager = PrefetchManager(client)

    assert manager.client == client
    assert hasattr(manager, "_prefetch_cache")


@pytest.mark.asyncio
async def test_prefetch_manager_empty_call():
    """Test PrefetchManager with empty inputs."""
    client = AsyncMock()
    manager = PrefetchManager(client)

    # Should handle empty list gracefully
    await manager.prefetch_related([], "field1", "field2")

    # Should handle no fields gracefully
    instances = [MagicMock(), MagicMock()]
    await manager.prefetch_related(instances)

    # No calls should be made
    client.search_read.assert_not_called()
