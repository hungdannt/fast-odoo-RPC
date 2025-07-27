"""
Batch operation executor for OdooFlow.

This module provides the execution engine for batch operations
with performance optimization and error handling.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
import logging

from .operations import (
    BatchOperation,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    OperationStatus,
)
from .exceptions import BatchExecutionError, BatchTimeoutError, BatchSizeError

logger = logging.getLogger(__name__)


class BatchExecutor:
    """Executes batch operations with performance optimization.

    This class handles the actual execution of batch operations,
    including chunking, parallel execution, and error handling.

    Features:
    - Automatic operation chunking
    - Parallel execution with concurrency control
    - Progress tracking and monitoring
    - Error handling and partial results
    - Performance optimization

    Example:
        >>> executor = BatchExecutor(client, max_chunk_size=100, max_concurrency=5)
        >>> results = await executor.execute_operations(operations)
    """

    def __init__(
        self,
        client: Any,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[int] = None,
        retry_attempts: int = 3,
    ):
        """Initialize batch executor.

        Args:
            client: OdooFlow client instance
            max_chunk_size: Maximum records per chunk
            max_concurrency: Maximum concurrent operations
            timeout: Operation timeout in seconds
            retry_attempts: Number of retry attempts for failed operations
        """
        self.client = client
        self.max_chunk_size = max_chunk_size
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.retry_attempts = retry_attempts

        # Execution state
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
            "total_records": 0,
            "processed_records": 0,
            "start_time": None,
            "end_time": None,
        }

    async def execute_operations(
        self,
        operations: List[BatchOperation],
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a list of batch operations.

        Args:
            operations: List of batch operations to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with execution results and statistics

        Raises:
            BatchExecutionError: If execution fails
        """
        if not operations:
            return {"results": [], "stats": self.stats}

        # Initialize stats
        self.stats["total_operations"] = len(operations)
        self.stats["total_records"] = sum(op.get_batch_size() for op in operations)
        self.stats["start_time"] = time.time()

        logger.info(
            f"Starting batch execution: {len(operations)} operations, {self.stats['total_records']} records"
        )

        try:
            # Chunk operations if needed
            chunked_operations = await self._chunk_operations(operations)

            # Execute operations
            results = await self._execute_chunked_operations(
                chunked_operations, progress_callback
            )

            # Finalize stats
            self.stats["end_time"] = time.time()
            duration = self.stats["end_time"] - self.stats["start_time"]

            logger.info(
                f"Batch execution completed in {duration:.2f}s: {self.stats['completed_operations']}/{self.stats['total_operations']} operations successful"
            )

            return {"results": results, "stats": self.stats, "duration": duration}

        except Exception as e:
            self.stats["end_time"] = time.time()
            logger.error(f"Batch execution failed: {e}")
            raise BatchExecutionError(f"Batch execution failed: {e}")

    async def _chunk_operations(
        self, operations: List[BatchOperation]
    ) -> List[BatchOperation]:
        """Chunk operations into smaller pieces if needed.

        Args:
            operations: List of operations to chunk

        Returns:
            List of chunked operations
        """
        chunked_operations = []

        for operation in operations:
            if operation.get_batch_size() > self.max_chunk_size:
                # Split large operations
                chunks = operation.split(self.max_chunk_size)
                chunked_operations.extend(chunks)
                logger.debug(
                    f"Split operation {operation.operation_id} into {len(chunks)} chunks"
                )
            else:
                chunked_operations.append(operation)

        logger.debug(
            f"Chunked {len(operations)} operations into {len(chunked_operations)} chunks"
        )
        return chunked_operations

    async def _execute_chunked_operations(
        self,
        operations: List[BatchOperation],
        progress_callback: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """Execute chunked operations with concurrency control.

        Args:
            operations: List of chunked operations
            progress_callback: Optional progress callback

        Returns:
            List of operation results
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_with_semaphore(operation):
            async with semaphore:
                return await self._execute_single_operation(operation)

        # Create tasks for all operations with semaphore
        tasks = [
            asyncio.create_task(execute_with_semaphore(operation))
            for operation in operations
        ]

        # Execute with progress tracking
        results = []
        completed = 0

        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                completed += 1

                # Update stats
                if result["success"]:
                    self.stats["completed_operations"] += 1
                    self.stats["processed_records"] += result.get("record_count", 0)
                else:
                    self.stats["failed_operations"] += 1

                # Call progress callback
                if progress_callback:
                    progress = {
                        "completed": completed,
                        "total": len(operations),
                        "percentage": (completed / len(operations)) * 100,
                        "stats": self.stats.copy(),
                    }
                    await progress_callback(progress)

            except Exception as e:
                logger.error(f"Operation execution failed: {e}")
                self.stats["failed_operations"] += 1
                results.append(
                    {"success": False, "error": str(e), "operation_id": None}
                )

        return results

    async def _execute_single_operation(
        self, operation: BatchOperation
    ) -> Dict[str, Any]:
        """Execute a single batch operation.

        Args:
            operation: Batch operation to execute

        Returns:
            Operation result dictionary
        """
        async with self.semaphore:  # Limit concurrency
            operation.status = OperationStatus.EXECUTING
            operation.started_at = time.time()

            try:
                # Execute with timeout
                if self.timeout:
                    result = await asyncio.wait_for(
                        self._perform_operation(operation), timeout=self.timeout
                    )
                else:
                    result = await self._perform_operation(operation)

                # Mark as completed
                operation.status = OperationStatus.COMPLETED
                operation.completed_at = time.time()
                operation.result = result

                return {
                    "success": True,
                    "operation_id": operation.operation_id,
                    "operation_type": operation.operation_type.value,
                    "model": operation.model,
                    "record_count": operation.get_batch_size(),
                    "result": result,
                    "duration": operation.get_duration(),
                }

            except asyncio.TimeoutError:
                operation.status = OperationStatus.FAILED
                operation.completed_at = time.time()
                operation.error = "Operation timeout"

                raise BatchTimeoutError(f"Operation {operation.operation_id} timed out")

            except Exception as e:
                operation.status = OperationStatus.FAILED
                operation.completed_at = time.time()
                operation.error = str(e)

                logger.error(f"Operation {operation.operation_id} failed: {e}")
                return {
                    "success": False,
                    "operation_id": operation.operation_id,
                    "operation_type": operation.operation_type.value,
                    "model": operation.model,
                    "record_count": operation.get_batch_size(),
                    "error": str(e),
                    "duration": operation.get_duration(),
                }

    async def _perform_operation(self, operation: BatchOperation) -> Any:
        """Perform the actual operation execution.

        Args:
            operation: Batch operation to perform

        Returns:
            Operation result

        Raises:
            BatchExecutionError: If operation fails
        """
        if isinstance(operation, CreateOperation):
            return await self._perform_create(operation)
        elif isinstance(operation, UpdateOperation):
            return await self._perform_update(operation)
        elif isinstance(operation, DeleteOperation):
            return await self._perform_delete(operation)
        else:
            raise BatchExecutionError(f"Unknown operation type: {type(operation)}")

    async def _perform_create(self, operation: CreateOperation) -> List[int]:
        """Perform batch create operation.

        Args:
            operation: Create operation

        Returns:
            List of created record IDs
        """
        logger.debug(
            f"Executing create operation: {operation.model}, {len(operation.data)} records"
        )

        # Use bulk_create if available, otherwise fall back to individual creates
        try:
            # Try bulk create first (most efficient)
            result = await self.client.execute_kw(
                operation.model, "create", [operation.data], operation.context or {}
            )

            # Handle different return formats
            if isinstance(result, list):
                return result
            else:
                return [result]

        except Exception as e:
            # Fall back to individual creates if bulk fails
            logger.warning(
                f"Bulk create failed, falling back to individual creates: {e}"
            )

            created_ids = []
            for record_data in operation.data:
                try:
                    record_id = await self.client.execute_kw(
                        operation.model,
                        "create",
                        [record_data],
                        operation.context or {},
                    )
                    created_ids.append(record_id)
                except Exception as record_error:
                    logger.error(
                        f"Failed to create record {record_data}: {record_error}"
                    )
                    # Continue with other records

            if not created_ids:
                raise BatchExecutionError("Failed to create any records individually.")

            return created_ids

    async def _perform_update(self, operation: UpdateOperation) -> bool:
        """Perform batch update operation.

        Args:
            operation: Update operation

        Returns:
            True if successful
        """
        logger.debug(f"Executing update operation: {operation.model}")

        if isinstance(operation.data, dict):
            # Bulk update with same data
            logger.debug(f"Bulk update: {len(operation.record_ids)} records")

            result = await self.client.execute_kw(
                operation.model,
                "write",
                [operation.record_ids, operation.data],
                operation.context or {},
            )
            return result

        else:
            # Individual updates
            logger.debug(f"Individual updates: {len(operation.data)} records")

            success_count = 0
            for record_data in operation.data:
                record_id = record_data.pop("id")
                try:
                    await self.client.execute_kw(
                        operation.model,
                        "write",
                        [[record_id], record_data],
                        operation.context or {},
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to update record {record_id}: {e}")
                    # Continue with other records

            return success_count == len(operation.data)

    async def _perform_delete(self, operation: DeleteOperation) -> bool:
        """Perform batch delete operation.

        Args:
            operation: Delete operation

        Returns:
            True if successful
        """
        logger.debug(
            f"Executing delete operation: {operation.model}, {len(operation.data)} records"
        )

        result = await self.client.execute_kw(
            operation.model, "unlink", [operation.data], operation.context or {}
        )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics.

        Returns:
            Dictionary with execution statistics
        """
        stats = self.stats.copy()

        if stats["start_time"] and stats["end_time"]:
            stats["duration"] = stats["end_time"] - stats["start_time"]

            # Calculate rates
            if stats["duration"] > 0:
                stats["operations_per_second"] = (
                    stats["completed_operations"] / stats["duration"]
                )
                stats["records_per_second"] = (
                    stats["processed_records"] / stats["duration"]
                )

        return stats
