"""
Performance benchmarks for Zenoo-RPC Phase 3 components.

This module provides comprehensive performance benchmarks for:
- Transaction management overhead
- Cache performance (hit/miss ratios, latency)
- Batch operation throughput
- Connection pooling efficiency
- Integrated component performance
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any

from src.zenoo_rpc.client import ZenooClient
from src.zenoo_rpc.transaction.manager import TransactionManager
from src.zenoo_rpc.cache.manager import CacheManager
from src.zenoo_rpc.batch.manager import BatchManager
from src.zenoo_rpc.cache.backends import MemoryCache, RedisCache
from src.zenoo_rpc.batch.operations import CreateOperation, UpdateOperation


# Configure pytest-asyncio for session-scoped event loop
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def benchmark_client():
    """Session-scoped client for benchmarking."""
    client = AsyncMock(spec=ZenooClient)
    
    # Mock fast responses for benchmarking
    client.execute_kw = AsyncMock(return_value=[1, 2, 3, 4, 5])
    client.search_read = AsyncMock(return_value=[
        {"id": i, "name": f"Record {i}"} for i in range(1, 101)
    ])
    
    # Setup managers
    client.transaction_manager = TransactionManager(client)
    client.cache_manager = CacheManager()
    await client.cache_manager.setup_memory_cache(max_size=10000, default_ttl=3600)
    client.batch_manager = BatchManager(client, max_chunk_size=100, max_concurrency=10)
    
    yield client
    
    # Cleanup
    await client.cache_manager.close()


class TestTransactionPerformance:
    """Benchmark transaction management performance."""
    
    async def test_transaction_creation_overhead(self, benchmark_client, benchmark):
        """Benchmark transaction creation and cleanup overhead."""
        client = benchmark_client

        def create_transaction_sync():
            # Create event loop for sync benchmark
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def create_transaction():
                    async with client.transaction_manager.transaction() as tx:
                        tx.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])
                        return tx.id

                return loop.run_until_complete(create_transaction())
            finally:
                loop.close()

        # Benchmark transaction creation
        result = benchmark(create_transaction_sync)
        assert result is not None

    async def test_transaction_operation_tracking(self, benchmark_client, benchmark):
        """Benchmark operation tracking performance."""
        client = benchmark_client
        
        async def track_operations():
            async with client.transaction_manager.transaction() as tx:
                # Add multiple operations
                for i in range(100):
                    tx.add_operation(
                        "create",
                        "res.partner",
                        record_ids=[i],
                        created_ids=[i],
                        data={"name": f"Partner {i}"}
                    )
                return len(tx.operations)
        
        result = await benchmark(track_operations)
        assert result == 100

    async def test_nested_transaction_performance(self, benchmark_client, benchmark):
        """Benchmark nested transaction performance."""
        client = benchmark_client
        
        async def nested_transactions():
            async with client.transaction_manager.transaction() as tx1:
                tx1.add_operation("create", "res.partner", record_ids=[1], created_ids=[1])
                
                savepoint_id = await tx1.create_savepoint("sp1")
                tx1.add_operation("update", "res.partner", record_ids=[1])
                
                await tx1.release_savepoint(savepoint_id)
                return tx1.id
        
        result = await benchmark(nested_transactions)
        assert result is not None


class TestCachePerformance:
    """Benchmark cache system performance."""
    
    async def test_memory_cache_set_performance(self, benchmark_client, benchmark):
        """Benchmark memory cache set operations."""
        cache_manager = benchmark_client.cache_manager
        
        async def cache_set_operations():
            for i in range(1000):
                await cache_manager.set(f"key_{i}", {"id": i, "data": f"value_{i}"}, ttl=3600)
            return 1000
        
        result = await benchmark(cache_set_operations)
        assert result == 1000

    async def test_memory_cache_get_performance(self, benchmark_client, benchmark):
        """Benchmark memory cache get operations."""
        cache_manager = benchmark_client.cache_manager
        
        # Pre-populate cache
        for i in range(1000):
            await cache_manager.set(f"bench_key_{i}", {"id": i, "data": f"value_{i}"}, ttl=3600)
        
        async def cache_get_operations():
            hits = 0
            for i in range(1000):
                result = await cache_manager.get(f"bench_key_{i}")
                if result is not None:
                    hits += 1
            return hits
        
        result = await benchmark(cache_get_operations)
        assert result == 1000  # All should be hits

    async def test_cache_hit_miss_ratio(self, benchmark_client, benchmark):
        """Benchmark cache hit/miss performance characteristics."""
        cache_manager = benchmark_client.cache_manager
        
        # Pre-populate 50% of keys
        for i in range(0, 1000, 2):
            await cache_manager.set(f"ratio_key_{i}", f"value_{i}", ttl=3600)
        
        async def mixed_cache_operations():
            hits = 0
            misses = 0
            for i in range(1000):
                result = await cache_manager.get(f"ratio_key_{i}")
                if result is not None:
                    hits += 1
                else:
                    misses += 1
            return {"hits": hits, "misses": misses}
        
        result = await benchmark(mixed_cache_operations)
        assert result["hits"] == 500
        assert result["misses"] == 500

    async def test_cache_invalidation_performance(self, benchmark_client, benchmark):
        """Benchmark cache invalidation performance."""
        cache_manager = benchmark_client.cache_manager
        
        # Pre-populate cache with pattern-based keys
        for i in range(1000):
            await cache_manager.set(f"res.partner:{i}", {"id": i}, ttl=3600)
            await cache_manager.set(f"res.company:{i}", {"id": i}, ttl=3600)
        
        async def invalidation_operations():
            # Invalidate by pattern
            partner_count = await cache_manager.invalidate_pattern("res.partner:*")
            company_count = await cache_manager.invalidate_pattern("res.company:*")
            return partner_count + company_count
        
        result = await benchmark(invalidation_operations)
        assert result == 2000


class TestBatchPerformance:
    """Benchmark batch operation performance."""
    
    async def test_batch_creation_performance(self, benchmark_client, benchmark):
        """Benchmark batch creation with many operations."""
        client = benchmark_client
        
        async def create_large_batch():
            batch = client.batch_manager.create_batch("perf_batch")
            
            # Add 1000 create operations
            for i in range(1000):
                operation = CreateOperation(
                    model="res.partner",
                    data={"name": f"Batch Partner {i}", "email": f"partner{i}@example.com"}
                )
                batch.add_operation(operation)
            
            return len(batch.operations)
        
        result = await benchmark(create_large_batch)
        assert result == 1000

    async def test_batch_execution_throughput(self, benchmark_client, benchmark):
        """Benchmark batch execution throughput."""
        client = benchmark_client
        
        # Mock batch execution to return quickly
        client.execute_kw.return_value = list(range(1, 101))  # 100 IDs
        
        async def execute_batch_operations():
            batch = client.batch_manager.create_batch("throughput_batch")
            
            # Add 100 operations
            for i in range(100):
                operation = CreateOperation(
                    model="res.partner",
                    data={"name": f"Throughput Partner {i}"}
                )
                batch.add_operation(operation)
            
            # Execute batch
            results = await client.batch_manager.execute_batch(batch)
            return len(results.get("results", []))
        
        result = await benchmark(execute_batch_operations)
        assert result >= 0  # Should complete successfully

    async def test_concurrent_batch_performance(self, benchmark_client, benchmark):
        """Benchmark concurrent batch execution."""
        client = benchmark_client
        
        async def concurrent_batches():
            async def single_batch(batch_id):
                batch = client.batch_manager.create_batch(f"concurrent_batch_{batch_id}")
                
                for i in range(50):
                    operation = CreateOperation(
                        model="res.partner",
                        data={"name": f"Concurrent Partner {batch_id}_{i}"}
                    )
                    batch.add_operation(operation)
                
                results = await client.batch_manager.execute_batch(batch)
                return batch_id
            
            # Run 10 batches concurrently
            tasks = [single_batch(i) for i in range(10)]
            completed = await asyncio.gather(*tasks)
            return len(completed)
        
        result = await benchmark(concurrent_batches)
        assert result == 10


class TestIntegratedPerformance:
    """Benchmark integrated component performance."""
    
    async def test_transaction_with_cache_performance(self, benchmark_client, benchmark):
        """Benchmark transaction performance with cache integration."""
        client = benchmark_client
        
        async def transaction_with_cache():
            # Pre-populate cache
            await client.cache_manager.set("perf_data", {"cached": True}, ttl=3600)
            
            async with client.transaction_manager.transaction() as tx:
                # Check cache
                cached_data = await client.cache_manager.get("perf_data")
                
                # Add operations
                for i in range(50):
                    tx.add_operation(
                        "create",
                        "res.partner",
                        record_ids=[i],
                        created_ids=[i]
                    )
                
                return len(tx.operations)
        
        result = await benchmark(transaction_with_cache)
        assert result == 50

    async def test_full_integration_workflow(self, benchmark_client, benchmark):
        """Benchmark complete workflow with all components."""
        client = benchmark_client
        
        async def full_workflow():
            # 1. Cache some reference data
            await client.cache_manager.set("countries", [{"id": 1, "name": "USA"}], ttl=3600)
            
            # 2. Start transaction
            async with client.transaction_manager.transaction() as tx:
                # 3. Get cached data
                countries = await client.cache_manager.get("countries")
                
                # 4. Create batch operations
                batch = client.batch_manager.create_batch("workflow_batch")
                
                for i in range(20):
                    operation = CreateOperation(
                        model="res.partner",
                        data={
                            "name": f"Workflow Partner {i}",
                            "country_id": countries[0]["id"] if countries else 1
                        }
                    )
                    batch.add_operation(operation)
                
                # 5. Execute batch within transaction
                results = await client.batch_manager.execute_batch(batch)
                
                # 6. Track operations in transaction
                for i in range(20):
                    tx.add_operation("create", "res.partner", record_ids=[i], created_ids=[i])
                
                return {
                    "cached_countries": len(countries) if countries else 0,
                    "batch_operations": len(batch.operations),
                    "transaction_operations": len(tx.operations)
                }
        
        result = await benchmark(full_workflow)
        assert result["cached_countries"] == 1
        assert result["batch_operations"] == 20
        assert result["transaction_operations"] == 20


class TestMemoryUsagePatterns:
    """Test memory usage patterns for performance optimization."""
    
    async def test_cache_memory_efficiency(self, benchmark_client, benchmark):
        """Test cache memory usage patterns."""
        cache_manager = benchmark_client.cache_manager
        
        async def memory_usage_test():
            # Store increasingly large objects
            for i in range(100):
                large_object = {
                    "id": i,
                    "data": "x" * (i * 100),  # Increasing size
                    "metadata": {"size": i * 100}
                }
                await cache_manager.set(f"large_obj_{i}", large_object, ttl=3600)
            
            # Get cache statistics
            stats = await cache_manager.get_stats()
            return stats.get("size", 0)
        
        result = await benchmark(memory_usage_test)
        assert result >= 0

    async def test_transaction_memory_scaling(self, benchmark_client, benchmark):
        """Test transaction memory usage with many operations."""
        client = benchmark_client
        
        async def memory_scaling_test():
            async with client.transaction_manager.transaction() as tx:
                # Add many operations with varying data sizes
                for i in range(500):
                    tx.add_operation(
                        "create",
                        "res.partner",
                        record_ids=[i],
                        created_ids=[i],
                        data={
                            "name": f"Memory Test Partner {i}",
                            "description": "x" * (i % 1000),  # Varying sizes
                            "metadata": {"index": i}
                        }
                    )
                
                return len(tx.operations)
        
        result = await benchmark(memory_scaling_test)
        assert result == 500
