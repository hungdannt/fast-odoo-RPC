"""
Comprehensive tests for Zenoo-RPC transaction management.

This module tests all aspects of transaction management including:
- Transaction manager and transaction lifecycle
- Transaction contexts and decorators
- Savepoints and nested transactions
- Rollback and commit operations
- Error handling and recovery
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

from zenoo_rpc.transaction.manager import TransactionManager, Transaction
from zenoo_rpc.transaction.context import transaction, atomic, TransactionContext
from zenoo_rpc.transaction.exceptions import (
    TransactionError,
    TransactionRollbackError,
    TransactionCommitError,
    NestedTransactionError,
    TransactionStateError,
)


class TestTransaction:
    """Test individual transaction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.transaction = Transaction(
            client=self.mock_client, transaction_id="test_tx_123"
        )

    def test_transaction_creation(self):
        """Test transaction creation and properties."""
        assert self.transaction.id == "test_tx_123"
        assert self.transaction.client == self.mock_client
        assert self.transaction.is_active is True
        assert self.transaction.is_nested is False
        assert self.transaction.parent is None
        assert len(self.transaction.operations) == 0
        assert len(self.transaction.savepoints) == 0
        assert len(self.transaction.children) == 0

    def test_transaction_operation_tracking(self):
        """Test operation tracking in transactions."""
        # Add operations
        self.transaction.add_operation("create", "res.partner", data={"name": "Test"})
        self.transaction.add_operation(
            "update", "res.partner", record_id=1, data={"email": "test@example.com"}
        )
        self.transaction.add_operation("delete", "res.partner", record_id=2)

        assert len(self.transaction.operations) == 3

        # Check operation details
        ops = self.transaction.operations
        assert ops[0].operation_type == "create"
        assert ops[0].model == "res.partner"
        assert ops[0].original_data == {"name": "Test"}

        assert ops[1].operation_type == "update"
        assert ops[1].record_ids == [1]
        assert ops[1].original_data == {"email": "test@example.com"}

        assert ops[2].operation_type == "delete"
        assert ops[2].record_ids == [2]

    @pytest.mark.asyncio
    async def test_transaction_savepoints(self):
        """Test savepoint functionality."""
        # Add initial operations
        self.transaction.add_operation(
            "create", "res.partner", data={"name": "Initial"}
        )

        # Create savepoint
        savepoint_id = await self.transaction.create_savepoint("sp1")
        assert len(self.transaction.savepoints) == 1
        assert self.transaction.savepoints[0].savepoint_id == savepoint_id
        assert len(self.transaction.operations) == 1

        # Add more operations after savepoint
        self.transaction.add_operation(
            "update", "res.partner", record_id=1, data={"name": "Updated"}
        )
        self.transaction.add_operation("delete", "res.partner", record_id=2)
        assert len(self.transaction.operations) == 3

        # Rollback to savepoint
        await self.transaction.rollback_to_savepoint(savepoint_id)

        # Should only have operations before savepoint
        assert len(self.transaction.operations) == 1
        assert self.transaction.operations[0].original_data == {"name": "Initial"}

    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test transaction commit."""
        # Add operations
        self.transaction.add_operation("create", "res.partner", data={"name": "Test"})

        # Mock successful commit
        self.mock_client.execute_kw.return_value = True

        await self.transaction.commit()

        assert not self.transaction.is_active
        assert self.transaction.committed_at is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback."""
        # Add operations
        self.transaction.add_operation("create", "res.partner", data={"name": "Test"})
        self.transaction.add_operation(
            "update", "res.partner", record_id=1, data={"name": "Updated"}
        )

        await self.transaction.rollback()

        assert not self.transaction.is_active
        assert self.transaction.rolled_back_at is not None
        # Operations should be cleared after rollback
        assert len(self.transaction.operations) == 0

    def test_nested_transaction(self):
        """Test nested transaction creation."""
        parent_tx = Transaction(client=self.mock_client, transaction_id="parent")
        child_tx = Transaction(
            client=self.mock_client, transaction_id="child", parent=parent_tx
        )

        assert child_tx.is_nested is True
        assert child_tx.parent == parent_tx
        assert child_tx in parent_tx.children

    def test_transaction_context_data(self):
        """Test transaction context data management."""
        # Set context data
        self.transaction.set_context("user_id", 123)
        self.transaction.set_context("lang", "en_US")

        assert self.transaction.get_context("user_id") == 123
        assert self.transaction.get_context("lang") == "en_US"
        assert self.transaction.get_context("nonexistent") is None
        assert self.transaction.get_context("nonexistent", "default") == "default"

        # Get all context
        context = self.transaction.get_context()
        assert context["user_id"] == 123
        assert context["lang"] == "en_US"


class TestTransactionManager:
    """Test transaction manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.transaction_manager = TransactionManager(self.mock_client)

    @pytest.mark.asyncio
    async def test_transaction_manager_creation(self):
        """Test transaction manager creation."""
        async with self.transaction_manager.transaction() as tx:
            assert isinstance(tx, Transaction)
            assert tx.is_active
            assert tx.client == self.mock_client
            assert not tx.is_nested

            # Should be tracked as current transaction
            assert self.transaction_manager.current_transaction == tx
            assert tx.id in self.transaction_manager.active_transactions

    @pytest.mark.asyncio
    async def test_nested_transactions(self):
        """Test nested transaction support."""
        async with self.transaction_manager.transaction() as parent_tx:
            assert parent_tx.is_active
            assert not parent_tx.is_nested

            async with self.transaction_manager.transaction() as child_tx:
                assert child_tx.is_active
                assert child_tx.is_nested
                assert child_tx.parent == parent_tx
                assert child_tx in parent_tx.children

                # Current transaction should be the child
                assert self.transaction_manager.current_transaction == child_tx

            # After child exits, parent should be current again
            assert self.transaction_manager.current_transaction == parent_tx

    @pytest.mark.asyncio
    async def test_transaction_auto_commit(self):
        """Test automatic commit on successful completion."""
        self.mock_client.execute_kw.return_value = True

        async with self.transaction_manager.transaction(auto_commit=True) as tx:
            tx.add_operation("create", "res.partner", data={"name": "Test"})
            # Should auto-commit on context exit

        assert not tx.is_active
        assert tx.committed_at is not None

    @pytest.mark.asyncio
    async def test_transaction_auto_rollback_on_error(self):
        """Test automatic rollback on exception."""
        tx = None
        with pytest.raises(ValueError):
            async with self.transaction_manager.transaction() as transaction:
                tx = transaction
                tx.add_operation("create", "res.partner", data={"name": "Test"})
                raise ValueError("Test error")

        assert not tx.is_active
        assert tx.rolled_back_at is not None

    @pytest.mark.asyncio
    async def test_transaction_manual_control(self):
        """Test manual transaction control."""
        async with self.transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", data={"name": "Test"})

            # Manual commit
            await tx.commit()

        assert not tx.is_active
        assert tx.committed_at is not None

    @pytest.mark.asyncio
    async def test_multiple_concurrent_transactions(self):
        """Test multiple concurrent transactions."""
        # Use separate transaction managers to avoid shared state
        tx_manager1 = TransactionManager(self.mock_client)
        tx_manager2 = TransactionManager(self.mock_client)

        tx1_id = None
        tx2_id = None

        async def transaction1():
            nonlocal tx1_id
            async with tx_manager1.transaction() as tx:
                tx1_id = tx.id
                await asyncio.sleep(0.01)  # Simulate work
                tx.add_operation("create", "res.partner", data={"name": "TX1"})

        async def transaction2():
            nonlocal tx2_id
            async with tx_manager2.transaction() as tx:
                tx2_id = tx.id
                await asyncio.sleep(0.01)  # Simulate work
                tx.add_operation("create", "res.partner", data={"name": "TX2"})

        # Run transactions concurrently
        await asyncio.gather(transaction1(), transaction2())

        assert tx1_id is not None
        assert tx2_id is not None
        assert tx1_id != tx2_id

        # Both should be completed and removed from active transactions
        assert tx1_id not in tx_manager1.active_transactions
        assert tx2_id not in tx_manager2.active_transactions

    def test_transaction_manager_stats(self):
        """Test transaction manager statistics."""
        stats = self.transaction_manager.get_stats()

        assert "active_transactions" in stats
        assert "total_transactions" in stats
        assert "successful_transactions" in stats
        assert "failed_transactions" in stats
        assert isinstance(stats["active_transactions"], int)
        assert isinstance(stats["total_transactions"], int)


class TestTransactionContextManagers:
    """Test transaction context managers and decorators."""

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self):
        """Test transaction context manager."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = TransactionManager(mock_client)

        async with transaction(mock_client) as tx:
            assert isinstance(tx, Transaction)
            assert tx.is_active
            tx.add_operation("create", "res.partner", data={"name": "Test"})

    @pytest.mark.asyncio
    async def test_atomic_decorator(self):
        """Test atomic decorator."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = TransactionManager(mock_client)

        call_count = 0

        @atomic
        async def test_function(client, data, _transaction=None):
            nonlocal call_count
            call_count += 1

            # Should have transaction injected
            assert _transaction is not None
            assert isinstance(_transaction, Transaction)
            assert _transaction.is_active

            _transaction.add_operation("create", "res.partner", data=data)
            return data["result"]

        result = await test_function(mock_client, {"result": "success"})

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_atomic_decorator_with_error(self):
        """Test atomic decorator with error handling."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = TransactionManager(mock_client)

        @atomic
        async def failing_function(client, _transaction=None):
            _transaction.add_operation("create", "res.partner", data={"name": "Test"})
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_function(mock_client)

    @pytest.mark.asyncio
    async def test_transaction_context_class(self):
        """Test TransactionContext class."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = TransactionManager(mock_client)

        ctx = TransactionContext(mock_client)

        async with ctx.begin() as tx:
            assert isinstance(tx, Transaction)
            assert ctx.get_current_transaction() == tx
            tx.add_operation("create", "res.partner", data={"name": "Test"})

        # Transaction should be cleared after context exit
        assert ctx.get_current_transaction() is None


class TestTransactionExceptions:
    """Test transaction exception handling."""

    def test_transaction_error(self):
        """Test basic transaction error."""
        error = TransactionError("Test transaction error")
        assert str(error) == "Test transaction error"

    def test_transaction_rollback_error(self):
        """Test transaction rollback error."""
        error = TransactionRollbackError("Rollback failed", transaction_id="tx123")
        assert "Rollback failed" in str(error)
        assert error.transaction_id == "tx123"

    def test_transaction_commit_error(self):
        """Test transaction commit error."""
        error = TransactionCommitError("Commit failed", transaction_id="tx456")
        assert "Commit failed" in str(error)
        assert error.transaction_id == "tx456"

    def test_savepoint_error(self):
        """Test savepoint error."""
        error = TransactionStateError("Savepoint failed")
        assert "Savepoint failed" in str(error)

    def test_nested_transaction_error(self):
        """Test nested transaction error."""
        error = NestedTransactionError("Nested transaction failed")
        assert "Nested transaction failed" in str(error)

    @pytest.mark.asyncio
    async def test_transaction_error_handling(self):
        """Test comprehensive transaction error handling."""
        mock_client = AsyncMock()
        transaction_manager = TransactionManager(mock_client)

        tx = None
        with pytest.raises(ValueError):
            async with transaction_manager.transaction() as transaction:
                tx = transaction
                tx.add_operation("create", "res.partner", data={"name": "Test"})
                # Manually raise error to trigger rollback
                raise ValueError("Simulated database error")

        # Transaction should be rolled back
        assert not tx.is_active
        assert tx.rolled_back_at is not None


class TestTransactionIntegration:
    """Test transaction integration with other components."""

    @pytest.mark.asyncio
    async def test_transaction_with_batch_operations(self):
        """Test transaction integration with batch operations."""
        mock_client = AsyncMock()
        transaction_manager = TransactionManager(mock_client)

        async with transaction_manager.transaction() as tx:
            # Simulate batch operations within transaction
            tx.add_operation(
                "batch_create",
                "res.partner",
                data=[
                    {"name": "Company A"},
                    {"name": "Company B"},
                    {"name": "Company C"},
                ],
            )

            tx.add_operation(
                "batch_update",
                "res.partner",
                record_ids=[1, 2, 3],
                data={"active": False},
            )

            assert len(tx.operations) == 2
            assert tx.operations[0].operation_type == "batch_create"
            assert tx.operations[1].operation_type == "batch_update"

    @pytest.mark.asyncio
    async def test_transaction_with_caching(self):
        """Test transaction integration with caching."""
        mock_client = AsyncMock()
        transaction_manager = TransactionManager(mock_client)

        async with transaction_manager.transaction() as tx:
            # Set transaction-specific context for cache invalidation
            tx.set_context("cache_invalidation", ["res.partner"])
            tx.set_context("cache_tags", ["partners", "companies"])

            tx.add_operation("create", "res.partner", data={"name": "Test"})

            # Verify context is set
            assert tx.get_context("cache_invalidation") == ["res.partner"]
            assert "partners" in tx.get_context("cache_tags")

    @pytest.mark.asyncio
    async def test_transaction_performance_monitoring(self):
        """Test transaction performance monitoring."""
        mock_client = AsyncMock()
        transaction_manager = TransactionManager(mock_client)

        async with transaction_manager.transaction() as tx:
            # Simulate operations
            tx.add_operation("create", "res.partner", data={"name": "Test"})
            await asyncio.sleep(0.01)  # Simulate processing time

        # Check timing information
        assert tx.start_time is not None
        assert tx.committed_at is not None
        duration = tx.get_duration()
        assert duration is not None
        assert duration > 0
