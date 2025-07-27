import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.zenoo_rpc.batch.context import (
    BatchOperationCollector,
    BatchProgressTracker,
    batch_operation,
)
from src.zenoo_rpc.batch.exceptions import BatchError
from src.zenoo_rpc.batch.manager import BatchManager


@pytest.mark.asyncio
async def test_batch_operation_collector_create(mocker):
    client_mock = AsyncMock()
    batch_manager_mock = AsyncMock()
    batch_manager_mock.bulk_create.return_value = [1, 2]

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    collector = BatchOperationCollector(client_mock, "res.partner", "create")

    collector.add({"name": "Test Company"})
    collector.add_many([{"name": "Another Company"}])

    assert collector.has_data() is True
    assert collector.get_count() == 2

    results = await collector.execute()

    assert collector.executed is True
    assert results == [1, 2]
    batch_manager_mock.bulk_create.assert_called_once()


@pytest.mark.asyncio
async def test_batch_operation_collector_update(mocker):
    client_mock = AsyncMock()
    batch_manager_mock = AsyncMock()
    batch_manager_mock.bulk_update.return_value = True

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    collector = BatchOperationCollector(client_mock, "res.partner", "update")

    collector.add({"id": 1, "name": "Updated Name"})

    assert collector.has_data() is True
    assert collector.get_count() == 1

    await collector.execute()

    batch_manager_mock.bulk_update.assert_called_once()


@pytest.mark.asyncio
async def test_batch_operation_collector_delete(mocker):
    client_mock = AsyncMock()
    batch_manager_mock = AsyncMock()
    batch_manager_mock.bulk_delete.return_value = True

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    collector = BatchOperationCollector(client_mock, "res.partner", "delete")

    collector.add(1)

    assert collector.has_data() is True
    assert collector.get_count() == 1

    await collector.execute()

    batch_manager_mock.bulk_delete.assert_called_once()


def test_batch_operation_collector_init_valid_type():
    """Test BatchOperationCollector initialization with valid operation type."""
    client_mock = AsyncMock()

    # Test with 'create' operation type
    collector = BatchOperationCollector(
        client=client_mock,
        model="res.partner",
        operation_type="create",
        chunk_size=50,
        context={"test": "context"},
    )

    # Assert properties are set correctly
    assert collector.client == client_mock
    assert collector.model == "res.partner"
    assert collector.operation_type == "create"  # Should be lowercase
    assert collector.chunk_size == 50
    assert collector.context == {"test": "context"}
    assert collector.data == []
    assert collector.executed is False
    assert collector.results is None

    # Test with uppercase operation type (should be converted to lowercase)
    collector_upper = BatchOperationCollector(
        client=client_mock, model="res.partner", operation_type="CREATE"
    )
    assert collector_upper.operation_type == "create"

    # Test with 'update' operation type
    collector_update = BatchOperationCollector(
        client=client_mock, model="res.partner", operation_type="UPDATE"
    )
    assert collector_update.operation_type == "update"

    # Test with 'delete' operation type
    collector_delete = BatchOperationCollector(
        client=client_mock, model="res.partner", operation_type="Delete"
    )
    assert collector_delete.operation_type == "delete"


def test_batch_operation_collector_init_invalid_type():
    """Test BatchOperationCollector initialization with invalid operation type."""
    client_mock = AsyncMock()

    # Test with invalid operation type
    with pytest.raises(BatchError) as exc_info:
        BatchOperationCollector(
            client=client_mock, model="res.partner", operation_type="invalid"
        )

    # Verify the error message
    assert "Invalid operation type: invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_batch_operation_collector_errors():
    client_mock = AsyncMock()
    collector = BatchOperationCollector(client_mock, "res.partner", "create")

    with pytest.raises(BatchError):
        await collector.execute()  # Cannot execute without data

    collector.add({"name": "Test Company"})

    collector.executed = True

    with pytest.raises(BatchError):
        collector.add({"name": "Should not add"})  # Cannot add after execution

    with pytest.raises(BatchError):
        collector.clear()  # Cannot clear after execution


@pytest.mark.asyncio
async def test_batch_operation_context_error_handling(mocker, caplog):
    """Test that batch_operation context logs and re-raises errors from execute()."""
    import logging

    client_mock = AsyncMock()

    # Mock BatchManager to raise an error inside execute()
    batch_manager_mock = AsyncMock()
    batch_manager_mock.bulk_create.side_effect = Exception("Test error in execute")
    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    # Set caplog level to capture ERROR logs
    caplog.set_level(logging.ERROR)

    # Use the batch_operation context manager
    with pytest.raises(BatchError) as exc_info:
        async with batch_operation(client_mock, "res.partner", "create") as collector:
            collector.add({"name": "Test Company"})
            # The exception should be raised when the context exits and execute() is called

    # Verify the exception message contains the expected text
    assert "Batch execution failed: Test error in execute" in str(exc_info.value)

    # Verify the context manager logged the error at ERROR level
    assert "Batch operation context error" in caplog.text
    assert "Batch execution failed: Test error in execute" in caplog.text

    # Verify the log was at ERROR level
    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    assert "Batch operation context error" in error_records[0].message
