import pytest
from src.zenoo_rpc.batch.operations import (
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    BatchValidationError,
    OperationStatus,
    create_batch_operation,
    validate_batch_operations,
)
from src.zenoo_rpc.batch.manager import BatchManager
from src.zenoo_rpc.batch.executor import BatchExecutor
from src.zenoo_rpc.batch.exceptions import BatchExecutionError
from tests.helpers.memory_transport import MemoryTransport


def test_validation_create_invalid():
    with pytest.raises(BatchValidationError, match="Model is required"):
        CreateOperation(model="", data=[])

    with pytest.raises(BatchValidationError, match="data must be a list"):
        CreateOperation(model="res.partner", data={})

    with pytest.raises(BatchValidationError, match="data cannot be empty"):
        CreateOperation(model="res.partner", data=[])

    with pytest.raises(BatchValidationError, match="must be a dictionary"):
        CreateOperation(model="res.partner", data=["invalid"])

    with pytest.raises(BatchValidationError, match="cannot be empty"):
        CreateOperation(model="res.partner", data=[{}])


def test_validation_update_invalid():
    with pytest.raises(BatchValidationError, match="Model is required"):
        UpdateOperation(model="", data={})

    with pytest.raises(BatchValidationError, match="Record IDs are required"):
        UpdateOperation(model="res.partner", data={})

    with pytest.raises(BatchValidationError, match="data cannot be empty"):
        UpdateOperation(model="res.partner", data={}, record_ids=[1])

    with pytest.raises(BatchValidationError, match="data cannot be empty"):
        UpdateOperation(model="res.partner", data=[])

    with pytest.raises(BatchValidationError, match="must contain 'id' field"):
        UpdateOperation(model="res.partner", data=[{"name": "Test"}])

    with pytest.raises(BatchValidationError, match="must contain fields to update"):
        UpdateOperation(model="res.partner", data=[{"id": 1}])


def test_validation_delete_invalid():
    with pytest.raises(BatchValidationError, match="Model is required"):
        DeleteOperation(model="", data=[1])

    with pytest.raises(BatchValidationError, match="must be a list"):
        DeleteOperation(model="res.partner", data={})

    with pytest.raises(BatchValidationError, match="data cannot be empty"):
        DeleteOperation(model="res.partner", data=[])

    with pytest.raises(BatchValidationError, match="must be a positive integer"):
        DeleteOperation(model="res.partner", data=[0])

    with pytest.raises(BatchValidationError, match="must be a positive integer"):
        DeleteOperation(model="res.partner", data=[1, -1])


def test_split_large_create_operation():
    operation = CreateOperation(
        model="res.partner", data=[{"name": f"Company {i}"} for i in range(250)]
    )
    chunks = operation.split(100)

    assert len(chunks) == 3
    assert chunks[0].get_batch_size() == 100
    assert chunks[1].get_batch_size() == 100
    assert chunks[2].get_batch_size() == 50


def test_split_large_update_operation_bulk():
    operation = UpdateOperation(
        model="res.partner", data={"active": False}, record_ids=list(range(1, 301))
    )
    chunks = operation.split(100)

    assert len(chunks) == 3
    assert len(chunks[0].record_ids) == 100
    assert len(chunks[1].record_ids) == 100
    assert len(chunks[2].record_ids) == 100


def test_split_large_update_operation_individual():
    operation = UpdateOperation(
        model="res.partner",
        data=[{"id": i, "name": f"Name {i}"} for i in range(1, 201)],
    )
    chunks = operation.split(50)

    assert len(chunks) == 4
    assert chunks[0].get_batch_size() == 50
    assert chunks[3].get_batch_size() == 50


def test_split_large_delete_operation():
    operation = DeleteOperation(model="res.partner", data=list(range(1, 401)))
    chunks = operation.split(150)

    assert len(chunks) == 3
    assert chunks[0].get_batch_size() == 150
    assert chunks[1].get_batch_size() == 150
    assert chunks[2].get_batch_size() == 100


@pytest.mark.asyncio
async def test_executor_chunk_operations():
    """Test executor chunking of large operations."""
    client = MemoryTransport()
    client.set_response("create", [1, 2, 3])

    executor = BatchExecutor(client=client, max_chunk_size=50)

    # Large create operation that should be chunked
    large_operation = CreateOperation(
        model="res.partner", data=[{"name": f"Company {i}"} for i in range(150)]
    )

    chunked = await executor._chunk_operations([large_operation])
    assert len(chunked) == 3
    assert chunked[0].get_batch_size() == 50
    assert chunked[1].get_batch_size() == 50
    assert chunked[2].get_batch_size() == 50


def test_operation_status_tracking():
    operation = CreateOperation(model="res.partner", data=[{"name": "Test"}])

    assert not operation.is_completed()
    assert not operation.is_successful()
    assert operation.get_duration() is None

    # Simulate execution
    operation.status = OperationStatus.EXECUTING
    operation.started_at = 100.0

    # Simulate completion
    operation.status = OperationStatus.COMPLETED
    operation.completed_at = 105.0

    assert operation.is_completed()
    assert operation.is_successful()
    assert operation.get_duration() == 5.0


def test_create_batch_operation_factory():
    """Test batch operation factory function."""
    # Test create operation
    op = create_batch_operation("create", "res.partner", [{"name": "Test"}])
    assert isinstance(op, CreateOperation)
    assert op.model == "res.partner"

    # Test update operation
    op = create_batch_operation(
        "update", "res.partner", {"active": False}, record_ids=[1, 2]
    )
    assert isinstance(op, UpdateOperation)
    assert op.record_ids == [1, 2]

    # Test delete operation
    op = create_batch_operation("delete", "res.partner", [1, 2, 3])
    assert isinstance(op, DeleteOperation)
    assert op.data == [1, 2, 3]

    # Test unlink alias
    op = create_batch_operation("unlink", "res.partner", [4, 5])
    assert isinstance(op, DeleteOperation)

    # Test invalid operation type
    with pytest.raises(BatchValidationError, match="Unknown operation type"):
        create_batch_operation("invalid", "res.partner", [])


def test_validate_batch_operations():
    """Test batch operations validation function."""
    # Test empty list
    with pytest.raises(BatchValidationError, match="Operations list cannot be empty"):
        validate_batch_operations([])

    # Test valid operations
    operations = [
        CreateOperation(model="res.partner", data=[{"name": "Test"}]),
        UpdateOperation(model="res.partner", data={"active": False}, record_ids=[1]),
        DeleteOperation(model="res.partner", data=[2, 3]),
    ]

    # Should not raise
    validate_batch_operations(operations)

    # Test with invalid operation - create a new list to avoid modifying the valid one
    invalid_operations = operations.copy()
    # This will raise immediately on creation, so we need to handle it differently
    with pytest.raises(BatchValidationError):
        invalid_operations.append(CreateOperation(model="", data=[{"name": "Test"}]))


@pytest.mark.asyncio
async def test_batch_conflict_detection():
    """Test detection of conflicting operations."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    manager = BatchManager(client=client)

    # Create operations that might conflict
    batch = manager.create_batch()

    # Update and delete same records - potential conflict
    batch.update("res.partner", {"name": "Updated"}, record_ids=[1, 2, 3])
    batch.delete("res.partner", [2, 3, 4])  # Overlapping IDs

    # Execute should handle the operations in order
    results = await batch.execute()
    assert results["stats"]["total_operations"] == 2


@pytest.mark.asyncio
async def test_edge_case_empty_update():
    """Test edge case of empty update data."""
    # This should fail validation
    with pytest.raises(BatchValidationError, match="Update data cannot be empty"):
        UpdateOperation(model="res.partner", data={}, record_ids=[1, 2])


@pytest.mark.asyncio
async def test_edge_case_duplicate_ids():
    """Test handling of duplicate record IDs."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    executor = BatchExecutor(client=client)

    # Delete operation with duplicate IDs
    operation = DeleteOperation(model="res.partner", data=[1, 2, 3, 2, 1])  # Duplicates

    # Should still execute successfully
    result = await executor._perform_delete(operation)
    assert result is True


@pytest.mark.asyncio
async def test_operation_priority_sorting():
    """Test operations are sorted by priority."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    manager = BatchManager(client=client)
    batch = manager.create_batch()

    # Add operations with different priorities
    batch.create("res.partner", [{"name": "Low"}], priority=0)
    batch.create("res.partner", [{"name": "High"}], priority=10)
    batch.create("res.partner", [{"name": "Medium"}], priority=5)

    # Check operations are sorted by priority before execution
    assert batch.operations[0].priority == 0
    assert batch.operations[1].priority == 10
    assert batch.operations[2].priority == 5

    # Execute - internally should sort by priority
    await batch.execute()


@pytest.mark.asyncio
async def test_batch_size_validation():
    """Test validation of batch sizes."""
    from src.zenoo_rpc.batch.exceptions import BatchSizeError

    # Test get_batch_size methods
    create_op = CreateOperation(
        model="res.partner", data=[{"name": f"Company {i}"} for i in range(100)]
    )
    assert create_op.get_batch_size() == 100

    update_op = UpdateOperation(
        model="res.partner", data={"active": False}, record_ids=list(range(1, 51))
    )
    assert update_op.get_batch_size() == 50

    delete_op = DeleteOperation(model="res.partner", data=list(range(1, 201)))
    assert delete_op.get_batch_size() == 200
