"""
Fluent query builder for OdooFlow.

This module provides a chainable, type-safe query interface for building
and executing Odoo queries with performance optimization and lazy loading.
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, AsyncIterator
from collections.abc import AsyncIterable

from ..models.base import OdooModel
from ..models.registry import get_model_class, get_registry
from .filters import FilterExpression, Q
from .expressions import Expression
from ..cache.manager import CacheManager

T = TypeVar("T", bound=OdooModel)


class QuerySet(AsyncIterable[T]):
    """Represents a lazy, chainable query set.

    This class provides a Django-like interface for building and executing
    queries against Odoo models. It supports method chaining, lazy evaluation,
    and efficient data fetching.

    Features:
    - Lazy evaluation (queries are not executed until needed)
    - Method chaining for building complex queries
    - Type safety with generic typing
    - Efficient pagination and iteration
    - Automatic model instantiation
    - Caching and prefetching support

    Example:
        >>> # Build a query
        >>> partners = client.model(ResPartner).filter(
        ...     is_company=True,
        ...     name__ilike="acme%"
        ... ).order_by("name").limit(10)
        >>>
        >>> # Execute and iterate
        >>> async for partner in partners:
        ...     print(partner.name)
        >>>
        >>> # Or get all results
        >>> partner_list = await partners.all()
    """

    def __init__(
        self,
        model_class: Type[T],
        client: Any,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the query set.

        Args:
            model_class: The model class to query
            client: OdooFlow client for executing queries
            domain: Odoo domain filter
            fields: Fields to fetch
            limit: Maximum number of records
            offset: Number of records to skip
            order: Sort order specification
            context: Additional context for the query
        """
        self.model_class = model_class
        self.client = client
        self._domain = domain or []
        self._fields = fields
        self._limit = limit
        self._offset = offset
        self._order = order
        self._context = context or {}

        # Cache manager
        self._cache_manager: Optional[CacheManager] = getattr(
            client, "cache_manager", None
        )
        self._cache_ttl = 300  # 5 minutes default TTL
        self._cache_enabled = True

        # Caching
        self._result_cache: Optional[List[T]] = None
        self._count_cache: Optional[int] = None

        # Execution state
        self._executed = False

        # Relationship optimization
        self._select_related: set = set()
        self._prefetch_related: set = set()

    def filter(self, *args: Union[Q, Expression], **kwargs: Any) -> "QuerySet[T]":
        """Add filter conditions to the query.

        Args:
            *args: Q objects or Expression objects
            **kwargs: Field-based filters

        Returns:
            New QuerySet with additional filters

        Example:
            >>> # Keyword filters
            >>> qs = partners.filter(is_company=True, name__ilike="acme%")
            >>>
            >>> # Q objects
            >>> qs = partners.filter(Q(name="ACME") | Q(name="Corp"))
            >>>
            >>> # Mixed
            >>> qs = partners.filter(Q(is_company=True), active=True)
        """
        new_domain = self._domain.copy()

        # Process Q objects and Expressions
        for arg in args:
            if hasattr(arg, "to_domain"):
                arg_domain = arg.to_domain()
                new_domain.extend(arg_domain)

        # Process keyword arguments
        if kwargs:
            filter_expr = FilterExpression(**kwargs)
            filter_domain = filter_expr.to_domain()
            new_domain.extend(filter_domain)

        return self._clone(domain=new_domain)

    def exclude(self, *args: Union[Q, Expression], **kwargs: Any) -> "QuerySet[T]":
        """Exclude records matching the given conditions.

        Args:
            *args: Q objects or Expression objects to exclude
            **kwargs: Field-based filters to exclude

        Returns:
            New QuerySet excluding matching records
        """
        # Create a negated filter
        if args or kwargs:
            exclude_q = Q(*args, **kwargs) if args else Q(**kwargs)
            negated_q = ~exclude_q
            return self.filter(negated_q)

        return self._clone()

    def order_by(self, *fields: str) -> "QuerySet[T]":
        """Set the sort order for the query.

        Args:
            *fields: Field names to sort by. Prefix with '-' for descending order.

        Returns:
            New QuerySet with specified ordering

        Example:
            >>> # Single field ascending
            >>> qs = partners.order_by("name")
            >>>
            >>> # Single field descending
            >>> qs = partners.order_by("-create_date")
            >>>
            >>> # Multiple fields
            >>> qs = partners.order_by("country_id", "-name")
        """
        if not fields:
            return self._clone(order=None)

        order_parts = []
        for field in fields:
            if field.startswith("-"):
                order_parts.append(f"{field[1:]} desc")
            else:
                order_parts.append(field)

        order = ", ".join(order_parts)
        return self._clone(order=order)

    def limit(self, count: int) -> "QuerySet[T]":
        """Limit the number of results.

        Args:
            count: Maximum number of records to return

        Returns:
            New QuerySet with limit applied
        """
        return self._clone(limit=count)

    def offset(self, count: int) -> "QuerySet[T]":
        """Set the offset for pagination.

        Args:
            count: Number of records to skip

        Returns:
            New QuerySet with offset applied
        """
        return self._clone(offset=count)

    def only(self, *fields: str) -> "QuerySet[T]":
        """Specify which fields to fetch from the server.

        Args:
            *fields: Field names to fetch

        Returns:
            New QuerySet that will only fetch specified fields

        Example:
            >>> # Only fetch name and email
            >>> qs = partners.only("name", "email")
        """
        return self._clone(fields=list(fields))

    def defer(self, *fields: str) -> "QuerySet[T]":
        """Specify which fields to exclude from fetching.

        Args:
            *fields: Field names to exclude

        Returns:
            New QuerySet that will exclude specified fields
        """
        if not self._fields:
            # If no fields specified, get all model fields and remove deferred ones
            all_fields = list(self.model_class.model_fields.keys())
            fields_to_fetch = [f for f in all_fields if f not in fields]
        else:
            # Remove deferred fields from existing field list
            fields_to_fetch = [f for f in self._fields if f not in fields]

        return self._clone(fields=fields_to_fetch)

    def with_context(self, **context: Any) -> "QuerySet[T]":
        """Add context to the query.

        Args:
            **context: Context variables to add

        Returns:
            New QuerySet with additional context
        """
        new_context = self._context.copy()
        new_context.update(context)
        return self._clone(context=new_context)

    def select_related(self, *field_names: str) -> "QuerySet[T]":
        """Select related fields to fetch in a single query.

        This is similar to Django's select_related - it follows foreign key
        relationships and fetches related data in the same query to avoid
        additional database hits.

        Args:
            *field_names: Names of related fields to fetch

        Returns:
            New QuerySet with related fields selected

        Example:
            >>> # Fetch partners with their companies in one query
            >>> partners = client.model(ResPartner).select_related('company_id').all()
            >>> # No additional query when accessing partner.company_id
        """
        new_qs = self._clone()
        if not hasattr(new_qs, "_select_related"):
            new_qs._select_related = set()
        else:
            new_qs._select_related = self._select_related.copy()

        new_qs._select_related.update(field_names)
        return new_qs

    def prefetch_related(self, *field_names: str) -> "QuerySet[T]":
        """Prefetch related fields in separate queries.

        This is similar to Django's prefetch_related - it fetches related
        data in separate queries but caches the results to avoid N+1 queries.

        Args:
            *field_names: Names of related fields to prefetch

        Returns:
            New QuerySet with related fields marked for prefetching

        Example:
            >>> # Fetch partners and prefetch their children
            >>> partners = client.model(ResPartner).prefetch_related('child_ids').all()
            >>> # No additional queries when accessing partner.child_ids
        """
        new_qs = self._clone()
        if not hasattr(new_qs, "_prefetch_related"):
            new_qs._prefetch_related = set()
        else:
            new_qs._prefetch_related = self._prefetch_related.copy()

        new_qs._prefetch_related.update(field_names)
        return new_qs

    async def all(self) -> List[T]:
        """Execute the query and return all results.

        Returns:
            List of model instances
        """
        if self._result_cache is not None:
            return self._result_cache

        # Execute the query
        records_data = await self._execute_query()

        # Convert to model instances
        results = []
        for record_data in records_data:
            instance = self._create_model_instance(record_data)
            results.append(instance)

        # Handle prefetch_related
        if self._prefetch_related and results:
            await self._handle_prefetch_related(results)

        # Cache the results
        self._result_cache = results
        self._executed = True

        return results

    async def first(self) -> Optional[T]:
        """Get the first result or None.

        Returns:
            First model instance or None if no results
        """
        # Create a limited query
        limited_qs = self.limit(1)
        results = await limited_qs.all()
        return results[0] if results else None

    async def get(self, *args, **filters: Any) -> T:
        """Get a single record matching the filters.

        Args:
            *args: If provided, first argument is treated as ID
            **filters: Additional filters to apply

        Returns:
            Single model instance

        Raises:
            ValueError: If no record found or multiple records found

        Examples:
            >>> # Get by ID (as documented in README.md)
            >>> partner = await client.model(ResPartner).get(1)
            >>>
            >>> # Get by filters
            >>> partner = await client.model(ResPartner).get(email="test@example.com")
            >>>
            >>> # Get by ID with additional filters (not supported in this approach)
            >>> partner = await client.model(ResPartner).get(id=1, is_company=True)
        """
        # Handle positional ID argument
        if args:
            if len(args) > 1:
                raise TypeError(f"get() takes at most 1 positional argument ({len(args)} given)")
            filters['id'] = args[0]

        qs = self.filter(**filters) if filters else self
        results = await qs.limit(2).all()  # Limit to 2 to detect multiple results

        if not results:
            raise ValueError(
                f"No {self.model_class.__name__} found matching the criteria"
            )
        elif len(results) > 1:
            raise ValueError(
                f"Multiple {self.model_class.__name__} found, expected exactly one"
            )

        return results[0]

    async def count(self) -> int:
        """Get the count of records matching the query.

        Returns:
            Number of matching records
        """
        if self._count_cache is not None:
            return self._count_cache

        # Execute count query
        count = await self.client.execute_kw(
            self.model_class.get_odoo_name(),
            "search_count",
            [self._domain],
            self._context,
        )

        self._count_cache = count
        return count

    async def exists(self) -> bool:
        """Check if any records match the query.

        Returns:
            True if at least one record exists, False otherwise
        """
        count = await self.count()
        return count > 0

    async def values(self, *fields: str) -> List[Dict[str, Any]]:
        """Return dictionaries instead of model instances.

        Args:
            *fields: Fields to include in the dictionaries

        Returns:
            List of dictionaries with field values
        """
        if fields:
            qs = self.only(*fields)
        else:
            qs = self

        return await qs._execute_query()

    async def values_list(self, *fields: str, flat: bool = False) -> List[Any]:
        """Return tuples of field values.

        Args:
            *fields: Fields to include in the tuples
            flat: If True and only one field, return flat list of values

        Returns:
            List of tuples or flat list if flat=True
        """
        if not fields:
            raise ValueError("At least one field must be specified")

        records = await self.only(*fields)._execute_query()

        if flat and len(fields) == 1:
            field = fields[0]
            return [record.get(field) for record in records]
        else:
            return [tuple(record.get(field) for field in fields) for record in records]

    def __aiter__(self) -> AsyncIterator[T]:
        """Make the QuerySet async iterable."""
        return self._async_iterator()

    async def _async_iterator(self) -> AsyncIterator[T]:
        """Async iterator implementation."""
        results = await self.all()
        for result in results:
            yield result

    def _clone(self, **kwargs: Any) -> "QuerySet[T]":
        """Create a copy of the QuerySet with modified parameters.

        Args:
            **kwargs: Parameters to modify

        Returns:
            New QuerySet instance
        """
        new_qs = QuerySet(
            model_class=self.model_class,
            client=self.client,
            domain=kwargs.get("domain", self._domain),
            fields=kwargs.get("fields", self._fields),
            limit=kwargs.get("limit", self._limit),
            offset=kwargs.get("offset", self._offset),
            order=kwargs.get("order", self._order),
            context=kwargs.get("context", self._context),
        )

        # Copy relationship optimization settings
        new_qs._select_related = self._select_related.copy()
        new_qs._prefetch_related = self._prefetch_related.copy()

        # Copy cache settings
        new_qs._cache_enabled = self._cache_enabled
        new_qs._cache_ttl = self._cache_ttl

        return new_qs

    async def _handle_prefetch_related(self, instances: List[T]) -> None:
        """Handle prefetch_related optimization.

        Args:
            instances: List of model instances to prefetch relationships for
        """
        if not self._prefetch_related or not instances:
            return

        # Use the prefetch manager to optimize relationship loading
        from .lazy import PrefetchManager

        manager = PrefetchManager(self.client)
        await manager.prefetch_related(
            instances, *self._prefetch_related, batch_size=100
        )

    async def _execute_query(self) -> List[Dict[str, Any]]:
        """Execute the query and return raw data.

        Returns:
            List of record dictionaries from Odoo
        """
        # Check cache first
        cached_result = await self._get_cached_result()
        if cached_result is not None:
            return cached_result

        # Prepare query parameters
        kwargs = {}

        if self._fields:
            kwargs["fields"] = self._fields
        if self._limit is not None:
            kwargs["limit"] = self._limit
        if self._offset:
            kwargs["offset"] = self._offset
        if self._order:
            kwargs["order"] = self._order

        # Merge context
        query_context = self._context.copy()
        kwargs["context"] = query_context

        # Execute search_read for efficiency
        result = await self.client.search_read(
            self.model_class.get_odoo_name(), domain=self._domain, **kwargs
        )

        # Cache the result
        await self._set_cached_result(result)

        return result

    def _create_model_instance(self, record_data: Dict[str, Any]) -> T:
        """Create a model instance from record data.

        Args:
            record_data: Raw record data from Odoo

        Returns:
            Model instance
        """
        # Add client reference for lazy loading
        record_data["client"] = self.client

        # Remove problematic 'self' key if present
        if "self" in record_data:
            record_data.pop("self", None)

        # Create the model instance
        return self.model_class(**record_data)

    def __repr__(self) -> str:
        """String representation of the QuerySet."""
        model_name = self.model_class.__name__
        if self._executed and self._result_cache is not None:
            count = len(self._result_cache)
            return f"<QuerySet [{count} {model_name} objects]>"
        else:
            return f"<QuerySet [unevaluated {model_name} query]>"

    def _generate_cache_key(self) -> str:
        """Generate a cache key for this query."""
        query_data = {
            "model": self.model_class.get_odoo_name(),
            "domain": self._domain,
            "fields": self._fields,
            "limit": self._limit,
            "offset": self._offset,
            "order": self._order,
            "context": self._context,
        }

        # Create a hash of the query data
        query_str = json.dumps(query_data, sort_keys=True)
        query_hash = hashlib.md5(query_str.encode(), usedforsecurity=False).hexdigest()

        return f"query:{self.model_class.get_odoo_name()}:{query_hash}"

    def cache(self, ttl: Optional[int] = None, enabled: bool = True) -> "QuerySet[T]":
        """Configure caching for this query.

        Args:
            ttl: Time to live in seconds (None for default)
            enabled: Whether to enable caching

        Returns:
            QuerySet with caching configuration
        """
        new_qs = self._clone()
        new_qs._cache_ttl = ttl if ttl is not None else self._cache_ttl
        new_qs._cache_enabled = enabled
        return new_qs

    async def _get_cached_result(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached result if available."""
        if not self._cache_enabled or not self._cache_manager:
            return None

        cache_key = self._generate_cache_key()
        return await self._cache_manager.get(cache_key)

    async def _set_cached_result(self, result: List[Dict[str, Any]]) -> None:
        """Cache the query result."""
        if not self._cache_enabled or not self._cache_manager:
            return

        cache_key = self._generate_cache_key()
        await self._cache_manager.set(cache_key, result, ttl=self._cache_ttl)

    async def _invalidate_cache(self) -> None:
        """Invalidate cache for this model."""
        if not self._cache_manager:
            return

        # Invalidate all cache entries for this model
        model_pattern = f"query:{self.model_class.get_odoo_name()}:*"
        await self._cache_manager.invalidate_pattern(model_pattern)


class QueryBuilder:
    """Main query builder interface.

    This class provides the entry point for building queries against
    Odoo models. It acts as a factory for QuerySet instances.

    Example:
        >>> builder = QueryBuilder(ResPartner, client)
        >>> partners = await builder.filter(is_company=True).all()
    """

    def __init__(self, model_class: Type[T], client: Any):
        """Initialize the query builder.

        Args:
            model_class: The model class to query
            client: OdooFlow client for executing queries
        """
        self.model_class = model_class
        self.client = client

        # Cache manager
        self._cache_manager: Optional[CacheManager] = getattr(
            client, "cache_manager", None
        )

    def all(self) -> QuerySet[T]:
        """Get all records (returns a QuerySet for lazy evaluation).

        Returns:
            QuerySet for all records
        """
        return QuerySet(self.model_class, self.client)

    def filter(self, *args: Union[Q, Expression], **kwargs: Any) -> QuerySet[T]:
        """Create a filtered QuerySet.

        Args:
            *args: Q objects or Expression objects
            **kwargs: Field-based filters

        Returns:
            Filtered QuerySet
        """
        return self.all().filter(*args, **kwargs)

    def exclude(self, *args: Union[Q, Expression], **kwargs: Any) -> QuerySet[T]:
        """Create a QuerySet excluding matching records.

        Args:
            *args: Q objects or Expression objects to exclude
            **kwargs: Field-based filters to exclude

        Returns:
            QuerySet excluding matching records
        """
        return self.all().exclude(*args, **kwargs)

    def order_by(self, *fields: str) -> QuerySet[T]:
        """Create an ordered QuerySet.

        Args:
            *fields: Field names to sort by

        Returns:
            Ordered QuerySet
        """
        return self.all().order_by(*fields)

    async def get(self, *args, **filters: Any) -> T:
        """Get a single record.

        Args:
            *args: If provided, first argument is treated as ID
            **filters: Filters to apply

        Returns:
            Single model instance

        Examples:
            >>> # Get by ID (as documented in README.md)
            >>> partner = await client.model(ResPartner).get(1)
            >>>
            >>> # Get by filters
            >>> partner = await client.model(ResPartner).get(is_company=True)
        """
        return await self.filter().get(*args, **filters)

    async def create(self, **values: Any) -> T:
        """Create a new record.

        Args:
            **values: Field values for the new record

        Returns:
            Created model instance
        """
        # Execute create operation
        record_id = await self.client.execute_kw(
            self.model_class.get_odoo_name(), "create", [values]
        )

        # Invalidate cache for this model
        await self._invalidate_cache()

        # Fetch the created record
        return await self.get(id=record_id)

    async def bulk_create(self, values_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple records efficiently.

        Args:
            values_list: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        # Execute bulk create
        record_ids = await self.client.execute_kw(
            self.model_class.get_odoo_name(), "create", values_list
        )

        # Invalidate cache for this model
        await self._invalidate_cache()

        # Fetch the created records
        return await self.filter(id__in=record_ids).all()

    def __call__(self, *args: Union[Q, Expression], **kwargs: Any) -> QuerySet[T]:
        """Make the builder callable as a shortcut for filter.

        Args:
            *args: Q objects or Expression objects
            **kwargs: Field-based filters

        Returns:
            Filtered QuerySet
        """
        return self.filter(*args, **kwargs)

    async def _invalidate_cache(self) -> None:
        """Invalidate cache for this model."""
        if not self._cache_manager:
            return

        # Invalidate all cache entries for this model
        model_pattern = f"query:{self.model_class.get_odoo_name()}:*"
        await self._cache_manager.invalidate_pattern(model_pattern)
