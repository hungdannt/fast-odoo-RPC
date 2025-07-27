import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from src.zenoo_rpc.batch.executor import BatchExecutor
from src.zenoo_rpc.batch.operations import (
    BatchOperation,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    OperationStatus,
    OperationType,
)
from src.zenoo_rpc.batch.exceptions import BatchExecutionError, BatchTimeoutError


@pytest.fixture
def client_mock():
    return AsyncMock()


@pytest.fixture
def batch_executor(client_mock):
    return BatchExecutor(
        client=client_mock, max_chunk_size=100, max_concurrency=5, timeout=10
    )


@pytest.fixture
def create_operation():
    return CreateOperation(
        model="res.partner",
        data=[
            {"name": "Test 1", "email": "test1@example.com"},
            {"name": "Test 2", "email": "test2@example.com"},
        ],
    )


@pytest.fixture
def update_operation():
    return UpdateOperation(
        model="res.partner", record_ids=[1, 2], data={"active": True}
    )


@pytest.fixture
def delete_operation():
    return DeleteOperation(model="res.partner", data=[3, 4])


async def test_executor_initialization(batch_executor):
    assert batch_executor.max_chunk_size == 100
    assert batch_executor.max_concurrency == 5
    assert batch_executor.timeout == 10
    assert batch_executor.retry_attempts == 3
    assert batch_executor.stats["total_operations"] == 0


async def test_execute_empty_operations(batch_executor):
    result = await batch_executor.execute_operations([])
    assert result["results"] == []
    assert result["stats"]["total_operations"] == 0


async def test_execute_create_operation(batch_executor, client_mock, create_operation):
    client_mock.execute_kw.return_value = [1, 2]

    result = await batch_executor.execute_operations([create_operation])

    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True
    assert result["results"][0]["result"] == [1, 2]
    assert result["stats"]["completed_operations"] == 1
    assert result["stats"]["failed_operations"] == 0


async def test_execute_update_operation(batch_executor, client_mock, update_operation):
    client_mock.execute_kw.return_value = True

    result = await batch_executor.execute_operations([update_operation])

    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True
    assert result["results"][0]["result"] is True
    assert result["stats"]["completed_operations"] == 1


async def test_execute_delete_operation(batch_executor, client_mock, delete_operation):
    client_mock.execute_kw.return_value = True

    result = await batch_executor.execute_operations([delete_operation])

    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True
    assert result["results"][0]["result"] is True


async def test_execute_multiple_operations(
    batch_executor, client_mock, create_operation, update_operation
):
    client_mock.execute_kw.side_effect = [[1, 2], True]

    result = await batch_executor.execute_operations(
        [create_operation, update_operation]
    )

    assert len(result["results"]) == 2
    assert all(r["success"] for r in result["results"])
    assert result["stats"]["completed_operations"] == 2
    assert result["stats"]["total_operations"] == 2


async def test_operation_failure_handling(
    batch_executor, client_mock, create_operation
):
    client_mock.execute_kw.side_effect = Exception("Database error")

    result = await batch_executor.execute_operations([create_operation])

    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is False
    assert "Database error" in result["results"][0]["error"]
    assert result["stats"]["failed_operations"] == 1


async def test_chunk_operations(batch_executor):
    # Create operation with 250 records (exceeds max_chunk_size of 100)
    large_data = [{"name": f"Test {i}"} for i in range(250)]
    large_operation = CreateOperation(model="res.partner", data=large_data)

    chunked = await batch_executor._chunk_operations([large_operation])

    assert len(chunked) == 3  # Should be split into 3 chunks (100, 100, 50)
    assert chunked[0].get_batch_size() == 100
    assert chunked[1].get_batch_size() == 100
    assert chunked[2].get_batch_size() == 50


async def test_progress_callback(batch_executor, client_mock, create_operation):
    client_mock.execute_kw.return_value = [1, 2]

    progress_updates = []

    async def progress_callback(progress):
        progress_updates.append(progress)

    await batch_executor.execute_operations([create_operation], progress_callback)

    assert len(progress_updates) > 0
    last_progress = progress_updates[-1]
    assert last_progress["completed"] == 1
    assert last_progress["total"] == 1
    assert last_progress["percentage"] == 100.0


async def test_operation_timeout(batch_executor, client_mock, create_operation):
    # Make execute_kw take longer than timeout
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(15)  # Longer than 10s timeout
        return [1, 2]

    client_mock.execute_kw = slow_execute
    batch_executor.timeout = 0.1  # Set very short timeout

    with pytest.raises(BatchExecutionError):
        await batch_executor.execute_operations([create_operation])


async def test_perform_create_bulk_success(
    batch_executor, client_mock, create_operation
):
    client_mock.execute_kw.return_value = [1, 2]

    result = await batch_executor._perform_create(create_operation)

    assert result == [1, 2]
    client_mock.execute_kw.assert_called_once_with(
        "res.partner", "create", [create_operation.data], {}
    )


async def test_perform_create_bulk_failure_fallback(
    batch_executor, client_mock, create_operation
):
    # First call (bulk) fails, individual calls succeed
    client_mock.execute_kw.side_effect = [
        Exception("Bulk create failed"),
        1,  # First individual create
        2,  # Second individual create
    ]

    result = await batch_executor._perform_create(create_operation)

    assert result == [1, 2]
    assert client_mock.execute_kw.call_count == 3  # 1 bulk + 2 individual


async def test_perform_update_bulk(batch_executor, client_mock, update_operation):
    client_mock.execute_kw.return_value = True

    result = await batch_executor._perform_update(update_operation)

    assert result is True
    client_mock.execute_kw.assert_called_once_with(
        "res.partner", "write", [[1, 2], {"active": True}], {}
    )


async def test_perform_update_individual(batch_executor, client_mock):
    # Update with individual data per record
    operation = UpdateOperation(
        model="res.partner",
        data=[{"id": 1, "name": "Updated 1"}, {"id": 2, "name": "Updated 2"}],
    )

    client_mock.execute_kw.return_value = True

    result = await batch_executor._perform_update(operation)

    assert result is True
    assert client_mock.execute_kw.call_count == 2


async def test_perform_delete(batch_executor, client_mock, delete_operation):
    client_mock.execute_kw.return_value = True

    result = await batch_executor._perform_delete(delete_operation)

    assert result is True
    client_mock.execute_kw.assert_called_once_with(
        "res.partner", "unlink", [[3, 4]], {}
    )


async def test_get_stats(batch_executor):
    batch_executor.stats = {
        "total_operations": 10,
        "completed_operations": 8,
        "failed_operations": 2,
        "total_records": 100,
        "processed_records": 80,
        "start_time": 100.0,
        "end_time": 110.0,
    }

    stats = batch_executor.get_stats()

    assert stats["duration"] == 10.0
    assert stats["operations_per_second"] == 0.8
    assert stats["records_per_second"] == 8.0


async def test_concurrent_execution(batch_executor, client_mock):
    # Create multiple operations
    operations = [
        CreateOperation(model="res.partner", data=[{"name": f"Test {i}"}])
        for i in range(10)
    ]

    # Track call times to verify concurrency
    call_times = []

    async def track_time(*args, **kwargs):
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
        return [len(call_times)]

    client_mock.execute_kw = track_time

    result = await batch_executor.execute_operations(operations)

    assert len(result["results"]) == 10
    assert all(r["success"] for r in result["results"])

    # With max_concurrency=5, should have parallel execution
    # Check that not all calls are sequential
    time_diffs = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]
    assert any(
        diff < 0.05 for diff in time_diffs
    )  # Some calls should be nearly simultaneous


async def test_execute_with_semaphore_limit(batch_executor, client_mock):
    # Set very low concurrency
    batch_executor.max_concurrency = 2
    batch_executor.semaphore = asyncio.Semaphore(2)

    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0

    async def count_concurrent(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.1)
        concurrent_count -= 1
        return [1]

    client_mock.execute_kw = count_concurrent

    operations = [
        CreateOperation(model="res.partner", data=[{"name": f"Test {i}"}])
        for i in range(5)
    ]

    await batch_executor.execute_operations(operations)

    # Should never exceed max_concurrency
    assert max_concurrent <= 2


async def test_unknown_operation_type(batch_executor):
    # Create a mock operation with unknown type
    class UnknownOperation(BatchOperation):
        def __init__(self):
            super().__init__(operation_type=None, model="test.model", data=[])

    unknown_op = UnknownOperation()

    with pytest.raises(BatchExecutionError, match="Unknown operation type"):
        await batch_executor._perform_operation(unknown_op)
