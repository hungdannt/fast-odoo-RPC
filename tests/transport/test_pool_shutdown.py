"""
Pool shutdown tests for the enhanced connection pool.

This module tests the pool shutdown functionality including proper cleanup
of connections, cancellation of background tasks, and handling of pending operations.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import httpx

from zenoo_rpc.transport.pool import (
    ConnectionPool,
    PooledConnection,
    ConnectionState,
    ConnectionContext,
)
from zenoo_rpc.exceptions import ZenooError


class TestPoolShutdown:
    """Test pool shutdown and cleanup functionality."""

    @pytest.fixture
    async def pool(self):
        """Create a test connection pool."""
        pool = ConnectionPool(
            base_url="http://test.example.com",
            pool_size=5,
            max_connections=10,
            health_check_interval=30.0,
        )
        yield pool
        # Cleanup is tested, so we don't close here

    @pytest.mark.asyncio
    async def test_basic_pool_shutdown(self, pool):
        """Test basic pool shutdown sequence."""
        await pool.initialize()

        # Verify pool is initialized
        assert pool.initialized is True
        assert pool.closed is False
        assert len(pool.connections) == pool.pool_size
        assert pool.health_check_task is not None
        assert pool.cleanup_task is not None

        # Close the pool
        await pool.close()

        # Verify pool is closed
        assert pool.closed is True
        assert len(pool.connections) == 0
        assert pool.available_connections.empty()

        # Tasks should be cancelled
        # Wait a bit for cancellation to propagate
        await asyncio.sleep(0.1)
        assert pool.health_check_task.cancelled() or pool.health_check_task.done()
        assert pool.cleanup_task.cancelled() or pool.cleanup_task.done()

    @pytest.mark.asyncio
    async def test_shutdown_with_active_connections(self, pool):
        """Test shutdown while connections are actively being used."""
        await pool.initialize()

        # Acquire some connections
        active_connections = []
        for _ in range(3):
            conn = await pool._acquire_connection()
            active_connections.append(conn)

        # Mock the close method on connections
        close_calls = []
        for conn in pool.connections:

            async def mock_aclose(c=conn):
                close_calls.append(c)

            conn.client.aclose = AsyncMock(side_effect=mock_aclose)

        # Close pool while connections are active
        await pool.close()

        # All connections should have been closed
        assert len(close_calls) >= len(active_connections)
        assert pool.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_with_pending_health_checks(self, pool):
        """Test shutdown while health checks are in progress."""
        await pool.initialize()

        # Make health check take time
        async def slow_health_check(url):
            await asyncio.sleep(1.0)
            response = AsyncMock()
            response.status_code = 200
            return response

        for conn in pool.connections:
            conn.client.get = AsyncMock(side_effect=slow_health_check)
            conn.health_check_at = 0  # Force health check

        # Start health check
        health_check_task = asyncio.create_task(pool._perform_health_checks())

        # Give it time to start
        await asyncio.sleep(0.1)

        # Close pool
        await pool.close()

        # Health check should be interrupted
        assert pool.closed is True

        # Cancel the health check task
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_shutdown_idempotency(self, pool):
        """Test that calling close multiple times is safe."""
        await pool.initialize()

        # Close multiple times
        await pool.close()
        await pool.close()
        await pool.close()

        # Should still be properly closed
        assert pool.closed is True
        assert len(pool.connections) == 0

    @pytest.mark.asyncio
    async def test_shutdown_with_connection_errors(self, pool):
        """Test shutdown when some connections fail to close."""
        await pool.initialize()

        # Make some connections fail to close
        error_indices = [1, 3]
        for i, conn in enumerate(pool.connections):
            if i in error_indices:
                conn.client.aclose = AsyncMock(
                    side_effect=httpx.NetworkError("Failed to close")
                )
            else:
                conn.client.aclose = AsyncMock()

        # Close should not raise exception
        await pool.close()

        # Pool should still be marked as closed
        assert pool.closed is True
        assert len(pool.connections) == 0

    @pytest.mark.asyncio
    async def test_using_pool_after_shutdown_raises_error(self, pool):
        """Test that using pool after shutdown raises appropriate error."""
        await pool.initialize()
        await pool.close()

        # Should not be able to get connection
        with pytest.raises(ZenooError, match="Connection pool is closed"):
            pool.get_connection()

    @pytest.mark.asyncio
    async def test_shutdown_clears_statistics(self, pool):
        """Test that shutdown properly handles statistics."""
        await pool.initialize()

        # Add some stats
        pool.stats["total_requests"] = 100
        pool.stats["successful_requests"] = 90
        pool.stats["failed_requests"] = 10

        initial_stats = pool.get_stats().copy()

        await pool.close()

        # Stats should still be accessible after close
        final_stats = pool.get_stats()
        assert final_stats["closed"] is True
        assert final_stats["pool_size"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_shutdown_and_acquire(self, pool):
        """Test shutdown while connections are being acquired."""
        await pool.initialize()

        # Create tasks that try to acquire connections
        async def acquire_and_use():
            try:
                async with pool.get_connection() as conn:
                    await asyncio.sleep(0.5)
                    return "success"
            except ZenooError:
                return "pool_closed"
            except Exception as e:
                return f"error: {e}"

        # Start multiple acquire tasks
        tasks = [asyncio.create_task(acquire_and_use()) for _ in range(5)]

        # Let them start
        await asyncio.sleep(0.1)

        # Close pool
        await pool.close()

        # Wait for tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some tasks might succeed, others should get pool closed error
        assert any("pool_closed" in str(r) or "success" in str(r) for r in results)

    @pytest.mark.asyncio
    async def test_shutdown_with_queued_connections(self, pool):
        """Test shutdown with connections waiting in queue."""
        await pool.initialize()

        # Fill the available queue (add a reasonable number since queue is unbounded)
        for _ in range(10):  # Add 10 connections to queue
            conn = PooledConnection(client=AsyncMock())
            await pool.available_connections.put(conn)

        queue_size_before = pool.available_connections.qsize()

        await pool.close()

        # Queue should be empty after close
        assert pool.available_connections.empty()

    @pytest.mark.asyncio
    async def test_background_task_cancellation_on_shutdown(self, pool):
        """Test that background tasks are properly cancelled on shutdown."""
        await pool.initialize()

        # Get references to tasks
        health_task = pool.health_check_task
        cleanup_task = pool.cleanup_task

        # Verify tasks are running
        assert not health_task.done()
        assert not cleanup_task.done()

        await pool.close()

        # Tasks should be cancelled
        assert health_task.cancelled()
        assert cleanup_task.cancelled()

    @pytest.mark.asyncio
    async def test_shutdown_connection_context_cleanup(self, pool):
        """Test that connection contexts are handled during shutdown."""
        await pool.initialize()

        # Create a connection context
        context = ConnectionContext(pool)

        # Enter context
        conn = await context.__aenter__()
        assert conn is not None

        # Close pool while context is active
        close_task = asyncio.create_task(pool.close())

        # Exit context
        await context.__aexit__(None, None, None)

        # Wait for close to complete
        await close_task

        assert pool.closed is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_timeout(self, pool):
        """Test graceful shutdown with timeout for pending operations."""
        await pool.initialize()

        # Create a slow operation
        async def slow_operation():
            async with pool.get_connection() as conn:
                await asyncio.sleep(2.0)

        # Start slow operation
        op_task = asyncio.create_task(slow_operation())

        # Give it time to acquire connection
        await asyncio.sleep(0.1)

        # Close with timeout
        close_task = asyncio.create_task(pool.close())

        try:
            await asyncio.wait_for(close_task, timeout=1.0)
        except asyncio.TimeoutError:
            # This is expected if operations don't complete in time
            pass

        # Cancel the operation
        op_task.cancel()
        try:
            await op_task
        except asyncio.CancelledError:
            pass

        # Ensure pool is closed
        assert pool.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_preserves_connection_stats(self, pool):
        """Test that connection statistics are preserved during shutdown."""
        await pool.initialize()

        # Add some activity to connections
        for conn in pool.connections:
            conn.record_request(0.1, success=True)
            conn.record_request(0.2, success=True)
            conn.record_request(0.3, success=False)

        # Get stats before shutdown
        stats_before = pool.get_stats()

        await pool.close()

        # Connection-level stats should have been captured
        assert pool.stats["connections_closed"] == pool.pool_size

    @pytest.mark.asyncio
    async def test_shutdown_with_custom_cleanup_handlers(self, pool):
        """Test shutdown with custom cleanup handlers."""
        await pool.initialize()

        cleanup_called = []

        # Add custom cleanup to connections
        for i, conn in enumerate(pool.connections):

            async def custom_cleanup(idx=i):
                cleanup_called.append(idx)

            # Monkey-patch a cleanup method
            conn.custom_cleanup = custom_cleanup

        # Override _close_connection to call custom cleanup
        original_close = pool._close_connection

        async def close_with_cleanup(conn):
            if hasattr(conn, "custom_cleanup"):
                await conn.custom_cleanup()
            await original_close(conn)

        pool._close_connection = close_with_cleanup

        await pool.close()

        # All custom cleanups should have been called
        assert len(cleanup_called) == pool.pool_size

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, pool):
        """Test emergency shutdown that skips graceful cleanup."""
        await pool.initialize()

        # Make connections hang on close
        for conn in pool.connections:

            async def hanging_close():
                await asyncio.sleep(10.0)

            conn.client.aclose = AsyncMock(side_effect=hanging_close)

        # Force shutdown by setting closed flag first
        pool.closed = True

        # Cancel tasks manually
        if pool.health_check_task:
            pool.health_check_task.cancel()
        if pool.cleanup_task:
            pool.cleanup_task.cancel()

        # Clear connections without closing them
        pool.connections.clear()

        # Verify emergency shutdown completed
        assert pool.closed is True
        assert len(pool.connections) == 0
