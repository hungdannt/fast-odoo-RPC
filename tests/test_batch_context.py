"""
Comprehensive test module for batch context and related functionality.

This module contains additional test cases to increase test coverage above 90%,
focusing on untested areas in batch context, operations, and error handling.
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from src.zenoo_rpc.batch.context import (
    batch_context,
    batch_operation,
    BatchOperationCollector,
    BatchProgressTracker,
)
from src.zenoo_rpc.batch.exceptions import (
    BatchError,
    BatchValidationError,
    BatchExecutionError,
)
from src.zenoo_rpc.batch.manager import BatchManager, Batch
from src.zenoo_rpc.batch.operations import BatchOperation, OperationType


class TestBatchContextErrorHandling:
    """Test error handling in batch context managers."""

    @pytest.mark.asyncio
    async def test_batch_context_with_exception(self, mocker):
        """Test batch context manager handles exceptions properly."""
        client_mock = AsyncMock()
        batch_mock = MagicMock()
        batch_mock.get_operation_count.return_value = 1
        batch_mock.execute = AsyncMock(side_effect=Exception("Test error"))

        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.return_value = batch_mock

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        # Mock logger to verify error logging
        logger_mock = MagicMock()
        mocker.patch("logging.getLogger", return_value=logger_mock)

        with pytest.raises(Exception, match="Test error"):
            async with batch_context(client_mock) as batch:
                assert batch == batch_mock

        # Verify error was logged
        logger_mock.error.assert_called_once()
        assert "Batch context error" in logger_mock.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_batch_context_empty_batch_no_execute(self, mocker):
        """Test that empty batch doesn't execute."""
        client_mock = AsyncMock()
        batch_mock = MagicMock()
        batch_mock.get_operation_count.return_value = 0  # Empty batch
        batch_mock.execute = AsyncMock()

        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.return_value = batch_mock

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        async with batch_context(client_mock) as batch:
            assert batch == batch_mock

        # Should not execute empty batch
        batch_mock.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_context_with_progress_callback(self, mocker):
        """Test batch context with progress callback."""
        client_mock = AsyncMock()
        progress_callback = AsyncMock()

        batch_mock = MagicMock()
        batch_mock.get_operation_count.return_value = 1
        batch_mock.execute = AsyncMock()

        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.return_value = batch_mock

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        async with batch_context(
            client_mock,
            progress_callback=progress_callback,
            max_chunk_size=50,
            max_concurrency=3,
        ) as batch:
            assert batch == batch_mock

        # Verify execute was called with progress callback
        batch_mock.execute.assert_called_once_with(progress_callback)

    @pytest.mark.asyncio
    async def test_batch_context_get_operation_count_exception(self, mocker, caplog):
        """Test batch context error handling when get_operation_count raises exception.

        This test specifically targets lines 62-67 of batch/context.py to ensure
        that when get_operation_count raises an exception in the batch_context,
        the exception is logged and re-raised.
        """
        # Create mocks
        client_mock = AsyncMock()
        batch_mock = MagicMock()

        # Make get_operation_count raise an exception
        batch_mock.get_operation_count.side_effect = Exception("Operation count error")
        batch_mock.execute = AsyncMock()  # Should not be called

        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.return_value = batch_mock

        # Patch BatchManager
        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        # Use caplog to capture log messages
        with caplog.at_level(logging.ERROR):
            # Verify the exception is propagated
            with pytest.raises(Exception, match="Operation count error"):
                async with batch_context(client_mock, auto_execute=True) as batch:
                    assert batch == batch_mock

        # Verify the error was logged with the expected message
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "Batch context error: Operation count error" in caplog.records[0].message

        # Verify execute was never called since exception occurred before
        batch_mock.execute.assert_not_called()


class TestBatchOperationContext:
    """Test batch operation context manager."""

    @pytest.mark.asyncio
    async def test_batch_operation_with_exception(self, mocker):
        """Test batch operation context handles exceptions."""
        client_mock = AsyncMock()

        # Mock BatchOperationCollector to raise exception
        collector_mock = MagicMock()
        collector_mock.has_data.return_value = True
        collector_mock.execute = AsyncMock(side_effect=BatchError("Execution failed"))

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchOperationCollector",
            return_value=collector_mock,
        )

        # Mock logger
        logger_mock = MagicMock()
        mocker.patch("logging.getLogger", return_value=logger_mock)

        with pytest.raises(BatchError, match="Execution failed"):
            async with batch_operation(
                client_mock, "res.partner", "create"
            ) as collector:
                assert collector == collector_mock

        # Verify error was logged
        logger_mock.error.assert_called_once()
        assert "Batch operation context error" in logger_mock.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_batch_operation_with_context_and_chunk_size(self, mocker):
        """Test batch operation with custom context and chunk size."""
        client_mock = AsyncMock()
        custom_context = {"lang": "en_US", "tz": "UTC"}

        # Capture the arguments passed to BatchOperationCollector
        collector_init_mock = MagicMock()

        def mock_collector_init(*args, **kwargs):
            collector_init_mock(*args, **kwargs)
            mock_instance = MagicMock()
            mock_instance.has_data.return_value = False
            mock_instance.execute = AsyncMock()
            return mock_instance

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchOperationCollector",
            side_effect=mock_collector_init,
        )

        async with batch_operation(
            client_mock, "res.partner", "update", chunk_size=25, context=custom_context
        ) as collector:
            pass

        # Verify BatchOperationCollector was created with correct parameters
        collector_init_mock.assert_called_once_with(
            client=client_mock,
            model="res.partner",
            operation_type="update",
            chunk_size=25,
            context=custom_context,
        )


class TestBatchOperationCollectorAdvanced:
    """Advanced tests for BatchOperationCollector."""

    def test_collector_invalid_operation_type(self):
        """Test collector raises error for invalid operation type."""
        client_mock = AsyncMock()

        with pytest.raises(BatchError, match="Invalid operation type: invalid"):
            BatchOperationCollector(client_mock, "res.partner", "invalid")

    def test_collector_add_after_execution(self):
        """Test adding items after execution raises error."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        # Mark as executed
        collector.executed = True

        with pytest.raises(BatchError, match="Cannot add items to executed batch"):
            collector.add({"name": "Test"})

        # Test adding normally before execution
        collector.executed = False
        collector.add({"name": "Normal Add"})
        assert collector.get_count() == 1

    def test_collector_add_many_after_execution(self):
        """Test adding many items after execution raises error."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        # Mark as executed
        collector.executed = True

        with pytest.raises(BatchError, match="Cannot add items to executed batch"):
            collector.add_many([{"name": "Test1"}, {"name": "Test2"}])

        # Test adding many normally before execution
        collector.executed = False
        collector.add_many([{"name": "Normal Add1"}, {"name": "Normal Add2"}])
        assert collector.get_count() == 2

        collector.clear()  # Clear for next test to keep isolation
        assert collector.get_count() == 0

        collector.add({"name": "Restart Normal Add"})  # Add after clear
        assert collector.get_count() == 1

        collector.add_many([{"name": "Normal Add Again"}])
        assert collector.get_count() == 2

        collector.clear()
        assert collector.get_count() == 0

        collector.executed = True
        with pytest.raises(BatchError, match="Cannot clear executed batch"):
            collector.clear()

    def test_collector_clear_after_execution(self):
        """Test clearing after execution raises error."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        # Mark as executed
        collector.executed = True

        with pytest.raises(BatchError, match="Cannot clear executed batch"):
            collector.clear()

    @pytest.mark.asyncio
    async def test_collector_execute_already_executed(self):
        """Test executing already executed batch raises error."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        # Mark as executed
        collector.executed = True

        with pytest.raises(BatchError, match="Batch operation already executed"):
            await collector.execute()

    @pytest.mark.asyncio
    async def test_collector_execute_no_data(self):
        """Test executing without data raises error."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        with pytest.raises(BatchError, match="No data to execute"):
            await collector.execute()

    @pytest.mark.asyncio
    async def test_collector_execute_with_error(self, mocker):
        """Test execute handles errors from batch manager."""
        client_mock = AsyncMock()
        batch_manager_mock = AsyncMock()
        batch_manager_mock.bulk_create = AsyncMock(
            side_effect=Exception("Network error")
        )

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        collector = BatchOperationCollector(client_mock, "res.partner", "create")
        collector.add({"name": "Test"})

        with pytest.raises(BatchError, match="Batch execution failed: Network error"):
            await collector.execute()

    def test_collector_get_count(self):
        """Test get_count returns correct number of items."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        assert collector.get_count() == 0

        collector.add({"name": "Test1"})
        assert collector.get_count() == 1

        collector.add_many([{"name": "Test2"}, {"name": "Test3"}])
        assert collector.get_count() == 3

    def test_collector_has_data(self):
        """Test has_data returns correct status."""
        client_mock = AsyncMock()
        collector = BatchOperationCollector(client_mock, "res.partner", "create")

        assert collector.has_data() is False

        collector.add({"name": "Test"})
        assert collector.has_data() is True

        collector.clear()
        assert collector.has_data() is False

    @pytest.mark.asyncio
    async def test_collector_update_operation(self, mocker):
        """Test collector with update operation."""
        client_mock = AsyncMock()
        batch_manager_mock = AsyncMock()
        batch_manager_mock.bulk_update.return_value = {"success": True}

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        collector = BatchOperationCollector(
            client_mock, "res.partner", "update", chunk_size=30, context={"test": True}
        )

        # Add update data
        collector.add({"id": 1, "name": "Updated Name", "email": "test@example.com"})
        collector.add({"id": 2, "active": False})

        result = await collector.execute()

        assert result == {"success": True}
        batch_manager_mock.bulk_update.assert_called_once_with(
            model="res.partner",
            data=[
                {"id": 1, "name": "Updated Name", "email": "test@example.com"},
                {"id": 2, "active": False},
            ],
            chunk_size=30,
            context={"test": True},
        )

    @pytest.mark.asyncio
    async def test_collector_delete_operation(self, mocker):
        """Test collector with delete operation."""
        client_mock = AsyncMock()
        batch_manager_mock = AsyncMock()
        batch_manager_mock.bulk_delete.return_value = {"deleted": 3}

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        collector = BatchOperationCollector(client_mock, "res.partner", "delete")

        # Add IDs to delete
        collector.add(1)
        collector.add_many([2, 3])

        result = await collector.execute()

        assert result == {"deleted": 3}
        batch_manager_mock.bulk_delete.assert_called_once_with(
            model="res.partner", record_ids=[1, 2, 3], chunk_size=None, context=None
        )


class TestBatchProgressTrackerAdvanced:
    """Advanced tests for BatchProgressTracker."""

    def test_tracker_remove_callback(self):
        """Test removing callbacks from tracker."""
        tracker = BatchProgressTracker()
        callback1 = MagicMock()
        callback2 = MagicMock()

        tracker.add_callback(callback1)
        tracker.add_callback(callback2)

        assert len(tracker.callbacks) == 2

        tracker.remove_callback(callback1)
        assert len(tracker.callbacks) == 1
        assert callback2 in tracker.callbacks

        # Removing non-existent callback should not raise error
        tracker.remove_callback(callback1)
        assert len(tracker.callbacks) == 1

    @pytest.mark.asyncio
    async def test_tracker_sync_callback(self):
        """Test tracker with synchronous callback."""
        tracker = BatchProgressTracker()
        sync_callback = MagicMock()  # Not AsyncMock

        tracker.add_callback(sync_callback)

        progress = {"percentage": 75.0, "current": 75, "total": 100}
        await tracker.callback(progress)

        sync_callback.assert_called_once_with(progress)
        assert tracker.get_current_progress() == progress

    @pytest.mark.asyncio
    async def test_tracker_callback_error_handling(self, mocker):
        """Test tracker handles callback errors gracefully."""
        tracker = BatchProgressTracker()

        # Create callbacks that raise errors
        error_callback = AsyncMock(side_effect=Exception("Callback error"))
        good_callback = AsyncMock()

        tracker.add_callback(error_callback)
        tracker.add_callback(good_callback)

        # Mock logger
        logger_mock = MagicMock()
        mocker.patch("logging.getLogger", return_value=logger_mock)

        progress = {"percentage": 50.0}
        await tracker.callback(progress)

        # Both callbacks should be called
        error_callback.assert_called_once_with(progress)
        good_callback.assert_called_once_with(progress)

        # Error should be logged
        logger_mock.error.assert_called_once()
        assert "Progress callback error" in logger_mock.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_tracker_multiple_progress_updates(self):
        """Test tracker with multiple progress updates."""
        tracker = BatchProgressTracker()
        callback = AsyncMock()
        tracker.add_callback(callback)

        # Send multiple progress updates
        progress_updates = [
            {"percentage": 0.0, "status": "starting"},
            {"percentage": 25.0, "status": "processing", "current": 25},
            {"percentage": 50.0, "status": "processing", "current": 50},
            {"percentage": 100.0, "status": "completed", "current": 100},
        ]

        for progress in progress_updates:
            await tracker.callback(progress)

        # Verify all callbacks were called
        assert callback.call_count == 4

        # Verify history
        history = tracker.get_history()
        assert len(history) == 4
        assert history == progress_updates

        # Verify current progress is the last update
        assert tracker.get_current_progress() == progress_updates[-1]

    def test_tracker_get_history_returns_copy(self):
        """Test that get_history returns a copy, not reference."""
        tracker = BatchProgressTracker()

        progress = {"percentage": 100.0}
        tracker.history.append(progress)

        history = tracker.get_history()
        history.append({"percentage": 50.0})  # Modify returned list

        # Original history should not be modified
        assert len(tracker.history) == 1
        assert tracker.history[0] == progress


class TestBatchExceptionHandling:
    """Test batch exception classes."""

    def test_batch_error_inheritance(self):
        """Test BatchError exception inheritance."""
        error = BatchError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_batch_validation_error(self):
        """Test BatchValidationError."""
        error = BatchValidationError(
            "Invalid data", validation_errors=[{"field": "name", "value": ""}]
        )
        assert isinstance(error, BatchError)
        assert len(error.validation_errors) == 1
        assert error.validation_errors[0]["field"] == "name"
        assert error.validation_errors[0]["value"] == ""
        assert "Invalid data" in str(error)

    def test_batch_execution_error(self):
        """Test BatchExecutionError."""
        failed_ops = [{"id": 123, "error": "Operation failed"}]
        partial_results = {"success": 5, "failed": 1}
        error = BatchExecutionError(
            "Execution failed",
            failed_operations=failed_ops,
            partial_results=partial_results,
        )
        assert isinstance(error, BatchError)
        assert error.failed_operations == failed_ops
        assert error.partial_results == partial_results
        assert "Execution failed" in str(error)


class TestBatchOperationsEnum:
    """Test batch operations and enums."""

    def test_operation_type_values(self):
        """Test OperationType enum values."""
        assert OperationType.CREATE.value == "create"
        assert OperationType.UPDATE.value == "update"
        assert OperationType.DELETE.value == "delete"
        assert OperationType.UNLINK.value == "unlink"

    def test_batch_operation_creation(self):
        """Test CreateOperation creation."""
        from src.zenoo_rpc.batch.operations import CreateOperation

        operation = CreateOperation(
            model="res.partner", data=[{"name": "Test"}], context={"lang": "en_US"}
        )

        assert operation.operation_type == OperationType.CREATE
        assert operation.model == "res.partner"
        assert operation.data == [{"name": "Test"}]
        assert operation.context == {"lang": "en_US"}
        assert operation.operation_id is not None
        assert operation.get_batch_size() == 1


class TestIntegrationScenarios:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_nested_batch_contexts(self, mocker):
        """Test nested batch contexts."""
        client_mock = AsyncMock()

        # Create two different batch mocks
        batch_mock1 = MagicMock()
        batch_mock1.get_operation_count.return_value = 1
        batch_mock1.execute = AsyncMock()

        batch_mock2 = MagicMock()
        batch_mock2.get_operation_count.return_value = 2
        batch_mock2.execute = AsyncMock()

        # Mock BatchManager to return different batches
        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.side_effect = [batch_mock1, batch_mock2]

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        async with batch_context(client_mock) as outer_batch:
            assert outer_batch == batch_mock1

            async with batch_context(client_mock, auto_execute=False) as inner_batch:
                assert inner_batch == batch_mock2

            # Inner batch should not execute (auto_execute=False)
            batch_mock2.execute.assert_not_called()

        # Outer batch should execute
        batch_mock1.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_with_progress_tracking(self, mocker):
        """Test batch execution with progress tracking."""
        client_mock = AsyncMock()

        # Create progress tracker
        tracker = BatchProgressTracker()
        progress_history = []

        async def track_progress(progress):
            progress_history.append(progress.copy())

        tracker.add_callback(track_progress)

        # Mock batch with progress updates
        batch_mock = MagicMock()
        batch_mock.get_operation_count.return_value = 100

        async def mock_execute(progress_callback):
            # Simulate progress updates
            for i in range(0, 101, 25):
                await progress_callback(
                    {"percentage": float(i), "current": i, "total": 100}
                )

        batch_mock.execute = mock_execute

        batch_manager_mock = MagicMock()
        batch_manager_mock.create_batch.return_value = batch_mock

        mocker.patch(
            "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
        )

        async with batch_context(
            client_mock, progress_callback=tracker.callback
        ) as batch:
            pass

        # Verify progress was tracked
        assert len(progress_history) == 5
        assert progress_history[0]["percentage"] == 0.0
        assert progress_history[-1]["percentage"] == 100.0

        # Verify tracker history
        assert len(tracker.get_history()) == 5


class TestAdditionalCoverage:
    """Additional tests to increase coverage above 90%."""

    @pytest.mark.asyncio
    async def test_batch_manager_edge_cases(self, mocker):
        """Test batch manager edge cases for better coverage."""
        from src.zenoo_rpc.batch.manager import BatchManager

        client_mock = AsyncMock()
        manager = BatchManager(client_mock)

        # Test create batch with custom parameters
        batch = manager.create_batch()
        assert batch is not None

        # Test bulk operations with empty data
        with pytest.raises(Exception):
            await manager.bulk_create("res.partner", [])

    def test_cache_exceptions(self):
        """Test cache exception classes."""
        from src.zenoo_rpc.cache.exceptions import (
            CacheError,
            CacheKeyError,
            CacheBackendError,
        )

        # Test CacheKeyError
        error = CacheKeyError("Invalid key")
        assert isinstance(error, CacheError)
        assert "Invalid key" in str(error)

        # Test CacheBackendError
        backend_error = CacheBackendError("Backend failed")
        assert isinstance(backend_error, CacheError)
        assert "Backend failed" in str(backend_error)

    def test_model_fields_edge_cases(self):
        """Test model field edge cases."""
        from src.zenoo_rpc.models.fields import (
            Many2OneField,
            One2ManyField,
            Many2ManyField,
        )

        # Test Many2One field
        field = Many2OneField("res.partner")
        assert field.relation == "res.partner"
        assert field.required is False

        # Test One2Many field
        o2m_field = One2ManyField("res.partner", "parent_id")
        assert o2m_field.relation == "res.partner"
        assert o2m_field.inverse_field == "parent_id"

        # Test Many2Many field
        m2m_field = Many2ManyField("res.partner.category")
        assert m2m_field.relation == "res.partner.category"

    @pytest.mark.asyncio
    async def test_client_edge_cases(self, mocker):
        """Test client edge cases."""
        from src.zenoo_rpc.client import ZenooClient
        from src.zenoo_rpc.transport.session import Session

        # Mock session
        session_mock = AsyncMock(spec=Session)
        session_mock.call = AsyncMock(return_value={"result": "success"})

        # Create client with mocked session
        client = ZenooClient("https://test.com")
        client._session = session_mock

        # Test version method
        session_mock.call.return_value = {"result": {"server_version": "14.0"}}
        version = await client.version()
        assert version == {"server_version": "14.0"}

    def test_query_expressions(self):
        """Test query expression classes."""
        from src.zenoo_rpc.query.expressions import (
            EQ,
            NE,
            GT,
            GTE,
            LT,
            LTE,
            IN,
            NOT_IN,
            LIKE,
            NOT_LIKE,
            ILIKE,
            NOT_ILIKE,
            CHILD_OF,
        )

        # Test all expression constants
        assert EQ == "="
        assert NE == "!="
        assert GT == ">"
        assert GTE == ">="
        assert LT == "<"
        assert LTE == "<="
        assert IN == "in"
        assert NOT_IN == "not in"
        assert LIKE == "like"
        assert NOT_LIKE == "not like"
        assert ILIKE == "ilike"
        assert NOT_ILIKE == "not ilike"
        assert CHILD_OF == "child_of"

    @pytest.mark.asyncio
    async def test_retry_policies(self):
        """Test retry policy classes."""
        from src.zenoo_rpc.retry.policies import (
            RetryPolicy,
            ExponentialBackoff,
            LinearBackoff,
            FixedDelay,
        )
        from src.zenoo_rpc.retry.strategies import RetryableError

        # Test ExponentialBackoff
        policy = ExponentialBackoff(max_retries=3, base_delay=1.0)
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0

        # Test should_retry
        error = RetryableError("Test error")
        assert policy.should_retry(error, attempt=1) is True
        assert policy.should_retry(error, attempt=4) is False

        # Test get_delay
        assert policy.get_delay(1) == 1.0  # First retry
        assert policy.get_delay(2) == 2.0  # Second retry (exponential)

    def test_cache_key_generation(self):
        """Test cache key generation."""
        from src.zenoo_rpc.cache.keys import CacheKeyGenerator

        generator = CacheKeyGenerator(prefix="test")

        # Test simple key generation
        key = generator.generate("method", {"arg": "value"})
        assert key.startswith("test:")
        assert "method" in key

        # Test with complex arguments
        complex_key = generator.generate(
            "search", {"model": "res.partner", "domain": [("active", "=", True)]}
        )
        assert "search" in complex_key
        assert "res.partner" in complex_key

    @pytest.mark.asyncio
    async def test_transaction_context_edge_cases(self):
        """Test transaction context edge cases."""
        from src.zenoo_rpc.transaction.context import TransactionContext
        from src.zenoo_rpc.transaction.manager import TransactionManager

        # Create transaction context
        client_mock = AsyncMock()
        manager = TransactionManager(client_mock)

        # Test context creation
        ctx = TransactionContext(manager, "test_tx")
        assert ctx.transaction_id == "test_tx"
        assert ctx.manager == manager

    def test_batch_executor_helpers(self):
        """Test batch executor helper methods."""
        from src.zenoo_rpc.batch.executor import BatchExecutor

        client_mock = AsyncMock()
        executor = BatchExecutor(client_mock)

        # Test chunk_data method
        data = list(range(10))
        chunks = list(executor._chunk_data(data, 3))
        assert len(chunks) == 4  # 3, 3, 3, 1
        assert chunks[0] == [0, 1, 2]
        assert chunks[-1] == [9]

    def test_model_registry_helpers(self):
        """Test model registry helper methods."""
        from src.zenoo_rpc.models.registry import ModelRegistry

        registry = ModelRegistry()

        # Test clear method
        registry.clear()
        assert len(registry._models) == 0

        # Test model name validation
        assert registry._is_valid_model_name("res.partner")
        assert registry._is_valid_model_name("account.move.line")
        assert not registry._is_valid_model_name("")
        assert not registry._is_valid_model_name("invalid name")
