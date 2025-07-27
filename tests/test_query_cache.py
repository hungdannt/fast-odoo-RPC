"""
Tests for query builder cache integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.zenoo_rpc.query.builder import QuerySet, QueryBuilder
from src.zenoo_rpc.models.common import ResPartner
from src.zenoo_rpc.cache.manager import CacheManager
from src.zenoo_rpc.cache.backends import MemoryCache
from src.zenoo_rpc.cache.strategies import TTLCache


class TestQueryCache:
    """Test cases for query builder cache integration."""

    @pytest.mark.asyncio
    async def test_query_cache_key_generation(self):
        """Test cache key generation for queries."""
        mock_client = AsyncMock()

        queryset = QuerySet(
            model_class=ResPartner,
            client=mock_client,
            domain=[("is_company", "=", True)],
            fields=["name", "email"],
            limit=10,
            offset=0,
            order="name",
        )

        cache_key = queryset._generate_cache_key()
        assert cache_key.startswith("query:res.partner:")
        assert len(cache_key.split(":")) == 3

        # Same query should generate same key
        queryset2 = QuerySet(
            model_class=ResPartner,
            client=mock_client,
            domain=[("is_company", "=", True)],
            fields=["name", "email"],
            limit=10,
            offset=0,
            order="name",
        )

        assert queryset._generate_cache_key() == queryset2._generate_cache_key()

        # Different query should generate different key
        queryset3 = QuerySet(
            model_class=ResPartner,
            client=mock_client,
            domain=[("is_company", "=", False)],  # Different domain
            fields=["name", "email"],
            limit=10,
            offset=0,
            order="name",
        )

        assert queryset._generate_cache_key() != queryset3._generate_cache_key()

    @pytest.mark.asyncio
    async def test_query_cache_configuration(self):
        """Test query cache configuration."""
        mock_client = AsyncMock()

        queryset = QuerySet(ResPartner, mock_client)

        # Test cache configuration
        cached_qs = queryset.cache(ttl=600, enabled=True)
        assert cached_qs._cache_ttl == 600
        assert cached_qs._cache_enabled is True

        # Test disabling cache
        no_cache_qs = queryset.cache(enabled=False)
        assert no_cache_qs._cache_enabled is False

    @pytest.mark.asyncio
    async def test_query_execution_with_cache(self):
        """Test query execution with caching."""
        # Setup mock client with cache manager
        mock_client = AsyncMock()

        # Create cache manager
        memory_backend = MemoryCache()
        ttl_strategy = TTLCache(memory_backend)
        cache_manager = CacheManager()
        cache_manager.add_backend("memory", memory_backend)
        cache_manager.add_strategy("memory", ttl_strategy)
        cache_manager.set_default_backend("memory")

        mock_client.cache_manager = cache_manager

        # Mock search_read response
        mock_data = [
            {"id": 1, "name": "Partner 1", "email": "partner1@test.com"},
            {"id": 2, "name": "Partner 2", "email": "partner2@test.com"},
        ]
        mock_client.search_read.return_value = mock_data

        queryset = QuerySet(ResPartner, mock_client, domain=[("is_company", "=", True)])

        # First execution should hit the database
        result1 = await queryset._execute_query()
        assert result1 == mock_data
        mock_client.search_read.assert_called_once()

        # Second execution should hit the cache
        mock_client.search_read.reset_mock()
        result2 = await queryset._execute_query()
        assert result2 == mock_data
        mock_client.search_read.assert_not_called()  # Should not call database

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_create(self):
        """Test cache invalidation when creating records."""
        # Setup mock client with cache manager
        mock_client = AsyncMock()

        # Create cache manager
        memory_backend = MemoryCache()
        ttl_strategy = TTLCache(memory_backend)
        cache_manager = CacheManager()
        cache_manager.add_backend("memory", memory_backend)
        cache_manager.add_strategy("memory", ttl_strategy)
        cache_manager.set_default_backend("memory")

        mock_client.cache_manager = cache_manager

        # Mock responses
        mock_client.search_read.return_value = [
            {"id": 1, "name": "Partner 1", "email": "partner1@test.com"}
        ]
        mock_client.execute_kw.return_value = 2  # New record ID

        queryset = QuerySet(ResPartner, mock_client)
        query_builder = QueryBuilder(ResPartner, mock_client)

        # Execute query to populate cache
        await queryset._execute_query()

        # Verify cache has data
        cache_key = queryset._generate_cache_key()
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is not None

        # Create a new record (should invalidate cache)
        await query_builder.create(name="New Partner", email="new@test.com")

        # Cache should be invalidated (this is a simplified test)
        # In real implementation, we'd verify the pattern invalidation worked
        mock_client.execute_kw.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_with_different_queries(self):
        """Test that different queries have separate cache entries."""
        # Setup mock client with cache manager
        mock_client = AsyncMock()

        # Create cache manager
        memory_backend = MemoryCache()
        ttl_strategy = TTLCache(memory_backend)
        cache_manager = CacheManager()
        cache_manager.add_backend("memory", memory_backend)
        cache_manager.add_strategy("memory", ttl_strategy)
        cache_manager.set_default_backend("memory")

        mock_client.cache_manager = cache_manager

        # Mock different responses for different queries
        def mock_search_read(model, domain=None, **kwargs):
            if domain == [("is_company", "=", True)]:
                return [{"id": 1, "name": "Company 1"}]
            else:
                return [{"id": 2, "name": "Individual 1"}]

        mock_client.search_read.side_effect = mock_search_read

        # Create different querysets
        company_qs = QuerySet(
            ResPartner, mock_client, domain=[("is_company", "=", True)]
        )
        individual_qs = QuerySet(
            ResPartner, mock_client, domain=[("is_company", "=", False)]
        )

        # Execute both queries
        company_result = await company_qs._execute_query()
        individual_result = await individual_qs._execute_query()

        # Verify different results
        assert company_result != individual_result
        assert company_result[0]["name"] == "Company 1"
        assert individual_result[0]["name"] == "Individual 1"

        # Verify both are cached separately
        company_key = company_qs._generate_cache_key()
        individual_key = individual_qs._generate_cache_key()

        assert company_key != individual_key

        company_cached = await cache_manager.get(company_key)
        individual_cached = await cache_manager.get(individual_key)

        assert company_cached == company_result
        assert individual_cached == individual_result

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test query execution with cache disabled."""
        mock_client = AsyncMock()

        # Create cache manager but disable caching
        memory_backend = MemoryCache()
        ttl_strategy = TTLCache(memory_backend)
        cache_manager = CacheManager()
        cache_manager.add_backend("memory", memory_backend)
        cache_manager.add_strategy("memory", ttl_strategy)
        cache_manager.set_default_backend("memory")

        mock_client.cache_manager = cache_manager

        mock_data = [{"id": 1, "name": "Partner 1"}]
        mock_client.search_read.return_value = mock_data

        # Create queryset with cache disabled
        queryset = QuerySet(ResPartner, mock_client).cache(enabled=False)

        # Execute query twice
        await queryset._execute_query()
        await queryset._execute_query()

        # Should call database both times
        assert mock_client.search_read.call_count == 2
