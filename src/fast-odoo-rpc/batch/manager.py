"""
Batch manager for OdooFlow.

This module provides the main interface for batch operations,
coordinating between operation creation, validation, and execution.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager
import logging

from .operations import (
    BatchOperation,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    create_batch_operation,
    validate_batch_operations,
)
from .executor import BatchExecutor
from .exceptions import BatchError, BatchValidationError

logger = logging.getLogger(__name__)


class BatchContext:
    """Context for collecting batch operations."""

    def __init__(self, manager: "BatchManager"):
        self.manager = manager
        self.operations: List[BatchOperation] = []
        self._stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
        }

    async def create(
        self,
        model: str,
        data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add create operation to batch."""
        operation = CreateOperation(model=model, data=data, context=context)
        self.operations.append(operation)
        return operation

    async def update(
        self,
        model: str,
        record_ids: List[int],
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add update operation to batch."""
        operation = UpdateOperation(
            model=model, record_ids=record_ids, data=data, context=context
        )
        self.operations.append(operation)
        return operation

    async def delete(
        self,
        model: str,
        record_ids: List[int],
        context: Optional[Dict[str, Any]] = None,
    ):
        """Add delete operation to batch."""
        operation = DeleteOperation(model=model, data=record_ids, context=context)
        self.operations.append(operation)
        return operation

    def get_stats(self) -> Dict[str, Any]:
        """Get batch statistics."""
        return self._stats.copy()


class BatchManager:
    """Main batch operations manager for OdooFlow.

    This class provides a high-level interface for creating and executing
    batch operations with automatic optimization and error handling.

    Features:
    - Fluent interface for batch building
    - Automatic operation optimization
    - Progress tracking and monitoring
    - Error handling and recovery
    - Performance statistics

    Example:
        >>> batch_manager = BatchManager(client)
        >>>
        >>> # Build batch operations
        >>> batch = batch_manager.create_batch()
        >>> batch.create("res.partner", [
        ...     {"name": "Company A", "is_company": True},
        ...     {"name": "Company B", "is_company": True}
        ... ])
        >>> batch.update("res.partner", {"active": False}, record_ids=[1, 2, 3])
        >>>
        >>> # Execute batch
        >>> results = await batch.execute()
    """

    def __init__(
        self,
        client: Any,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[int] = None,
    ):
        """Initialize batch manager.

        Args:
            client: OdooFlow client instance
            max_chunk_size: Maximum records per chunk
            max_concurrency: Maximum concurrent operations
            timeout: Operation timeout in seconds
        """
        self.client = client
        self.max_chunk_size = max_chunk_size
        self.max_concurrency = max_concurrency
        self.timeout = timeout

        # Active batches
        self.active_batches: Dict[str, "Batch"] = {}

        # Statistics
        self.stats = {
            "total_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
            "total_operations": 0,
            "total_records": 0,
        }

    def create_batch(self, batch_id: Optional[str] = None) -> "Batch":
        """Create a new batch for operations.

        Args:
            batch_id: Optional batch identifier

        Returns:
            Batch instance
        """
        batch_id = batch_id or str(uuid.uuid4())
        batch = Batch(self, batch_id)
        self.active_batches[batch_id] = batch

        logger.debug(f"Created batch {batch_id}")
        return batch

    async def execute_operations(
        self,
        operations: List[BatchOperation],
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Execute a list of batch operations directly.

        Args:
            operations: List of batch operations
            progress_callback: Optional progress callback

        Returns:
            Execution results
        """
        # Validate operations
        validate_batch_operations(operations)

        # Create executor
        executor = BatchExecutor(
            client=self.client,
            max_chunk_size=self.max_chunk_size,
            max_concurrency=self.max_concurrency,
            timeout=self.timeout,
        )

        # Execute operations
        results = await executor.execute_operations(operations, progress_callback)

        # Update stats
        self.stats["total_operations"] += len(operations)
        self.stats["total_records"] += sum(op.get_batch_size() for op in operations)

        return results

    @asynccontextmanager
    async def batch(self):
        """Create a batch context for collecting operations.

        Returns:
            BatchContext for collecting operations
        """
        batch_context = BatchContext(self)
        try:
            yield batch_context
            # Execute all collected operations when exiting context
            if batch_context.operations:
                result = await self.execute_operations(batch_context.operations)
                # Update batch context stats
                batch_context._stats.update(
                    {
                        "total_operations": len(batch_context.operations),
                        "completed_operations": result["stats"]["completed_operations"],
                        "failed_operations": result["stats"]["failed_operations"],
                    }
                )
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    async def bulk_create(
        self,
        model: str,
        records: List[Dict[str, Any]],
        chunk_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[int]:
        """Bulk create records.

        Args:
            model: Odoo model name
            records: List of record data
            chunk_size: Optional chunk size override
            context: Optional context

        Returns:
            List of created record IDs
        """
        operation = CreateOperation(model=model, data=records, context=context)

        executor = BatchExecutor(
            client=self.client,
            max_chunk_size=chunk_size or self.max_chunk_size,
            max_concurrency=self.max_concurrency,
            timeout=self.timeout,
        )

        results = await executor.execute_operations([operation])

        # Aggregate results from all chunks
        all_ids = []
        for result in results["results"]:
            if result["success"]:
                # For create operations, result is a list of IDs
                if isinstance(result["result"], list):
                    all_ids.extend(result["result"])
                else:
                    all_ids.append(result["result"])
            else:
                # If any chunk fails, report the error
                raise BatchError(
                    f"Bulk create failed: {result.get('error', 'Unknown error')}"
                )

        return all_ids

    async def bulk_update(
        self,
        model: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        record_ids: Optional[List[int]] = None,
        chunk_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Bulk update records.

        Args:
            model: Odoo model name
            data: Update data (dict for same data, list for individual data)
            record_ids: Record IDs (required if data is dict)
            chunk_size: Optional chunk size override
            context: Optional context

        Returns:
            True if successful
        """
        operation = UpdateOperation(
            model=model, data=data, record_ids=record_ids, context=context
        )

        executor = BatchExecutor(
            client=self.client,
            max_chunk_size=chunk_size or self.max_chunk_size,
            max_concurrency=self.max_concurrency,
            timeout=self.timeout,
        )

        results = await executor.execute_operations([operation])

        # Check if all chunks succeeded
        for result in results["results"]:
            if not result["success"]:
                raise BatchError(
                    f"Bulk update failed: {result.get('error', 'Unknown error')}"
                )

        # All chunks succeeded
        return True

    async def bulk_delete(
        self,
        model: str,
        record_ids: List[int],
        chunk_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Bulk delete records.

        Args:
            model: Odoo model name
            record_ids: List of record IDs to delete
            chunk_size: Optional chunk size override
            context: Optional context

        Returns:
            True if successful
        """
        operation = DeleteOperation(model=model, data=record_ids, context=context)

        executor = BatchExecutor(
            client=self.client,
            max_chunk_size=chunk_size or self.max_chunk_size,
            max_concurrency=self.max_concurrency,
            timeout=self.timeout,
        )

        results = await executor.execute_operations([operation])

        # Check if all chunks succeeded
        for result in results["results"]:
            if not result["success"]:
                raise BatchError(
                    f"Bulk delete failed: {result.get('error', 'Unknown error')}"
                )

        # All chunks succeeded
        return True

    def get_batch(self, batch_id: str) -> Optional["Batch"]:
        """Get an active batch by ID.

        Args:
            batch_id: Batch identifier

        Returns:
            Batch instance or None
        """
        return self.active_batches.get(batch_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get batch manager statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()


class Batch:
    """Represents a batch of operations to be executed together.

    This class provides a fluent interface for building batch operations
    with automatic validation and optimization.

    Example:
        >>> batch = batch_manager.create_batch()
        >>> batch.create("res.partner", [{"name": "Test"}])
        >>> batch.update("res.partner", {"active": False}, record_ids=[1, 2])
        >>> results = await batch.execute()
    """

    def __init__(self, manager: BatchManager, batch_id: str):
        """Initialize batch.

        Args:
            manager: Batch manager instance
            batch_id: Batch identifier
        """
        self.manager = manager
        self.batch_id = batch_id
        self.operations: List[BatchOperation] = []
        self.executed = False
        self.results: Optional[Dict[str, Any]] = None

    def create(
        self,
        model: str,
        records: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> "Batch":
        """Add create operation to batch.

        Args:
            model: Odoo model name
            records: List of record data
            context: Optional context
            priority: Operation priority

        Returns:
            Self for method chaining
        """
        operation = CreateOperation(
            model=model, data=records, context=context, priority=priority
        )
        self.operations.append(operation)

        logger.debug(
            f"Added create operation to batch {self.batch_id}: {model}, {len(records)} records"
        )
        return self

    def update(
        self,
        model: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        record_ids: Optional[List[int]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> "Batch":
        """Add update operation to batch.

        Args:
            model: Odoo model name
            data: Update data
            record_ids: Record IDs (required if data is dict)
            context: Optional context
            priority: Operation priority

        Returns:
            Self for method chaining
        """
        operation = UpdateOperation(
            model=model,
            data=data,
            record_ids=record_ids,
            context=context,
            priority=priority,
        )
        self.operations.append(operation)

        logger.debug(f"Added update operation to batch {self.batch_id}: {model}")
        return self

    def delete(
        self,
        model: str,
        record_ids: List[int],
        context: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> "Batch":
        """Add delete operation to batch.

        Args:
            model: Odoo model name
            record_ids: List of record IDs to delete
            context: Optional context
            priority: Operation priority

        Returns:
            Self for method chaining
        """
        operation = DeleteOperation(
            model=model, data=record_ids, context=context, priority=priority
        )
        self.operations.append(operation)

        logger.debug(
            f"Added delete operation to batch {self.batch_id}: {model}, {len(record_ids)} records"
        )
        return self

    def add_operation(self, operation: BatchOperation) -> "Batch":
        """Add a custom operation to batch.

        Args:
            operation: Batch operation to add

        Returns:
            Self for method chaining
        """
        self.operations.append(operation)
        logger.debug(
            f"Added custom operation to batch {self.batch_id}: {operation.operation_type.value}"
        )
        return self

    async def execute(
        self, progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute all operations in the batch.

        Args:
            progress_callback: Optional progress callback

        Returns:
            Execution results

        Raises:
            BatchError: If batch has already been executed or validation fails
        """
        if self.executed:
            raise BatchError(f"Batch {self.batch_id} has already been executed")

        if not self.operations:
            raise BatchError(f"Batch {self.batch_id} has no operations to execute")

        logger.info(
            f"Executing batch {self.batch_id} with {len(self.operations)} operations"
        )

        try:
            # Sort operations by priority
            sorted_operations = sorted(
                self.operations, key=lambda op: op.priority, reverse=True
            )

            # Execute operations
            self.results = await self.manager.execute_operations(
                sorted_operations, progress_callback
            )

            self.executed = True

            # Update manager stats
            if self.results["stats"]["failed_operations"] == 0:
                self.manager.stats["completed_batches"] += 1
            else:
                self.manager.stats["failed_batches"] += 1

            self.manager.stats["total_batches"] += 1

            # Remove from active batches
            self.manager.active_batches.pop(self.batch_id, None)

            logger.info(f"Batch {self.batch_id} execution completed")
            return self.results

        except Exception as e:
            self.manager.stats["failed_batches"] += 1
            self.manager.stats["total_batches"] += 1
            logger.error(f"Batch {self.batch_id} execution failed: {e}")
            raise

    def get_operation_count(self) -> int:
        """Get the number of operations in the batch.

        Returns:
            Number of operations
        """
        return len(self.operations)

    def get_record_count(self) -> int:
        """Get the total number of records in the batch.

        Returns:
            Total number of records
        """
        return sum(op.get_batch_size() for op in self.operations)

    def clear(self) -> "Batch":
        """Clear all operations from the batch.

        Returns:
            Self for method chaining
        """
        if self.executed:
            raise BatchError(f"Cannot clear executed batch {self.batch_id}")

        self.operations.clear()
        logger.debug(f"Cleared all operations from batch {self.batch_id}")
        return self
