import pytest
from src.zenoo_rpc.batch.manager import BatchManager
from src.zenoo_rpc.batch.executor import BatchExecutor
from src.zenoo_rpc.batch.operations import (
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    OperationStatus,
)
from src.zenoo_rpc.batch.exceptions import BatchError
from tests.helpers.memory_transport import MemoryTransport


@pytest.mark.asyncio
async def test_batch_lifecycle():
    """Test complete batch lifecycle from creation to execution."""
    # Initialize the BatchManager with a mock transport
    client = MemoryTransport()
    # Set up responses for the operations
    client.set_response("execute_kw", [1])  # For create
    client.set_response("execute_kw", True)  # For update
    client.set_response("execute_kw", True)  # For delete

    manager = BatchManager(client=client)

    # Test creating batch with context manager
    async with manager.batch() as batch_ctx:
        await batch_ctx.create(
            "res.partner", [{"name": "Company A", "is_company": True}]
        )
        await batch_ctx.update("res.partner", [1, 2, 3], {"active": False})
        await batch_ctx.delete("res.partner", [4, 5, 6])

        # Check that operations were collected
        assert len(batch_ctx.operations) == 3
        assert batch_ctx.operations[0].operation_type.value == "create"
        assert batch_ctx.operations[1].operation_type.value == "update"
        assert batch_ctx.operations[2].operation_type.value == "delete"

    # After context manager exits, operations should have been executed
    # Check the statistics
    stats = batch_ctx.get_stats()
    assert stats["total_operations"] == 3
    assert stats["completed_operations"] == 3
    assert stats["failed_operations"] == 0

    # Verify client was called
    assert client.get_call_count("execute_kw") >= 3


@pytest.mark.asyncio
async def test_batch_lifecycle_with_batch_object():
    """Test batch lifecycle using Batch object directly."""
    client = MemoryTransport()
    client.set_response("execute_kw", [1, 2, 3])  # For create operations

    manager = BatchManager(client=client)

    # Create a batch using the Batch object
    batch = manager.create_batch("test-batch-1")

    # Add operations using fluent interface
    batch.create("res.partner", [{"name": "Company A"}])
    batch.create("res.partner", [{"name": "Company B"}])
    batch.update("res.partner", {"active": False}, record_ids=[1, 2])
    batch.delete("res.partner", [3, 4])

    # Check operations were added
    assert len(batch.operations) == 4
    assert batch.get_operation_count() == 4
    assert not batch.executed

    # Execute the batch
    results = await batch.execute()

    # Check execution results
    assert batch.executed
    assert results is not None
    assert "stats" in results
    assert results["stats"]["total_operations"] == 4

    # Verify manager stats were updated
    manager_stats = manager.get_stats()
    assert manager_stats["total_batches"] == 1
    assert manager_stats["total_operations"] == 4


@pytest.mark.asyncio
async def test_batch_lifecycle_error_handling():
    """Test batch lifecycle with errors."""
    client = MemoryTransport()
    client.set_error("execute_kw", Exception("Operation failed"))

    manager = BatchManager(client=client)

    # Test that operations gracefully handle errors
    # The batch context manager will execute operations and handle errors internally
    async with manager.batch() as batch_ctx:
        await batch_ctx.create("res.partner", [{"name": "Test"}])

    # Check that operation failed but was handled
    stats = batch_ctx.get_stats()
    assert stats["total_operations"] == 1
    assert stats["completed_operations"] == 0
    assert stats["failed_operations"] == 1


@pytest.mark.asyncio
async def test_batch_history_and_stats():
    """Test batch history tracking and statistics."""
    client = MemoryTransport()
    client.set_response("execute_kw", [1, 2, 3])

    manager = BatchManager(client=client)

    # Execute multiple batches
    for i in range(3):
        batch = manager.create_batch(f"batch-{i}")
        batch.create("res.partner", [{"name": f"Company {i}"}])
        await batch.execute()

    # Check cumulative stats
    stats = manager.get_stats()
    assert stats["total_batches"] == 3
    assert stats["completed_batches"] == 3
    assert stats["failed_batches"] == 0
    assert stats["total_operations"] == 3


@pytest.mark.asyncio
async def test_batch_clear_and_cleanup():
    """Test batch cleanup after execution."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    manager = BatchManager(client=client)

    # Create and execute a batch
    batch_id = "test-cleanup-batch"
    batch = manager.create_batch(batch_id)

    # Verify batch is in active batches
    assert batch_id in manager.active_batches
    assert manager.get_batch(batch_id) is not None

    # Add operation and execute
    batch.create("res.partner", [{"name": "Test"}])
    await batch.execute()

    # Verify batch was removed from active batches after execution
    assert batch_id not in manager.active_batches
    assert manager.get_batch(batch_id) is None
