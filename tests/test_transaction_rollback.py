"""
Tests for transaction rollback and compensating operations.
"""

import pytest
from unittest.mock import AsyncMock

from src.zenoo_rpc.transaction.manager import (
    Transaction,
    TransactionManager,
    TransactionState,
    OperationRecord,
    Savepoint,
)


class TestTransactionRollback:
    """Test cases for transaction rollback functionality."""

    @pytest.mark.asyncio
    async def test_operation_record_compensating_operations(self):
        """Test compensating operation generation."""
        # Test create operation
        create_op = OperationRecord(
            operation_type="create",
            model="res.partner",
            record_ids=[1, 2],
            created_ids=[1, 2],
        )

        compensating = create_op.get_compensating_operation()
        assert compensating["type"] == "delete"
        assert compensating["model"] == "res.partner"
        assert compensating["ids"] == [1, 2]

        # Test update operation
        update_op = OperationRecord(
            operation_type="update",
            model="res.partner",
            record_ids=[1],
            original_data={"name": "Old Name", "email": "old@test.com"},
        )

        compensating = update_op.get_compensating_operation()
        assert compensating["type"] == "update"
        assert compensating["model"] == "res.partner"
        assert compensating["ids"] == [1]
        assert compensating["values"] == {"name": "Old Name", "email": "old@test.com"}

        # Test delete operation
        delete_op = OperationRecord(
            operation_type="delete",
            model="res.partner",
            record_ids=[1],
            original_data={"name": "Deleted Partner", "email": "deleted@test.com"},
        )

        compensating = delete_op.get_compensating_operation()
        assert compensating["type"] == "create"
        assert compensating["model"] == "res.partner"
        assert compensating["values"] == {
            "name": "Deleted Partner",
            "email": "deleted@test.com",
        }

    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback with compensating operations."""
        mock_client = AsyncMock()
        transaction = Transaction(mock_client, "test-tx")

        # Add operations
        transaction.add_operation("create", "res.partner", [1, 2], created_ids=[1, 2])
        transaction.add_operation(
            "update", "res.partner", [3], original_data={"name": "Old Name"}
        )

        # Execute rollback
        await transaction.rollback()

        # Verify state
        assert transaction.state == TransactionState.ROLLED_BACK

        # Verify compensating operations were executed
        mock_client.unlink.assert_called_once_with("res.partner", [1, 2])
        mock_client.write.assert_called_once_with(
            "res.partner", [3], {"name": "Old Name"}
        )

    @pytest.mark.asyncio
    async def test_savepoint_creation_and_rollback(self):
        """Test savepoint creation and rollback."""
        mock_client = AsyncMock()
        transaction = Transaction(mock_client, "test-tx")

        # Add initial operation
        transaction.add_operation("create", "res.partner", [1], created_ids=[1])

        # Create savepoint
        savepoint_id = await transaction.create_savepoint("test_savepoint")
        assert len(transaction.savepoints) == 1
        assert transaction.savepoints[0].name == "test_savepoint"

        # Add more operations after savepoint
        transaction.add_operation(
            "update", "res.partner", [2], original_data={"name": "Old"}
        )
        transaction.add_operation("create", "res.partner", [3], created_ids=[3])

        assert len(transaction.operations) == 3

        # Rollback to savepoint
        await transaction.rollback_to_savepoint(savepoint_id)

        # Verify only operations after savepoint were rolled back
        assert len(transaction.operations) == 1  # Only first operation remains
        assert transaction.operations[0].operation_type == "create"
        assert transaction.operations[0].record_ids == [1]

        # Verify compensating operations were called for operations after savepoint
        mock_client.write.assert_called_once_with("res.partner", [2], {"name": "Old"})
        mock_client.unlink.assert_called_once_with("res.partner", [3])

    @pytest.mark.asyncio
    async def test_nested_transaction_rollback(self):
        """Test rollback with nested transactions."""
        mock_client = AsyncMock()
        manager = TransactionManager(mock_client)

        async with manager.transaction() as parent_tx:
            parent_tx.add_operation("create", "res.partner", [1], created_ids=[1])

            async with manager.transaction() as child_tx:
                child_tx.add_operation(
                    "update", "res.partner", [2], original_data={"name": "Old"}
                )

                # Rollback child transaction
                await child_tx.rollback()

                assert child_tx.state == TransactionState.ROLLED_BACK
                assert parent_tx.state == TransactionState.ACTIVE

        # Parent should still commit successfully
        assert parent_tx.state == TransactionState.COMMITTED

    @pytest.mark.asyncio
    async def test_transaction_manager_context(self):
        """Test transaction manager context with rollback."""
        mock_client = AsyncMock()
        manager = TransactionManager(mock_client)

        try:
            async with manager.transaction() as tx:
                tx.add_operation("create", "res.partner", [1], created_ids=[1])
                tx.add_operation(
                    "update",
                    "res.partner",
                    [2],
                    original_data={"email": "old@test.com"},
                )

                # Simulate an error to trigger rollback
                raise ValueError("Test error")

        except ValueError:
            pass  # Expected error

        # Transaction should be rolled back
        assert tx.state == TransactionState.ROLLED_BACK

        # Verify compensating operations were executed
        mock_client.unlink.assert_called_once_with("res.partner", [1])
        mock_client.write.assert_called_once_with(
            "res.partner", [2], {"email": "old@test.com"}
        )

    @pytest.mark.asyncio
    async def test_compensating_operation_execution(self):
        """Test individual compensating operation execution."""
        mock_client = AsyncMock()
        transaction = Transaction(mock_client, "test-tx")

        # Test delete compensating operation
        delete_op = {"type": "delete", "model": "res.partner", "ids": [1, 2, 3]}
        # Create mock operation record for delete
        from src.zenoo_rpc.transaction.manager import OperationRecord
        delete_record = OperationRecord(
            operation_type="create",
            model="res.partner",
            record_ids=[1, 2, 3],
            created_ids=[1, 2, 3]
        )
        await transaction._execute_compensating_operation(delete_op, delete_record)
        mock_client.unlink.assert_called_once_with("res.partner", [1, 2, 3])

        # Test update compensating operation
        update_op = {
            "type": "update",
            "model": "res.partner",
            "ids": [1],
            "values": {"name": "Restored Name", "email": "restored@test.com"},
        }
        # Create mock operation record for update
        update_record = OperationRecord(
            operation_type="update",
            model="res.partner",
            record_ids=[1],
            original_data={"name": "Restored Name", "email": "restored@test.com"}
        )
        await transaction._execute_compensating_operation(update_op, update_record)
        mock_client.write.assert_called_once_with(
            "res.partner", [1], {"name": "Restored Name", "email": "restored@test.com"}
        )

    @pytest.mark.asyncio
    async def test_multiple_savepoints(self):
        """Test multiple savepoints and selective rollback."""
        mock_client = AsyncMock()
        transaction = Transaction(mock_client, "test-tx")

        # Operation 1
        transaction.add_operation("create", "res.partner", [1], created_ids=[1])

        # Savepoint 1
        sp1_id = await transaction.create_savepoint("sp1")

        # Operation 2
        transaction.add_operation(
            "update", "res.partner", [2], original_data={"name": "Old2"}
        )

        # Savepoint 2
        sp2_id = await transaction.create_savepoint("sp2")

        # Operation 3
        transaction.add_operation("create", "res.partner", [3], created_ids=[3])

        assert len(transaction.operations) == 3
        assert len(transaction.savepoints) == 2

        # Rollback to savepoint 1
        await transaction.rollback_to_savepoint(sp1_id)

        # Should have only operation 1
        assert len(transaction.operations) == 1
        assert transaction.operations[0].record_ids == [1]

        # Should have only savepoint 1
        assert len(transaction.savepoints) == 1
        assert transaction.savepoints[0].savepoint_id == sp1_id

        # Verify compensating operations for operations 2 and 3
        mock_client.write.assert_called_once_with("res.partner", [2], {"name": "Old2"})
        mock_client.unlink.assert_called_once_with("res.partner", [3])
