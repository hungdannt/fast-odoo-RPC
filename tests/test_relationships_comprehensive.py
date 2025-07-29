"""
Comprehensive tests for relationships module to improve coverage.

This test file focuses on testing scenarios and methods that are not covered
in the basic test_relationships.py file to increase overall coverage.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.zenoo_rpc.models.relationships import (
    LazyRelationship, 
    RelationshipManager
)


class TestLazyRelationshipComprehensive:
    """Comprehensive test cases for LazyRelationship."""

    @pytest.mark.asyncio
    async def test_lazy_relationship_awaitable(self):
        """Test LazyRelationship __await__ method."""
        client = AsyncMock()
        client.search_read.return_value = [
            {"id": 123, "name": "Test", "display_name": "Test"}
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

        # Test awaiting the relationship directly
        result = await lazy_rel
        assert result["id"] == 123
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_lazy_relationship_all_method_single(self):
        """Test LazyRelationship all() method for single record."""
        client = AsyncMock()
        client.search_read.return_value = [
            {"id": 123, "name": "Test", "display_name": "Test"}
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

        # Test all() method for single record
        result = await lazy_rel.all()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 123

    @pytest.mark.asyncio
    async def test_lazy_relationship_all_method_collection(self):
        """Test LazyRelationship all() method for collection."""
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

        # Test all() method for collection
        result = await lazy_rel.all()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Child 1"
        assert result[1]["name"] == "Child 2"

    @pytest.mark.asyncio
    async def test_lazy_relationship_all_method_empty(self):
        """Test LazyRelationship all() method with empty data."""
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

        result = await lazy_rel_single.all()
        assert result == []

        # Test empty collection
        lazy_rel_collection = LazyRelationship(
            parent_record=parent_record,
            field_name="child_ids",
            relation_model="res.partner",
            relation_ids=[],
            client=client,
            is_collection=True,
        )

        result = await lazy_rel_collection.all()
        assert result == []

    @pytest.mark.asyncio
    async def test_lazy_relationship_prefetch_cache(self):
        """Test LazyRelationship prefetch cache functionality."""
        client = AsyncMock()
        parent_record = MagicMock()

        # Clear any existing cache
        if hasattr(LazyRelationship, '_prefetch_cache'):
            LazyRelationship._prefetch_cache.clear()

        lazy_rel = LazyRelationship(
            parent_record=parent_record,
            field_name="company_id",
            relation_model="res.company",
            relation_ids=123,
            client=client,
            is_collection=False,
        )

        # Manually populate prefetch cache
        cache_key = f"{lazy_rel.relation_model}:{lazy_rel.relation_ids}"
        LazyRelationship._prefetch_cache[cache_key] = {
            "id": 123, "name": "Cached", "display_name": "Cached"
        }

        # Load should return cached data without calling client
        result = await lazy_rel.load()
        assert result["name"] == "Cached"
        client.search_read.assert_not_called()

    @pytest.mark.asyncio
    async def test_lazy_relationship_batch_loading_mechanism(self):
        """Test LazyRelationship batch loading mechanism in detail."""
        client = AsyncMock()
        client.search_read.return_value = [
            {"id": 1, "name": "Item 1", "display_name": "Item 1"},
            {"id": 2, "name": "Item 2", "display_name": "Item 2"},
        ]

        # Clear batch queues
        if hasattr(LazyRelationship, '_batch_queue'):
            LazyRelationship._batch_queue.clear()
        if hasattr(LazyRelationship, '_batch_tasks'):
            LazyRelationship._batch_tasks.clear()

        parent_record = MagicMock()

        # Create relationships that should be batched
        rel1 = LazyRelationship(
            parent_record=parent_record,
            field_name="category_id",
            relation_model="product.category",
            relation_ids=1,
            client=client,
            is_collection=False,
        )

        rel2 = LazyRelationship(
            parent_record=parent_record,
            field_name="category_id",
            relation_model="product.category",
            relation_ids=2,
            client=client,
            is_collection=False,
        )

        # Load both relationships
        result1 = await rel1.load()
        result2 = await rel2.load()

        assert result1["id"] == 1
        assert result2["id"] == 2

    @pytest.mark.asyncio
    async def test_lazy_relationship_loading_task_reuse(self):
        """Test LazyRelationship reuses loading task when already loading."""
        client = AsyncMock()

        # Create a slow loading function
        load_count = 0
        async def slow_load(*args, **kwargs):
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.1)
            return [{"id": 123, "name": "Test", "display_name": "Test"}]

        client.search_read = slow_load

        parent_record = MagicMock()
        lazy_rel = LazyRelationship(
            parent_record=parent_record,
            field_name="company_id",
            relation_model="res.company",
            relation_ids=123,
            client=client,
            is_collection=False,
        )

        # Start multiple loads concurrently
        tasks = [lazy_rel.load() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should return the same result
        assert all(r == results[0] for r in results)
        # But load should only be called once due to task reuse
        assert load_count == 1


class TestRelationshipManager:
    """Test cases for RelationshipManager."""

    def test_relationship_manager_init(self):
        """Test RelationshipManager initialization."""
        record = MagicMock()
        client = MagicMock()

        manager = RelationshipManager(record, client)

        assert manager.record == record
        assert manager.client == client
        assert manager._relationships == {}

    def test_parse_relation_data_many2one(self):
        """Test _parse_relation_data for Many2one fields."""
        record = MagicMock()
        client = MagicMock()
        manager = RelationshipManager(record, client)

        # Test with tuple format [id, name]
        result = manager._parse_relation_data([123, "Test Company"], False)
        assert result == 123

        # Test with integer ID
        result = manager._parse_relation_data(123, False)
        assert result == 123

        # Test with False (empty)
        result = manager._parse_relation_data(False, False)
        assert result is None

        # Test with None
        result = manager._parse_relation_data(None, False)
        assert result is None

    def test_parse_relation_data_one2many_many2many(self):
        """Test _parse_relation_data for One2many/Many2many fields."""
        record = MagicMock()
        client = MagicMock()
        manager = RelationshipManager(record, client)

        # Test with list of IDs
        result = manager._parse_relation_data([1, 2, 3], True)
        assert result == [1, 2, 3]

        # Test with empty list
        result = manager._parse_relation_data([], True)
        assert result == []

        # Test with False (empty)
        result = manager._parse_relation_data(False, True)
        assert result == []

        # Test with None
        result = manager._parse_relation_data(None, True)
        assert result == []

    def test_create_relationship(self):
        """Test create_relationship method."""
        record = MagicMock()
        client = MagicMock()
        manager = RelationshipManager(record, client)

        # Test creating Many2one relationship
        relationship = manager.create_relationship(
            field_name="company_id",
            relation_model="res.company",
            relation_data=123,
            is_collection=False
        )

        assert isinstance(relationship, LazyRelationship)
        assert relationship.field_name == "company_id"
        assert relationship.relation_model == "res.company"
        assert relationship.relation_ids == 123
        assert relationship.is_collection is False

        # Test creating One2many relationship
        relationship = manager.create_relationship(
            field_name="child_ids",
            relation_model="res.partner",
            relation_data=[1, 2, 3],
            is_collection=True
        )

        assert isinstance(relationship, LazyRelationship)
        assert relationship.field_name == "child_ids"
        assert relationship.relation_model == "res.partner"
        assert relationship.relation_ids == [1, 2, 3]
        assert relationship.is_collection is True

    @pytest.mark.asyncio
    async def test_prefetch_relationships(self):
        """Test prefetch_relationships method."""
        record = MagicMock()
        client = AsyncMock()
        manager = RelationshipManager(record, client)

        # Mock relationships
        rel1 = MagicMock()
        rel1.relation_model = "res.country"
        rel1.relation_ids = 1
        rel1.is_collection = False
        rel1._is_loaded = False

        rel2 = MagicMock()
        rel2.relation_model = "res.country"
        rel2.relation_ids = 2
        rel2.is_collection = False
        rel2._is_loaded = False

        manager._relationships = {
            "country_id": rel1,
            "state_id": rel2
        }

        # Mock client response
        client.search_read.return_value = [
            {"id": 1, "name": "Country 1"},
            {"id": 2, "name": "Country 2"}
        ]

        # Test prefetching
        await manager.prefetch_relationships(["country_id", "state_id"])

        # Verify client was called
        client.search_read.assert_called_once()

        # Verify relationships were marked as loaded
        assert rel1._is_loaded is True
        assert rel2._is_loaded is True

    @pytest.mark.asyncio
    async def test_prefetch_relationships_mixed_models(self):
        """Test prefetch_relationships with mixed models."""
        record = MagicMock()
        client = AsyncMock()
        manager = RelationshipManager(record, client)

        # Mock relationships with different models
        rel1 = MagicMock()
        rel1.relation_model = "res.country"
        rel1.relation_ids = 1
        rel1.is_collection = False
        rel1._is_loaded = False

        rel2 = MagicMock()
        rel2.relation_model = "res.partner"
        rel2.relation_ids = 2
        rel2.is_collection = False
        rel2._is_loaded = False

        manager._relationships = {
            "country_id": rel1,
            "partner_id": rel2
        }

        # Mock client responses
        client.search_read.side_effect = [
            [{"id": 1, "name": "Country 1"}],
            [{"id": 2, "name": "Partner 1"}]
        ]

        # Test prefetching
        await manager.prefetch_relationships(["country_id", "partner_id"])

        # Should be called twice (once per model)
        assert client.search_read.call_count == 2

    def test_invalidate_field(self):
        """Test invalidate_field method."""
        record = MagicMock()
        client = MagicMock()
        manager = RelationshipManager(record, client)

        # Mock relationship
        rel = MagicMock()
        rel._is_loaded = True
        rel._loaded_data = {"id": 123, "name": "Test"}

        manager._relationships = {"company_id": rel}

        # Test invalidation
        manager.invalidate_field("company_id")

        assert rel._is_loaded is False
        assert rel._loaded_data is None

    def test_invalidate_all(self):
        """Test invalidate_all method."""
        record = MagicMock()
        client = MagicMock()
        manager = RelationshipManager(record, client)

        # Mock multiple relationships
        rel1 = MagicMock()
        rel1._is_loaded = True
        rel1._loaded_data = {"id": 1}

        rel2 = MagicMock()
        rel2._is_loaded = True
        rel2._loaded_data = {"id": 2}

        manager._relationships = {
            "company_id": rel1,
            "partner_id": rel2
        }

        # Test invalidation
        manager.invalidate_all()

        assert rel1._is_loaded is False
        assert rel1._loaded_data is None
        assert rel2._is_loaded is False
        assert rel2._loaded_data is None
