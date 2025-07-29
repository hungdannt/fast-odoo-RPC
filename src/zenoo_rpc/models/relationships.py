"""
Relationship handling and lazy loading for Odoo models.

This module provides the infrastructure for handling relationships between
Odoo models, including lazy loading and efficient data fetching.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable, Awaitable
from weakref import WeakKeyDictionary

T = TypeVar("T")


class LazyRelationship:
    """Represents a lazy-loaded relationship field.

    This class acts as a proxy for relationship data that hasn't been
    loaded yet. When accessed, it automatically fetches the data from
    the server.

    Features:
    - Lazy loading on first access
    - Caching of loaded data
    - Support for both single records and collections
    - Async loading with proper error handling

    Example:
        >>> # This creates a lazy relationship
        >>> partner.company_id  # Returns LazyRelationship
        >>>
        >>> # This triggers loading and returns the actual data
        >>> company = await partner.company_id  # Returns ResPartner instance
    """

    def __init__(
        self,
        parent_record: Any,
        field_name: str,
        relation_model: str,
        relation_ids: Union[int, List[int], None],
        client: Any,
        is_collection: bool = False,
    ):
        """Initialize a lazy relationship.

        Args:
            parent_record: The record that owns this relationship
            field_name: Name of the relationship field
            relation_model: Name of the related Odoo model
            relation_ids: ID(s) of related records
            client: OdooFlow client for data fetching
            is_collection: Whether this is a collection (One2many/Many2many)
        """
        self.parent_record = parent_record
        self.field_name = field_name
        self.relation_model = relation_model
        self.relation_ids = relation_ids
        self.client = client
        self.is_collection = is_collection

        # Cache for loaded data
        self._loaded_data: Optional[Any] = None
        self._is_loaded = False
        self._loading_task: Optional[asyncio.Task] = None

        # N+1 prevention cache (class-level shared cache)
        if not hasattr(LazyRelationship, "_prefetch_cache"):
            LazyRelationship._prefetch_cache = {}

        # Batch loading queue for N+1 prevention
        if not hasattr(LazyRelationship, "_batch_queue"):
            LazyRelationship._batch_queue = {}
            LazyRelationship._batch_tasks = {}

    async def load(self) -> Any:
        """Load the relationship data from the server.

        Returns:
            The loaded record(s) or None if no data
        """
        # Return cached data if already loaded
        if self._is_loaded:
            return self._loaded_data

        # Check prefetch cache first
        cache_key = f"{self.relation_model}:{self.relation_ids}"
        if cache_key in LazyRelationship._prefetch_cache:
            self._loaded_data = LazyRelationship._prefetch_cache[cache_key]
            self._is_loaded = True
            return self._loaded_data

        # If already loading, wait for the existing task
        if self._loading_task and not self._loading_task.done():
            return await self._loading_task

        # Use batch loading for N+1 prevention
        return await self._load_with_batching()

    async def _load_with_batching(self) -> Any:
        """Load data using batch loading to prevent N+1 queries."""
        batch_key = f"{self.relation_model}:{self.field_name}"

        # Add this relationship to the batch queue
        if batch_key not in LazyRelationship._batch_queue:
            LazyRelationship._batch_queue[batch_key] = []

        LazyRelationship._batch_queue[batch_key].append(self)

        # If batch task is already running, wait for it
        if batch_key in LazyRelationship._batch_tasks:
            task = LazyRelationship._batch_tasks[batch_key]
            if not task.done():
                await task
                return self._loaded_data

        # Start batch loading task
        LazyRelationship._batch_tasks[batch_key] = asyncio.create_task(
            self._execute_batch_load(batch_key)
        )

        await LazyRelationship._batch_tasks[batch_key]
        return self._loaded_data

    async def _execute_batch_load(self, batch_key: str) -> None:
        """Execute batch loading for all relationships in the queue."""
        # Small delay to collect more relationships
        await asyncio.sleep(0.001)

        relationships = LazyRelationship._batch_queue.pop(batch_key, [])
        if not relationships:
            return

        # Collect all IDs to load
        all_ids = set()
        for rel in relationships:
            if rel.relation_ids:
                if isinstance(rel.relation_ids, list):
                    all_ids.update(rel.relation_ids)
                else:
                    all_ids.add(rel.relation_ids)

        if not all_ids:
            # Mark all as loaded with empty data
            for rel in relationships:
                rel._loaded_data = [] if rel.is_collection else None
                rel._is_loaded = True
            return

        try:
            # Fetch all records in one query
            records_data = await self.client.search_read(
                model=self.relation_model,
                domain=[("id", "in", list(all_ids))],
                fields=["id", "name", "display_name"],
            )

            # Create lookup dictionary
            records_by_id = {record["id"]: record for record in records_data}

            # Populate cache and set loaded data for each relationship
            for rel in relationships:
                if rel.relation_ids:
                    if rel.is_collection:
                        # Handle collections
                        if isinstance(rel.relation_ids, list):
                            raw_data = [
                                records_by_id.get(rid)
                                for rid in rel.relation_ids
                                if rid in records_by_id
                            ]
                            # Convert to model instances
                            rel._loaded_data = rel._convert_to_model_instances(raw_data)
                        else:
                            rel._loaded_data = []
                    else:
                        # Handle single records
                        if isinstance(rel.relation_ids, list) and rel.relation_ids:
                            raw_record = records_by_id.get(rel.relation_ids[0])
                        else:
                            raw_record = records_by_id.get(rel.relation_ids)

                        # Convert to model instance
                        if raw_record:
                            instances = rel._convert_to_model_instances([raw_record])
                            rel._loaded_data = instances[0] if instances else None
                        else:
                            rel._loaded_data = None
                else:
                    rel._loaded_data = [] if rel.is_collection else None

                rel._is_loaded = True

                # Cache the result
                cache_key = f"{rel.relation_model}:{rel.relation_ids}"
                LazyRelationship._prefetch_cache[cache_key] = rel._loaded_data

        except Exception as e:
            # Mark all as failed
            for rel in relationships:
                rel._loaded_data = [] if rel.is_collection else None
                rel._is_loaded = True
            raise e

        finally:
            # Clean up batch task
            LazyRelationship._batch_tasks.pop(batch_key, None)

    async def _fetch_data(self) -> Any:
        """Fetch the actual data from the server."""
        try:
            if not self.relation_ids:
                self._loaded_data = [] if self.is_collection else None
                self._is_loaded = True
                return self._loaded_data

            # Determine which fields to fetch
            # For now, we'll fetch basic fields. This can be optimized later.
            basic_fields = ["id", "name", "display_name"]

            if self.is_collection:
                # Handle One2many/Many2many
                if isinstance(self.relation_ids, list):
                    records_data = await self.client.search_read(
                        self.relation_model,
                        domain=[("id", "in", self.relation_ids)],
                        fields=basic_fields,
                    )

                    # Convert to model instances
                    self._loaded_data = self._convert_to_model_instances(records_data)
                else:
                    self._loaded_data = []
            else:
                # Handle Many2one
                if isinstance(self.relation_ids, int):
                    records_data = await self.client.search_read(
                        self.relation_model,
                        domain=[("id", "=", self.relation_ids)],
                        fields=basic_fields,
                        limit=1,
                    )

                    # Convert to model instance
                    if records_data:
                        instances = self._convert_to_model_instances([records_data[0]])
                        self._loaded_data = instances[0] if instances else None
                    else:
                        self._loaded_data = None
                else:
                    self._loaded_data = None

            self._is_loaded = True
            return self._loaded_data

        except Exception as e:
            # Reset loading state on error
            self._loading_task = None
            raise e

    def is_loaded(self) -> bool:
        """Check if the relationship data has been loaded.

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
        """Invalidate the cached data, forcing a reload on next access."""
        self._loaded_data = None
        self._is_loaded = False
        if self._loading_task and not self._loading_task.done():
            self._loading_task.cancel()
        self._loading_task = None

    def _convert_to_model_instances(self, records_data: List[Dict[str, Any]]) -> List[Any]:
        """Convert raw record data to model instances.

        Args:
            records_data: List of raw record dictionaries from Odoo

        Returns:
            List of model instances
        """
        if not records_data:
            return []

        try:
            # Try to get the model class from registry
            from .registry import get_registry
            registry = get_registry()

            # Try to get registered model class
            model_class = registry.get_model(self.relation_model)
            if model_class:
                # Convert each record to model instance
                instances = []
                for record_data in records_data:
                    # Add client reference for lazy loading
                    record_data["client"] = self.client

                    # Remove problematic 'self' key if present
                    if "self" in record_data:
                        record_data.pop("self", None)

                    # Create model instance
                    instance = model_class(**record_data)
                    instances.append(instance)

                return instances
            else:
                # Fallback: return raw data if no model class found
                return records_data

        except Exception as e:
            # Fallback: return raw data on any error
            # This ensures lazy loading still works even if model conversion fails
            return records_data

    async def all(self) -> List[Any]:
        """Get all items for collection relationships.

        This method provides the same interface as LazyCollection.all()
        for consistency with the documented API.

        Returns:
            List of all items for collections, or single item wrapped in list for non-collections

        Raises:
            ValueError: If this is not a collection relationship

        Examples:
            >>> # For One2many/Many2many fields (collections)
            >>> children = await partner.child_ids.all()  # Returns List[ResPartner]
            >>>
            >>> # For Many2one fields (single records) - returns single item in list
            >>> company = await partner.parent_id.all()  # Returns List[ResPartner] with 1 item
        """
        # Load the data first
        data = await self.load()

        if self.is_collection:
            # For collections, return the list as-is
            return data if isinstance(data, list) else []
        else:
            # For single records, wrap in a list for consistency
            return [data] if data is not None else []

    def __await__(self):
        """Make the relationship awaitable."""
        return self.load().__await__()

    def __repr__(self) -> str:
        """String representation of the lazy relationship."""
        status = "loaded" if self._is_loaded else "not loaded"
        collection_type = "collection" if self.is_collection else "single"
        return f"LazyRelationship({self.field_name}, {self.relation_model}, {collection_type}, {status})"


class RelationshipManager:
    """Manages relationships for an Odoo model instance.

    This class handles the creation and management of lazy relationships,
    prefetching strategies, and relationship caching.
    """

    def __init__(self, record: Any, client: Any):
        """Initialize the relationship manager.

        Args:
            record: The model instance that owns the relationships
            client: OdooFlow client for data operations
        """
        self.record = record
        self.client = client
        self._relationships: Dict[str, LazyRelationship] = {}

    def create_relationship(
        self,
        field_name: str,
        relation_model: str,
        relation_data: Any,
        is_collection: bool = False,
    ) -> LazyRelationship:
        """Create a lazy relationship for a field.

        Args:
            field_name: Name of the relationship field
            relation_model: Name of the related Odoo model
            relation_data: Raw relationship data from Odoo
            is_collection: Whether this is a collection relationship

        Returns:
            LazyRelationship instance
        """
        # Parse relation data based on Odoo format
        relation_ids = self._parse_relation_data(relation_data, is_collection)

        # Create the lazy relationship
        relationship = LazyRelationship(
            parent_record=self.record,
            field_name=field_name,
            relation_model=relation_model,
            relation_ids=relation_ids,
            client=self.client,
            is_collection=is_collection,
        )

        # Cache it
        self._relationships[field_name] = relationship
        return relationship

    def _parse_relation_data(
        self, relation_data: Any, is_collection: bool
    ) -> Union[int, List[int], None]:
        """Parse relationship data from Odoo format.

        Args:
            relation_data: Raw data from Odoo
            is_collection: Whether this is a collection

        Returns:
            Parsed relation IDs
        """
        if relation_data is None or relation_data is False:
            return None

        if is_collection:
            # One2many/Many2many: list of IDs
            if isinstance(relation_data, list):
                return [
                    item if isinstance(item, int) else item[0] for item in relation_data
                ]
            return []
        else:
            # Many2one: single ID or [id, name] tuple
            if isinstance(relation_data, list) and len(relation_data) >= 1:
                return relation_data[0]  # Extract ID from [id, name]
            elif isinstance(relation_data, int):
                return relation_data
            return None

    def get_relationship(self, field_name: str) -> Optional[LazyRelationship]:
        """Get a relationship by field name.

        Args:
            field_name: Name of the relationship field

        Returns:
            LazyRelationship instance or None
        """
        return self._relationships.get(field_name)

    async def prefetch_relationships(
        self, field_names: List[str], fields: Optional[List[str]] = None
    ) -> None:
        """Prefetch multiple relationships efficiently.

        Args:
            field_names: List of relationship field names to prefetch
            fields: Specific fields to fetch for related records
        """
        # Group relationships by model for efficient fetching
        model_groups: Dict[str, List[LazyRelationship]] = {}

        for field_name in field_names:
            relationship = self._relationships.get(field_name)
            if relationship and not relationship.is_loaded():
                model_name = relationship.relation_model
                if model_name not in model_groups:
                    model_groups[model_name] = []
                model_groups[model_name].append(relationship)

        # Fetch data for each model group
        for model_name, relationships in model_groups.items():
            # Collect all IDs for this model
            all_ids = set()
            for rel in relationships:
                if rel.relation_ids:
                    if isinstance(rel.relation_ids, list):
                        all_ids.update(rel.relation_ids)
                    else:
                        all_ids.add(rel.relation_ids)

            if all_ids:
                # Fetch all records at once
                fetch_fields = fields or ["id", "name", "display_name"]
                records_data = await self.client.search_read(
                    model_name,
                    domain=[("id", "in", list(all_ids))],
                    fields=fetch_fields,
                )

                # Create a lookup dict
                records_by_id = {record["id"]: record for record in records_data}

                # Populate each relationship's cache
                for rel in relationships:
                    if rel.is_collection:
                        if isinstance(rel.relation_ids, list):
                            rel._loaded_data = [
                                records_by_id.get(rid)
                                for rid in rel.relation_ids
                                if rid in records_by_id
                            ]
                        else:
                            rel._loaded_data = []
                    else:
                        if isinstance(rel.relation_ids, int):
                            rel._loaded_data = records_by_id.get(rel.relation_ids)
                        else:
                            rel._loaded_data = None

                    rel._is_loaded = True

    def invalidate_all(self) -> None:
        """Invalidate all cached relationships."""
        for relationship in self._relationships.values():
            relationship.invalidate()

    def invalidate_field(self, field_name: str) -> None:
        """Invalidate a specific relationship field.

        Args:
            field_name: Name of the field to invalidate
        """
        relationship = self._relationships.get(field_name)
        if relationship:
            relationship.invalidate()
