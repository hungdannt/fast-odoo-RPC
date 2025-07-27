"""
Comprehensive tests for Zenoo-RPC batch operations.

This module tests all aspects of batch operations including:
- Batch operations (Create, Update, Delete)
- Batch manager and executor
- Batch context managers
- Operation splitting and optimization
- Error handling and rollback
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from zenoo_rpc.batch.manager import BatchManager, Batch
from zenoo_rpc.batch.operations import (
    BatchOperation,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    OperationType,
    OperationStatus,
    create_batch_operation,
)
from zenoo_rpc.batch.executor import BatchExecutor
from zenoo_rpc.batch.context import batch_context, batch_operation
from zenoo_rpc.batch.exceptions import (
    BatchError,
    BatchExecutionError,
    BatchValidationError,
)


class TestBatchOperations:
    """Test individual batch operations."""

    def test_create_operation(self):
        """Test create operation creation and properties."""
        data = [
            {"name": "Company A", "is_company": True},
            {"name": "Company B", "is_company": True},
            {"name": "Person C", "is_company": False},
        ]

        operation = CreateOperation(
            model="res.partner", data=data, priority=1  # High priority
        )

        assert operation.operation_type == OperationType.CREATE
        assert operation.model == "res.partner"
        assert operation.data == data
        assert operation.priority == 1
        assert operation.get_batch_size() == 3
        assert not operation.is_completed()
        assert operation.get_duration() is None

    def test_update_operation_bulk(self):
        """Test bulk update operation."""
        operation = UpdateOperation(
            model="res.partner",
            data={"active": False, "category_id": 5},
            record_ids=[1, 2, 3, 4, 5],
        )

        assert operation.operation_type == OperationType.UPDATE
        assert operation.get_batch_size() == 5
        assert operation.is_bulk_operation()
        assert operation.data == {"active": False, "category_id": 5}
        assert operation.record_ids == [1, 2, 3, 4, 5]

    def test_update_operation_individual(self):
        """Test individual update operations."""
        data = [
            {"id": 1, "name": "Updated Name 1", "email": "new1@example.com"},
            {"id": 2, "name": "Updated Name 2", "email": "new2@example.com"},
        ]

        operation = UpdateOperation(model="res.partner", data=data)

        assert operation.operation_type == OperationType.UPDATE
        assert operation.get_batch_size() == 2
        assert not operation.is_bulk_operation()
        assert operation.data == data
        assert operation.record_ids is None

    def test_delete_operation(self):
        """Test delete operation."""
        record_ids = [10, 11, 12, 13, 14]

        operation = DeleteOperation(model="res.partner", data=record_ids)

        assert operation.operation_type == OperationType.DELETE
        assert operation.model == "res.partner"
        assert operation.data == record_ids
        assert operation.get_batch_size() == 5

    def test_operation_splitting(self):
        """Test operation splitting for large batches."""
        # Create large create operation
        data = [{"name": f"Company {i}"} for i in range(250)]

        operation = CreateOperation(model="res.partner", data=data)

        # Split into chunks of 100
        chunks = operation.split(100)

        assert len(chunks) == 3  # 250 / 100 = 3 chunks
        assert chunks[0].get_batch_size() == 100
        assert chunks[1].get_batch_size() == 100
        assert chunks[2].get_batch_size() == 50

        # Verify data integrity
        total_data = []
        for chunk in chunks:
            total_data.extend(chunk.data)

        assert len(total_data) == 250
        assert total_data == data

    def test_update_operation_splitting_bulk(self):
        """Test bulk update operation splitting."""
        operation = UpdateOperation(
            model="res.partner",
            data={"active": False},
            record_ids=list(range(1, 251)),  # 250 IDs
        )

        chunks = operation.split(100)

        assert len(chunks) == 3
        assert chunks[0].get_batch_size() == 100
        assert chunks[1].get_batch_size() == 100
        assert chunks[2].get_batch_size() == 50

        # Verify all chunks are bulk operations
        for chunk in chunks:
            assert chunk.is_bulk_operation()
            assert chunk.data == {"active": False}

    def test_update_operation_splitting_individual(self):
        """Test individual update operation splitting."""
        data = [{"id": i, "name": f"Name {i}"} for i in range(1, 151)]  # 150 records

        operation = UpdateOperation(model="res.partner", data=data)

        chunks = operation.split(50)

        assert len(chunks) == 3
        assert chunks[0].get_batch_size() == 50
        assert chunks[1].get_batch_size() == 50
        assert chunks[2].get_batch_size() == 50

        # Verify data integrity
        total_data = []
        for chunk in chunks:
            total_data.extend(chunk.data)

        assert len(total_data) == 150
        assert total_data == data

    def test_delete_operation_splitting(self):
        """Test delete operation splitting."""
        record_ids = list(range(1, 301))  # 300 IDs

        operation = DeleteOperation(model="res.partner", data=record_ids)

        chunks = operation.split(100)

        assert len(chunks) == 3
        assert chunks[0].get_batch_size() == 100
        assert chunks[1].get_batch_size() == 100
        assert chunks[2].get_batch_size() == 100

        # Verify data integrity
        total_ids = []
        for chunk in chunks:
            total_ids.extend(chunk.data)

        assert len(total_ids) == 300
        assert total_ids == record_ids

    def test_operation_factory(self):
        """Test batch operation factory function."""
        # Test create operation
        create_op = create_batch_operation(
            "create", "res.partner", [{"name": "Test"}], priority=1
        )
        assert isinstance(create_op, CreateOperation)
        assert create_op.priority == 1

        # Test update operation
        update_op = create_batch_operation(
            "update", "res.partner", {"active": False}, record_ids=[1, 2, 3]
        )
        assert isinstance(update_op, UpdateOperation)
        assert update_op.is_bulk_operation()

        # Test delete operation
        delete_op = create_batch_operation("delete", "res.partner", [1, 2, 3])
        assert isinstance(delete_op, DeleteOperation)

        # Test invalid operation type
        with pytest.raises(BatchValidationError):
            create_batch_operation("invalid", "res.partner", {})


class TestBatchManager:
    """Test batch manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.batch_manager = BatchManager(self.mock_client)

    def test_batch_creation(self):
        """Test batch creation."""
        batch = self.batch_manager.create_batch()

        assert isinstance(batch, Batch)
        assert batch.batch_id is not None
        assert batch.get_operation_count() == 0
        assert batch.get_record_count() == 0

    def test_batch_operations(self):
        """Test adding operations to batch."""
        batch = self.batch_manager.create_batch()

        # Add create operation
        batch.create(
            "res.partner",
            [
                {"name": "Company A", "is_company": True},
                {"name": "Company B", "is_company": True},
            ],
        )

        # Add update operation
        batch.update("res.partner", {"active": False}, record_ids=[1, 2, 3])

        # Add delete operation
        batch.delete("res.partner", [4, 5, 6])

        assert batch.get_operation_count() == 3
        assert batch.get_record_count() == 8  # 2 + 3 + 3

        # Access operations directly from batch.operations
        operations = batch.operations
        assert len(operations) == 3
        assert operations[0].operation_type == OperationType.CREATE
        assert operations[1].operation_type == OperationType.UPDATE
        assert operations[2].operation_type == OperationType.DELETE

    @pytest.mark.asyncio
    async def test_bulk_create(self):
        """Test bulk create operation."""
        # Mock successful response
        self.mock_client.execute_kw.return_value = [100, 101, 102]

        records = [
            {"name": "Company A", "is_company": True},
            {"name": "Company B", "is_company": True},
            {"name": "Company C", "is_company": True},
        ]

        result = await self.batch_manager.bulk_create("res.partner", records)

        assert result == [100, 101, 102]
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "create", [records], {}
        )

    @pytest.mark.asyncio
    async def test_bulk_update(self):
        """Test bulk update operation."""
        # Mock successful response
        self.mock_client.execute_kw.return_value = True

        result = await self.batch_manager.bulk_update(
            "res.partner",
            {"active": False, "category_id": 5},
            record_ids=[1, 2, 3, 4, 5],
        )

        assert result is True
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner",
            "write",
            [[1, 2, 3, 4, 5], {"active": False, "category_id": 5}],
            {},
        )

    @pytest.mark.asyncio
    async def test_bulk_delete(self):
        """Test bulk delete operation."""
        # Mock successful response
        self.mock_client.execute_kw.return_value = True

        result = await self.batch_manager.bulk_delete("res.partner", [1, 2, 3])

        assert result is True
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "unlink", [[1, 2, 3]], {}
        )

    @pytest.mark.asyncio
    async def test_batch_execution_with_splitting(self):
        """Test batch execution with automatic splitting."""
        batch = self.batch_manager.create_batch()

        # Add large create operation that will be split
        large_data = [{"name": f"Company {i}"} for i in range(250)]
        batch.create("res.partner", large_data)

        # Mock responses for split operations
        self.mock_client.execute_kw.side_effect = [
            list(range(1, 101)),  # First chunk: 100 records
            list(range(101, 201)),  # Second chunk: 100 records
            list(range(201, 251)),  # Third chunk: 50 records
        ]

        # Execute the batch
        results = await batch.execute()

        # Should return a dict with results and stats
        assert "results" in results
        assert "stats" in results
        assert self.mock_client.execute_kw.call_count == 3


class TestBatchExecutor:
    """Test batch executor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.executor = BatchExecutor(self.mock_client)

    @pytest.mark.asyncio
    async def test_execute_create_operation(self):
        """Test executing create operation."""
        operation = CreateOperation(
            model="res.partner", data=[{"name": "Test Company"}]
        )

        self.mock_client.execute_kw.return_value = [123]

        result = await self.executor.execute_operation(operation)

        assert result == [123]
        assert operation.is_completed()
        assert operation.result == [123]
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "create", [[{"name": "Test Company"}]], {}
        )

    @pytest.mark.asyncio
    async def test_execute_update_operation_bulk(self):
        """Test executing bulk update operation."""
        operation = UpdateOperation(
            model="res.partner", data={"active": False}, record_ids=[1, 2, 3]
        )

        self.mock_client.execute_kw.return_value = True

        result = await self.executor.execute_operation(operation)

        assert result is True
        assert operation.is_completed()
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "write", [[1, 2, 3], {"active": False}], {}
        )

    @pytest.mark.asyncio
    async def test_execute_update_operation_individual(self):
        """Test executing individual update operations."""
        data = [{"id": 1, "name": "Updated 1"}, {"id": 2, "name": "Updated 2"}]

        operation = UpdateOperation(model="res.partner", data=data)

        self.mock_client.execute_kw.side_effect = [True, True]

        result = await self.executor.execute_operation(operation)

        assert result == [True, True]
        assert operation.is_completed()
        assert self.mock_client.execute_kw.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_delete_operation(self):
        """Test executing delete operation."""
        operation = DeleteOperation(model="res.partner", data=[1, 2, 3])

        self.mock_client.execute_kw.return_value = True

        result = await self.executor.execute_operation(operation)

        assert result is True
        assert operation.is_completed()
        self.mock_client.execute_kw.assert_called_once_with(
            "res.partner", "unlink", [[1, 2, 3]], {}
        )

    @pytest.mark.asyncio
    async def test_execute_operation_with_error(self):
        """Test operation execution with error."""
        operation = CreateOperation(model="res.partner", data=[{"name": "Test"}])

        self.mock_client.execute_kw.side_effect = Exception("Database error")

        with pytest.raises(BatchExecutionError):
            await self.executor.execute_operation(operation)

        assert not operation.is_completed()
        assert operation.error is not None

    @pytest.mark.asyncio
    async def test_execute_batch_operations(self):
        """Test executing multiple operations in batch."""
        operations = [
            CreateOperation("res.partner", [{"name": "Company A"}]),
            UpdateOperation("res.partner", {"active": False}, record_ids=[1]),
            DeleteOperation("res.partner", [2]),
        ]

        self.mock_client.execute_kw.side_effect = [[100], True, True]

        results = await self.executor.execute_batch(operations)

        assert len(results) == 3
        assert results[0] == [100]
        assert results[1] is True
        assert results[2] is True

        # All operations should be completed
        for operation in operations:
            assert operation.is_completed()

    @pytest.mark.asyncio
    async def test_execute_batch_with_priority(self):
        """Test batch execution respects operation priority."""
        operations = [
            CreateOperation(
                "res.partner", [{"name": "Low"}], priority=0
            ),  # Low priority
            CreateOperation(
                "res.partner", [{"name": "High"}], priority=2
            ),  # High priority
            CreateOperation(
                "res.partner", [{"name": "Normal"}], priority=1
            ),  # Normal priority
        ]

        self.mock_client.execute_kw.side_effect = [[1], [2], [3]]

        results = await self.executor.execute_batch(operations)

        # Should execute in priority order: HIGH, NORMAL, LOW
        assert len(results) == 3

        # Verify execution order by checking call arguments
        calls = self.mock_client.execute_kw.call_args_list
        assert calls[0][0][1] == "create"  # First call
        assert calls[0][0][2] == [[{"name": "High"}]]  # High priority first

    @pytest.mark.asyncio
    async def test_execute_batch_with_rollback(self):
        """Test batch execution with rollback on error."""
        operations = [
            CreateOperation("res.partner", [{"name": "Success 1"}]),
            CreateOperation("res.partner", [{"name": "Success 2"}]),
            CreateOperation("res.partner", [{"name": "Failure"}]),  # This will fail
        ]

        # First two succeed, third fails
        self.mock_client.execute_kw.side_effect = [
            [100],
            [101],
            Exception("Validation error"),
        ]

        with pytest.raises(BatchExecutionError):
            await self.executor.execute_batch(operations, rollback_on_error=True)

        # First two operations should be completed but may be rolled back
        assert operations[0].is_completed()
        assert operations[1].is_completed()
        assert not operations[2].is_completed()
        assert operations[2].error is not None


class TestBatchContextManagers:
    """Test batch context managers."""

    @pytest.mark.asyncio
    async def test_batch_context(self):
        """Test batch_context context manager."""
        mock_client = AsyncMock()
        mock_client.batch_manager = BatchManager(mock_client)
        mock_client.execute_kw.side_effect = [[100], True, True]

        async with batch_context(mock_client) as batch:
            assert isinstance(batch, Batch)

            # Add operations
            batch.create("res.partner", [{"name": "Test Company"}])
            batch.update("res.partner", {"active": False}, record_ids=[1])
            batch.delete("res.partner", [2])

        # Operations should be executed automatically on context exit
        assert mock_client.execute_kw.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_operation_decorator(self):
        """Test batch_operation decorator."""
        mock_client = AsyncMock()
        mock_client.batch_manager = BatchManager(mock_client)
        mock_client.execute_kw.return_value = [100]

        @batch_operation
        async def create_partners(client, names: List[str], _batch=None):
            assert _batch is not None
            for name in names:
                _batch.create("res.partner", [{"name": name}])
            return "success"

        result = await create_partners(mock_client, ["Company A", "Company B"])

        assert result == "success"
        # Should have executed 2 create operations
        assert mock_client.execute_kw.call_count == 2


class TestBatchExceptions:
    """Test batch exception handling."""

    def test_batch_validation_error(self):
        """Test batch validation error."""
        with pytest.raises(BatchValidationError):
            CreateOperation("", [])  # Empty model name

    def test_batch_execution_error(self):
        """Test batch execution error."""
        error = BatchExecutionError("Test error", operation_index=1)
        assert str(error) == "Test error"
        assert error.operation_index == 1

    @pytest.mark.asyncio
    async def test_batch_error_handling(self):
        """Test comprehensive batch error handling."""
        mock_client = AsyncMock()
        batch_manager = BatchManager(mock_client)

        # Create operation that will fail
        operation = CreateOperation("res.partner", [{"name": "Test"}])
        mock_client.execute_kw.side_effect = Exception("Database connection lost")

        with pytest.raises(BatchExecutionError) as exc_info:
            await batch_manager.execute_operation(operation)

        assert "Database connection lost" in str(exc_info.value)
        assert not operation.is_completed()
        assert operation.error is not None


class TestBatchPerformance:
    """Test batch performance optimizations."""

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent execution of independent operations."""
        mock_client = AsyncMock()
        executor = BatchExecutor(mock_client, max_concurrent=3)

        # Create operations that can run concurrently
        operations = [
            CreateOperation("res.partner", [{"name": f"Company {i}"}]) for i in range(5)
        ]

        # Mock delayed responses to test concurrency
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.01)
            return [100]

        mock_client.execute_kw.side_effect = delayed_response

        start_time = asyncio.get_event_loop().time()
        results = await executor.execute_batch(operations)
        end_time = asyncio.get_event_loop().time()

        assert len(results) == 5
        # With concurrency, should be faster than sequential execution
        # (This is a rough test - actual timing may vary)
        assert end_time - start_time < 0.1  # Should be much less than 5 * 0.01

    @pytest.mark.asyncio
    async def test_memory_efficient_large_batch(self):
        """Test memory efficiency with large batches."""
        mock_client = AsyncMock()
        batch_manager = BatchManager(mock_client)

        # Create very large dataset
        large_data = [{"name": f"Company {i}"} for i in range(10000)]

        # Mock response
        mock_client.execute_kw.return_value = list(range(1, 10001))

        # Execute with streaming/chunking
        result = await batch_manager.bulk_create(
            "res.partner", large_data, chunk_size=1000
        )

        assert len(result) == 10000
        # Should have been split into 10 chunks
        assert mock_client.execute_kw.call_count == 10
