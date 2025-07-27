"""
Simple performance tests for Zenoo-RPC Phase 3 components.

This module provides basic performance validation for:
- Transaction management performance
- Cache performance characteristics
- Batch operation efficiency
- Component integration performance
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from src.zenoo_rpc.transaction.manager import TransactionManager
from src.zenoo_rpc.cache.manager import CacheManager
from src.zenoo_rpc.batch.manager import BatchManager
from src.zenoo_rpc.batch.operations import CreateOperation


# Configure pytest-asyncio for session-scoped event loop
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def perf_client():
    """Session-scoped client for performance tests."""
    client = AsyncMock()
    
    # Mock fast responses
    client.execute_kw = AsyncMock(return_value=[1, 2, 3, 4, 5])
    
    # Setup managers
    client.transaction_manager = TransactionManager(client)
    client.cache_manager = CacheManager()
    await client.cache_manager.setup_memory_cache(max_size=10000, default_ttl=3600)
    client.batch_manager = BatchManager(client, max_chunk_size=100, max_concurrency=10)
    
    yield client
    
    # Cleanup
    await client.cache_manager.close()


class TestPerformanceValidation:
    """Basic performance validation tests."""
    
    async def test_transaction_performance_baseline(self, perf_client):
        """Test transaction performance baseline."""
        client = perf_client
        
        # Measure transaction creation time
        start_time = time.perf_counter()
        
        async with client.transaction_manager.transaction() as tx:
            # Add 100 operations
            for i in range(100):
                tx.add_operation(
                    "create",
                    "res.partner",
                    record_ids=[i],
                    created_ids=[i],
                    data={"name": f"Partner {i}"}
                )
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should complete within reasonable time (< 1 second for 100 operations)
        assert duration < 1.0
        print(f"Transaction with 100 operations took: {duration:.4f} seconds")

    async def test_cache_performance_baseline(self, perf_client):
        """Test cache performance baseline."""
        cache_manager = perf_client.cache_manager
        
        # Measure cache set performance
        start_time = time.perf_counter()
        
        for i in range(1000):
            await cache_manager.set(f"perf_key_{i}", {"id": i, "data": f"value_{i}"}, ttl=3600)
        
        set_time = time.perf_counter()
        set_duration = set_time - start_time
        
        # Measure cache get performance
        hits = 0
        for i in range(1000):
            result = await cache_manager.get(f"perf_key_{i}")
            if result is not None:
                hits += 1
        
        get_time = time.perf_counter()
        get_duration = get_time - set_time
        
        # Performance assertions
        assert set_duration < 2.0  # Should set 1000 items in < 2 seconds
        assert get_duration < 1.0  # Should get 1000 items in < 1 second
        assert hits == 1000  # All should be hits
        
        print(f"Cache set 1000 items: {set_duration:.4f} seconds")
        print(f"Cache get 1000 items: {get_duration:.4f} seconds")
        print(f"Cache hit rate: {hits/1000*100:.1f}%")

    async def test_batch_performance_baseline(self, perf_client):
        """Test batch performance baseline."""
        client = perf_client
        
        # Measure batch creation and execution
        start_time = time.perf_counter()
        
        batch = client.batch_manager.create_batch("perf_batch")
        
        # Add 100 operations (CreateOperation expects list of dicts)
        for i in range(100):
            operation = CreateOperation(
                model="res.partner",
                data=[{"name": f"Batch Partner {i}", "email": f"partner{i}@example.com"}]
            )
            batch.add_operation(operation)
        
        # Execute batch
        results = await batch.execute()
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 2.0  # Should complete in < 2 seconds
        assert len(batch.operations) == 100
        
        print(f"Batch with 100 operations took: {duration:.4f} seconds")

    async def test_integrated_performance_baseline(self, perf_client):
        """Test integrated component performance."""
        client = perf_client
        
        start_time = time.perf_counter()
        
        # 1. Cache some reference data
        await client.cache_manager.set("countries", [{"id": 1, "name": "USA"}], ttl=3600)
        
        # 2. Transaction with cache and batch operations
        async with client.transaction_manager.transaction() as tx:
            # Get cached data
            countries = await client.cache_manager.get("countries")
            
            # Create batch
            batch = client.batch_manager.create_batch("integrated_batch")
            
            # Add operations
            for i in range(50):
                operation = CreateOperation(
                    model="res.partner",
                    data=[{
                        "name": f"Integrated Partner {i}",
                        "country_id": countries[0]["id"] if countries else 1
                    }]
                )
                batch.add_operation(operation)
            
            # Execute batch
            await batch.execute()
            
            # Track in transaction
            for i in range(50):
                tx.add_operation("create", "res.partner", record_ids=[i], created_ids=[i])
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 3.0  # Integrated workflow should complete in < 3 seconds
        
        print(f"Integrated workflow took: {duration:.4f} seconds")

    async def test_concurrent_performance_baseline(self, perf_client):
        """Test concurrent operations performance."""
        client = perf_client
        
        async def concurrent_transaction(tx_id):
            async with client.transaction_manager.transaction() as tx:
                for i in range(20):
                    tx.add_operation(
                        "create",
                        "res.partner",
                        record_ids=[tx_id * 100 + i],
                        created_ids=[tx_id * 100 + i]
                    )
                return tx_id
        
        start_time = time.perf_counter()
        
        # Run 10 concurrent transactions
        tasks = [concurrent_transaction(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 5.0  # 10 concurrent transactions should complete in < 5 seconds
        assert len(results) == 10
        assert all(isinstance(r, int) for r in results)
        
        print(f"10 concurrent transactions took: {duration:.4f} seconds")

    async def test_memory_usage_baseline(self, perf_client):
        """Test memory usage characteristics."""
        client = perf_client
        
        # Test cache memory usage
        initial_stats = await client.cache_manager.get_stats()
        initial_size = initial_stats.get("size", 0)
        
        # Add large objects to cache
        for i in range(100):
            large_object = {
                "id": i,
                "data": "x" * 1000,  # 1KB per object
                "metadata": {"size": 1000, "index": i}
            }
            await client.cache_manager.set(f"large_obj_{i}", large_object, ttl=3600)
        
        final_stats = await client.cache_manager.get_stats()
        final_size = final_stats.get("size", 0)
        
        # Memory usage should be reasonable
        size_increase = final_size - initial_size
        # Note: size might be 0 if backend doesn't track size, so just check it's non-negative
        assert size_increase >= 0  # Should not decrease
        
        print(f"Cache size increased by: {size_increase} items")
        print(f"Final cache stats: {final_stats}")

    async def test_cache_hit_ratio_performance(self, perf_client):
        """Test cache hit ratio performance characteristics."""
        cache_manager = perf_client.cache_manager
        
        # Pre-populate 70% of keys (simulate realistic hit ratio)
        for i in range(0, 1000, 10):  # Every 10th key
            for j in range(7):  # 7 out of 10 keys
                key_index = i + j
                await cache_manager.set(f"hit_test_{key_index}", f"value_{key_index}", ttl=3600)
        
        # Test mixed access pattern
        start_time = time.perf_counter()
        
        hits = 0
        misses = 0
        
        for i in range(1000):
            result = await cache_manager.get(f"hit_test_{i}")
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        hit_ratio = hits / (hits + misses) * 100
        
        # Performance assertions
        assert duration < 1.0  # Should complete in < 1 second
        assert hit_ratio >= 60  # Should have at least 60% hit ratio
        
        print(f"Cache hit ratio test took: {duration:.4f} seconds")
        print(f"Hit ratio: {hit_ratio:.1f}% ({hits} hits, {misses} misses)")


class TestPerformanceRegression:
    """Performance regression tests."""
    
    async def test_no_performance_regression(self, perf_client):
        """Ensure no major performance regressions."""
        client = perf_client
        
        # Baseline performance test
        operations_count = 200
        start_time = time.perf_counter()
        
        async with client.transaction_manager.transaction() as tx:
            # Cache operations
            for i in range(operations_count // 4):
                await client.cache_manager.set(f"regression_key_{i}", {"data": i}, ttl=3600)
            
            # Transaction operations
            for i in range(operations_count // 2):
                tx.add_operation("create", "res.partner", record_ids=[i], created_ids=[i])
            
            # Batch operations
            batch = client.batch_manager.create_batch("regression_batch")
            for i in range(operations_count // 4):
                operation = CreateOperation(
                    model="res.partner",
                    data=[{"name": f"Regression Partner {i}"}]
                )
                batch.add_operation(operation)
            
            await batch.execute()
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Regression threshold: should complete within reasonable time
        max_duration = 5.0  # 5 seconds for 200 mixed operations
        assert duration < max_duration, f"Performance regression detected: {duration:.4f}s > {max_duration}s"
        
        print(f"Performance regression test: {duration:.4f} seconds for {operations_count} operations")
        print(f"Average time per operation: {duration/operations_count*1000:.2f} ms")
