"""Tests for concurrency in transaction handling.

This module validates concurrency primitives, isolation, and atomicity by
executing multiple concurrent transactions and checking for isolation violations.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock

from zenoo_rpc.transaction.manager import TransactionManager, TransactionState
from zenoo_rpc.transaction.exceptions import TransactionCommitError


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def transaction_manager(mock_client):
    return TransactionManager(client=mock_client)


async def create_and_rollback(tx_manager, record_id):
    """Coroutine to create and rollback a transaction."""
    async with tx_manager.transaction(auto_commit=False) as tx:
        tx.add_operation("create", "res.partner", record_ids=[record_id])
        await tx.rollback()
        assert tx.state == TransactionState.ROLLED_BACK


@pytest.mark.asyncio
async def test_concurrent_transactions(transaction_manager):
    """Test concurrent identical transactions for isolation."""
    tasks = [create_and_rollback(transaction_manager, i) for i in range(20)]
    await asyncio.gather(*tasks)
    stats = transaction_manager.get_stats()
    # Rolled back transactions are counted as failed
    assert stats["failed_transactions"] == 20
    assert stats["successful_transactions"] == 0
    assert stats["active_transactions"] == 0


async def create_and_commit(tx_manager, record_id):
    """Coroutine to create and commit a transaction."""
    async with tx_manager.transaction() as tx:
        tx.add_operation("create", "res.partner", record_ids=[record_id])
        await tx.commit()
        assert tx.state == TransactionState.COMMITTED


@given(st.integers(min_value=5, max_value=50))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_atomicity_with_random_transaction_count(
    transaction_manager, transaction_count
):
    """Test atomicity using random transaction counts."""
    # Reset transaction manager stats for each test run
    transaction_manager.successful_transactions = 0
    transaction_manager.failed_transactions = 0

    tasks = [
        create_and_commit(transaction_manager, i) for i in range(transaction_count)
    ]
    await asyncio.gather(*tasks)
    stats = transaction_manager.get_stats()
    assert stats["failed_transactions"] == 0
    assert stats["successful_transactions"] == transaction_count
    assert stats["active_transactions"] == 0
