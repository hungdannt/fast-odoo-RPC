"""Tests for transaction context and atomic decorator.

This module ensures that transaction contexts and the atomic decorator
behave as intended, including:
- Propagation across async contexts
- Decorator application
- Exception handling
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, patch, Mock

from zenoo_rpc.transaction.context import (
    atomic,
    TransactionContext,
    transaction,
    SavepointContext,
)
from zenoo_rpc.transaction.manager import TransactionManager, TransactionState
from zenoo_rpc.transaction.exceptions import TransactionError, TransactionRollbackError


class MockClient:
    """Mock client for testing."""

    def __init__(self):
        self.write = AsyncMock()
        self.unlink = AsyncMock()
        self.create = AsyncMock()
        self.transaction_manager = TransactionManager(self)


@pytest.fixture
def mock_client():
    return MockClient()


@pytest.fixture
def transaction_manager(mock_client):
    return mock_client.transaction_manager


@pytest.mark.asyncio
async def test_atomic_decorator(transaction_manager):
    """Test atomic decorator to ensure transaction control."""

    @atomic(client=transaction_manager.client)
    async def sample_function(**kwargs):
        # The decorator adds _transaction to kwargs
        assert "_transaction" in kwargs
        assert kwargs["_transaction"].state == TransactionState.ACTIVE

    await sample_function()
    stats = transaction_manager.get_stats()
    assert stats["successful_transactions"] == 1


@pytest.mark.asyncio
async def test_atomic_decorator_with_exception(transaction_manager):
    """Test atomic decorator with exception propagation."""

    @atomic(client=transaction_manager.client)
    async def failing_function(**kwargs):
        raise RuntimeError("Intentional Error")

    with pytest.raises(RuntimeError) as exc_info:
        await failing_function()

    assert "Intentional Error" in str(exc_info.value)

    stats = transaction_manager.get_stats()
    assert stats["failed_transactions"] == 1


@pytest.mark.asyncio
async def test_transaction_context_direct_usage(mock_client):
    """Test direct usage of TransactionContext for manual control."""
    context = TransactionContext(client=mock_client)

    async with context.begin(auto_commit=True) as tx:
        tx.add_operation("create", "res.partner", record_ids=[1])
        assert tx.state == TransactionState.ACTIVE

    assert tx.state == TransactionState.COMMITTED


@given(st.text(min_size=1))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_transaction_contextvar_propagation(transaction_manager, random_id):
    """Test transaction contextvar propagation across coroutines."""
    context_var = None

    async def nested_inside(tx_id):
        nonlocal context_var
        context_var = tx_id
        await asyncio.sleep(0)  # Yield control
        return context_var

    async with transaction_manager.transaction(transaction_id=random_id) as tx:
        result = await nested_inside(tx.id)
        assert result == random_id


@pytest.mark.asyncio
async def test_exception_propagation_in_context(transaction_manager):
    """Test that exceptions propagate correctly within transaction contexts."""
    try:
        async with transaction_manager.transaction() as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])
            raise ValueError("Test exception")
    except ValueError as e:
        assert str(e) == "Test exception"
        assert tx.state == TransactionState.ROLLED_BACK


@pytest.mark.asyncio
async def test_atomic_decorator_without_parentheses(mock_client):
    """Test atomic decorator used without parentheses."""

    @atomic
    async def sample_function(client, **kwargs):
        # Function should receive client in args
        assert hasattr(client, "transaction_manager")
        # And transaction in kwargs
        assert "_transaction" in kwargs
        return "success"

    result = await sample_function(mock_client)
    assert result == "success"

    stats = mock_client.transaction_manager.get_stats()
    assert stats["successful_transactions"] == 1


@pytest.mark.asyncio
async def test_atomic_decorator_with_client_in_kwargs(mock_client):
    """Test atomic decorator with client passed in kwargs."""

    @atomic()
    async def sample_function(**kwargs):
        # Transaction should be added to kwargs
        assert "_transaction" in kwargs
        tx = kwargs["_transaction"]
        assert tx.state == TransactionState.ACTIVE
        return "success"

    result = await sample_function(client=mock_client)
    assert result == "success"


@pytest.mark.asyncio
async def test_transaction_context_convenience_function(mock_client):
    """Test the transaction convenience function."""
    async with transaction(mock_client) as tx:
        assert tx.state == TransactionState.ACTIVE
        tx.add_operation("create", "res.partner", record_ids=[1])

    # Should auto-commit
    assert tx.state == TransactionState.COMMITTED


@pytest.mark.asyncio
async def test_transaction_context_no_transaction_support():
    """Test error when client doesn't support transactions."""
    client_without_tx = Mock(spec=[])

    with pytest.raises(TransactionError) as exc_info:
        async with transaction(client_without_tx) as tx:
            pass

    assert "Client does not support transactions" in str(exc_info.value)


@pytest.mark.asyncio
async def test_savepoint_context(transaction_manager):
    """Test SavepointContext functionality."""
    async with transaction_manager.transaction() as tx:
        tx.add_operation("create", "res.company", record_ids=[1])

        # Use SavepointContext
        async with SavepointContext(tx, "test_savepoint") as sp:
            assert sp.created_savepoint is not None
            tx.add_operation("create", "res.partner", record_ids=[2])
            tx.add_operation("create", "res.partner", record_ids=[3])

        # Operations should still be there after normal exit
        assert len(tx.operations) == 3


@pytest.mark.asyncio
async def test_savepoint_context_with_exception(transaction_manager, mock_client):
    """Test SavepointContext with exception handling."""
    async with transaction_manager.transaction() as tx:
        tx.add_operation("create", "res.company", record_ids=[1], created_ids=[1])

        try:
            async with SavepointContext(tx, "test_savepoint") as sp:
                tx.add_operation(
                    "create", "res.partner", record_ids=[2], created_ids=[2]
                )
                tx.add_operation(
                    "create", "res.partner", record_ids=[3], created_ids=[3]
                )
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should have rolled back to savepoint (only company operation remains)
        assert len(tx.operations) == 1
        assert tx.operations[0].model == "res.company"


@pytest.mark.asyncio
async def test_savepoint_context_manual_rollback(transaction_manager):
    """Test manual rollback in SavepointContext."""
    async with transaction_manager.transaction() as tx:
        tx.add_operation("create", "res.company", record_ids=[1])

        async with SavepointContext(tx, "test_savepoint") as sp:
            tx.add_operation("create", "res.partner", record_ids=[2])

            # Manual rollback
            await sp.rollback()

        # Should have rolled back to savepoint
        assert len(tx.operations) == 1


@pytest.mark.asyncio
async def test_savepoint_context_inactive_transaction(transaction_manager):
    """Test SavepointContext with inactive transaction."""
    async with transaction_manager.transaction() as tx:
        await tx.commit()

        with pytest.raises(TransactionError) as exc_info:
            async with SavepointContext(tx, "test_savepoint"):
                pass

        assert "Cannot create savepoint in inactive transaction" in str(exc_info.value)


@given(st.text(min_size=1))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_transaction_contextvar_propagation_hypothesis(
    transaction_manager, random_id
):
    """Test transaction context propagation with random IDs."""
    # Reset stats for each run
    transaction_manager.successful_transactions = 0
    transaction_manager.failed_transactions = 0

    async with transaction_manager.transaction(transaction_id=random_id) as tx:
        assert tx.id == random_id
        tx.add_operation("create", "res.partner", record_ids=[1])

    retrieved = transaction_manager.get_transaction(random_id)
    assert retrieved is None  # Should be cleaned up
