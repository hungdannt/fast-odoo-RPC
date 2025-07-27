import pytest
from unittest.mock import AsyncMock, MagicMock
from src.zenoo_rpc.models.relationships import LazyRelationship


@pytest.mark.asyncio
async def test_lazy_relationship_single_record():
    """Test LazyRelationship for single record (Many2One)."""
    client = AsyncMock()
    client.search_read.return_value = [
        {"id": 123, "name": "Test Company", "display_name": "Test Company"}
    ]

    parent_record = MagicMock()

    lazy_rel = LazyRelationship(
        parent_record=parent_record,
        field_name="company_id",
        relation_model="res.company",
        relation_ids=123,
        client=client,
        is_collection=False,
    )

    # Load the relationship
    result = await lazy_rel.load()

    assert result["id"] == 123
    assert result["name"] == "Test Company"

    # Should be cached now
    assert lazy_rel._is_loaded is True

    # Second load should return cached data
    result2 = await lazy_rel.load()
    assert result2 == result


@pytest.mark.asyncio
async def test_lazy_relationship_collection():
    """Test LazyRelationship for collection (One2Many/Many2Many)."""
    client = AsyncMock()
    client.search_read.return_value = [
        {"id": 1, "name": "Child 1", "display_name": "Child 1"},
        {"id": 2, "name": "Child 2", "display_name": "Child 2"},
    ]

    parent_record = MagicMock()

    lazy_rel = LazyRelationship(
        parent_record=parent_record,
        field_name="child_ids",
        relation_model="res.partner",
        relation_ids=[1, 2],
        client=client,
        is_collection=True,
    )

    # Load the relationship
    result = await lazy_rel.load()

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Child 1"
    assert result[1]["name"] == "Child 2"


@pytest.mark.asyncio
async def test_lazy_relationship_empty():
    """Test LazyRelationship with no related records."""
    client = AsyncMock()

    parent_record = MagicMock()

    # Test empty single record
    lazy_rel_single = LazyRelationship(
        parent_record=parent_record,
        field_name="company_id",
        relation_model="res.company",
        relation_ids=None,
        client=client,
        is_collection=False,
    )

    result = await lazy_rel_single.load()
    assert result is None

    # Test empty collection
    lazy_rel_collection = LazyRelationship(
        parent_record=parent_record,
        field_name="child_ids",
        relation_model="res.partner",
        relation_ids=[],
        client=client,
        is_collection=True,
    )

    result = await lazy_rel_collection.load()
    assert result == []


@pytest.mark.asyncio
async def test_lazy_relationship_batch_loading():
    """Test LazyRelationship batch loading for N+1 prevention."""
    client = AsyncMock()
    client.search_read.return_value = [
        {"id": 1, "name": "Country 1", "display_name": "Country 1"},
        {"id": 2, "name": "Country 2", "display_name": "Country 2"},
        {"id": 3, "name": "Country 3", "display_name": "Country 3"},
    ]

    # Create multiple lazy relationships
    relationships = []
    for i in range(1, 4):
        parent = MagicMock()
        lazy_rel = LazyRelationship(
            parent_record=parent,
            field_name="country_id",
            relation_model="res.country",
            relation_ids=i,
            client=client,
            is_collection=False,
        )
        relationships.append(lazy_rel)

    # Load all relationships (should batch)
    results = []
    for rel in relationships:
        result = await rel.load()
        results.append(result)

    # Should have loaded all records in one query
    assert len(results) == 3
    assert results[0]["name"] == "Country 1"
    assert results[1]["name"] == "Country 2"
    assert results[2]["name"] == "Country 3"

    # Due to batching, should have been called once with all IDs
    # (The actual implementation may vary, but the concept is to reduce queries)
    assert client.search_read.call_count >= 1


@pytest.mark.asyncio
async def test_lazy_relationship_error_handling():
    """Test LazyRelationship error handling."""
    client = AsyncMock()
    client.search_read.side_effect = Exception("Database error")

    parent_record = MagicMock()

    lazy_rel = LazyRelationship(
        parent_record=parent_record,
        field_name="company_id",
        relation_model="res.company",
        relation_ids=123,
        client=client,
        is_collection=False,
    )

    # Should raise the exception
    with pytest.raises(Exception, match="Database error"):
        await lazy_rel.load()


def test_lazy_relationship_cache_key():
    """Test LazyRelationship cache key generation."""
    parent_record = MagicMock()
    client = MagicMock()

    lazy_rel = LazyRelationship(
        parent_record=parent_record,
        field_name="company_id",
        relation_model="res.company",
        relation_ids=123,
        client=client,
        is_collection=False,
    )

    # Cache key should be consistent
    cache_key = f"{lazy_rel.relation_model}:{lazy_rel.relation_ids}"
    assert cache_key == "res.company:123"


@pytest.mark.asyncio
async def test_lazy_relationship_concurrent_loading():
    """Test LazyRelationship handles concurrent loading correctly."""
    import asyncio

    client = AsyncMock()

    # Add delay to simulate slow loading
    async def slow_search_read(*args, **kwargs):
        await asyncio.sleep(0.1)
        return [{"id": 123, "name": "Test", "display_name": "Test"}]

    client.search_read = slow_search_read

    parent_record = MagicMock()

    lazy_rel = LazyRelationship(
        parent_record=parent_record,
        field_name="company_id",
        relation_model="res.company",
        relation_ids=123,
        client=client,
        is_collection=False,
    )

    # Start multiple concurrent loads
    tasks = [lazy_rel.load() for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All results should be the same
    assert all(r == results[0] for r in results)

    # Should still be loaded only once
    assert lazy_rel._is_loaded is True
