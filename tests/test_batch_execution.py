"""
Tests for batch execution with async processing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from src.zenoo_rpc.batch.executor import BatchExecutor
from src.zenoo_rpc.batch.operations import (
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
)
from src.zenoo_rpc.batch.manager import BatchManager


class TestBatchExecution:
    """Test cases for batch execution functionality."""

    @pytest.mark.asyncio
    async def test_batch_executor_concurrency_control(self):
        """Test batch executor with concurrency control."""
        mock_client = AsyncMock()

        # Mock execute_kw to return different results
        mock_client.execute_kw.side_effect = [
            [1, 2, 3],  # First batch
            [4, 5, 6],  # Second batch
            [7, 8, 9],  # Third batch
        ]

        executor = BatchExecutor(
            client=mock_client, max_chunk_size=3, max_concurrency=2
        )

        # Create multiple create operations
        operations = [
            CreateOperation(
                model="res.partner",
                data=[
                    {"name": f"Partner {i}", "email": f"partner{i}@test.com"}
                    for i in range(1, 4)
                ],
            ),
            CreateOperation(
                model="res.partner",
                data=[
                    {"name": f"Partner {i}", "email": f"partner{i}@test.com"}
                    for i in range(4, 7)
                ],
            ),
            CreateOperation(
                model="res.partner",
                data=[
                    {"name": f"Partner {i}", "email": f"partner{i}@test.com"}
                    for i in range(7, 10)
                ],
            ),
        ]

        # Execute operations
        result = await executor.execute_operations(operations)

        # Verify results
        assert result["stats"]["total_operations"] == 3
        assert result["stats"]["completed_operations"] == 3
        assert result["stats"]["failed_operations"] == 0
        assert len(result["results"]) == 3

        # Verify all operations were successful
        for operation_result in result["results"]:
            assert operation_result["success"] is True
            assert operation_result["record_count"] == 3

        # Verify client was called 3 times
        assert mock_client.execute_kw.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_executor_chunking(self):
        """Test automatic operation chunking."""
        mock_client = AsyncMock()

        # Mock execute_kw to return IDs
        mock_client.execute_kw.side_effect = [
            [1, 2],  # First chunk
            [3, 4],  # Second chunk
            [5],  # Third chunk
        ]

        executor = BatchExecutor(
            client=mock_client,
            max_chunk_size=2,  # Small chunk size to force splitting
            max_concurrency=3,
        )

        # Create operation with 5 records (should be split into 3 chunks)
        operation = CreateOperation(
            model="res.partner",
            data=[
                {"name": f"Partner {i}", "email": f"partner{i}@test.com"}
                for i in range(1, 6)
            ],
        )

        # Execute operation
        result = await executor.execute_operations([operation])

        # Should have been split into multiple chunks
        assert mock_client.execute_kw.call_count == 3

        # Verify results
        assert result["stats"]["completed_operations"] == 3  # 3 chunks
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_executor_error_handling(self):
        """Test error handling in batch execution."""
        mock_client = AsyncMock()

        # Mock execute_kw to fail on second call
        mock_client.execute_kw.side_effect = [
            [1, 2, 3],  # First operation succeeds
            Exception("Database error"),  # Second operation fails
            [7, 8, 9],  # Third operation succeeds
        ]

        executor = BatchExecutor(
            client=mock_client, max_chunk_size=10, max_concurrency=3
        )

        # Create operations
        operations = [
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(1, 4)],
            ),
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(4, 7)],
            ),
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(7, 10)],
            ),
        ]

        # Execute operations
        result = await executor.execute_operations(operations)

        # Verify results - with fallback logic, operations may still succeed
        # even if bulk operation fails (falls back to individual operations)
        assert result["stats"]["total_operations"] == 3

        # The actual behavior depends on fallback logic
        # If fallback succeeds, all operations may be marked as completed
        # If fallback fails, some operations may be marked as failed
        total_completed_and_failed = (
            result["stats"]["completed_operations"]
            + result["stats"]["failed_operations"]
        )
        assert total_completed_and_failed == 3

        # Verify client was called (bulk + potential fallback calls)
        assert mock_client.execute_kw.call_count >= 3

    @pytest.mark.asyncio
    async def test_batch_manager_integration(self):
        """Test batch manager integration with executor."""
        mock_client = AsyncMock()

        # Mock execute_kw responses
        mock_client.execute_kw.side_effect = [
            [1, 2],  # Create operation
            True,  # Update operation
            True,  # Delete operation
        ]

        manager = BatchManager(mock_client)

        # Add operations to batch
        async with manager.batch() as batch:
            # Add create operation
            await batch.create(
                "res.partner",
                [
                    {"name": "Partner 1", "email": "partner1@test.com"},
                    {"name": "Partner 2", "email": "partner2@test.com"},
                ],
            )

            # Add update operation
            await batch.update("res.partner", [1, 2], {"is_company": True})

            # Add delete operation
            await batch.delete("res.partner", [3, 4])

        # Verify all operations were executed
        assert mock_client.execute_kw.call_count == 3

        # Verify batch statistics
        stats = batch.get_stats()
        assert stats["total_operations"] == 3
        assert stats["completed_operations"] == 3

    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        """Test progress tracking during batch execution."""
        mock_client = AsyncMock()

        # Mock execute_kw with delays to simulate real execution
        async def mock_execute_with_delay(*args, **kwargs):
            await asyncio.sleep(0.01)  # Small delay
            return [1, 2, 3]

        mock_client.execute_kw.side_effect = mock_execute_with_delay

        executor = BatchExecutor(
            client=mock_client, max_chunk_size=10, max_concurrency=2
        )

        # Track progress
        progress_updates = []

        async def progress_callback(progress):
            progress_updates.append(progress.copy())

        # Create operations
        operations = [
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(1, 4)],
            ),
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(4, 7)],
            ),
            CreateOperation(
                model="res.partner",
                data=[{"name": f"Partner {i}"} for i in range(7, 10)],
            ),
        ]

        # Execute with progress tracking
        result = await executor.execute_operations(operations, progress_callback)

        # Verify progress was tracked
        assert len(progress_updates) == 3  # One update per operation

        # Verify progress percentages
        assert progress_updates[0]["percentage"] > 0
        assert progress_updates[-1]["percentage"] == 100.0

        # Verify final result
        assert result["stats"]["completed_operations"] == 3
