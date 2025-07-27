"""Tests for transaction manager edge cases.

This module tests edge cases and error handling scenarios for the TransactionManager,
including:
- Broken savepoint names and invalid savepoint IDs
- Rollback after commit
- Commit failure recovery
- State transitions violations
- Utility methods (lines 560-577)
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch
import uuid

from zenoo_rpc.transaction.manager import (
    TransactionManager,
    Transaction,
    TransactionState,
    OperationRecord,
)
from zenoo_rpc.transaction.exceptions import (
    TransactionError,
    TransactionRollbackError,
    TransactionCommitError,
    TransactionStateError,
)


class MockClient:
    """Mock client for testing."""

    def __init__(self):
        self.write = AsyncMock()
        self.unlink = AsyncMock()
        self.create = AsyncMock()
        self.transaction_manager = None


@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    client = MockClient()
    client.transaction_manager = TransactionManager(client)
    return client


@pytest.fixture
def transaction_manager(mock_client):
    """Create a transaction manager with mock client."""
    return TransactionManager(mock_client)


class TestSavepointEdgeCases:
    """Test edge cases related to savepoints."""

    @pytest.mark.asyncio
    async def test_invalid_savepoint_id(self, transaction_manager):
        """Test rollback to non-existent savepoint ID."""
        async with transaction_manager.transaction() as tx:
            # Create a valid savepoint
            sp_id = await tx.create_savepoint("valid_sp")

            # Try to rollback to non-existent savepoint
            with pytest.raises(TransactionError) as exc_info:
                await tx.rollback_to_savepoint("non_existent_id")

            assert "Savepoint non_existent_id not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_savepoint_with_special_characters(self, transaction_manager):
        """Test savepoint names with special characters."""
        special_names = [
            "sp-with-dashes",
            "sp_with_underscores",
            "sp.with.dots",
            "sp@with@at",
            "sp with spaces",
            "sp\twith\ttabs",
            "sp\nwith\nnewlines",
            "sp'with'quotes",
            'sp"with"double"quotes',
            "sp/with/slashes",
            "sp\\with\\backslashes",
        ]

        async with transaction_manager.transaction() as tx:
            for name in special_names:
                sp_id = await tx.create_savepoint(name)
                assert sp_id is not None

                # Verify the savepoint was created
                sp = tx.savepoints[-1]
                assert sp.name == name
                assert sp.savepoint_id == sp_id

    @pytest.mark.asyncio
    async def test_savepoint_in_inactive_transaction(self, transaction_manager):
        """Test creating savepoint in non-active transaction."""
        async with transaction_manager.transaction() as tx:
            # Commit the transaction
            await tx.commit()

            # Try to create savepoint after commit
            with pytest.raises(TransactionStateError) as exc_info:
                await tx.create_savepoint("too_late")

            assert "Cannot create savepoint in committed transaction" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_rollback_to_savepoint_after_commit(self, transaction_manager):
        """Test rolling back to savepoint after transaction is committed."""
        async with transaction_manager.transaction() as tx:
            sp_id = await tx.create_savepoint("sp1")
            await tx.commit()

            with pytest.raises(TransactionStateError) as exc_info:
                await tx.rollback_to_savepoint(sp_id)

            assert "Cannot rollback in committed transaction" in str(exc_info.value)

    @given(num_savepoints=st.integers(min_value=50, max_value=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_many_savepoints(self, transaction_manager, num_savepoints):
        """Test creating many savepoints and selective rollback."""
        async with transaction_manager.transaction() as tx:
            savepoint_ids = []

            # Create many savepoints
            for i in range(num_savepoints):
                tx.add_operation("create", f"model_{i}", record_ids=[i])
                sp_id = await tx.create_savepoint(f"sp_{i}")
                savepoint_ids.append(sp_id)

            assert len(tx.savepoints) == num_savepoints
            assert len(tx.operations) == num_savepoints

            # Rollback to middle savepoint
            middle_idx = num_savepoints // 2
            await tx.rollback_to_savepoint(savepoint_ids[middle_idx])

            # Should have only savepoints and operations up to middle
            assert len(tx.savepoints) == middle_idx + 1
            assert len(tx.operations) == middle_idx + 1


class TestTransactionStateViolations:
    """Test violations of transaction state transitions."""

    @pytest.mark.asyncio
    async def test_commit_after_rollback(self, transaction_manager):
        """Test committing after rollback."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])

            # Rollback the transaction
            await tx.rollback()
            assert tx.state == TransactionState.ROLLED_BACK

            # Try to commit after rollback
            with pytest.raises(TransactionStateError) as exc_info:
                await tx.commit()

            assert "Cannot commit rolled_back transaction" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_after_commit(self, transaction_manager):
        """Test rolling back after commit."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])

            # Commit the transaction
            await tx.commit()
            assert tx.state == TransactionState.COMMITTED

            # Try to rollback after commit - should just log warning
            await tx.rollback()  # Should not raise, just log warning
            assert tx.state == TransactionState.COMMITTED  # State unchanged

    @pytest.mark.asyncio
    async def test_double_commit(self, transaction_manager):
        """Test committing a transaction twice."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])

            # First commit
            await tx.commit()
            assert tx.state == TransactionState.COMMITTED

            # Second commit should fail
            with pytest.raises(TransactionStateError):
                await tx.commit()

    @pytest.mark.asyncio
    async def test_operations_on_inactive_transaction(self, transaction_manager):
        """Test adding operations to inactive transaction."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            # Commit to make inactive
            await tx.commit()

            # Try to add operation
            with pytest.raises(TransactionStateError) as exc_info:
                tx.add_operation("create", "res.partner", record_ids=[1])

            assert "Cannot add operation to committed transaction" in str(
                exc_info.value
            )


class TestCommitFailureRecovery:
    """Test recovery from commit failures."""

    @pytest.mark.asyncio
    async def test_commit_with_perform_failure(self, transaction_manager, mock_client):
        """Test commit failure during _perform_commit."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", record_ids=[1])

            # Mock _perform_commit to fail
            with patch.object(
                tx, "_perform_commit", side_effect=Exception("Perform commit failed")
            ):
                with pytest.raises(TransactionCommitError) as exc_info:
                    await tx.commit()

                assert "Failed to commit transaction" in str(exc_info.value)
                assert tx.state == TransactionState.FAILED
                assert exc_info.value.transaction_id == tx.id
                assert exc_info.value.original_error.args[0] == "Perform commit failed"

    @pytest.mark.asyncio
    async def test_nested_commit_failure(self, transaction_manager):
        """Test commit failure in nested transactions."""
        async with transaction_manager.transaction() as parent_tx:
            async with transaction_manager.transaction() as child_tx:
                child_tx.add_operation("create", "res.partner", record_ids=[1])

                # Force child to fail state
                child_tx.state = TransactionState.FAILED

            # Parent commit should handle failed child
            with patch.object(parent_tx, "_perform_commit"):
                await parent_tx.commit()
                # Should still commit despite failed child
                assert parent_tx.state == TransactionState.COMMITTED


class TestRollbackFailureRecovery:
    """Test recovery from rollback failures."""

    @pytest.mark.asyncio
    async def test_rollback_with_compensating_failure(
        self, transaction_manager, mock_client
    ):
        """Test rollback when compensating operations fail."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            tx.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])
            tx.add_operation(
                "update", "res.partner", record_ids=[2], original_data={"name": "old"}
            )

            # Make unlink fail
            mock_client.unlink.side_effect = Exception("Unlink failed")

            # Rollback should still complete but log errors
            with pytest.raises(TransactionRollbackError) as exc_info:
                await tx.rollback()

            assert "Failed to rollback transaction" in str(exc_info.value)
            assert tx.state == TransactionState.FAILED

    @pytest.mark.asyncio
    async def test_rollback_unknown_operation_type(self, transaction_manager):
        """Test rollback with unknown operation type."""
        async with transaction_manager.transaction(auto_commit=False) as tx:
            # Manually create an operation with invalid type
            invalid_op = OperationRecord(
                operation_type="invalid_type", model="res.partner", record_ids=[1]
            )
            tx.operations.append(invalid_op)

            # get_compensating_operation should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                invalid_op.get_compensating_operation()

            assert "Unknown operation type: invalid_type" in str(exc_info.value)


class TestUtilityMethods:
    """Test utility methods (lines 560-577)."""

    @pytest.mark.asyncio
    async def test_get_current_transaction(self, transaction_manager):
        """Test get_current_transaction method (line 560)."""
        # No current transaction
        assert transaction_manager.get_current_transaction() is None

        # With active transaction
        async with transaction_manager.transaction() as tx:
            assert transaction_manager.get_current_transaction() == tx

            # With nested transaction
            async with transaction_manager.transaction() as nested_tx:
                assert transaction_manager.get_current_transaction() == nested_tx

            # Back to parent
            assert transaction_manager.get_current_transaction() == tx

        # After exit
        assert transaction_manager.get_current_transaction() is None

    @pytest.mark.asyncio
    async def test_get_transaction_by_id(self, transaction_manager):
        """Test get_transaction method (lines 562-571)."""
        # Non-existent transaction
        assert transaction_manager.get_transaction("non_existent") is None

        # Create transactions with specific IDs
        tx_id1 = str(uuid.uuid4())
        tx_id2 = str(uuid.uuid4())

        async with transaction_manager.transaction(transaction_id=tx_id1) as tx1:
            async with transaction_manager.transaction(transaction_id=tx_id2) as tx2:
                # Both should be retrievable
                assert transaction_manager.get_transaction(tx_id1) == tx1
                assert transaction_manager.get_transaction(tx_id2) == tx2

                # Check ID assignment
                assert tx1.id == tx_id1
                assert tx2.id == tx_id2

        # After exit, should not be retrievable
        assert transaction_manager.get_transaction(tx_id1) is None
        assert transaction_manager.get_transaction(tx_id2) is None

    @pytest.mark.asyncio
    async def test_rollback_all(self, transaction_manager):
        """Test rollback_all method (lines 573-577)."""
        # Test with no transactions
        await transaction_manager.rollback_all()

        # Test with multiple active transactions
        transactions = []

        # Create multiple transactions manually
        for i in range(5):
            tx = Transaction(transaction_manager.client, transaction_id=f"tx_{i}")
            tx.state = TransactionState.ACTIVE
            transaction_manager.active_transactions[tx.id] = tx
            transactions.append(tx)

            # Add some operations
            for j in range(3):
                tx.add_operation("create", f"model_{i}", record_ids=[j])

        # All should be active
        assert all(tx.is_active for tx in transactions)
        assert len(transaction_manager.active_transactions) == 5

        # Rollback all
        await transaction_manager.rollback_all()

        # All should be rolled back
        assert all(tx.state == TransactionState.ROLLED_BACK for tx in transactions)

        # Test with mixed states
        tx1 = Transaction(transaction_manager.client, "mixed_1")
        tx1.state = TransactionState.ACTIVE
        tx2 = Transaction(transaction_manager.client, "mixed_2")
        tx2.state = TransactionState.COMMITTED  # Already committed
        tx3 = Transaction(transaction_manager.client, "mixed_3")
        tx3.state = TransactionState.ACTIVE

        transaction_manager.active_transactions = {
            "mixed_1": tx1,
            "mixed_2": tx2,
            "mixed_3": tx3,
        }

        await transaction_manager.rollback_all()

        # Only active ones should be rolled back
        assert tx1.state == TransactionState.ROLLED_BACK
        assert tx2.state == TransactionState.COMMITTED  # Unchanged
        assert tx3.state == TransactionState.ROLLED_BACK


class TestEdgeCaseScenarios:
    """Test complex edge case scenarios."""

    @pytest.mark.asyncio
    async def test_savepoint_rollback_with_failed_operations(
        self, transaction_manager, mock_client
    ):
        """Test savepoint rollback when some operations fail."""
        async with transaction_manager.transaction() as tx:
            # Add operations
            tx.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])
            sp1 = await tx.create_savepoint("sp1")

            tx.add_operation("create", "res.partner", record_ids=[2], created_ids=[2])
            tx.add_operation("create", "res.partner", record_ids=[3], created_ids=[3])

            # Make second unlink fail
            call_count = 0

            def unlink_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Unlink failed for second call")
                return None

            mock_client.unlink.side_effect = unlink_side_effect

            # Rollback to savepoint - should raise error but continue with other operations
            with pytest.raises(TransactionRollbackError) as exc_info:
                await tx.rollback_to_savepoint(sp1)

            # Check error message
            assert "Failed to rollback to savepoint" in str(exc_info.value)

            # Should have attempted to rollback both operations
            assert mock_client.unlink.call_count == 2

    @pytest.mark.asyncio
    async def test_transaction_context_cleanup_on_exception(self, transaction_manager):
        """Test proper cleanup when exception occurs in transaction context."""
        tx_id = "cleanup_test"

        with pytest.raises(RuntimeError):
            async with transaction_manager.transaction(transaction_id=tx_id) as tx:
                # Verify transaction is active and tracked
                assert tx.id == tx_id
                assert transaction_manager.get_transaction(tx_id) == tx
                assert transaction_manager.get_current_transaction() == tx

                # Raise exception
                raise RuntimeError("Test exception")

        # Verify cleanup happened
        assert transaction_manager.get_transaction(tx_id) is None
        assert transaction_manager.get_current_transaction() is None

        # Transaction should be rolled back
        assert tx.state == TransactionState.ROLLED_BACK
        assert transaction_manager.failed_transactions == 1

    @pytest.mark.asyncio
    async def test_empty_operations_handling(self, transaction_manager, mock_client):
        """Test handling of operations with empty data."""
        async with transaction_manager.transaction() as tx:
            # Add operations with edge case data
            tx.add_operation("create", "res.partner", record_ids=[], created_ids=[])
            tx.add_operation("update", "res.partner", record_ids=[], original_data={})
            tx.add_operation("delete", "res.partner", record_ids=[], original_data=None)

            # These should work without errors
            await tx.rollback()

            # Verify no calls were made for empty operations
            mock_client.unlink.assert_not_called()
            mock_client.write.assert_not_called()

    @given(
        operations=st.lists(
            st.tuples(
                st.sampled_from(["create", "update", "delete"]),
                st.text(min_size=1, max_size=50),
                st.lists(st.integers(min_value=1, max_value=1000), max_size=100),
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_large_transaction_handling(self, transaction_manager, operations):
        """Test handling of large transactions with many operations."""
        async with transaction_manager.transaction() as tx:
            for op_type, model, record_ids in operations:
                if op_type == "create":
                    tx.add_operation(
                        op_type, model, record_ids=record_ids, created_ids=record_ids
                    )
                else:
                    tx.add_operation(
                        op_type,
                        model,
                        record_ids=record_ids,
                        original_data={"data": "test"},
                    )

            # Should handle large number of operations
            assert len(tx.operations) == len(operations)

            # Create savepoints at intervals after adding operations
            savepoints = []
            for i in range(0, len(operations), 10):
                # Create savepoint after every 10 operations
                # The savepoint stores the current number of operations
                sp_id = await tx.create_savepoint(f"sp_{i}")
                savepoints.append((len(tx.operations), sp_id))

            # Test rollback to random savepoint
            if savepoints and len(savepoints) > 1:
                # Get the middle savepoint
                middle_idx = len(savepoints) // 2
                expected_operations, sp_id = savepoints[middle_idx]

                await tx.rollback_to_savepoint(sp_id)

                # Operations should be truncated to the savepoint position
                assert len(tx.operations) == expected_operations
