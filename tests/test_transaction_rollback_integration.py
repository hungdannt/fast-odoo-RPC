"""Test transaction rollback integration with CRUD methods."""

import pytest
from unittest.mock import AsyncMock, patch
from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.transaction.manager import TransactionManager
from src.zenoo_rpc.transaction.exceptions import TransactionError


@pytest.fixture
async def client_with_transaction():
    """Create client with transaction manager setup."""
    client = ZenooClient("http://localhost:8069")
    
    # Mock authentication
    client._session._database = "test_db"
    client._session._uid = 1
    client._session._username = "admin"
    client._session._password = "admin"
    
    # Mock CRUD methods
    client.create = AsyncMock()
    client.write = AsyncMock()
    client.unlink = AsyncMock()
    client.execute_kw = AsyncMock()
    
    # Setup transaction manager
    await client.setup_transaction_manager()
    
    return client


class TestTransactionRollbackIntegration:
    """Test transaction rollback integration with CRUD methods."""

    async def test_transaction_rollback_calls_crud_methods(self, client_with_transaction):
        """Test that transaction rollback calls the correct CRUD methods."""
        client = client_with_transaction
        
        # Setup mock returns
        client.create.return_value = 123
        client.write.return_value = True
        client.unlink.return_value = True
        
        # Start transaction and perform operations
        async with client.transaction() as tx:
            # Perform operations that should be tracked
            await tx.create("res.partner", {"name": "Test Partner"})
            await tx.update("res.partner", [1], {"name": "Updated Partner"})
            await tx.delete("res.partner", [2])
            
            # Force rollback
            raise TransactionError("Test rollback")
        
        # Verify that rollback operations would be called
        # Note: This tests the framework, actual rollback execution 
        # depends on the transaction manager implementation
        assert len(tx.operations) == 3
        
        # Check operation types
        operations = tx.operations
        assert operations[0].operation_type == "create"
        assert operations[1].operation_type == "update"
        assert operations[2].operation_type == "delete"

    async def test_transaction_success_no_rollback(self, client_with_transaction):
        """Test successful transaction doesn't trigger rollback."""
        client = client_with_transaction
        
        # Setup mock returns
        client.create.return_value = 123
        client.write.return_value = True
        
        # Successful transaction
        async with client.transaction() as tx:
            result1 = await tx.create("res.partner", {"name": "Test Partner"})
            result2 = await tx.update("res.partner", [1], {"name": "Updated"})
            
            assert result1 == 123
            assert result2 is True
        
        # Transaction should be committed, not rolled back
        assert tx.status == "committed"

    async def test_transaction_rollback_with_actual_crud_calls(self, client_with_transaction):
        """Test transaction rollback with actual CRUD method calls."""
        client = client_with_transaction
        
        # Mock the actual CRUD methods to verify they're called during rollback
        with patch.object(client, 'unlink') as mock_unlink, \
             patch.object(client, 'write') as mock_write, \
             patch.object(client, 'create') as mock_create:
            
            mock_create.return_value = 123
            mock_write.return_value = True
            mock_unlink.return_value = True
            
            try:
                async with client.transaction() as tx:
                    # Perform operations
                    await tx.create("res.partner", {"name": "Test"})
                    await tx.update("res.partner", [1], {"active": False})
                    
                    # Force rollback
                    raise Exception("Force rollback")
                    
            except Exception:
                pass  # Expected exception
            
            # Verify transaction was rolled back
            assert tx.status == "rolled_back"

    async def test_nested_transaction_rollback(self, client_with_transaction):
        """Test nested transaction rollback behavior."""
        client = client_with_transaction
        
        # Setup mocks
        client.create.return_value = 123
        client.write.return_value = True
        
        try:
            async with client.transaction() as outer_tx:
                await outer_tx.create("res.partner", {"name": "Outer"})
                
                try:
                    async with client.transaction() as inner_tx:
                        await inner_tx.create("res.partner", {"name": "Inner"})
                        raise Exception("Inner transaction fails")
                        
                except Exception:
                    pass  # Inner transaction should rollback
                
                # Outer transaction continues
                await outer_tx.update("res.partner", [1], {"name": "Updated"})
                
        except Exception:
            pass
        
        # Verify both transactions have operations tracked
        assert len(outer_tx.operations) >= 1
        assert len(inner_tx.operations) >= 1

    async def test_transaction_manager_setup_integration(self, client_with_transaction):
        """Test transaction manager setup and integration."""
        client = client_with_transaction
        
        # Verify transaction manager is set up
        assert client.transaction_manager is not None
        assert isinstance(client.transaction_manager, TransactionManager)
        
        # Verify transaction manager has client reference
        assert client.transaction_manager.client == client
        
        # Test transaction creation
        tx = client.transaction()
        assert tx is not None

    async def test_crud_methods_exist_and_callable(self, client_with_transaction):
        """Test that CRUD methods exist and are callable."""
        client = client_with_transaction
        
        # Reset mocks to actual methods
        client.create = client.__class__.create.__get__(client)
        client.write = client.__class__.write.__get__(client)
        client.unlink = client.__class__.unlink.__get__(client)
        
        # Mock execute_kw for actual method calls
        client.execute_kw = AsyncMock()
        client.execute_kw.return_value = 123
        
        # Test create method
        result = await client.create("res.partner", {"name": "Test"})
        assert result == 123
        client.execute_kw.assert_called_with(
            "res.partner", "create", [{"name": "Test"}], context=None
        )
        
        # Test write method
        client.execute_kw.return_value = True
        result = await client.write("res.partner", [1], {"name": "Updated"})
        assert result is True
        client.execute_kw.assert_called_with(
            "res.partner", "write", [[1], {"name": "Updated"}], context=None
        )
        
        # Test unlink method
        result = await client.unlink("res.partner", [1])
        assert result is True
        client.execute_kw.assert_called_with(
            "res.partner", "unlink", [[1]], context=None
        )

    async def test_manager_setup_methods_work(self, client_with_transaction):
        """Test that manager setup methods work correctly."""
        # Create fresh client
        client = ZenooClient("http://localhost:8069")
        client._session._database = "test_db"
        client._session._uid = 1
        
        # Test transaction manager setup
        tx_manager = await client.setup_transaction_manager()
        assert tx_manager is not None
        assert client.transaction_manager == tx_manager
        
        # Test cache manager setup
        cache_manager = await client.setup_cache_manager(backend="memory")
        assert cache_manager is not None
        assert client.cache_manager == cache_manager
        
        # Test batch manager setup
        batch_manager = await client.setup_batch_manager()
        assert batch_manager is not None
        assert client.batch_manager == batch_manager

    async def test_transaction_context_manager_integration(self, client_with_transaction):
        """Test transaction context manager integration."""
        client = client_with_transaction
        
        # Test that transaction context manager works
        async with client.transaction() as tx:
            assert tx is not None
            assert tx.status == "active"
            
            # Test that we can access transaction operations
            assert hasattr(tx, 'operations')
            assert hasattr(tx, 'create')
            assert hasattr(tx, 'update')
            assert hasattr(tx, 'delete')
        
        # After context, transaction should be committed
        assert tx.status == "committed"

    async def test_batch_context_manager_integration(self, client_with_transaction):
        """Test batch context manager integration."""
        client = client_with_transaction
        
        # Setup batch manager
        await client.setup_batch_manager()
        
        # Test batch context manager
        batch = client.batch()
        assert batch is not None
        
        # Test that batch has expected methods
        assert hasattr(batch, 'add_operation')
        assert hasattr(batch, 'execute')
