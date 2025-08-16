"""
Batch operation context managers for OdooFlow.

This module provides convenient context managers for batch operations
with automatic execution and error handling.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from contextlib import asynccontextmanager

from .manager import BatchManager, Batch
from .exceptions import BatchError


@asynccontextmanager
async def batch_context(
    client: Any,
    auto_execute: bool = True,
    progress_callback: Optional[Callable] = None,
    max_chunk_size: int = 100,
    max_concurrency: int = 5,
):
    """Context manager for batch operations.

    This context manager automatically creates a batch, yields it for
    operation building, and executes it when the context exits.

    Args:
        client: OdooFlow client instance
        auto_execute: Whether to auto-execute on context exit
        progress_callback: Optional progress callback
        max_chunk_size: Maximum records per chunk
        max_concurrency: Maximum concurrent operations

    Yields:
        Batch instance

    Example:
        >>> async with batch_context(client) as batch:
        ...     batch.create("res.partner", [{"name": "Company A"}])
        ...     batch.update("res.partner", {"active": False}, record_ids=[1, 2])
        ...     # Batch is automatically executed when context exits
    """
    # Create batch manager
    batch_manager = BatchManager(
        client=client, max_chunk_size=max_chunk_size, max_concurrency=max_concurrency
    )

    # Create batch
    batch = batch_manager.create_batch()

    try:
        yield batch

        # Auto-execute if enabled and batch has operations
        if auto_execute and batch.get_operation_count() > 0:
            await batch.execute(progress_callback)

    except Exception as e:
        # Log error but don't suppress it
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Batch context error: {e}")
        raise


@asynccontextmanager
async def batch_operation(
    client: Any,
    model: str,
    operation_type: str,
    chunk_size: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
):
    """Context manager for single batch operation.

    This context manager is designed for accumulating data for a single
    type of operation and executing it when the context exits.

    Args:
        client: OdooFlow client instance
        model: Odoo model name
        operation_type: Operation type ("create", "update", "delete")
        chunk_size: Optional chunk size
        context: Optional operation context

    Yields:
        BatchOperationCollector instance

    Example:
        >>> async with batch_operation(client, "res.partner", "create") as collector:
        ...     collector.add({"name": "Company A", "is_company": True})
        ...     collector.add({"name": "Company B", "is_company": True})
        ...     # Records are automatically created when context exits
    """
    collector = BatchOperationCollector(
        client=client,
        model=model,
        operation_type=operation_type,
        chunk_size=chunk_size,
        context=context,
    )

    try:
        yield collector

        # Execute accumulated operations
        if collector.has_data():
            await collector.execute()

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Batch operation context error: {e}")
        raise


class BatchOperationCollector:
    """Collects data for a single batch operation.

    This class accumulates data for a specific operation type
    and executes it as a batch when requested.

    Example:
        >>> collector = BatchOperationCollector(client, "res.partner", "create")
        >>> collector.add({"name": "Company A"})
        >>> collector.add({"name": "Company B"})
        >>> results = await collector.execute()
    """

    def __init__(
        self,
        client: Any,
        model: str,
        operation_type: str,
        chunk_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize batch operation collector.

        Args:
            client: OdooFlow client instance
            model: Odoo model name
            operation_type: Operation type
            chunk_size: Optional chunk size
            context: Optional operation context
        """
        self.client = client
        self.model = model
        self.operation_type = operation_type.lower()
        self.chunk_size = chunk_size
        self.context = context

        # Data collection
        self.data: List[Any] = []
        self.executed = False
        self.results: Optional[Any] = None

        # Validation
        if self.operation_type not in ("create", "update", "delete"):
            raise BatchError(f"Invalid operation type: {operation_type}")

    def add(self, item: Any) -> None:
        """Add an item to the batch.

        Args:
            item: Item to add (dict for create/update, int for delete)
        """
        if self.executed:
            raise BatchError("Cannot add items to executed batch")

        self.data.append(item)

    def add_many(self, items: List[Any]) -> None:
        """Add multiple items to the batch.

        Args:
            items: List of items to add
        """
        if self.executed:
            raise BatchError("Cannot add items to executed batch")

        self.data.extend(items)

    def has_data(self) -> bool:
        """Check if collector has data to process.

        Returns:
            True if has data
        """
        return len(self.data) > 0

    def get_count(self) -> int:
        """Get the number of items in the batch.

        Returns:
            Number of items
        """
        return len(self.data)

    async def execute(self) -> Any:
        """Execute the batch operation.

        Returns:
            Operation results

        Raises:
            BatchError: If already executed or no data
        """
        if self.executed:
            raise BatchError("Batch operation already executed")

        if not self.data:
            raise BatchError("No data to execute")

        # Create batch manager
        batch_manager = BatchManager(
            client=self.client, max_chunk_size=self.chunk_size or 100
        )

        try:
            if self.operation_type == "create":
                self.results = await batch_manager.bulk_create(
                    model=self.model,
                    records=self.data,
                    chunk_size=self.chunk_size,
                    context=self.context,
                )
            elif self.operation_type == "update":
                # For update, data should be in format [{"id": 1, "field": "value"}, ...]
                self.results = await batch_manager.bulk_update(
                    model=self.model,
                    data=self.data,
                    chunk_size=self.chunk_size,
                    context=self.context,
                )
            elif self.operation_type == "delete":
                # For delete, data should be list of IDs
                self.results = await batch_manager.bulk_delete(
                    model=self.model,
                    record_ids=self.data,
                    chunk_size=self.chunk_size,
                    context=self.context,
                )

            self.executed = True
            return self.results

        except Exception as e:
            raise BatchError(f"Batch execution failed: {e}")

    def clear(self) -> None:
        """Clear all collected data.

        Raises:
            BatchError: If already executed
        """
        if self.executed:
            raise BatchError("Cannot clear executed batch")

        self.data.clear()


class BatchProgressTracker:
    """Tracks progress of batch operations.

    This class provides progress tracking capabilities for batch operations
    with callbacks and statistics.

    Example:
        >>> tracker = BatchProgressTracker()
        >>>
        >>> async def progress_callback(progress):
        ...     print(f"Progress: {progress['percentage']:.1f}%")
        >>>
        >>> tracker.set_callback(progress_callback)
        >>>
        >>> async with batch_context(client, progress_callback=tracker.callback) as batch:
        ...     # Operations will report progress
        ...     pass
    """

    def __init__(self):
        """Initialize progress tracker."""
        self.callbacks: List[Callable] = []
        self.current_progress: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, Any]] = []

    def add_callback(self, callback: Callable) -> None:
        """Add a progress callback.

        Args:
            callback: Async function to call with progress updates
        """
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a progress callback.

        Args:
            callback: Callback to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def callback(self, progress: Dict[str, Any]) -> None:
        """Main progress callback that distributes to registered callbacks.

        Args:
            progress: Progress information
        """
        self.current_progress = progress
        self.history.append(progress.copy())

        # Call all registered callbacks
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Progress callback error: {e}")

    def get_current_progress(self) -> Optional[Dict[str, Any]]:
        """Get current progress information.

        Returns:
            Current progress or None
        """
        return self.current_progress

    def get_history(self) -> List[Dict[str, Any]]:
        """Get progress history.

        Returns:
            List of progress updates
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear progress history."""
        self.history.clear()
        self.current_progress = None
