import pytest
from unittest.mock import AsyncMock, MagicMock
from src.zenoo_rpc.batch.context import batch_context, batch_operation
from src.zenoo_rpc.batch.manager import BatchManager


@pytest.mark.asyncio
async def test_batch_context_auto_execute(mocker):
    client_mock = AsyncMock()
    batch_mock = MagicMock()
    batch_mock.get_operation_count.return_value = 2
    batch_mock.execute = AsyncMock()

    batch_manager_mock = MagicMock()
    batch_manager_mock.create_batch.return_value = batch_mock

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    async with batch_context(client_mock) as batch:
        assert batch == batch_mock

    batch_mock.execute.assert_called_once()


@pytest.mark.asyncio
async def test_batch_context_no_auto_execute(mocker):
    client_mock = AsyncMock()
    batch_mock = MagicMock()
    batch_mock.get_operation_count.return_value = 2
    batch_mock.execute = AsyncMock()

    batch_manager_mock = MagicMock()
    batch_manager_mock.create_batch.return_value = batch_mock

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchManager", return_value=batch_manager_mock
    )

    async with batch_context(client_mock, auto_execute=False) as batch:
        assert batch == batch_mock

    batch_mock.execute.assert_not_called()


@pytest.mark.asyncio
async def test_batch_operation_context(mocker):
    client_mock = AsyncMock()

    # Mock BatchOperationCollector
    collector_mock = MagicMock()
    collector_mock.has_data.return_value = True
    collector_mock.execute = AsyncMock()

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchOperationCollector",
        return_value=collector_mock,
    )

    async with batch_operation(client_mock, "res.partner", "create") as collector:
        assert collector == collector_mock

    collector_mock.execute.assert_called_once()


@pytest.mark.asyncio
async def test_batch_operation_context_no_data(mocker):
    client_mock = AsyncMock()

    # Mock BatchOperationCollector with no data
    collector_mock = MagicMock()
    collector_mock.has_data.return_value = False
    collector_mock.execute = AsyncMock()

    mocker.patch(
        "src.zenoo_rpc.batch.context.BatchOperationCollector",
        return_value=collector_mock,
    )

    async with batch_operation(client_mock, "res.partner", "create") as collector:
        assert collector == collector_mock

    collector_mock.execute.assert_not_called()
