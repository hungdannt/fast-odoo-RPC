import pytest
from src.zenoo_rpc.batch.manager import BatchManager
from src.zenoo_rpc.batch.executor import BatchExecutor
from src.zenoo_rpc.batch.exceptions import BatchError
from tests.helpers.memory_transport import MemoryTransport


@pytest.mark.asyncio
async def test_bulk_create_happy_path():
    """Test successful bulk create operation."""
    client = MemoryTransport()
    client.set_response("execute_kw", [1, 2, 3])
    manager = BatchManager(client=client)

    result = await manager.bulk_create("res.partner", [{"name": "A"}, {"name": "B"}])
    assert result == [1, 2, 3]
    assert client.get_call_count("execute_kw") >= 1


@pytest.mark.asyncio
async def test_bulk_create_error_path():
    """Test bulk create operation with errors."""
    client = MemoryTransport()
    client.set_error("execute_kw", Exception("Error creating"))
    manager = BatchManager(client=client)

    with pytest.raises(BatchError, match="Bulk create failed"):
        await manager.bulk_create("res.partner", [{"name": "Err"}])


@pytest.mark.asyncio
async def test_bulk_create_with_chunking():
    """Test bulk create with automatic chunking."""
    client = MemoryTransport()

    # Keep track of created IDs
    created_count = 0

    def create_callback(params):
        nonlocal created_count
        # Check if this is a bulk create (list of records) or single create
        if params["method"] == "create" and isinstance(params["args"][0], list):
            # Bulk create - return list of IDs
            count = len(params["args"][0])
            ids = list(range(created_count + 1, created_count + count + 1))
            created_count += count
            return ids
        elif params["method"] == "create":
            # Single create - return single ID
            created_count += 1
            return created_count
        return True

    client.set_callback("execute_kw", create_callback)

    manager = BatchManager(client=client, max_chunk_size=50)

    # Create 150 records, should be split into 3 chunks
    records = [{"name": f"Company {i}"} for i in range(150)]
    result = await manager.bulk_create("res.partner", records)

    assert len(result) == 150
    # Should have been called 3 times due to chunking
    assert client.get_call_count("execute_kw") >= 3


@pytest.mark.asyncio
async def test_bulk_update_happy_path():
    """Test successful bulk update operation."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)
    manager = BatchManager(client=client)

    result = await manager.bulk_update("res.partner", {"name": "Updated"}, [1, 2, 3])
    assert result is True
    assert client.get_call_count("execute_kw") >= 1


@pytest.mark.asyncio
async def test_bulk_update_error_path():
    """Test bulk update operation with errors."""
    client = MemoryTransport()
    client.set_error("execute_kw", Exception("Error updating"))
    manager = BatchManager(client=client)

    with pytest.raises(BatchError, match="Bulk update failed"):
        await manager.bulk_update("res.partner", {"name": "Err"}, [1])


@pytest.mark.asyncio
async def test_bulk_update_individual_records():
    """Test bulk update with individual record data."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)
    manager = BatchManager(client=client)

    # Update with individual data for each record
    update_data = [
        {"id": 1, "name": "Updated 1"},
        {"id": 2, "name": "Updated 2"},
        {"id": 3, "name": "Updated 3"},
    ]

    result = await manager.bulk_update("res.partner", update_data)
    assert result is True


@pytest.mark.asyncio
async def test_bulk_update_with_context():
    """Test bulk update with custom context."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)
    manager = BatchManager(client=client)

    context = {"lang": "en_US", "active_test": False}
    result = await manager.bulk_update(
        "res.partner", {"active": False}, [1, 2, 3], context=context
    )
    assert result is True

    # Verify context was passed
    calls = client.get_call_history("execute_kw")
    # Check that at least one call had the context in kwargs
    context_found = False
    for call in calls:
        if "params" in call and "kwargs" in call["params"]:
            if call["params"]["kwargs"] == context:
                context_found = True
                break
    assert context_found, "Context was not passed to execute_kw"


@pytest.mark.asyncio
async def test_bulk_delete_happy_path():
    """Test successful bulk delete operation."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)
    manager = BatchManager(client=client)

    result = await manager.bulk_delete("res.partner", [1, 2, 3])
    assert result is True
    assert client.get_call_count("execute_kw") >= 1


@pytest.mark.asyncio
async def test_bulk_delete_error_path():
    """Test bulk delete operation with errors."""
    client = MemoryTransport()
    client.set_error("execute_kw", Exception("Error deleting"))
    manager = BatchManager(client=client)

    with pytest.raises(BatchError, match="Bulk delete failed"):
        await manager.bulk_delete("res.partner", [1])


@pytest.mark.asyncio
async def test_bulk_delete_with_chunking():
    """Test bulk delete with automatic chunking."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    manager = BatchManager(client=client, max_chunk_size=100)

    # Delete 350 records, should be split into 4 chunks
    record_ids = list(range(1, 351))
    result = await manager.bulk_delete("res.partner", record_ids)

    assert result is True
    # Should have been called 4 times due to chunking
    assert client.get_call_count("execute_kw") >= 4


@pytest.mark.asyncio
async def test_executor_fallback_on_bulk_create_failure():
    """Test executor fallback to individual creates when bulk fails."""
    client = MemoryTransport()

    # First call (bulk) fails, subsequent calls (individual) succeed
    call_count = 0

    def mock_execute(params):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Bulk create not supported")
        return call_count  # Return record ID

    client.set_callback("execute_kw", mock_execute)

    executor = BatchExecutor(client=client)
    from src.zenoo_rpc.batch.operations import CreateOperation

    operation = CreateOperation(
        model="res.partner", data=[{"name": "A"}, {"name": "B"}, {"name": "C"}]
    )

    result = await executor._perform_create(operation)

    # Should return 3 IDs from individual creates
    assert result == [2, 3, 4]
    assert call_count == 4  # 1 bulk attempt + 3 individual creates


@pytest.mark.asyncio
async def test_executor_concurrent_operations():
    """Test executor handling concurrent operations."""
    client = MemoryTransport()
    client.set_response("execute_kw", True)

    executor = BatchExecutor(client=client, max_concurrency=2)

    from src.zenoo_rpc.batch.operations import (
        CreateOperation,
        UpdateOperation,
        DeleteOperation,
    )

    operations = [
        CreateOperation(model="res.partner", data=[{"name": "A"}]),
        UpdateOperation(model="res.partner", data={"active": False}, record_ids=[1]),
        DeleteOperation(model="res.partner", data=[2]),
        CreateOperation(model="res.partner", data=[{"name": "B"}]),
        UpdateOperation(model="res.partner", data={"active": True}, record_ids=[3]),
    ]

    results = await executor.execute_operations(operations)

    assert results["stats"]["total_operations"] == 5
    assert results["stats"]["completed_operations"] == 5
    assert results["stats"]["failed_operations"] == 0
