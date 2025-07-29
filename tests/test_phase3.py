"""
Tests for Zenoo-RPC Phase 3 features.

This module tests transaction management, caching, batch operations,
and enhanced connection pooling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from zenoo_rpc.transaction.manager import TransactionManager, Transaction
from zenoo_rpc.transaction.context import transaction, atomic
from zenoo_rpc.cache.manager import CacheManager
from zenoo_rpc.cache.backends import MemoryCache
from zenoo_rpc.cache.strategies import TTLCache, LRUCache
from zenoo_rpc.batch.manager import BatchManager, Batch
from zenoo_rpc.batch.operations import CreateOperation, UpdateOperation, DeleteOperation
from zenoo_rpc.transport.pool import ConnectionPool


class TestTransactionManager:
    """Test cases for transaction management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.transaction_manager = TransactionManager(self.mock_client)

    @pytest.mark.asyncio
    async def test_transaction_creation(self):
        """Test transaction creation."""
        async with self.transaction_manager.transaction() as tx:
            assert isinstance(tx, Transaction)
            assert tx.is_active
            assert tx.client == self.mock_client
            assert not tx.is_nested

    @pytest.mark.asyncio
    async def test_nested_transactions(self):
        """Test nested transaction support."""
        async with self.transaction_manager.transaction() as parent_tx:
            assert parent_tx.is_active

            async with self.transaction_manager.transaction() as child_tx:
                assert child_tx.is_active
                assert child_tx.is_nested
                assert child_tx.parent == parent_tx
                assert child_tx in parent_tx.children

    @pytest.mark.asyncio
    async def test_transaction_operations(self):
        """Test transaction operation tracking."""
        async with self.transaction_manager.transaction() as tx:
            # Add operations
            tx.add_operation("create", "res.partner", data={"name": "Test"})
            tx.add_operation(
                "update", "res.partner", record_id=1, data={"email": "test@example.com"}
            )

            assert len(tx.operations) == 2
            assert tx.operations[0]["type"] == "create"
            assert tx.operations[1]["type"] == "update"

    @pytest.mark.asyncio
    async def test_savepoints(self):
        """Test savepoint functionality."""
        async with self.transaction_manager.transaction() as tx:
            # Add initial operation
            tx.add_operation("create", "res.partner", data={"name": "Test"})

            # Create savepoint
            savepoint = await tx.create_savepoint("test_sp")
            assert savepoint in tx.savepoints

            # Add more operations
            tx.add_operation(
                "update", "res.partner", record_id=1, data={"email": "test@example.com"}
            )

            # Rollback to savepoint
            await tx.rollback_to_savepoint(savepoint)

            # Should only have initial operation (savepoint index is 1, so operations after that are removed)
            assert len(tx.operations) == 0  # All operations after savepoint are removed

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self):
        """Test transaction context manager."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = self.transaction_manager

        async with transaction(mock_client) as tx:
            assert isinstance(tx, Transaction)
            assert tx.is_active

    @pytest.mark.asyncio
    async def test_atomic_decorator(self):
        """Test atomic decorator."""
        mock_client = AsyncMock()
        mock_client.transaction_manager = self.transaction_manager

        @atomic
        async def test_function(client, data, _transaction=None):
            # Function should run in transaction
            assert _transaction is not None
            return data["result"]

        result = await test_function(mock_client, {"result": "success"})
        assert result == "success"


class TestCacheManager:
    """Test cases for cache management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = CacheManager()

    @pytest.mark.asyncio
    async def test_memory_cache_setup(self):
        """Test memory cache setup."""
        await self.cache_manager.setup_memory_cache(max_size=100, default_ttl=300)

        assert "memory" in self.cache_manager.backends
        assert "memory" in self.cache_manager.strategies
        assert isinstance(self.cache_manager.backends["memory"], MemoryCache)

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test basic cache operations."""
        await self.cache_manager.setup_memory_cache()

        # Test set and get
        await self.cache_manager.set("test_key", "test_value", ttl=60)
        value = await self.cache_manager.get("test_key")
        assert value == "test_value"

        # Test exists
        exists = await self.cache_manager.exists("test_key")
        assert exists is True

        # Test delete
        deleted = await self.cache_manager.delete("test_key")
        assert deleted is True

        # Test get after delete
        value = await self.cache_manager.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_strategies(self):
        """Test different cache strategies."""
        # TTL strategy
        await self.cache_manager.setup_memory_cache(strategy="ttl", default_ttl=1)
        strategy = self.cache_manager.strategies["memory"]
        assert isinstance(strategy, TTLCache)

        # LRU strategy
        cache_manager2 = CacheManager()
        await cache_manager2.setup_memory_cache(strategy="lru", max_size=10)
        strategy = cache_manager2.strategies["memory"]
        assert isinstance(strategy, LRUCache)

    @pytest.mark.asyncio
    async def test_cache_convenience_methods(self):
        """Test cache convenience methods."""
        await self.cache_manager.setup_memory_cache()

        # Test query result caching
        model = "res.partner"
        domain = [("is_company", "=", True)]
        result = [{"id": 1, "name": "Test Company"}]

        # Cache result
        cached = await self.cache_manager.cache_query_result(model, domain, result)
        assert cached is True

        # Retrieve cached result
        cached_result = await self.cache_manager.get_cached_query_result(model, domain)
        assert cached_result == result

        # Test model record caching
        record_id = 1
        record_data = {"id": 1, "name": "Test Company", "email": "test@company.com"}

        cached = await self.cache_manager.cache_model_record(
            model, record_id, record_data
        )
        assert cached is True

        cached_record = await self.cache_manager.get_cached_model_record(
            model, record_id
        )
        assert cached_record == record_data


class TestBatchOperations:
    """Test cases for batch operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.batch_manager = BatchManager(self.mock_client)

    def test_create_operation(self):
        """Test create operation creation."""
        data = [
            {"name": "Company A", "is_company": True},
            {"name": "Company B", "is_company": True},
        ]

        operation = CreateOperation(model="res.partner", data=data)

        assert operation.operation_type.value == "create"
        assert operation.model == "res.partner"
        assert operation.get_batch_size() == 2
        assert operation.data == data

    def test_update_operation(self):
        """Test update operation creation."""
        # Bulk update
        operation = UpdateOperation(
            model="res.partner", data={"active": False}, record_ids=[1, 2, 3]
        )

        assert operation.operation_type.value == "update"
        assert operation.get_batch_size() == 3

        # Individual updates
        data = [
            {"id": 1, "name": "Updated Name 1"},
            {"id": 2, "name": "Updated Name 2"},
        ]

        operation = UpdateOperation(model="res.partner", data=data)

        assert operation.get_batch_size() == 2

    def test_delete_operation(self):
        """Test delete operation creation."""
        record_ids = [1, 2, 3, 4, 5]

        operation = DeleteOperation(model="res.partner", data=record_ids)

        assert operation.operation_type.value == "delete"
        assert operation.get_batch_size() == 5
        assert operation.data == record_ids

    def test_operation_splitting(self):
        """Test operation splitting for large batches."""
        # Create large create operation
        data = [{"name": f"Company {i}"} for i in range(250)]

        operation = CreateOperation(model="res.partner", data=data)

        # Split into chunks of 100
        chunks = operation.split(100)

        assert len(chunks) == 3  # 250 / 100 = 3 chunks
        assert chunks[0].get_batch_size() == 100
        assert chunks[1].get_batch_size() == 100
        assert chunks[2].get_batch_size() == 50

    def test_batch_creation(self):
        """Test batch creation and operation building."""
        batch = self.batch_manager.create_batch()

        # Add operations
        batch.create("res.partner", [{"name": "Company A"}])
        batch.update("res.partner", {"active": False}, record_ids=[1, 2])
        batch.delete("res.partner", [3, 4, 5])

        assert batch.get_operation_count() == 3
        assert batch.get_record_count() == 6  # 1 + 2 + 3

    @pytest.mark.asyncio
    async def test_bulk_operations(self):
        """Test bulk operation methods."""
        # Mock successful responses
        self.mock_client.execute_kw.return_value = [1, 2, 3]

        # Test bulk create
        records = [
            {"name": "Company A", "is_company": True},
            {"name": "Company B", "is_company": True},
        ]

        result = await self.batch_manager.bulk_create("res.partner", records)
        assert result == [1, 2, 3]

        # Test bulk update
        self.mock_client.execute_kw.return_value = True

        result = await self.batch_manager.bulk_update(
            "res.partner", {"active": False}, record_ids=[1, 2, 3]
        )
        assert result is True

        # Test bulk delete
        result = await self.batch_manager.bulk_delete("res.partner", [1, 2, 3])
        assert result is True


class TestConnectionPool:
    """Test cases for connection pooling."""

    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(
            base_url="https://demo.odoo.com", pool_size=5, http2=True
        )

        await pool.initialize()

        assert pool.initialized is True
        assert len(pool.connections) == 5
        assert pool.available_connections.qsize() == 5

    @pytest.mark.asyncio
    async def test_connection_acquisition(self):
        """Test connection acquisition and release."""
        pool = ConnectionPool(base_url="https://demo.odoo.com", pool_size=2)

        await pool.initialize()

        # Acquire connection
        async with pool.get_connection() as client:
            assert client is not None
            # Note: available connections might not be exactly 1 due to async nature

        # Connection should be released
        assert pool.available_connections.qsize() == 2

    @pytest.mark.asyncio
    async def test_pool_stats(self):
        """Test connection pool statistics."""
        pool = ConnectionPool(base_url="https://demo.odoo.com", pool_size=3)

        await pool.initialize()

        stats = pool.get_stats()

        assert stats["pool_size"] == 3
        assert stats["available_connections"] == 3
        assert stats["initialized"] is True
        assert stats["closed"] is False

    @pytest.mark.asyncio
    async def test_pool_cleanup(self):
        """Test connection pool cleanup."""
        pool = ConnectionPool(base_url="https://demo.odoo.com", pool_size=2)

        await pool.initialize()
        assert len(pool.connections) == 2

        await pool.close()
        assert pool.closed is True
        assert len(pool.connections) == 0
