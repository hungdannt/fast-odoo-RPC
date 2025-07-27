"""
Lazy loading implementation for OdooFlow.

This module provides lazy loading capabilities for efficient data fetching,
including lazy collections and deferred loading strategies.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, AsyncIterator
from collections.abc import AsyncIterable
from weakref import WeakKeyDictionary

T = TypeVar("T")


class LazyLoader:
    """Base class for lazy loading implementations.

    This class provides the foundation for lazy loading of data that
    hasn't been fetched from the server yet.
    """

    def __init__(self, loader_func: callable, *args: Any, **kwargs: Any):
        """Initialize the lazy loader.

        Args:
            loader_func: Function to call when loading data
            *args: Arguments for the loader function
            **kwargs: Keyword arguments for the loader function
        """
        self.loader_func = loader_func
        self.args = args
        self.kwargs = kwargs
        self._loaded_data: Optional[Any] = None
        self._is_loaded = False
        self._loading_task: Optional[asyncio.Task] = None

    async def load(self) -> Any:
        """Load the data if not already loaded.

        Returns:
            The loaded data
        """
        if self._is_loaded:
            return self._loaded_data

        # If already loading, wait for the existing task
        if self._loading_task and not self._loading_task.done():
            return await self._loading_task

        # Start loading
        self._loading_task = asyncio.create_task(self._do_load())
        return await self._loading_task

    async def _do_load(self) -> Any:
        """Perform the actual loading."""
        try:
            self._loaded_data = await self.loader_func(*self.args, **self.kwargs)
            self._is_loaded = True
            return self._loaded_data
        except Exception as e:
            # Reset loading state on error
            self._loading_task = None
            raise e

    def is_loaded(self) -> bool:
        """Check if the data has been loaded.

        Returns:
            True if data is loaded, False otherwise
        """
        return self._is_loaded

    def get_cached_data(self) -> Any:
        """Get cached data without triggering a load.

        Returns:
            Cached data or None if not loaded
        """
        return self._loaded_data if self._is_loaded else None

    def invalidate(self) -> None:
        """Invalidate the cached data."""
        self._loaded_data = None
        self._is_loaded = False
        if self._loading_task and not self._loading_task.done():
            self._loading_task.cancel()
        self._loading_task = None

    def __await__(self):
        """Make the loader awaitable."""
        return self.load().__await__()


class LazyCollection(AsyncIterable[T]):
    """Lazy collection that loads data on demand.

    This class represents a collection of objects that are loaded
    lazily when accessed. It supports async iteration and various
    collection operations.

    Example:
        >>> # Create a lazy collection
        >>> lazy_partners = LazyCollection(load_partners_func, domain=[...])
        >>>
        >>> # Iterate over items (triggers loading)
        >>> async for partner in lazy_partners:
        ...     print(partner.name)
        >>>
        >>> # Or get all items
        >>> partners = await lazy_partners.all()
    """

    def __init__(
        self,
        loader_func: callable,
        model_class: Optional[Type[T]] = None,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize the lazy collection.

        Args:
            loader_func: Function to load the collection data
            model_class: Model class for type safety
            *args: Arguments for the loader function
            **kwargs: Keyword arguments for the loader function
        """
        self.loader_func = loader_func
        self.model_class = model_class
        self.args = args
        self.kwargs = kwargs

        self._loaded_items: Optional[List[T]] = None
        self._is_loaded = False
        self._loading_task: Optional[asyncio.Task] = None

    async def all(self) -> List[T]:
        """Get all items in the collection.

        Returns:
            List of all items
        """
        if self._is_loaded:
            return self._loaded_items or []

        # If already loading, wait for the existing task
        if self._loading_task and not self._loading_task.done():
            return await self._loading_task

        # Start loading
        self._loading_task = asyncio.create_task(self._load_all())
        return await self._loading_task

    async def _load_all(self) -> List[T]:
        """Load all items from the server."""
        try:
            items = await self.loader_func(*self.args, **self.kwargs)
            self._loaded_items = items if isinstance(items, list) else [items]
            self._is_loaded = True
            return self._loaded_items
        except Exception as e:
            # Reset loading state on error
            self._loading_task = None
            raise e

    async def first(self) -> Optional[T]:
        """Get the first item or None.

        Returns:
            First item or None if collection is empty
        """
        items = await self.all()
        return items[0] if items else None

    async def count(self) -> int:
        """Get the count of items in the collection.

        Returns:
            Number of items
        """
        items = await self.all()
        return len(items)

    async def exists(self) -> bool:
        """Check if the collection has any items.

        Returns:
            True if collection has items, False otherwise
        """
        count = await self.count()
        return count > 0

    def is_loaded(self) -> bool:
        """Check if the collection has been loaded.

        Returns:
            True if loaded, False otherwise
        """
        return self._is_loaded

    def get_cached_items(self) -> Optional[List[T]]:
        """Get cached items without triggering a load.

        Returns:
            Cached items or None if not loaded
        """
        return self._loaded_items if self._is_loaded else None

    def invalidate(self) -> None:
        """Invalidate the cached items."""
        self._loaded_items = None
        self._is_loaded = False
        if self._loading_task and not self._loading_task.done():
            self._loading_task.cancel()
        self._loading_task = None

    def __aiter__(self) -> AsyncIterator[T]:
        """Make the collection async iterable."""
        return self._async_iterator()

    async def _async_iterator(self) -> AsyncIterator[T]:
        """Async iterator implementation."""
        items = await self.all()
        for item in items:
            yield item

    def __await__(self):
        """Make the collection awaitable (returns all items)."""
        return self.all().__await__()

    def __repr__(self) -> str:
        """String representation of the lazy collection."""
        if self._is_loaded and self._loaded_items is not None:
            count = len(self._loaded_items)
            model_name = self.model_class.__name__ if self.model_class else "object"
            return f"<LazyCollection [{count} {model_name} objects]>"
        else:
            model_name = self.model_class.__name__ if self.model_class else "object"
            return f"<LazyCollection [unloaded {model_name} collection]>"


class PrefetchManager:
    """Manages prefetching strategies for efficient data loading.

    This class helps optimize data loading by prefetching related
    data in batches to reduce the number of database queries.
    """

    def __init__(self, client: Any):
        """Initialize the prefetch manager.

        Args:
            client: OdooFlow client for data operations
        """
        self.client = client
        self._prefetch_cache: WeakKeyDictionary = WeakKeyDictionary()

    async def prefetch_related(
        self, instances: List[Any], *field_names: str, batch_size: int = 100
    ) -> None:
        """Prefetch related fields for a list of instances.

        Args:
            instances: List of model instances
            *field_names: Names of related fields to prefetch
            batch_size: Number of instances to process in each batch
        """
        if not instances or not field_names:
            return

        # Group instances by model type
        model_groups: Dict[Type, List[Any]] = {}
        for instance in instances:
            model_class = type(instance)
            if model_class not in model_groups:
                model_groups[model_class] = []
            model_groups[model_class].append(instance)

        # Process each model group
        for model_class, model_instances in model_groups.items():
            await self._prefetch_for_model(
                model_class, model_instances, field_names, batch_size
            )

    async def _prefetch_for_model(
        self,
        model_class: Type,
        instances: List[Any],
        field_names: List[str],
        batch_size: int,
    ) -> None:
        """Prefetch fields for instances of a specific model.

        Args:
            model_class: The model class
            instances: List of instances of this model
            field_names: Field names to prefetch
            batch_size: Batch size for processing
        """
        # Process in batches
        for i in range(0, len(instances), batch_size):
            batch = instances[i : i + batch_size]

            # Get relationship fields info
            relationship_fields = model_class.get_relationship_fields()

            for field_name in field_names:
                if field_name in relationship_fields:
                    await self._prefetch_relationship_field(
                        batch, field_name, relationship_fields[field_name]
                    )

    async def _prefetch_relationship_field(
        self, instances: List[Any], field_name: str, field_info: Any
    ) -> None:
        """Prefetch a specific relationship field.

        Args:
            instances: List of instances
            field_name: Name of the relationship field
            field_info: Field information from the model
        """
        # Collect all related IDs
        related_ids = set()

        for instance in instances:
            field_value = getattr(instance, field_name, None)
            if field_value:
                if isinstance(field_value, list):
                    # One2many/Many2many
                    related_ids.update(field_value)
                else:
                    # Many2one
                    related_ids.add(field_value)

        if not related_ids:
            return

        # Get the related model name from field info
        # This would need to be implemented based on the field type
        # For now, this is a placeholder
        pass

    def clear_cache(self) -> None:
        """Clear the prefetch cache."""
        self._prefetch_cache.clear()
