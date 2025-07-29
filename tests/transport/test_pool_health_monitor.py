"""
Health monitor tests for the enhanced connection pool.

This module tests the health monitoring functionality including health checks,
unhealthy connection detection, and cleanup of bad connections.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call, Mock
import pytest
import httpx

from zenoo_rpc.transport.pool import (
    ConnectionPool,
    PooledConnection,
    ConnectionState,
    ConnectionStats,
)
from zenoo_rpc.transport.httpx_transport import AsyncTransport
from zenoo_rpc.exceptions import ZenooError


class TestHealthMonitor:
    """Test health monitoring functionality."""

    @pytest.fixture
    async def pool(self):
        """Create a test connection pool."""
        pool = EnhancedConnectionPool(
            base_url="http://test.example.com",
            pool_size=3,
            health_check_interval=5.0,
            max_error_rate=10.0,
        )
        yield pool
        if pool.initialized:
            await pool.close()

    @pytest.mark.asyncio
    async def test_connection_health_check_interval(self):
        """Test that connections are checked at the configured interval."""
        # Create a connection
        mock_client = AsyncMock()
        connection = PooledConnection(client=mock_client)

        # Initially should not need health check
        assert connection.should_health_check(interval=30.0) is False

        # Simulate time passing
        with patch("time.time") as mock_time:
            mock_time.return_value = connection.health_check_at + 31.0
            assert connection.should_health_check(interval=30.0) is True

    @pytest.mark.asyncio
    async def test_connection_health_based_on_error_rate(self):
        """Test connection health determination based on error rate."""
        mock_client = AsyncMock()
        connection = PooledConnection(client=mock_client)

        # Initially healthy
        assert connection.is_healthy(max_error_rate=10.0) is True

        # Add some successful requests
        for _ in range(9):
            connection.record_request(0.1, success=True)

        # Add one failure - should still be healthy (10% error rate)
        connection.record_request(0.1, success=False)
        assert connection.is_healthy(max_error_rate=10.0) is True

        # Add another failure - should be unhealthy (>10% error rate)
        connection.record_request(0.1, success=False)
        assert connection.is_healthy(max_error_rate=10.0) is False

    @pytest.mark.asyncio
    async def test_mark_connection_unhealthy(self):
        """Test marking a connection as unhealthy."""
        mock_client = AsyncMock()
        connection = PooledConnection(client=mock_client)

        assert connection.state != ConnectionState.UNHEALTHY
        assert connection.is_healthy() is True

        connection.mark_unhealthy()

        assert connection.state == ConnectionState.UNHEALTHY
        assert connection.is_healthy() is False

    @pytest.mark.asyncio
    async def test_health_check_loop_runs_periodically(self, pool):
        """Test that health check loop runs at intervals."""
        await pool.initialize()

        # Mock the perform health checks method
        with patch.object(pool, "_perform_health_checks") as mock_health_check:
            # Let the health check loop run for a bit
            await asyncio.sleep(0.1)

            # Should have created the task
            assert pool.health_check_task is not None
            assert not pool.health_check_task.done()

    @pytest.mark.asyncio
    async def test_health_check_with_healthy_connections(self, pool):
        """Test health check with all healthy connections."""
        await pool.initialize()

        # Force all connections to need health check
        for conn in pool.connections:
            conn.health_check_at = 0

        # Mock successful health check responses
        for connection in pool.connections:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            connection.client.get = AsyncMock(return_value=mock_response)

        initial_connection_count = len(pool.connections)
        initial_health_checks = pool.stats["health_checks"]

        # Perform health checks
        await pool._perform_health_checks()

        # All connections should still be present
        assert len(pool.connections) == initial_connection_count

        # Stats should be updated
        assert pool.stats["health_checks"] > initial_health_checks

    @pytest.mark.asyncio
    async def test_health_check_removes_unhealthy_connections(self, pool):
        """Test that health check removes unhealthy connections."""
        await pool.initialize()

        # Make some connections fail health check
        unhealthy_indices = [0, 2]
        for i, connection in enumerate(pool.connections):
            if i in unhealthy_indices:
                # Mock failed health check
                mock_response = AsyncMock()
                mock_response.status_code = 500
                connection.client.get = AsyncMock(return_value=mock_response)
            else:
                # Mock successful health check
                mock_response = AsyncMock()
                mock_response.status_code = 200
                connection.client.get = AsyncMock(return_value=mock_response)

        initial_count = len(pool.connections)

        # Force health check time
        for conn in pool.connections:
            conn.health_check_at = time.time() - 100

        # Perform health checks
        await pool._perform_health_checks()

        # Unhealthy connections should be removed
        assert len(pool.connections) == initial_count - len(unhealthy_indices)

    @pytest.mark.asyncio
    async def test_health_check_with_exception_marks_unhealthy(self, pool):
        """Test that exceptions during health check mark connection as unhealthy."""
        await pool.initialize()

        # Make one connection throw exception during health check
        pool.connections[0].client.get = AsyncMock(
            side_effect=httpx.NetworkError("Network error")
        )

        # Others succeed
        for conn in pool.connections[1:]:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            conn.client.get = AsyncMock(return_value=mock_response)

        # Force health check
        for conn in pool.connections:
            conn.health_check_at = time.time() - 100

        await pool._perform_health_checks()

        # Connection with exception should be removed
        assert len(pool.connections) == 2

    @pytest.mark.asyncio
    async def test_monkeypatch_transport_health_check_failure(self, pool):
        """Test monkeypatching AsyncTransport.health_check to return unhealthy after N calls."""
        await pool.initialize()

        # Counter for tracking calls
        call_count = 0
        unhealthy_after = 3

        async def mock_health_check(self):
            nonlocal call_count
            call_count += 1
            # Return healthy for first N calls, then unhealthy
            return call_count <= unhealthy_after

        # Patch the health check method on AsyncTransport
        with patch.object(AsyncTransport, "health_check", mock_health_check):
            # Mock the aclose method for AsyncTransport as it uses close instead
            async def mock_aclose():
                pass

            # Create new connections with AsyncTransport
            for i in range(len(pool.connections)):
                # Replace httpx client with AsyncTransport
                transport = AsyncTransport(pool.base_url)
                transport.aclose = mock_aclose  # Add aclose method
                pool.connections[i].client = transport

            # Perform multiple health checks
            for _ in range(5):
                # Force all connections to need health check
                for conn in pool.connections:
                    conn.health_check_at = 0

                # Mock the get method to use our patched health_check
                for conn in pool.connections:

                    async def mock_get(url):
                        is_healthy = await conn.client.health_check()
                        response = AsyncMock()
                        response.status_code = 200 if is_healthy else 500
                        return response

                    conn.client.get = mock_get

                await pool._perform_health_checks()
                await asyncio.sleep(0.1)

            # After unhealthy_after calls, connections should start being removed
            assert len(pool.connections) < pool.pool_size

    @pytest.mark.asyncio
    async def test_cleanup_loop_removes_idle_connections(self, pool):
        """Test that cleanup loop removes idle connections."""
        pool.connection_ttl = 1.0  # Short TTL for testing
        await pool.initialize()

        # Mark all connections as idle and old
        initial_time = time.time()
        for conn in pool.connections:
            conn.state = ConnectionState.IDLE
            conn.stats.last_used = initial_time

        initial_count = len(pool.connections)

        # Need to patch time in the pool module, not locally
        with patch("zenoo_rpc.transport.pool.time") as mock_time:
            # Set time to be past TTL
            mock_time.time.return_value = initial_time + 2.0

            # Run cleanup
            await pool._cleanup_connections()

        # Some connections should be removed (but not all due to minimum limit)
        # The cleanup will close at most half of the connections
        assert len(pool.connections) < initial_count
        # And then restore to pool_size
        assert len(pool.connections) == pool.pool_size

    @pytest.mark.asyncio
    async def test_cleanup_maintains_minimum_pool_size(self, pool):
        """Test that cleanup maintains minimum pool size."""
        await pool.initialize()

        # Remove most connections
        while len(pool.connections) > 1:
            await pool._close_connection(pool.connections[0])

        initial_count = len(pool.connections)

        # Run cleanup
        await pool._cleanup_connections()

        # Should have created new connections to maintain pool size
        assert len(pool.connections) == pool.pool_size
        assert len(pool.connections) > initial_count

    @pytest.mark.asyncio
    async def test_acquire_connection_replaces_unhealthy(self, pool):
        """Test that acquiring a connection replaces unhealthy ones."""
        await pool.initialize()

        # Get a connection and mark it unhealthy
        unhealthy_conn = pool.connections[0]
        unhealthy_conn.mark_unhealthy()

        # Put it in the available queue
        await pool.available_connections.put(unhealthy_conn)

        # Mock _close_connection and _create_connection
        closed_connections = []

        async def mock_close(conn):
            closed_connections.append(conn)
            if conn in pool.connections:
                pool.connections.remove(conn)

        new_conn = PooledConnection(client=AsyncMock())

        with patch.object(pool, "_close_connection", side_effect=mock_close):
            with patch.object(pool, "_create_connection", return_value=new_conn):
                # Acquire connection
                acquired = await pool._acquire_connection()

                # Should have closed the unhealthy one
                assert unhealthy_conn in closed_connections

                # Should have gotten the new connection
                assert acquired == new_conn

    @pytest.mark.asyncio
    async def test_connection_statistics_tracking(self):
        """Test that connection statistics are properly tracked."""
        mock_client = AsyncMock()
        connection = PooledConnection(client=mock_client)

        # Initial stats
        assert connection.stats.request_count == 0
        assert connection.stats.error_count == 0
        assert connection.stats.average_response_time == 0.0
        assert connection.stats.error_rate == 0.0

        # Record some requests
        connection.record_request(0.1, success=True)
        connection.record_request(0.2, success=True)
        connection.record_request(0.3, success=False)

        # Check updated stats
        assert connection.stats.request_count == 3
        assert connection.stats.error_count == 1
        assert connection.stats.average_response_time == pytest.approx(0.2)
        assert connection.stats.error_rate == pytest.approx(33.33, rel=0.01)

    @pytest.mark.asyncio
    async def test_pool_statistics_aggregation(self, pool):
        """Test that pool statistics are properly aggregated."""
        await pool.initialize()

        # Add some stats to connections
        for i, conn in enumerate(pool.connections):
            conn.stats.request_count = (i + 1) * 10
            conn.stats.error_count = i
            conn.stats.total_response_time = (i + 1) * 1.0

        stats = pool.get_stats()

        # Check aggregated stats
        assert stats["total_connection_requests"] == 60  # 10 + 20 + 30
        assert stats["total_connection_errors"] == 3  # 0 + 1 + 2
        assert "average_response_time" in stats
        assert "overall_error_rate" in stats

    @pytest.mark.asyncio
    async def test_health_check_updates_connection_timestamp(self, pool):
        """Test that successful health check updates the timestamp."""
        await pool.initialize()

        connection = pool.connections[0]
        old_timestamp = connection.health_check_at

        # Mock successful health check
        mock_response = AsyncMock()
        mock_response.status_code = 200
        connection.client.get = AsyncMock(return_value=mock_response)

        # Force health check
        connection.health_check_at = 0

        await pool._perform_health_checks()

        # Timestamp should be updated
        assert connection.health_check_at > old_timestamp

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, pool):
        """Test that health checks handle concurrent execution properly."""
        pool.pool_size = 10
        await pool.initialize()

        # Mock all connections to have varying response times
        for i, conn in enumerate(pool.connections):

            async def make_delayed_response(delay):
                await asyncio.sleep(delay)
                response = AsyncMock()
                response.status_code = 200
                return response

            conn.client.get = AsyncMock(
                side_effect=lambda url, d=i * 0.01: make_delayed_response(d)
            )
            conn.health_check_at = 0

        # Perform health checks
        start_time = time.time()
        await pool._perform_health_checks()
        duration = time.time() - start_time

        # Should complete relatively quickly (concurrent, not sequential)
        assert duration < 0.5

        # All connections should have been checked
        for conn in pool.connections:
            assert conn.health_check_at > start_time

    @pytest.mark.asyncio
    async def test_release_connection_replaces_old_connections(self, pool):
        """Test that releasing old connections creates replacements (covers lines 368-377)."""
        pool.connection_ttl = 1.0  # Short TTL
        await pool.initialize()

        # Get a connection and use it
        connection = await pool._acquire_connection()

        # Make the connection old by mocking its creation time
        connection.stats.created_at = time.time() - 2.0  # Older than TTL

        initial_count = len(pool.connections)

        # Mock _create_connection to track new connections
        new_connections_created = []
        original_create = pool._create_connection

        async def mock_create():
            conn = await original_create()
            new_connections_created.append(conn)
            return conn

        with patch.object(pool, "_create_connection", side_effect=mock_create):
            # Release the old connection
            await pool._release_connection(connection)

        # Old connection should be closed and replaced
        assert connection not in pool.connections
        assert len(new_connections_created) == 1
        assert len(pool.connections) == initial_count
