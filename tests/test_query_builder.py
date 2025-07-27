"""
Tests for Zenoo-RPC query builder and fluent interface.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from zenoo_rpc.query.builder import QueryBuilder, QuerySet
from zenoo_rpc.query.filters import Q, FilterExpression
from zenoo_rpc.query.expressions import Field, Equal, Like
from zenoo_rpc.models.common import ResPartner


class TestQueryExpressions:
    """Test cases for query expressions."""

    def test_field_creation(self):
        """Test Field creation and basic operations."""
        name_field = Field("name")
        assert name_field.name == "name"

        # Test equality
        eq_expr = name_field == "John"
        assert isinstance(eq_expr, Equal)
        assert eq_expr.field == "name"
        assert eq_expr.value == "John"

        # Test like
        like_expr = name_field.like("John%")
        assert isinstance(like_expr, Like)
        assert like_expr.field == "name"
        assert like_expr.value == "John%"

    def test_expression_to_domain(self):
        """Test expression conversion to Odoo domain."""
        name_field = Field("name")

        # Test equality
        eq_expr = name_field == "John"
        domain = eq_expr.to_domain()
        assert domain == [("name", "=", "John")]

        # Test greater than
        age_field = Field("age")
        gt_expr = age_field > 18
        domain = gt_expr.to_domain()
        assert domain == [("age", ">", 18)]

        # Test ilike
        ilike_expr = name_field.ilike("john%")
        domain = ilike_expr.to_domain()
        assert domain == [("name", "ilike", "john%")]

    def test_expression_combination(self):
        """Test combining expressions with logical operators."""
        name_field = Field("name")
        age_field = Field("age")

        # Test AND
        and_expr = (name_field == "John") & (age_field > 18)
        domain = and_expr.to_domain()
        # AND is implicit in Odoo domains
        assert len(domain) == 2
        assert ("name", "=", "John") in domain
        assert ("age", ">", 18) in domain

        # Test OR
        or_expr = (name_field == "John") | (name_field == "Jane")
        domain = or_expr.to_domain()
        # OR requires explicit operator
        assert "|" in domain
        assert ("name", "=", "John") in domain
        assert ("name", "=", "Jane") in domain


class TestFilterExpression:
    """Test cases for FilterExpression."""

    def test_simple_filters(self):
        """Test simple keyword filters."""
        filter_expr = FilterExpression(name="John", age=25)
        domain = filter_expr.to_domain()

        assert len(domain) == 2
        assert ("name", "=", "John") in domain
        assert ("age", "=", 25) in domain

    def test_field_lookups(self):
        """Test Django-style field lookups."""
        # Test ilike
        filter_expr = FilterExpression(name__ilike="john%")
        domain = filter_expr.to_domain()
        assert domain == [("name", "ilike", "john%")]

        # Test greater than
        filter_expr = FilterExpression(age__gt=18)
        domain = filter_expr.to_domain()
        assert domain == [("age", ">", 18)]

        # Test in
        filter_expr = FilterExpression(status__in=["active", "pending"])
        domain = filter_expr.to_domain()
        assert domain == [("status", "in", ["active", "pending"])]

    def test_contains_lookup(self):
        """Test contains lookup conversion."""
        filter_expr = FilterExpression(name__contains="john")
        domain = filter_expr.to_domain()
        assert domain == [("name", "ilike", "%john%")]

    def test_startswith_endswith(self):
        """Test startswith and endswith lookups."""
        # Startswith
        filter_expr = FilterExpression(name__startswith="john")
        domain = filter_expr.to_domain()
        assert domain == [("name", "ilike", "john%")]

        # Endswith
        filter_expr = FilterExpression(name__endswith="doe")
        domain = filter_expr.to_domain()
        assert domain == [("name", "ilike", "%doe")]

    def test_null_checks(self):
        """Test null check lookups."""
        # Is null
        filter_expr = FilterExpression(email__isnull=True)
        domain = filter_expr.to_domain()
        assert domain == [("email", "=", False)]

        # Is not null
        filter_expr = FilterExpression(email__isnotnull=True)
        domain = filter_expr.to_domain()
        assert domain == [("email", "!=", False)]


class TestQObject:
    """Test cases for Q object."""

    def test_q_creation(self):
        """Test Q object creation."""
        q = Q(name="John", age=25)
        assert q.filters == {"name": "John", "age": 25}

    def test_q_to_domain(self):
        """Test Q object conversion to domain."""
        q = Q(name="John", is_active=True)
        domain = q.to_domain()

        assert len(domain) == 2
        assert ("name", "=", "John") in domain
        assert ("is_active", "=", True) in domain

    def test_q_and_combination(self):
        """Test Q object AND combination."""
        q1 = Q(name="John")
        q2 = Q(age=25)

        combined = q1 & q2
        domain = combined.to_domain()

        # AND is implicit
        assert ("name", "=", "John") in domain
        assert ("age", "=", 25) in domain

    def test_q_or_combination(self):
        """Test Q object OR combination."""
        q1 = Q(name="John")
        q2 = Q(name="Jane")

        combined = q1 | q2
        domain = combined.to_domain()

        # OR requires explicit operator
        assert "|" in domain
        assert ("name", "=", "John") in domain
        assert ("name", "=", "Jane") in domain

    def test_q_negation(self):
        """Test Q object negation."""
        q = Q(name="John")
        negated = ~q

        domain = negated.to_domain()

        # NOT requires explicit operator
        assert "!" in domain
        assert ("name", "=", "John") in domain

    def test_complex_q_combination(self):
        """Test complex Q object combinations."""
        # (name="John" OR name="Jane") AND age > 18
        name_q = Q(name="John") | Q(name="Jane")
        age_q = Q(age__gt=18)

        complex_q = name_q & age_q
        domain = complex_q.to_domain()

        # Should contain OR for names and age condition
        assert "|" in domain
        assert ("name", "=", "John") in domain
        assert ("name", "=", "Jane") in domain
        assert ("age", ">", 18) in domain


class TestQuerySet:
    """Test cases for QuerySet."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        # Disable cache for testing
        self.mock_client.cache_manager = None
        self.queryset = QuerySet(ResPartner, self.mock_client)

    def test_queryset_creation(self):
        """Test QuerySet creation."""
        assert self.queryset.model_class == ResPartner
        assert self.queryset.client == self.mock_client
        assert self.queryset._domain == []
        assert self.queryset._limit is None
        assert self.queryset._offset == 0

    def test_filter_method(self):
        """Test filter method."""
        # Test keyword filters
        filtered = self.queryset.filter(name="John", is_company=True)

        assert len(filtered._domain) == 2
        assert ("name", "=", "John") in filtered._domain
        assert ("is_company", "=", True) in filtered._domain

    def test_filter_with_q(self):
        """Test filter method with Q objects."""
        q = Q(name="John") | Q(name="Jane")
        filtered = self.queryset.filter(q)

        # Should contain OR logic
        assert "|" in filtered._domain
        assert ("name", "=", "John") in filtered._domain
        assert ("name", "=", "Jane") in filtered._domain

    def test_exclude_method(self):
        """Test exclude method."""
        excluded = self.queryset.exclude(name="John")

        # Should contain NOT logic
        assert "!" in excluded._domain
        assert ("name", "=", "John") in excluded._domain

    def test_order_by_method(self):
        """Test order_by method."""
        # Single field ascending
        ordered = self.queryset.order_by("name")
        assert ordered._order == "name"

        # Single field descending
        ordered = self.queryset.order_by("-name")
        assert ordered._order == "name desc"

        # Multiple fields
        ordered = self.queryset.order_by("country_id", "-name")
        assert ordered._order == "country_id, name desc"

    def test_limit_and_offset(self):
        """Test limit and offset methods."""
        limited = self.queryset.limit(10)
        assert limited._limit == 10

        offset = self.queryset.offset(20)
        assert offset._offset == 20

        # Chain them
        paginated = self.queryset.limit(10).offset(20)
        assert paginated._limit == 10
        assert paginated._offset == 20

    def test_only_method(self):
        """Test only method for field selection."""
        only_fields = self.queryset.only("name", "email")
        assert only_fields._fields == ["name", "email"]

    def test_defer_method(self):
        """Test defer method for field exclusion."""
        # Mock model fields
        ResPartner.model_fields = {
            "id": None,
            "name": None,
            "email": None,
            "phone": None,
            "is_company": None,
        }

        deferred = self.queryset.defer("phone", "is_company")
        expected_fields = ["id", "name", "email"]
        assert set(deferred._fields) == set(expected_fields)

    def test_with_context(self):
        """Test with_context method."""
        with_ctx = self.queryset.with_context(lang="en_US", tz="UTC")
        assert with_ctx._context["lang"] == "en_US"
        assert with_ctx._context["tz"] == "UTC"

    def test_clone_method(self):
        """Test QuerySet cloning."""
        original = self.queryset.filter(name="John").limit(10)
        cloned = original._clone(limit=20)

        # Original should be unchanged
        assert original._limit == 10
        # Clone should have new limit
        assert cloned._limit == 20
        # Domain should be copied
        assert cloned._domain == original._domain

    @pytest.mark.asyncio
    async def test_all_method(self):
        """Test all method execution."""
        # Mock search_read response
        mock_data = [
            {"id": 1, "name": "John Doe", "is_company": False},
            {"id": 2, "name": "ACME Corp", "is_company": True},
        ]
        self.mock_client.search_read.return_value = mock_data

        results = await self.queryset.all()

        # Should call search_read
        self.mock_client.search_read.assert_called_once()

        # Should return model instances
        assert len(results) == 2
        assert all(isinstance(r, ResPartner) for r in results)
        assert results[0].name == "John Doe"
        assert results[1].name == "ACME Corp"

    @pytest.mark.asyncio
    async def test_first_method(self):
        """Test first method."""
        mock_data = [{"id": 1, "name": "John Doe", "is_company": False}]
        self.mock_client.search_read.return_value = mock_data

        result = await self.queryset.first()

        # Should limit to 1
        call_args = self.mock_client.search_read.call_args
        assert call_args[1]["limit"] == 1

        # Should return single instance
        assert isinstance(result, ResPartner)
        assert result.name == "John Doe"

    @pytest.mark.asyncio
    async def test_count_method(self):
        """Test count method."""
        self.mock_client.execute_kw.return_value = 42

        count = await self.queryset.count()

        # Should call search_count
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "search_count", [[]], {}
        )
        assert count == 42


class TestQueryBuilder:
    """Test cases for QueryBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        # Disable cache for testing
        self.mock_client.cache_manager = None
        self.builder = QueryBuilder(ResPartner, self.mock_client)

    def test_builder_creation(self):
        """Test QueryBuilder creation."""
        assert self.builder.model_class == ResPartner
        assert self.builder.client == self.mock_client

    def test_all_method(self):
        """Test all method returns QuerySet."""
        queryset = self.builder.all()
        assert isinstance(queryset, QuerySet)
        assert queryset.model_class == ResPartner

    def test_filter_method(self):
        """Test filter method returns filtered QuerySet."""
        queryset = self.builder.filter(name="John")
        assert isinstance(queryset, QuerySet)
        assert ("name", "=", "John") in queryset._domain

    def test_callable_interface(self):
        """Test builder callable interface."""
        queryset = self.builder(name="John", is_company=True)
        assert isinstance(queryset, QuerySet)
        assert ("name", "=", "John") in queryset._domain
        assert ("is_company", "=", True) in queryset._domain

    @pytest.mark.asyncio
    async def test_get_method(self):
        """Test get method."""
        mock_data = [{"id": 1, "name": "John Doe", "is_company": False}]
        self.mock_client.search_read.return_value = mock_data

        result = await self.builder.get(id=1)

        assert isinstance(result, ResPartner)
        assert result.name == "John Doe"

    @pytest.mark.asyncio
    async def test_create_method(self):
        """Test create method."""
        self.mock_client.execute_kw.return_value = 123
        mock_data = [{"id": 123, "name": "New Partner", "is_company": False}]
        self.mock_client.search_read.return_value = mock_data

        result = await self.builder.create(name="New Partner", is_company=False)

        # Should call create then fetch the record
        create_call = self.mock_client.execute_kw.call_args_list[0]
        assert create_call[0] == (
            "res.partner",
            "create",
            [{"name": "New Partner", "is_company": False}],
        )

        assert isinstance(result, ResPartner)
        assert result.name == "New Partner"
