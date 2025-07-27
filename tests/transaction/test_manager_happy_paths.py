"""Tests for transaction manager happy path scenarios.

This module tests successful transaction sequences including:
- Start, commit, and rollback operations
- Nested savepoints
- Duration calculation
- Statistics aggregation
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch
import time

from zenoo_rpc.transaction.manager import (
    TransactionManager,
    Transaction,
    TransactionState,
)
from zenoo_rpc.transaction.exceptions import TransactionStateError


class MockClient:
    """Mock client for testing."""

    def __init__(self):
        self.write = AsyncMock()
        self.unlink = AsyncMock()
        self.create = AsyncMock()


@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    return MockClient()


@pytest.fixture
def transaction_manager(mock_client):
    """Create a transaction manager with mock client."""
    return TransactionManager(mock_client)


class TestTransactionLifecycle:
    """Test transaction lifecycle operations."""

    @pytest.mark.asyncio
    async def test_simple_commit_sequence(self, transaction_manager):
        """Test a simple start-commit sequence."""
        async with transaction_manager.transaction() as tx:
            assert tx.state == TransactionState.ACTIVE
            assert tx.is_active
            assert not tx.is_nested
            assert tx.parent is None

            # Add an operation
            tx.add_operation(
                operation_type="create",
                model="res.partner",
                record_ids=[1],
                created_ids=[1],
            )

            assert len(tx.operations) == 1

        # Transaction should auto-commit on context exit
        assert tx.state == TransactionState.COMMITTED
        assert not tx.is_active
        assert transaction_manager.successful_transactions == 1
        assert transaction_manager.failed_transactions == 0

    @pytest.mark.asyncio
    async def test_explicit_commit(self, transaction_manager):
        """Test explicit commit before context exit."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            assert tx.state == TransactionState.ACTIVE

            # Add multiple operations
            tx.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])
            tx.add_operation(
                "update", "res.partner", record_ids=[1], original_data={"name": "old"}
            )
            tx.add_operation(
                "delete",
                "res.partner",
                record_ids=[2],
                original_data={"name": "deleted"},
            )

            await tx.commit()
            assert tx.state == TransactionState.COMMITTED
            assert tx.committed_at is not None
            assert tx.end_time is not None

    @pytest.mark.asyncio
    async def test_explicit_rollback(self, transaction_manager, mock_client):
        """Test explicit rollback."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            # Add operations to rollback
            tx.add_operation(
                operation_type="create",
                model="res.partner",
                record_ids=[1],
                created_ids=[1],
            )
            tx.add_operation(
                operation_type="update",
                model="res.partner",
                record_ids=[2],
                original_data={"name": "original", "email": "old@example.com"},
            )

            await tx.rollback()
            assert tx.state == TransactionState.ROLLED_BACK
            assert tx.rolled_back_at is not None
            assert tx.end_time is not None
            assert len(tx.operations) == 0  # Operations cleared after rollback

            # Verify compensating operations were called
            mock_client.unlink.assert_called_once_with("res.partner", [1])
            mock_client.write.assert_called_once_with(
                "res.partner", [2], {"name": "original", "email": "old@example.com"}
            )

    @pytest.mark.asyncio
    async def test_auto_rollback_on_exception(self, transaction_manager):
        """Test automatic rollback on exception."""
        with pytest.raises(ValueError):
            async with transaction_manager.transaction() as tx:
                tx.add_operation(
                    "create", "res.partner", record_ids=[1], created_ids=[1]
                )
                raise ValueError("Test error")

        assert tx.state == TransactionState.ROLLED_BACK
        assert transaction_manager.failed_transactions == 1


class TestSavepoints:
    """Test savepoint functionality."""

    @pytest.mark.asyncio
    async def test_create_single_savepoint(self, transaction_manager):
        """Test creating a single savepoint."""
        async with transaction_manager.transaction() as tx:
            # Create savepoint
            sp_id = await tx.create_savepoint("test_sp")
            assert sp_id is not None
            assert len(tx.savepoints) == 1
            assert tx.savepoints[0].name == "test_sp"
            assert tx.savepoints[0].savepoint_id == sp_id
            assert tx.savepoints[0].operation_index == 0

    @pytest.mark.asyncio
    async def test_multiple_savepoints(self, transaction_manager):
        """Test creating multiple savepoints."""
        async with transaction_manager.transaction() as tx:
            # Add operations and create savepoints
            tx.add_operation("create", "res.partner", record_ids=[1])
            sp1 = await tx.create_savepoint("sp1")

            tx.add_operation("create", "res.partner", record_ids=[2])
            sp2 = await tx.create_savepoint("sp2")

            tx.add_operation("create", "res.partner", record_ids=[3])
            sp3 = await tx.create_savepoint("sp3")

            assert len(tx.savepoints) == 3
            assert tx.savepoints[0].operation_index == 1
            assert tx.savepoints[1].operation_index == 2
            assert tx.savepoints[2].operation_index == 3

    @pytest.mark.asyncio
    async def test_rollback_to_savepoint(self, transaction_manager, mock_client):
        """Test rolling back to a savepoint."""
        async with transaction_manager.transaction() as tx:
            # Operation 1
            tx.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])

            # Savepoint 1
            sp1 = await tx.create_savepoint("sp1")

            # Operations 2 and 3
            tx.add_operation("create", "res.partner", record_ids=[2], created_ids=[2])
            tx.add_operation("create", "res.partner", record_ids=[3], created_ids=[3])

            # Rollback to savepoint 1
            await tx.rollback_to_savepoint(sp1)

            # Should have only 1 operation and 1 savepoint
            assert len(tx.operations) == 1
            assert len(tx.savepoints) == 1

            # Verify compensating operations for rolled back operations
            assert mock_client.unlink.call_count == 2
            mock_client.unlink.assert_any_call("res.partner", [3])
            mock_client.unlink.assert_any_call("res.partner", [2])

    @pytest.mark.asyncio
    async def test_nested_savepoints_with_rollback(
        self, transaction_manager, mock_client
    ):
        """Test nested savepoints with selective rollback."""
        async with transaction_manager.transaction() as tx:
            # Base operation
            tx.add_operation("create", "res.company", record_ids=[1], created_ids=[1])
            company_sp = await tx.create_savepoint("company")

            # Department operations
            tx.add_operation(
                "create", "hr.department", record_ids=[10], created_ids=[10]
            )
            dept_sp = await tx.create_savepoint("department")

            # Employee operations
            tx.add_operation(
                "create", "hr.employee", record_ids=[100], created_ids=[100]
            )
            tx.add_operation(
                "create", "hr.employee", record_ids=[101], created_ids=[101]
            )

            # Rollback only employees, keep department
            await tx.rollback_to_savepoint(dept_sp)

            assert len(tx.operations) == 2  # Company + Department
            assert len(tx.savepoints) == 2

            # Add new employee after rollback
            tx.add_operation(
                "create", "hr.employee", record_ids=[102], created_ids=[102]
            )

            await tx.commit()
            assert len(tx.operations) == 3


class TestNestedTransactions:
    """Test nested transaction functionality."""

    @pytest.mark.asyncio
    async def test_simple_nested_transaction(self, transaction_manager):
        """Test a simple nested transaction."""
        async with transaction_manager.transaction() as parent_tx:
            assert parent_tx.parent is None
            assert not parent_tx.is_nested

            async with transaction_manager.transaction() as child_tx:
                assert child_tx.parent == parent_tx
                assert child_tx.is_nested
                assert child_tx in parent_tx.children

                # Child commits first
                await child_tx.commit()
                assert child_tx.state == TransactionState.COMMITTED

            # Parent commits
            await parent_tx.commit()
            assert parent_tx.state == TransactionState.COMMITTED

    @pytest.mark.asyncio
    async def test_multiple_nested_transactions(self, transaction_manager):
        """Test multiple levels of nested transactions."""
        async with transaction_manager.transaction() as tx1:
            tx1.add_operation("create", "level1", record_ids=[1])

            async with transaction_manager.transaction() as tx2:
                tx2.add_operation("create", "level2", record_ids=[2])

                async with transaction_manager.transaction() as tx3:
                    tx3.add_operation("create", "level3", record_ids=[3])
                    assert tx3.parent == tx2
                    assert tx2.parent == tx1
                    assert tx1.parent is None


class TestDurationCalculation:
    """Test transaction duration calculation."""

    @pytest.mark.asyncio
    async def test_duration_property(self, transaction_manager):
        """Test duration property calculation."""
        async with transaction_manager.transaction() as tx:
            # Manually set times for testing
            tx.start_time = 100.0
            tx.end_time = 110.5

            assert tx.duration == 10.5

            # No duration if times not set
            tx.start_time = None
            assert tx.duration is None

    @pytest.mark.asyncio
    async def test_get_duration_method(self, transaction_manager):
        """Test get_duration method with different scenarios."""
        async with transaction_manager.transaction() as tx:
            # Test with no start time
            tx.start_time = None
            assert tx.get_duration() is None

            # Test with start time but no end time (active transaction)
            tx.start_time = 100.0
            tx.end_time = None
            tx.committed_at = None
            tx.rolled_back_at = None

            # Mock current time
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 105.0
                assert tx.get_duration() == 5.0

            # Test with committed_at
            tx.committed_at = 108.0
            assert tx.get_duration() == 8.0

            # Test with rolled_back_at (should use this over committed_at)
            tx.rolled_back_at = 107.0
            assert tx.get_duration() == 7.0

            # Test with end_time (should use this over others)
            tx.end_time = 106.0
            assert tx.get_duration() == 6.0

    @pytest.mark.asyncio
    async def test_duration_no_event_loop(self, transaction_manager):
        """Test duration calculation when no event loop is available."""
        async with transaction_manager.transaction() as tx:
            tx.start_time = 100.0

            # Mock to raise RuntimeError (no event loop)
            with patch("asyncio.get_event_loop", side_effect=RuntimeError):
                with patch("time.time", return_value=105.0):
                    assert tx.get_duration() == 5.0


class TestTransactionStats:
    """Test transaction statistics and aggregation."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, mock_client):
        """Test transaction statistics tracking."""
        manager = TransactionManager(mock_client)

        # Initial stats
        stats = manager.get_stats()
        assert stats["successful_transactions"] == 0
        assert stats["failed_transactions"] == 0
        assert stats["active_transactions"] == 0
        assert stats["total_operations"] == 0

        # Successful transaction
        async with manager.transaction() as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])
            tx.add_operation("update", "res.partner", record_ids=[2])

        stats = manager.get_stats()
        assert stats["successful_transactions"] == 1
        assert stats["failed_transactions"] == 0

        # Failed transaction
        try:
            async with manager.transaction() as tx:
                tx.add_operation("delete", "res.partner", record_ids=[3])
                raise Exception("Test failure")
        except:
            pass

        stats = manager.get_stats()
        assert stats["successful_transactions"] == 1
        assert stats["failed_transactions"] == 1

    @pytest.mark.asyncio
    async def test_active_transaction_tracking(self, transaction_manager):
        """Test tracking of active transactions."""
        # No active transactions initially
        stats = transaction_manager.get_stats()
        assert stats["active_transactions"] == 0
        assert stats["current_transaction_id"] is None

        # Start a transaction
        async with transaction_manager.transaction() as tx:
            stats = transaction_manager.get_stats()
            assert stats["active_transactions"] == 1
            assert stats["current_transaction_id"] == tx.id
            assert stats["total_transactions"] == 1

            # Start nested transaction
            async with transaction_manager.transaction() as nested_tx:
                stats = transaction_manager.get_stats()
                assert stats["active_transactions"] == 2
                assert stats["current_transaction_id"] == nested_tx.id
                assert stats["total_transactions"] == 2

    @pytest.mark.asyncio
    async def test_operation_count_in_stats(self, transaction_manager):
        """Test operation counting in statistics."""
        async with transaction_manager.transaction() as tx1:
            tx1.add_operation("create", "res.partner", record_ids=[1])
            tx1.add_operation("update", "res.partner", record_ids=[2])

            async with transaction_manager.transaction() as tx2:
                tx2.add_operation("delete", "res.partner", record_ids=[3])
                tx2.add_operation("create", "res.company", record_ids=[4])
                tx2.add_operation("update", "res.company", record_ids=[5])

                stats = transaction_manager.get_stats()
                assert stats["total_operations"] == 5

    @pytest.mark.asyncio
    async def test_get_transaction_stats_alias(self, transaction_manager):
        """Test that get_transaction_stats and get_stats return same results."""
        async with transaction_manager.transaction() as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])

            stats1 = transaction_manager.get_stats()
            stats2 = transaction_manager.get_transaction_stats()

            assert stats1 == stats2


class TestTransactionContext:
    """Test transaction context management."""

    @pytest.mark.asyncio
    async def test_context_storage(self, transaction_manager):
        """Test storing and retrieving context data."""
        async with transaction_manager.transaction() as tx:
            # Set context values
            tx.set_context("user_id", 123)
            tx.set_context("company_id", 456)
            tx.set_context("metadata", {"source": "api", "version": "1.0"})

            # Get individual values
            assert tx.get_context("user_id") == 123
            assert tx.get_context("company_id") == 456
            assert tx.get_context("metadata") == {"source": "api", "version": "1.0"}

            # Get with default
            assert tx.get_context("missing_key", "default") == "default"

            # Get all context
            all_context = tx.get_context()
            assert all_context == {
                "user_id": 123,
                "company_id": 456,
                "metadata": {"source": "api", "version": "1.0"},
            }


# Hypothesis strategies for testing
operation_strategy = st.sampled_from(["create", "update", "delete"])
model_strategy = st.sampled_from(
    ["res.partner", "res.company", "product.product", "sale.order"]
)
record_ids_strategy = st.lists(
    st.integers(min_value=1, max_value=1000), min_size=1, max_size=10
)


class TestHypothesisStrategies:
    """Test with Hypothesis for property-based testing."""

    @given(
        operations=st.lists(
            st.tuples(operation_strategy, model_strategy, record_ids_strategy),
            min_size=1,
            max_size=20,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_random_operations_sequence(self, transaction_manager, operations):
        """Test random sequences of operations."""
        async with transaction_manager.transaction() as tx:
            for op_type, model, record_ids in operations:
                if op_type == "create":
                    tx.add_operation(
                        op_type, model, record_ids=record_ids, created_ids=record_ids
                    )
                elif op_type == "update":
                    tx.add_operation(
                        op_type,
                        model,
                        record_ids=record_ids,
                        original_data={"name": "old"},
                    )
                else:  # delete
                    tx.add_operation(
                        op_type,
                        model,
                        record_ids=record_ids,
                        original_data={"name": "deleted"},
                    )

            assert len(tx.operations) == len(operations)
            await tx.commit()
            assert tx.state == TransactionState.COMMITTED

    @given(
        num_savepoints=st.integers(min_value=1, max_value=10),
        operations_per_savepoint=st.integers(min_value=1, max_value=5),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_random_savepoint_operations(
        self, transaction_manager, num_savepoints, operations_per_savepoint
    ):
        """Test random savepoint creation and operations."""
        async with transaction_manager.transaction() as tx:
            savepoints = []

            for i in range(num_savepoints):
                # Add operations before savepoint
                for j in range(operations_per_savepoint):
                    tx.add_operation(
                        "create",
                        f"model.{i}.{j}",
                        record_ids=[i * 100 + j],
                        created_ids=[i * 100 + j],
                    )

                # Create savepoint
                sp_id = await tx.create_savepoint(f"sp_{i}")
                savepoints.append(sp_id)

            assert len(tx.savepoints) == num_savepoints
            assert len(tx.operations) == num_savepoints * operations_per_savepoint

    @given(
        transaction_ids=st.lists(
            st.text(min_size=1, max_size=20), min_size=1, max_size=5, unique=True
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_concurrent_transaction_ids(self, mock_client, transaction_ids):
        """Test multiple transactions with different IDs."""
        manager = TransactionManager(mock_client)

        # Create transactions with specific IDs
        transactions = []
        for tx_id in transaction_ids:
            tx = Transaction(mock_client, transaction_id=tx_id)
            manager.active_transactions[tx_id] = tx
            transactions.append(tx)

        # Verify all transactions can be retrieved
        for tx_id, tx in zip(transaction_ids, transactions):
            retrieved = manager.get_transaction(tx_id)
            assert retrieved == tx
            assert retrieved.id == tx_id


class TestTransactionOperations:
    """Test transaction operation management."""

    @pytest.mark.asyncio
    async def test_operation_backward_compatibility(self, transaction_manager):
        """Test backward compatibility for operation parameters."""
        async with transaction_manager.transaction() as tx:
            # Test with 'data' parameter (backward compatibility)
            tx.add_operation(
                operation_type="update",
                model="res.partner",
                record_ids=[1],
                data={"name": "original", "email": "old@test.com"},
            )

            assert len(tx.operations) == 1
            assert tx.operations[0].original_data == {
                "name": "original",
                "email": "old@test.com",
            }

            # Test with record_id parameter (single ID)
            tx.add_operation(
                operation_type="delete",
                model="res.partner",
                record_id=42,
                original_data={"name": "to_delete"},
            )

            assert len(tx.operations) == 2
            assert tx.operations[1].record_ids == [42]

    @pytest.mark.asyncio
    async def test_compensating_operations(self, transaction_manager):
        """Test generation of compensating operations."""
        async with transaction_manager.transaction() as tx:
            # Create operation
            tx.add_operation(
                operation_type="create",
                model="res.partner",
                record_ids=[1, 2, 3],
                created_ids=[1, 2, 3],
            )
            comp_op = tx.operations[0].get_compensating_operation()
            assert comp_op["type"] == "delete"
            assert comp_op["model"] == "res.partner"
            assert comp_op["ids"] == [1, 2, 3]

            # Update operation
            tx.add_operation(
                operation_type="update",
                model="res.company",
                record_ids=[10],
                original_data={"name": "Old Corp", "email": "old@corp.com"},
            )
            comp_op = tx.operations[1].get_compensating_operation()
            assert comp_op["type"] == "update"
            assert comp_op["model"] == "res.company"
            assert comp_op["ids"] == [10]
            assert comp_op["values"] == {"name": "Old Corp", "email": "old@corp.com"}

            # Delete operation
            tx.add_operation(
                operation_type="delete",
                model="product.product",
                record_ids=[100],
                original_data={"name": "Product", "price": 99.99},
            )
            comp_op = tx.operations[2].get_compensating_operation()
            assert comp_op["type"] == "create"
            assert comp_op["model"] == "product.product"
            assert comp_op["values"] == {"name": "Product", "price": 99.99}


@pytest.mark.asyncio
async def test_manager_utility_methods(transaction_manager):
    """Test utility methods on TransactionManager."""
    # Test get_current_transaction when none exists
    assert transaction_manager.get_current_transaction() is None

    # Test rollback_all with no transactions
    await transaction_manager.rollback_all()  # Should not raise

    # Test with active transactions
    async with transaction_manager.transaction() as tx1:
        async with transaction_manager.transaction() as tx2:
            # Both should be active
            assert tx1.is_active
            assert tx2.is_active

            # Current should be tx2
            assert transaction_manager.get_current_transaction() == tx2

            # Test rollback_all
            active_count = len(transaction_manager.active_transactions)
            assert active_count == 2
