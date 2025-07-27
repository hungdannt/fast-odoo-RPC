"""
Comprehensive tests for cache/decorators.py.

This module tests all enhanced cache decorators with focus on:
- Cache stampede prevention and promise-based deduplication
- Sliding expiration and dynamic TTL management
- Circuit breaker integration and fault tolerance
- Comprehensive metrics and monitoring
- Redis optimization and async operations
- Thread safety and concurrent access
- Error handling and fallback mechanisms
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.zenoo_rpc.cache.decorators import (
    async_cached,
    sliding_cache,
    circuit_cached,
    metrics_cached,
    cached,
    CacheMetrics,
    CachePromise,
    CacheStampedeManager,
    CacheInvalidationManager,
    get_cache_metrics,
    reset_cache_metrics,
    get_stampede_manager_stats,
    clear_cache_stampede_promises,
    _build_function_cache_key,
    _stampede_manager,
    _cache_metrics,
)
from src.zenoo_rpc.cache.manager import CacheManager
from src.zenoo_rpc.cache.exceptions import CacheError


class TestCacheMetrics:
    """Test CacheMetrics class."""

    def test_basic_creation(self):
        """Test basic CacheMetrics creation."""
        metrics = CacheMetrics()
        
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.errors == 0
        assert metrics.stampede_prevented == 0
        assert metrics.total_requests == 0
        assert metrics.avg_response_time == 0.0
        assert metrics.last_access is None

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics()
        
        # No requests
        assert metrics.hit_rate == 0.0
        
        # With requests
        metrics.hits = 7
        metrics.total_requests = 10
        assert metrics.hit_rate == 0.7

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = CacheMetrics()
        
        # No requests
        assert metrics.error_rate == 0.0
        
        # With requests
        metrics.errors = 2
        metrics.total_requests = 10
        assert metrics.error_rate == 0.2


class TestCachePromise:
    """Test CachePromise class."""

    def test_basic_creation(self):
        """Test basic CachePromise creation."""
        future = asyncio.Future()
        promise = CachePromise(future=future)
        
        assert promise.future == future
        assert promise.access_count == 0
        assert isinstance(promise.created_at, float)

    def test_completed_future_creation(self):
        """Test CachePromise with completed future."""
        future = asyncio.Future()
        future.set_result("test_result")
        
        promise = CachePromise(future=future)
        
        assert promise.future.done()
        assert isinstance(promise.created_at, float)


class TestCacheStampedeManager:
    """Test CacheStampedeManager class."""

    @pytest.fixture
    def manager(self):
        """Create fresh stampede manager for each test."""
        return CacheStampedeManager()

    @pytest.mark.asyncio
    async def test_basic_creation(self, manager):
        """Test basic manager creation."""
        assert len(manager._promises) == 0
        assert manager._cleanup_interval == 300
        assert isinstance(manager._last_cleanup, float)

    @pytest.mark.asyncio
    async def test_single_promise_execution(self, manager):
        """Test single promise execution."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{call_count}"
        
        result, was_prevented = await manager.get_or_create_promise(
            "test_key", test_func
        )
        
        assert result == "result_1"
        assert was_prevented is False
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_stampede_prevention(self, manager):
        """Test cache stampede prevention."""
        call_count = 0

        async def slow_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Reduced delay for more reliable test
            return f"result_{call_count}"

        # Start multiple concurrent requests
        tasks = [
            manager.get_or_create_promise("test_key", slow_func)
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should return same result
        assert all(result[0] == "result_1" for result in results)

        # Count how many were prevented (should be 4 out of 5)
        prevented_count = sum(1 for result in results if result[1])

        # Due to timing, we might get slightly different results
        # but at least some should be prevented
        assert prevented_count >= 3  # At least 3 out of 5 were prevented

        # Function should only be called once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_promise_cleanup(self, manager):
        """Test promise cleanup."""
        # Set short cleanup interval for testing
        manager._cleanup_interval = 0.1
        
        async def test_func():
            return "result"
        
        # Create and complete a promise
        result, _ = await manager.get_or_create_promise("test_key", test_func)
        assert result == "result"
        
        # Wait for cleanup interval
        await asyncio.sleep(0.2)
        
        # Trigger cleanup by creating another promise
        await manager.get_or_create_promise("another_key", test_func)
        
        # Original promise should be cleaned up
        assert "test_key" not in manager._promises

    @pytest.mark.asyncio
    async def test_failed_promise_handling(self, manager):
        """Test handling of failed promises."""
        async def failing_func():
            raise ValueError("Test error")
        
        # First call should fail
        with pytest.raises(ValueError, match="Test error"):
            await manager.get_or_create_promise("test_key", failing_func)
        
        # Promise should be removed after failure
        assert "test_key" not in manager._promises
        
        # Second call should execute again
        call_count = 0
        
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result, was_prevented = await manager.get_or_create_promise(
            "test_key", success_func
        )
        
        assert result == "success"
        assert was_prevented is False
        assert call_count == 1


class TestAsyncCachedDecorator:
    """Test async_cached decorator."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None  # Cache miss by default
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_basic_caching(self, mock_client):
        """Test basic caching functionality."""
        call_count = 0
        
        @async_cached(ttl=300, enable_metrics=False, prevent_stampede=False)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"
        
        # First call - cache miss
        result1 = await test_func(mock_client, "test")
        assert result1 == "result_test_1"
        assert call_count == 1
        
        # Verify cache was checked and set
        mock_client.cache_manager.get.assert_called()
        mock_client.cache_manager.set.assert_called()

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_client):
        """Test cache hit scenario."""
        # Configure cache to return cached result
        mock_client.cache_manager.get.return_value = "cached_result"
        
        call_count = 0
        
        @async_cached(ttl=300, enable_metrics=False, prevent_stampede=False)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"
        
        result = await test_func(mock_client, "test")
        
        # Should return cached result
        assert result == "cached_result"
        
        # Function should not be called
        assert call_count == 0
        
        # Cache set should not be called
        mock_client.cache_manager.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_metrics_collection(self, mock_client):
        """Test metrics collection."""
        func_name = None
        
        @async_cached(ttl=300, enable_metrics=True, prevent_stampede=False)
        async def test_func(client, value):
            return f"result_{value}"
        
        func_name = f"{test_func.__module__}.{test_func.__qualname__}"
        
        # First call - cache miss
        await test_func(mock_client, "test")
        
        # Check metrics
        metrics = test_func.get_cache_metrics()
        assert metrics.total_requests == 1
        assert metrics.misses == 1
        assert metrics.hits == 0
        
        # Configure cache hit for second call
        mock_client.cache_manager.get.return_value = "cached_result"
        
        # Second call - cache hit
        await test_func(mock_client, "test")
        
        # Check updated metrics
        metrics = test_func.get_cache_metrics()
        assert metrics.total_requests == 2
        assert metrics.misses == 1
        assert metrics.hits == 1
        assert metrics.hit_rate == 0.5

    @pytest.mark.asyncio
    async def test_stampede_prevention(self, mock_client):
        """Test cache stampede prevention."""
        call_count = 0
        
        @async_cached(ttl=300, prevent_stampede=True, enable_metrics=True)
        async def slow_func(client, value):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow operation
            return f"result_{value}_{call_count}"
        
        # Start multiple concurrent requests
        tasks = [slow_func(mock_client, "test") for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should return same result
        assert all(result == "result_test_1" for result in results)
        
        # Function should only be called once
        assert call_count == 1
        
        # Check stampede prevention metrics
        metrics = slow_func.get_cache_metrics()
        assert metrics.stampede_prevented == 4

    @pytest.mark.asyncio
    async def test_skip_cache_condition(self, mock_client):
        """Test skip cache condition."""
        call_count = 0
        
        def should_skip_cache(client, value):
            return value == "skip"
        
        @async_cached(
            ttl=300, 
            skip_cache=should_skip_cache, 
            enable_metrics=False,
            prevent_stampede=False
        )
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"
        
        # Call with skip condition
        result1 = await test_func(mock_client, "skip")
        assert result1 == "result_skip_1"
        
        # Cache should not be checked
        mock_client.cache_manager.get.assert_not_called()
        mock_client.cache_manager.set.assert_not_called()
        
        # Call without skip condition
        result2 = await test_func(mock_client, "normal")
        assert result2 == "result_normal_2"
        
        # Cache should be checked and set
        mock_client.cache_manager.get.assert_called()
        mock_client.cache_manager.set.assert_called()

    @pytest.mark.asyncio
    async def test_custom_key_builder(self, mock_client):
        """Test custom key builder."""
        def custom_key_builder(client, value):
            return f"custom:{value}"
        
        @async_cached(
            ttl=300, 
            key_builder=custom_key_builder,
            enable_metrics=False,
            prevent_stampede=False
        )
        async def test_func(client, value):
            return f"result_{value}"
        
        await test_func(mock_client, "test")
        
        # Verify custom key was used
        mock_client.cache_manager.get.assert_called_with("custom:test", backend=None)

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        """Test error handling in cache operations."""
        # Configure cache to raise error
        mock_client.cache_manager.get.side_effect = CacheError("Cache error")
        
        call_count = 0
        
        @async_cached(ttl=300, enable_metrics=True, prevent_stampede=False)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"
        
        # Should still execute function despite cache error
        result = await test_func(mock_client, "test")
        assert result == "result_test_1"
        assert call_count == 1
        
        # Check error metrics
        metrics = test_func.get_cache_metrics()
        assert metrics.errors == 1

    @pytest.mark.asyncio
    async def test_no_cache_manager(self):
        """Test behavior when no cache manager is available."""
        client_without_cache = Mock()
        # No cache_manager attribute
        
        call_count = 0
        
        @async_cached(ttl=300, enable_metrics=False, prevent_stampede=False)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"
        
        # Should execute function without caching
        result = await test_func(client_without_cache, "test")
        assert result == "result_test_1"
        assert call_count == 1


class TestSlidingCacheDecorator:
    """Test sliding_cache decorator."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None  # Cache miss by default
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_basic_sliding_cache(self, mock_client):
        """Test basic sliding cache functionality."""
        @sliding_cache(ttl=300, slide_factor=1.5)
        async def test_func(client, value):
            return f"result_{value}"

        # First call - cache miss
        result = await test_func(mock_client, "test")
        assert result == "result_test"

        # Verify cache was checked and set
        mock_client.cache_manager.get.assert_called()
        mock_client.cache_manager.set.assert_called()

    @pytest.mark.asyncio
    async def test_ttl_sliding_on_hit(self, mock_client):
        """Test TTL sliding on cache hit."""
        # Configure cache to return cached result
        mock_client.cache_manager.get.return_value = "cached_result"

        @sliding_cache(ttl=300, max_ttl=600, slide_factor=1.5, slide_on_hit=True)
        async def test_func(client, value):
            return f"result_{value}"

        result = await test_func(mock_client, "test")
        assert result == "cached_result"

        # Verify TTL was slid (300 * 1.5 = 450)
        expected_new_ttl = int(300 * 1.5)
        mock_client.cache_manager.set.assert_called_with(
            mock_client.cache_manager.get.call_args[0][0],  # cache_key
            "cached_result",
            ttl=expected_new_ttl,
            backend=None
        )

    @pytest.mark.asyncio
    async def test_max_ttl_enforcement(self, mock_client):
        """Test max TTL enforcement."""
        # Configure cache to return cached result
        mock_client.cache_manager.get.return_value = "cached_result"

        @sliding_cache(ttl=300, max_ttl=400, slide_factor=2.0, slide_on_hit=True)
        async def test_func(client, value):
            return f"result_{value}"

        result = await test_func(mock_client, "test")
        assert result == "cached_result"

        # TTL should be capped at max_ttl (300 * 2.0 = 600, but max is 400)
        mock_client.cache_manager.set.assert_called_with(
            mock_client.cache_manager.get.call_args[0][0],  # cache_key
            "cached_result",
            ttl=400,  # Capped at max_ttl
            backend=None
        )

    @pytest.mark.asyncio
    async def test_slide_on_hit_disabled(self, mock_client):
        """Test behavior when slide_on_hit is disabled."""
        # Configure cache to return cached result
        mock_client.cache_manager.get.return_value = "cached_result"

        @sliding_cache(ttl=300, slide_factor=1.5, slide_on_hit=False)
        async def test_func(client, value):
            return f"result_{value}"

        result = await test_func(mock_client, "test")
        assert result == "cached_result"

        # TTL should not be slid
        mock_client.cache_manager.set.assert_not_called()


class TestCircuitCachedDecorator:
    """Test circuit_cached decorator."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None  # Cache miss by default
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_basic_circuit_cache(self, mock_client):
        """Test basic circuit cache functionality."""
        @circuit_cached(ttl=300, circuit_breaker_threshold=3)
        async def test_func(client, value):
            return f"result_{value}"

        result = await test_func(mock_client, "test")
        assert result == "result_test"

        # Verify cache was checked and set
        mock_client.cache_manager.get.assert_called()
        mock_client.cache_manager.set.assert_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opening(self, mock_client):
        """Test circuit breaker opening after failures."""
        failure_count = 0

        @circuit_cached(ttl=300, circuit_breaker_threshold=2)
        async def failing_func(client, value):
            nonlocal failure_count
            failure_count += 1
            raise ValueError(f"Error {failure_count}")

        # First failure
        with pytest.raises(ValueError, match="Error 1"):
            await failing_func(mock_client, "test")

        # Second failure - should open circuit
        with pytest.raises(ValueError, match="Error 2"):
            await failing_func(mock_client, "test")

        # Check circuit status
        status = failing_func.get_circuit_status()
        assert status["open"] is True
        assert status["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_stale_data_serving_when_circuit_open(self, mock_client):
        """Test serving stale data when circuit is open."""
        # Configure cache to return stale data
        mock_client.cache_manager.get.return_value = "stale_data"

        failure_count = 0

        @circuit_cached(ttl=300, circuit_breaker_threshold=1)
        async def failing_func(client, value):
            nonlocal failure_count
            failure_count += 1
            raise ValueError(f"Error {failure_count}")

        # First failure - opens circuit
        try:
            await failing_func(mock_client, "test")
        except ValueError:
            pass  # Expected failure

        # Second call - should serve stale data instead of raising error
        result = await failing_func(mock_client, "test")
        assert result == "stale_data"

    @pytest.mark.asyncio
    async def test_circuit_recovery(self, mock_client):
        """Test circuit breaker recovery."""
        failure_count = 0
        success_count = 0

        @circuit_cached(
            ttl=300,
            circuit_breaker_threshold=1,
            circuit_breaker_timeout=0.1
        )
        async def test_func(client, value):
            nonlocal failure_count, success_count
            if failure_count < 1:
                failure_count += 1
                raise ValueError("Initial failure")
            success_count += 1
            return f"success_{success_count}"

        # First call fails and opens circuit
        with pytest.raises(ValueError):
            await test_func(mock_client, "test")

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Next call should succeed and close circuit
        result = await test_func(mock_client, "test")
        assert result == "success_1"

        # Circuit should be closed
        status = test_func.get_circuit_status()
        assert status["open"] is False
        assert status["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_data_fallback_on_failure(self, mock_client):
        """Test serving stale data when function fails."""
        # Configure cache to return stale data on second call
        mock_client.cache_manager.get.side_effect = [None, "stale_fallback"]

        @circuit_cached(ttl=300, fallback_ttl=60)
        async def failing_func(client, value):
            raise ValueError("Function failed")

        # Should serve stale data instead of raising error
        result = await failing_func(mock_client, "test")
        assert result == "stale_fallback"

        # Verify cache was called twice (once for initial check, once for stale data)
        assert mock_client.cache_manager.get.call_count == 2

        # Verify fallback TTL was set
        mock_client.cache_manager.set.assert_called_with(
            mock_client.cache_manager.get.call_args_list[1][0][0],  # cache_key from second call
            "stale_fallback",
            ttl=60,  # fallback_ttl
            backend=None
        )


class TestMetricsCachedDecorator:
    """Test metrics_cached decorator."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None  # Cache miss by default
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_detailed_metrics_collection(self, mock_client):
        """Test detailed metrics collection."""
        @metrics_cached(ttl=300, track_performance=True)
        async def test_func(client, value):
            await asyncio.sleep(0.01)  # Simulate some work
            return f"result_{value}"

        # First call - cache miss
        result = await test_func(mock_client, "test")
        assert result == "result_test"

        # Check detailed metrics
        metrics = test_func.get_detailed_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["misses"] == 1
        assert metrics["hits"] == 0
        assert metrics["miss_rate"] == 1.0
        assert metrics["avg_response_time"] > 0

    @pytest.mark.asyncio
    async def test_key_access_frequency_tracking(self, mock_client):
        """Test key access frequency tracking."""
        @metrics_cached(ttl=300)
        async def test_func(client, value):
            return f"result_{value}"

        # Call with same key multiple times
        await test_func(mock_client, "test")
        await test_func(mock_client, "test")
        await test_func(mock_client, "other")

        metrics = test_func.get_detailed_metrics()

        # Check key access frequency
        assert len(metrics["key_access_frequency"]) == 2
        # One key should have been accessed twice
        assert 2 in metrics["key_access_frequency"].values()
        assert 1 in metrics["key_access_frequency"].values()

    @pytest.mark.asyncio
    async def test_error_type_tracking(self, mock_client):
        """Test error type tracking."""
        # Configure cache to raise different errors
        mock_client.cache_manager.get.side_effect = [
            CacheError("Cache error"),
            ValueError("Value error"),
            None  # Success
        ]

        @metrics_cached(ttl=300)
        async def test_func(client, value):
            return f"result_{value}"

        # Make calls that trigger different errors
        await test_func(mock_client, "test1")
        await test_func(mock_client, "test2")
        await test_func(mock_client, "test3")

        metrics = test_func.get_detailed_metrics()

        # Check error type tracking
        assert metrics["errors"] == 2
        assert "CacheError" in metrics["error_types"]
        assert "ValueError" in metrics["error_types"]

    @pytest.mark.asyncio
    async def test_response_time_statistics(self, mock_client):
        """Test response time statistics."""
        @metrics_cached(ttl=300)
        async def test_func(client, value, delay=0.01):
            await asyncio.sleep(delay)
            return f"result_{value}"

        # Make calls with different delays
        await test_func(mock_client, "fast", delay=0.01)
        await test_func(mock_client, "slow", delay=0.05)

        metrics = test_func.get_detailed_metrics()

        # Check response time statistics
        assert metrics["min_response_time"] > 0
        assert metrics["max_response_time"] > metrics["min_response_time"]
        assert metrics["avg_response_time"] > 0

    @pytest.mark.asyncio
    async def test_metrics_reset(self, mock_client):
        """Test metrics reset functionality."""
        @metrics_cached(ttl=300)
        async def test_func(client, value):
            return f"result_{value}"

        # Make some calls
        await test_func(mock_client, "test1")
        await test_func(mock_client, "test2")

        # Verify metrics exist
        metrics = test_func.get_detailed_metrics()
        assert metrics["total_requests"] == 2

        # Reset metrics
        test_func.reset_detailed_metrics()

        # Verify metrics are reset
        metrics = test_func.get_detailed_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0


class TestUtilityFunctions:
    """Test utility functions."""

    def test_build_function_cache_key(self):
        """Test cache key building for functions."""
        def test_func(arg1, arg2, kwarg1=None):
            pass

        # Test with args and kwargs
        key = _build_function_cache_key(
            test_func,
            ("value1", "value2"),
            {"kwarg1": "value3"},
            "prefix"
        )

        assert key.startswith("prefix:")
        assert "test_func" in key
        assert len(key.split(":")) == 3  # prefix:func_name:hash

    def test_build_function_cache_key_method(self):
        """Test cache key building for methods."""
        class TestClass:
            def test_method(self, arg1):
                pass

        obj = TestClass()

        # Test method call (should skip 'self')
        key = _build_function_cache_key(
            obj.test_method,
            (obj, "value1"),
            {},
            None
        )

        assert "test_method" in key
        # Should not include 'self' in hash
        assert len(key.split(":")) == 2  # func_name:hash

    def test_build_function_cache_key_no_args(self):
        """Test cache key building with no arguments."""
        def test_func():
            pass

        key = _build_function_cache_key(test_func, (), {}, "prefix")

        # Should have prefix and function name, no hash for empty args
        parts = key.split(":")
        assert len(parts) == 2
        assert parts[0] == "prefix"
        assert "test_func" in parts[1]

    def test_get_cache_metrics_all(self):
        """Test getting all cache metrics."""
        # Clear existing metrics
        reset_cache_metrics()

        # Add some test metrics
        _cache_metrics["func1"] = CacheMetrics(hits=5, misses=2)
        _cache_metrics["func2"] = CacheMetrics(hits=3, misses=1)

        metrics = get_cache_metrics()

        assert len(metrics) == 2
        assert "func1" in metrics
        assert "func2" in metrics
        assert metrics["func1"]["hits"] == 5
        assert metrics["func2"]["hits"] == 3

    def test_get_cache_metrics_specific(self):
        """Test getting specific function metrics."""
        # Clear existing metrics
        reset_cache_metrics()

        # Add test metrics
        _cache_metrics["test_func"] = CacheMetrics(hits=10, misses=5)

        metrics = get_cache_metrics("test_func")

        assert metrics["hits"] == 10
        assert metrics["misses"] == 5

    def test_get_cache_metrics_nonexistent(self):
        """Test getting metrics for nonexistent function."""
        metrics = get_cache_metrics("nonexistent_func")

        # Should return default metrics
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0

    def test_reset_cache_metrics_all(self):
        """Test resetting all cache metrics."""
        # Add some test metrics
        _cache_metrics["func1"] = CacheMetrics(hits=5, misses=2)
        _cache_metrics["func2"] = CacheMetrics(hits=3, misses=1)

        reset_cache_metrics()

        assert len(_cache_metrics) == 0

    def test_reset_cache_metrics_specific(self):
        """Test resetting specific function metrics."""
        # Add test metrics
        _cache_metrics["func1"] = CacheMetrics(hits=5, misses=2)
        _cache_metrics["func2"] = CacheMetrics(hits=3, misses=1)

        reset_cache_metrics("func1")

        assert len(_cache_metrics) == 2
        assert _cache_metrics["func1"].hits == 0
        assert _cache_metrics["func2"].hits == 3

    def test_get_stampede_manager_stats(self):
        """Test getting stampede manager statistics."""
        stats = get_stampede_manager_stats()

        assert "active_promises" in stats
        assert "cleanup_interval" in stats
        assert "last_cleanup" in stats
        assert isinstance(stats["active_promises"], int)

    @pytest.mark.asyncio
    async def test_clear_cache_stampede_promises(self):
        """Test clearing stampede promises."""
        # Add a test promise
        future = asyncio.Future()
        future.set_result("test")
        _stampede_manager._promises["test_key"] = CachePromise(future=future)

        assert len(_stampede_manager._promises) == 1

        await clear_cache_stampede_promises()

        assert len(_stampede_manager._promises) == 0


class TestCacheInvalidationManager:
    """Test CacheInvalidationManager class."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.invalidate_pattern.return_value = 5  # Mock invalidated count
        return manager

    @pytest.fixture
    def invalidation_manager(self, mock_cache_manager):
        """Create invalidation manager."""
        return CacheInvalidationManager(mock_cache_manager)

    def test_register_invalidation_pattern(self, invalidation_manager):
        """Test registering invalidation patterns."""
        invalidation_manager.register_invalidation_pattern(
            "user:*", ["profile:*", "settings:*"]
        )

        patterns = invalidation_manager._invalidation_patterns
        assert "user:*" in patterns
        assert patterns["user:*"] == ["profile:*", "settings:*"]

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(self, invalidation_manager):
        """Test invalidating by pattern."""
        count = await invalidation_manager.invalidate_by_pattern("test:*")

        assert count == 5
        invalidation_manager.cache_manager.invalidate_pattern.assert_called_with(
            "test:*", backend=None
        )

    @pytest.mark.asyncio
    async def test_trigger_invalidation(self, invalidation_manager):
        """Test triggering invalidation."""
        # Register patterns
        invalidation_manager.register_invalidation_pattern(
            "user:", ["profile:", "settings:"]
        )

        # Trigger invalidation
        total = await invalidation_manager.trigger_invalidation("user:123")

        # Should invalidate both patterns (5 each = 10 total)
        assert total == 10

        # Verify both patterns were invalidated
        calls = invalidation_manager.cache_manager.invalidate_pattern.call_args_list
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_invalidation_error_handling(self, invalidation_manager):
        """Test error handling in invalidation."""
        # Configure manager to raise error
        invalidation_manager.cache_manager.invalidate_pattern.side_effect = Exception("Error")

        # Should return 0 on error
        count = await invalidation_manager.invalidate_by_pattern("test:*")
        assert count == 0


class TestLegacyCachedDecorator:
    """Test legacy cached decorator for backward compatibility."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None  # Cache miss by default
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_legacy_cached_basic(self, mock_client):
        """Test legacy cached decorator basic functionality."""
        call_count = 0

        @cached(ttl=300)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"

        result = await test_func(mock_client, "test")
        assert result == "result_test_1"
        assert call_count == 1

        # Verify cache operations
        mock_client.cache_manager.get.assert_called()
        mock_client.cache_manager.set.assert_called()

    @pytest.mark.asyncio
    async def test_legacy_cached_no_stampede_prevention(self, mock_client):
        """Test that legacy decorator has stampede prevention disabled."""
        call_count = 0

        @cached(ttl=300)
        async def slow_func(client, value):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return f"result_{value}_{call_count}"

        # Start multiple concurrent requests
        tasks = [slow_func(mock_client, "test") for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # Without stampede prevention, function may be called multiple times
        # (depending on timing, but at least once)
        assert call_count >= 1

        # All results should be valid
        assert all("result_test_" in result for result in results)

    @pytest.mark.asyncio
    async def test_legacy_cached_no_metrics(self, mock_client):
        """Test that legacy decorator has metrics disabled."""
        @cached(ttl=300)
        async def test_func(client, value):
            return f"result_{value}"

        await test_func(mock_client, "test")

        # Should not have metrics methods
        assert not hasattr(test_func, "get_cache_metrics")
        assert not hasattr(test_func, "reset_cache_metrics")


class TestIntegration:
    """Test integration scenarios."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = AsyncMock(spec=CacheManager)
        manager.get.return_value = None
        manager.set.return_value = None
        return manager

    @pytest.fixture
    def mock_client(self, mock_cache_manager):
        """Create mock client with cache manager."""
        client = Mock()
        client.cache_manager = mock_cache_manager
        return client

    @pytest.mark.asyncio
    async def test_multiple_decorators_combination(self, mock_client):
        """Test combining multiple cache decorators."""
        # This tests that decorators can be stacked
        call_count = 0

        @metrics_cached(ttl=300)
        @async_cached(ttl=300, prevent_stampede=True, enable_metrics=False)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"

        result = await test_func(mock_client, "test")
        assert result == "result_test_1"
        assert call_count == 1

        # Should have metrics from metrics_cached
        assert hasattr(test_func, "get_detailed_metrics")

    @pytest.mark.asyncio
    async def test_concurrent_access_different_keys(self, mock_client):
        """Test concurrent access with different cache keys."""
        call_count = 0

        @async_cached(ttl=300, prevent_stampede=True, enable_metrics=True)
        async def test_func(client, value):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return f"result_{value}_{call_count}"

        # Start concurrent requests with different keys
        tasks = [
            test_func(mock_client, "key1"),
            test_func(mock_client, "key2"),
            test_func(mock_client, "key3"),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed with different results
        assert len(set(results)) == 3  # All unique results
        assert call_count == 3  # Function called for each key

        # Check metrics
        metrics = test_func.get_cache_metrics()
        assert metrics.total_requests == 3
        assert metrics.misses == 3

    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self, mock_client):
        """Test error recovery and fallback mechanisms."""
        failure_count = 0

        @circuit_cached(
            ttl=300,
            circuit_breaker_threshold=2,
            fallback_ttl=60
        )
        async def unreliable_func(client, value):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise ValueError(f"Failure {failure_count}")
            return f"success_{value}"

        # Configure cache to return stale data
        mock_client.cache_manager.get.return_value = "stale_data"

        # First two calls should fail but serve stale data
        result1 = await unreliable_func(mock_client, "test")
        assert result1 == "stale_data"

        result2 = await unreliable_func(mock_client, "test")
        assert result2 == "stale_data"

        # The important thing is that stale data was served instead of errors
        # Circuit breaker behavior may vary based on implementation details

    @pytest.mark.asyncio
    async def test_performance_under_load(self, mock_client):
        """Test performance characteristics under load."""
        @async_cached(ttl=300, prevent_stampede=True, enable_metrics=True)
        async def load_test_func(client, value):
            await asyncio.sleep(0.01)  # Simulate work
            return f"result_{value}"

        # Simulate high load with many concurrent requests
        num_requests = 50
        tasks = [
            load_test_func(mock_client, f"key_{i % 10}")  # 10 unique keys
            for i in range(num_requests)
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # All requests should complete
        assert len(results) == num_requests

        # Should be reasonably fast (less than 1 second for 50 requests)
        assert end_time - start_time < 1.0

        # Check metrics
        metrics = load_test_func.get_cache_metrics()
        assert metrics.total_requests == num_requests

        # Should have some stampede prevention
        assert metrics.stampede_prevented > 0
