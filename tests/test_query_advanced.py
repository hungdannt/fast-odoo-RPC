"""
Advanced tests for Zenoo-RPC query builder and lazy loading.

This module tests advanced query functionality including:
- Complex query building and chaining
- Lazy loading and relationship queries
- Query optimization and caching
- Advanced filtering and expressions
- Edge cases and error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any, Optional

from zenoo_rpc.query.builder import QueryBuilder, QuerySet
from zenoo_rpc.query.filters import Q, FilterExpression
from zenoo_rpc.query.expressions import (
    Field,
    Equal,
    NotEqual,
    GreaterThan,
    LessThan,
    GreaterEqual,
    LessEqual,
    Like,
    ILike,
    In,
    NotIn,
    Contains,
    StartsWith,
    EndsWith,
)
from zenoo_rpc.query.lazy import LazyLoader, LazyCollection
from zenoo_rpc.models.common import ResPartner, ResCountry, SaleOrder, SaleOrderLine


class TestAdvancedQueryBuilder:
    """Test advanced query builder functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.query_builder = QueryBuilder(ResPartner, self.mock_client)

    def test_complex_query_chaining(self):
        """Test complex query chaining."""
        queryset = (
            self.query_builder.filter(is_company=True)
            .filter(Q(name__ilike="acme%") | Q(name__ilike="test%"))
            .exclude(active=False)
            .order_by("-create_date", "name")
            .limit(50)
            .offset(100)
            .only("id", "name", "email", "phone")
            .with_context(lang="en_US", tz="UTC")
        )

        # Verify query structure
        assert len(queryset._domain) >= 3  # is_company, name filters, exclude active
        assert queryset._order == "create_date desc, name"
        assert queryset._limit == 50
        assert queryset._offset == 100
        assert set(queryset._fields) == {"id", "name", "email", "phone"}
        assert queryset._context["lang"] == "en_US"
        assert queryset._context["tz"] == "UTC"

    def test_nested_q_objects(self):
        """Test nested Q object combinations."""
        # Complex query: (name contains "company" OR is_company=True) AND (country is US OR CA) AND active=True
        complex_q = (
            (Q(name__contains="company") | Q(is_company=True))
            & (Q(country_id__name="United States") | Q(country_id__name="Canada"))
            & Q(active=True)
        )

        queryset = self.query_builder.filter(complex_q)
        domain = queryset._domain

        # Should contain logical operators and conditions
        assert len(domain) > 0
        assert any(op in domain for op in ["&", "|"])  # Should have logical operators

    def test_field_expressions_advanced(self):
        """Test advanced field expressions."""
        name_field = Field("name")
        date_field = Field("create_date")
        amount_field = Field("credit_limit")

        # Test complex expressions
        queryset = self.query_builder.filter(
            name_field.ilike("company%"),
            date_field >= "2023-01-01",
            (amount_field >= 1000) & (amount_field <= 50000),
            Field("email").is_not_null(),
            Field("category_id").in_([1, 2, 3, 4]),
        )

        domain = queryset._domain
        assert len(domain) >= 5

        # Check specific conditions
        assert ("name", "ilike", "company%") in domain
        assert ("create_date", ">=", "2023-01-01") in domain
        assert ("email", "!=", False) in domain
        # Note: in_ method should be used instead of in
        # This test may need adjustment based on actual implementation

    def test_subquery_simulation(self):
        """Test subquery-like functionality."""
        # Simulate subquery: partners whose orders have total > 1000
        # In real Odoo, this would be done with domain filters

        # First, get order IDs with total > 1000
        order_queryset = QuerySet(SaleOrder, self.mock_client).filter(
            amount_total__gt=1000
        )

        # Then filter partners by those order IDs
        partner_queryset = self.query_builder.filter(
            sale_order_ids__in=order_queryset  # This would need special handling
        )

        # For now, just verify the query structure is built correctly
        assert isinstance(partner_queryset, QuerySet)

    @pytest.mark.asyncio
    async def test_query_optimization(self):
        """Test query optimization features."""
        # Mock data
        mock_data = [
            {"id": 1, "name": "Company A", "email": "a@company.com"},
            {"id": 2, "name": "Company B", "email": "b@company.com"},
        ]
        self.mock_client.search_read.return_value = mock_data

        # Test query with only specific fields
        queryset = self.query_builder.filter(is_company=True).only(
            "id", "name", "email"
        )

        results = await queryset.all()

        # Verify only requested fields were fetched
        call_args = self.mock_client.search_read.call_args
        assert "fields" in call_args[1]
        assert set(call_args[1]["fields"]) == {"id", "name", "email"}

    @pytest.mark.asyncio
    async def test_query_with_prefetch(self):
        """Test query with relationship prefetching."""
        # Mock partner data with country relationships
        mock_partners = [
            {"id": 1, "name": "Partner 1", "country_id": [1, "United States"]},
            {"id": 2, "name": "Partner 2", "country_id": [2, "Canada"]},
        ]

        # Mock country data
        mock_countries = [
            {"id": 1, "name": "United States", "code": "US"},
            {"id": 2, "name": "Canada", "code": "CA"},
        ]

        self.mock_client.search_read.side_effect = [mock_partners, mock_countries]

        # Query with prefetch
        queryset = self.query_builder.filter(is_company=True).prefetch_related(
            "country_id"
        )

        results = await queryset.all()

        assert len(results) == 2
        # Verify prefetch was attempted (would need actual implementation)
        assert self.mock_client.search_read.call_count >= 1

    @pytest.mark.asyncio
    async def test_query_aggregation(self):
        """Test query aggregation functions."""
        # Mock aggregation response
        self.mock_client.execute_kw.return_value = 150

        # Test count query (basic aggregation)
        queryset = self.query_builder.filter(is_company=True)
        count = await queryset.count()

        assert count == 150
        assert self.mock_client.execute_kw.called

    def test_query_annotation(self):
        """Test query annotation functionality."""
        # Test basic query structure (annotation would need implementation)
        queryset = self.query_builder.filter(is_company=True)

        # For now, just verify the query structure
        assert isinstance(queryset, QuerySet)
        # Actual annotation would need implementation in the query builder


class TestLazyLoading:
    """Test lazy loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()

    @pytest.mark.asyncio
    async def test_lazy_relationship_loading(self):
        """Test lazy loading of relationships."""
        # Mock partner with country relationship
        partner = ResPartner(
            id=1, name="Test Partner", country_id=123, client=self.mock_client
        )

        # Mock country data
        country_data = {"id": 123, "name": "United States", "code": "US"}
        self.mock_client.search_read.return_value = [country_data]

        # Access relationship (should trigger lazy loading)
        country = await partner.country_id

        assert isinstance(country, ResCountry)
        assert country.id == 123
        assert country.name == "United States"

        # Verify lazy loading was called
        self.mock_client.search_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_lazy_collection_loading(self):
        """Test lazy loading of collections."""
        # Mock partner with order relationships
        partner = ResPartner(id=1, name="Test Partner", client=self.mock_client)

        # Mock order data
        order_data = [
            {"id": 10, "name": "SO001", "partner_id": 1, "amount_total": 1000.0},
            {"id": 11, "name": "SO002", "partner_id": 1, "amount_total": 2000.0},
        ]
        self.mock_client.search_read.return_value = order_data

        # Access collection (should trigger lazy loading)
        orders = await partner.sale_order_ids.all()

        assert len(orders) == 2
        assert all(isinstance(order, SaleOrder) for order in orders)
        assert orders[0].name == "SO001"
        assert orders[1].amount_total == 2000.0

    @pytest.mark.asyncio
    async def test_lazy_collection_filtering(self):
        """Test filtering on lazy collections."""
        partner = ResPartner(id=1, name="Test Partner", client=self.mock_client)

        # Mock filtered order data
        filtered_order_data = [
            {"id": 10, "name": "SO001", "partner_id": 1, "amount_total": 5000.0}
        ]
        self.mock_client.search_read.return_value = filtered_order_data

        # Filter collection
        large_orders = await partner.sale_order_ids.filter(amount_total__gt=1000).all()

        assert len(large_orders) == 1
        assert large_orders[0].amount_total == 5000.0

        # Verify filter was applied in domain
        call_args = self.mock_client.search_read.call_args
        domain = call_args[0][1]
        assert ("partner_id", "=", 1) in domain
        assert ("amount_total", ">", 1000) in domain

    @pytest.mark.asyncio
    async def test_lazy_collection_pagination(self):
        """Test pagination on lazy collections."""
        partner = ResPartner(id=1, name="Test Partner", client=self.mock_client)

        # Mock paginated data
        page_data = [
            {"id": i, "name": f"SO{i:03d}", "partner_id": 1}
            for i in range(10, 20)  # 10 records
        ]
        self.mock_client.search_read.return_value = page_data

        # Get paginated results
        orders = await partner.sale_order_ids.limit(10).offset(10).all()

        assert len(orders) == 10

        # Verify pagination parameters
        call_args = self.mock_client.search_read.call_args
        assert call_args[1]["limit"] == 10
        assert call_args[1]["offset"] == 10

    @pytest.mark.asyncio
    async def test_lazy_loading_caching(self):
        """Test caching in lazy loading."""
        partner = ResPartner(
            id=1, name="Test Partner", country_id=123, client=self.mock_client
        )

        # Mock country data
        country_data = {"id": 123, "name": "United States", "code": "US"}
        self.mock_client.search_read.return_value = [country_data]

        # Access relationship multiple times
        country1 = await partner.country_id
        country2 = await partner.country_id

        # Should be the same object (cached)
        assert country1 is country2

        # Should only call client once (cached after first call)
        assert self.mock_client.search_read.call_count == 1


class TestQueryEdgeCases:
    """Test query edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.query_builder = QueryBuilder(ResPartner, self.mock_client)

    def test_empty_query(self):
        """Test empty query handling."""
        queryset = self.query_builder.all()

        # Should have empty domain
        assert queryset._domain == []
        assert queryset._limit is None
        assert queryset._offset == 0

    def test_invalid_field_names(self):
        """Test handling of invalid field names."""
        # This should not raise an error at query build time
        # but might at execution time
        queryset = self.query_builder.filter(invalid_field="value")

        assert len(queryset._domain) == 1
        assert ("invalid_field", "=", "value") in queryset._domain

    def test_conflicting_filters(self):
        """Test conflicting filter conditions."""
        # Add conflicting conditions
        queryset = self.query_builder.filter(active=True).filter(active=False)

        # Both conditions should be in domain (AND logic)
        domain = queryset._domain
        assert ("active", "=", True) in domain
        assert ("active", "=", False) in domain

    @pytest.mark.asyncio
    async def test_query_execution_error(self):
        """Test query execution error handling."""
        # Mock client error
        self.mock_client.search_read.side_effect = Exception("Database error")

        queryset = self.query_builder.filter(is_company=True)

        with pytest.raises(Exception):
            await queryset.all()

    @pytest.mark.asyncio
    async def test_empty_result_handling(self):
        """Test handling of empty query results."""
        # Mock empty result
        self.mock_client.search_read.return_value = []

        queryset = self.query_builder.filter(name="NonExistent")
        results = await queryset.all()

        assert results == []
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_large_result_set(self):
        """Test handling of large result sets."""
        # Mock large result set
        large_data = [
            {"id": i, "name": f"Partner {i}", "is_company": True}
            for i in range(1, 1001)  # 1000 records
        ]
        self.mock_client.search_read.return_value = large_data

        queryset = self.query_builder.filter(is_company=True)
        results = await queryset.all()

        assert len(results) == 1000
        assert all(isinstance(partner, ResPartner) for partner in results)

    def test_query_cloning(self):
        """Test query cloning and immutability."""
        original = self.query_builder.filter(is_company=True).limit(10)

        # Clone with modifications
        cloned = original.filter(active=True).limit(20)

        # Original should be unchanged
        assert original._limit == 10
        assert len(original._domain) == 1

        # Clone should have modifications
        assert cloned._limit == 20
        assert len(cloned._domain) == 2

    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """Test concurrent query execution."""
        # Mock different responses for concurrent queries
        responses = [
            [{"id": 1, "name": "Company A"}],
            [{"id": 2, "name": "Person B"}],
            [{"id": 3, "name": "Company C"}],
        ]
        self.mock_client.search_read.side_effect = responses

        # Create concurrent queries
        query1 = self.query_builder.filter(is_company=True)
        query2 = self.query_builder.filter(is_company=False)
        query3 = self.query_builder.filter(name__ilike="company%")

        # Execute concurrently
        results = await asyncio.gather(query1.all(), query2.all(), query3.all())

        assert len(results) == 3
        assert len(results[0]) == 1
        assert len(results[1]) == 1
        assert len(results[2]) == 1

        # Verify all queries were executed
        assert self.mock_client.search_read.call_count == 3


class TestQueryPerformance:
    """Test query performance optimizations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.query_builder = QueryBuilder(ResPartner, self.mock_client)

    @pytest.mark.asyncio
    async def test_query_batching(self):
        """Test query batching for large datasets."""
        # Mock large dataset
        batch_size = 100
        total_records = 250

        # Mock responses for batched queries
        batches = []
        for i in range(0, total_records, batch_size):
            batch = [
                {"id": j, "name": f"Partner {j}"}
                for j in range(i + 1, min(i + batch_size + 1, total_records + 1))
            ]
            batches.append(batch)

        self.mock_client.search_read.side_effect = batches

        # Execute query with batching (would need implementation)
        queryset = self.query_builder.filter(is_company=True)

        # For now, just test regular execution
        results = await queryset.all()

        # Verify client was called
        assert self.mock_client.search_read.called

    @pytest.mark.asyncio
    async def test_query_caching(self):
        """Test query result caching."""
        # Mock data
        mock_data = [{"id": 1, "name": "Cached Partner"}]
        self.mock_client.search_read.return_value = mock_data

        queryset = self.query_builder.filter(is_company=True)

        # Execute query multiple times
        results1 = await queryset.all()
        results2 = await queryset.all()

        # Both should return same data
        assert results1 == results2

        # Client should be called for each execution (no caching implemented yet)
        assert self.mock_client.search_read.call_count == 2

    def test_query_optimization_hints(self):
        """Test query optimization hints."""
        # Test various optimization hints
        queryset = (
            self.query_builder.filter(is_company=True)
            .hint("use_index", "partner_company_idx")
            .hint("batch_size", 500)
            .hint("prefetch", ["country_id", "parent_id"])
        )

        # For now, just verify the query structure
        assert isinstance(queryset, QuerySet)
        # Actual optimization hints would need implementation
